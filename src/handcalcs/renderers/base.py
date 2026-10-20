from __future__ import annotations
import datetime
import math
from collections import deque, ChainMap
from dataclasses import dataclass, field
from typing import ClassVar, Callable, Optional, Any
from jinja2 import Template, Environment, DebugUndefined
from handcalcs.parsing.nodes import HcNode
from handcalcs.parsing.sequence import HcSequence

jinja_env = Environment(undefined=DebugUndefined)

# Node type imports only used for typing
from handcalcs.parsing.nodes import (
    HcNode,
    Name,
    Constant,
    Attribute,
    List,
    Dictionary,
    Tuple,
    Set,
)
from handcalcs.parsing.null_values import NoValue
from handcalcs.parsing.operator_nodes import (
    AddOp,
    MultOp,
    SubOp,
    DivOp,
    ModuloOp,
    MatMultOp,
    FloorOp,
    PowOp,
    HcBinOp,
    EqOp,
    GtOp,
    GtEOp,
    LtOp,
    LtEOp,
    NeqOp,
    IsOp,
    IsNotOp,
    InOp,
    NotInOp,
    HcCompOp,
    AndOp,
    OrOp,
    HcBoolOp,
    HcUnaryOp,
)
from handcalcs.parsing.inline_nodes import (
    InlineComment,
    FunctionCall,
    Keyword,
    Compare,
    InlineCommand,
    Comprehension,
    ComprehensionChain,
    IfExp,
)
from handcalcs.parsing.line_nodes import (
    CalcLine,
    ExprLine,
    Import,
    CommentCommand,
    Heading,
    CommentLine,
)
from handcalcs.parsing.block_nodes import (
    IfBlock,
    ElseBlock,
    ElifBlock,
    ForBlock,
    FunctionBlock,
    ParamsBlock,
    CommentsBlock,
    CalcsBlock,
)

RenderHandler = Callable

# The rule sub-categories that may be registered against a particular node type,
# in the order they execute within ``render_node``:
#   pre  -> transform the node before it is rendered (any mode)
#   sym  -> transform the node while ``context.current_mode == 'sym'``
#   num  -> transform the node while ``context.current_mode == 'num'``
#   post -> transform the rendered result (string or list of strings)
RULE_CATEGORIES = ("pre", "sym", "num", "post")

# Operator precedence, shared by ``infix_binop`` (binary operands) and
# ``render_unary_op`` (parenthesizing a unary operator's operand). Unary
# arithmetic operators bind tighter than the binary arithmetic operators but
# looser than exponentiation, hence the 2.5 slot between MultOp (2) and PowOp (3).
UNARY_PRECEDENCE = 2.5
OP_PRECEDENCE = {
    # A conditional expression binds loosest of all, so it is parenthesized as
    # the operand of any operator: ``2 * (a if c else b)``.
    IfExp: -3,
    # Boolean operators bind looser than everything else, with ``or`` looser than
    # ``and`` (Python's precedence). An operand of a bool op is parenthesized only
    # when it binds *looser* than the op itself, so an ``or`` nested inside an
    # ``and`` is parenthesized (``a and (b or c)``) while an ``and`` inside an
    # ``or`` is not (``a and b or c``). Comparisons are absent from this table and
    # so are treated as infinitely tight -- never parenthesized inside a bool op.
    OrOp: -2,
    AndOp: -1,
    AddOp: 1,
    SubOp: 1,
    MultOp: 2,
    DivOp: 2,
    FloorOp: 2,
    ModuloOp: 2,
    MatMultOp: 2,
    HcUnaryOp: UNARY_PRECEDENCE,
    PowOp: 3,
}


# Marks a source line continuation inside a rendered column. ``infix_binop`` emits
# it in place of the space beside an operator that is followed (or preceded) by a
# ``\`` or bracketed line break in the source; ``render_calcline`` splits the
# column on it. It never reaches the final output.
CONTINUATION_MARK = "\x00"

# The rendered form of a ``# hc: --pagebreak`` command: a form feed, which is a
# page break in plain text. Each renderer's join step turns it into its own
# page break (LaTeX ``\newpage``, a CSS ``break-after`` div, a Word page break).
PAGE_BREAK = "\f"

# Comment-command options that act once, where they appear, rather than
# setting the render context for the lines that follow.
ONE_SHOT_COMMANDS = ("line_break", "params_block", "page_break")


def breakable_ops(tree) -> frozenset[int]:
    """
    The ids of the operators in an expression tree whose source line break is
    kept in the rendered output: the ``+``, ``-`` and ``*`` operators on the top
    level of the expression, where a break cannot fall inside a fraction, a power,
    a function call or brackets. A continuation anywhere else renders as one line.
    """
    found: set[int] = set()

    def walk(node) -> None:
        if not isinstance(node, (AddOp, SubOp, MultOp)):
            return
        if node.line_break:
            found.add(id(node))
        pre = OP_PRECEDENCE[type(node)]
        for child, is_right in ((node.left, False), (node.right, True)):
            child_pre = OP_PRECEDENCE.get(type(child), float("inf"))
            # Skip an operand that ``infix_binop`` puts in brackets.
            if child_pre < pre or (
                is_right and child_pre == pre and type(node) is SubOp
            ):
                continue
            walk(child)

    if len(tree) == 1:
        walk(tree[0])
    return frozenset(found)


def _reify(value):
    """
    Wrap a raw runtime Python value in the matching HcNode so it renders through
    the existing node handlers (and their format-code logic). A scalar becomes a
    ``Constant`` marked ``calculated`` (so the format code applies to it);
    ``list``/``tuple``/``set``/``dict`` become the corresponding collection
    node, recursively. An existing HcNode is returned unchanged. This
    keeps all value formatting in one place (``render_constant`` and the
    collection handlers) rather than duplicating it.
    """
    if isinstance(value, HcNode):
        return value
    if isinstance(value, list):
        return List(elems=deque(_reify(v) for v in value))
    if isinstance(value, tuple):
        return Tuple(elems=deque(_reify(v) for v in value))
    if isinstance(value, set):
        return Set(elems=deque(_reify(v) for v in value))
    if isinstance(value, dict):
        return Dictionary(
            keys=deque(_reify(k) for k in value.keys()),
            values=deque(_reify(v) for v in value.values()),
        )
    return Constant(value=value, calculated=True)


def _copy_rule_handlers(
    src: dict[str, dict[str, list[Callable]]],
) -> dict[str, dict[str, list[Callable]]]:
    """Deep-ish copy of the ``{node_type: {category: [fn, ...]}}`` rule store."""
    return {
        node_type: {category: list(fns) for category, fns in categories.items()}
        for node_type, categories in src.items()
    }


class ContextValueError(Exception):
    pass


# The columns a calc line can show, in order: assignment target, symbolic,
# numeric substitution and result. ``context.mode`` is ``'full'`` (all of them),
# a string naming the columns to keep (e.g. ``'ass sym res'``), or one or more
# drop aliases naming the columns to remove (e.g. ``'no_num'``).
MODE_COLUMNS = ("ass", "sym", "num", "res")
MODE_DROP_ALIASES = {
    "no_num": "num",
    "drop_numeric": "num",
    "no_sym": "sym",
    "drop_symbolic": "sym",
}


def mode_columns(mode: str) -> set[str]:
    """
    Return the set of calc-line columns shown under ``mode``.

    ``'full'`` shows every column. If the mode contains a drop alias
    (``no_num``/``drop_numeric``, ``no_sym``/``drop_symbolic``), every column
    except the dropped ones is shown, e.g. ``'no_num'`` -> ``{'ass', 'sym',
    'res'}``. Otherwise the mode names the columns to keep, matched as
    substrings (``'ass sym res'``). The aliases are checked first because they
    contain ``num``/``sym`` themselves.
    """
    if mode == "full":
        return set(MODE_COLUMNS)
    tokens = mode.replace(",", " ").split()
    dropped = {
        MODE_DROP_ALIASES[token] for token in tokens if token in MODE_DROP_ALIASES
    }
    if dropped:
        return set(MODE_COLUMNS) - dropped
    return {column for column in MODE_COLUMNS if column in mode}


class ContextKeyError(Exception):
    pass


class RenderContext:
    def __init__(
        self,
        space: str = " ",
        newline: str = "\n",
        indent: str = "    ",
        assign: str = "=",
        mode: str = "full",
        format_code: str = ".5g",
        param_line: bool = False,
        lpar="(",
        rpar=")",
        **kwargs,
    ):
        self.space = space
        self.newline = newline
        self.indent = indent
        self.assign = assign
        self.mode = mode
        self.format_code = format_code
        self.param_line = param_line
        self.lpar = lpar
        self.rpar = rpar

        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def sparse(cls, **kwargs) -> "RenderContext":
        """
        Build a context that carries *only* the given attributes, with no defaults.

        This is the line-scoped layer of a ``BaseRenderContext``: because it holds
        only explicitly-set overrides, ``BaseRenderContext.current`` (a ChainMap of
        line over global) falls through to the global context for every key the
        line does not override. A full ``RenderContext()`` here would instead
        shadow the global context with its own defaults.
        """
        obj = cls.__new__(cls)
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

    def __repr__(self):
        attrs = [
            f"{k}={v}"
            for k, v in self.__dict__.items()
            if not k.startswith("_") and k.islower()
        ]
        repr_attrs = ", ".join(attrs)
        return f"{__class__.__name__}({repr_attrs})"

    def __or__(self, other):
        if not isinstance(other, self.__class__):
            raise ValueError(
                f"Can only union between two RenderContexts, not {type(other)}."
            )
        else:
            return RenderContext(**(self.__dict__ | other.__dict__))


class BaseRenderContext:
    def __init__(self, global_context: RenderContext, line_context: RenderContext):

        self.global_context = global_context
        self.line_context = line_context

    @property
    def current(self):
        return RenderContext(
            **ChainMap(self.line_context.__dict__, self.global_context.__dict__)
        )


# Registry mapping a renderer's 'name' to its class. Populated automatically as
# renderer subclasses are defined (see BaseRenderer.__init_subclass__) and used to
# resolve the 'default_renderer' global config option to a class.
_RENDERER_REGISTRY: dict[str, "type[BaseRenderer]"] = {}


def get_renderer(name: str) -> "Optional[type[BaseRenderer]]":
    """
    Return the renderer class registered under 'name', or None if no renderer
    with that name has been defined/imported.
    """
    return _RENDERER_REGISTRY.get(name)


class BaseRenderer:
    name: ClassVar[str] = "base"
    node_handlers: ClassVar[dict[str, Callable]] = {}
    header_handlers: ClassVar[dict[str, Callable]] = {}
    # Rules keyed by node type, then by category ('pre'/'sym'/'num'/'post'),
    # each an ordered list executed in registration order. The node type is the
    # master category and the pre/sym/num/post are the sub-categories (mirroring
    # the 'header:{node_type}' block-header registration). The pseudo node type
    # 'root' carries the sequence-level pre/post renderers.
    rule_handlers: ClassVar[dict[str, dict[str, list[Callable]]]] = {}
    # Leads the value of a continuation row (a line continued from the source) in
    # a calc grid, indenting it past the start of the expression above.
    CONTINUATION_INDENT: ClassVar[str] = "  "
    # Split a leading Greek name from an identifier component when an uppercase
    # letter or digit follows it (``DeltaH`` -> ΔH); see ``identifiers.py``.
    GREEK_PREFIXES: ClassVar[bool] = True
    # How several ``_`` subscripts are shown: ``"comma"`` (``N_pl_Rd`` ->
    # N with subscript "pl,Rd") or ``"nested"`` (``x_a_b`` -> x_{a_{b}}). The
    # ``subscripts`` render-context field overrides it.
    SUBSCRIPT_STYLE: ClassVar[str] = "comma"
    # The keywords of a conditional expression (``a if test else b``), with
    # their surrounding spaces; see ``render_if_exp``.
    IF_EXP_KEYWORDS: ClassVar[tuple[str, str]] = (" if ", " else ")
    # The keywords of a comprehension clause (``for t in ts``), with their
    # surrounding spaces; see ``render_comprehension``.
    COMPREHENSION_KEYWORDS: ClassVar[tuple[str, str]] = (" for ", " in ")

    def __init__(self) -> None:
        self._handlers: dict[str, Callable] = dict(self.node_handlers)
        self._header_handlers: dict[str, Callable] = dict(self.header_handlers)
        self._rule_handlers: dict[str, dict[str, list[Callable]]] = _copy_rule_handlers(
            self.rule_handlers
        )

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.node_handlers = dict(cls.node_handlers)
        cls.header_handlers = dict(cls.header_handlers)
        cls.rule_handlers = _copy_rule_handlers(cls.rule_handlers)
        # Auto-register the renderer under its 'name' so that a renderer can be
        # looked up by name (e.g. the 'default_renderer' global config option).
        # Only register when the subclass declares its own 'name' -- an inherited
        # name must not clobber the parent's registry entry (e.g. an anonymous
        # BaseRenderer subclass would otherwise overwrite 'base').
        name = cls.__dict__.get("name")
        if name:
            _RENDERER_REGISTRY[name] = cls

    def create_context(self, **kwargs) -> RenderContext:
        return BaseRenderContext(RenderContext(**kwargs), RenderContext.sparse())

    def render(
        self, node: HcNode, base_context: Optional[BaseRenderContext] = None
    ) -> str:
        """
        Render a node.

        If 'context' is None, a new context is created.
        """
        if base_context is None:
            base_context = self.create_context()
        if node.type == "root":
            return self.render_root(node, base_context)
        return self.render_node(node, base_context)

    def render_root(self, root: HcSequence, base_context: BaseRenderContext) -> list:
        """
        Render an HcSequence (root node) into the master list.

        The sequence-level pre/post renderers are registered against the pseudo
        node type 'root' (i.e. 'root:pre' and 'root:post'); they run before and
        after the sequence body and contribute leading/trailing items.
        """
        root_rules = self._rule_handlers.get("root", {})
        parts = [pre(self, root, base_context) for pre in root_rules.get("pre", [])]
        for node in root.sequence:
            parts.append(self.render(node, base_context))
        parts.extend(
            post(self, root, base_context) for post in root_rules.get("post", [])
        )
        return parts

    def complete(self, tree: list, base_context: BaseRenderContext) -> Any:
        """
        A function called at the completion of every render. This function is intended
        to be over-ridden by individual renderers in order to "complete" the rendering.

        The BaseRenderer that all renderers inherit from includes a special ".join" method
        with the same function signature as this one. For many renderers that return a str,
        calling the .join() method will be sufficient as the implementation for this function.
        """
        # Example implementation:
        # completed = self.join(tree, base_context)
        # return completed
        # BaseRenderer intentionally returns just `tree`; text renderers
        # (PlainTextRenderer, HTMLRenderer) override this to join into a str.
        return tree

    def join(self, tree: list, base_context: Optional[BaseRenderContext] = None) -> str:
        """
        Join a rendered nested-list structure into final text.

        This is the post-render pass that inserts the spacing, indentation and
        newlines that the node handlers deliberately leave out:

        - a string item is a whole line (heading, comment, block header);
        - an all-string list is a rendered line whose components are joined by a
          single space;
        - a ``[header_string, body_list]`` list is a block: the header is a line
          at the current depth and the body lines are rendered one level deeper.

        Falsy items (``None``, ``""``, ``[]``) render nothing (they are
        command/ignored lines), so they never produce a stray blank line.

        ``base_context`` is optional: callers that just want text from a tree
        (tests, ``demo()`` post-processing) can omit it and get a default context.
        """
        if base_context is None:
            base_context = self.create_context()
        return "".join(self.join_items(tree, 0, base_context))

    def join_items(
        self, items: list, depth: int, base_context: BaseRenderContext
    ) -> list[str]:
        lines: list[str] = []
        for item in items:
            lines.extend(self.join_item(item, depth, base_context))
        return lines

    def join_item(self, item, depth: int, base_context: BaseRenderContext) -> list[str]:
        if not item:
            return []
        context = base_context.current
        indent = context.indent * depth
        nl = context.newline
        if isinstance(item, str):
            # A one-shot line-break directive renders as a bare newline; it is
            # already a complete blank line, so don't append another newline
            # (which would produce a double blank line).
            if item and not item.strip("\n"):
                return [item]
            # A multi-line string (e.g. a rendered params grid) is indented line
            # by line so it sits at the correct depth inside a nested block.
            if nl in item:
                return [f"{indent}{line}{nl}" for line in item.split(nl)]
            return [f"{indent}{item}{nl}"]
        # A block is ``[header_string, body_list]`` -- detected by its body being
        # a list. An all-string list is a rendered line.
        if isinstance(item[-1], list):
            header, body = item[0], item[-1]
            # A headerless (flat) block -- e.g. a CommentsBlock/CalcsBlock, which
            # only groups consecutive lines and introduces no intro line -- emits
            # no header and keeps its body at the current depth rather than
            # indenting it one level deeper.
            if not (isinstance(header, str) and header.strip()):
                return self.join_items(body, depth, base_context)
            lines = [f"{indent}{header}{nl}"]
            lines.extend(self.join_items(body, depth + 1, base_context))
            return lines
        joined = context.space.join(item)
        # An all-string line whose columns are all empty carries no content --
        # e.g. an ignored (`# hc: -i`) line renders to '' and is wrapped as
        # [''] by the block body. Emitting it would add a stray blank line, so
        # it renders nothing (like the falsy items filtered at the top).
        if not joined:
            return []
        return [f"{indent}{joined}{nl}"]

    def render_node(self, node: HcNode, base_context: BaseRenderContext) -> str:
        """
        Render one node with an existing context.

        Rules registered against this node type run in category order: 'pre'
        (always), then 'sym' or 'num' gated on ``context.current_mode``, then the
        node handler, then 'post' on the rendered result. Multiple rules in a
        category run in registration order.
        """
        # A raw runtime value (e.g. a Name/Attribute's captured value) has no
        # ``type`` discriminant, so it is wrapped in the matching HcNode and
        # rendered through the existing handlers, picking up the format code
        # (scalars and collection elements alike). Anything already carrying a
        # ``type`` (any node instance) passes through unchanged.
        if not hasattr(node, "type"):
            node = _reify(node)
        node_rules = self._rule_handlers.get(node.type, {})
        current_mode = getattr(base_context.current, "current_mode", None)

        for rule in node_rules.get("pre", []):
            node = rule(self, node, base_context)
        if current_mode == "sym":
            for rule in node_rules.get("sym", []):
                node = rule(self, node, base_context)
        elif current_mode == "num":
            for rule in node_rules.get("num", []):
                node = rule(self, node, base_context)

        handler = self._handlers.get(node.type)
        if handler is None:
            raise NotImplementedError(
                f"A handler for node type = '{node.type}' has not been registered in this renderer."
            )
        rendered = handler(self, node, base_context)

        for rule in node_rules.get("post", []):
            rendered = rule(self, rendered, node, base_context)
        return rendered

    def render_header(self, node: HcNode, base_context: BaseRenderContext) -> str:
        """
        Render the introductory/context-establishing header line for a block node.

        Dispatches to the handler registered under 'header:{node.type}'. Block
        nodes with no registered header handler render no header (empty string),
        letting a renderer opt in per block type.
        """
        handler = self._header_handlers.get(node.type)
        if handler is None:
            return ""
        return handler(self, node, base_context)

    @staticmethod
    def _route_registration(
        node_classifier: str,
        handler: Callable,
        node_handlers: dict,
        header_handlers: dict,
        rule_handlers: dict,
    ) -> None:
        """
        Route a registration to the right store based on its classifier:

        - ``header:{node_type}`` -> the block-header handler for that node type;
        - ``{node_type}:{category}`` where category is one of pre/sym/num/post ->
          appended to that node type's ordered rule list for that category
          (the pseudo node type 'root' carries the sequence pre/post renderers);
        - a bare name -> the node handler for that node type.
        """
        if ":" in node_classifier and node_classifier.count(":") == 1:
            left, right = node_classifier.split(":")
            if left == "header":
                # 'header:{node_type}' registers the header handler for a block
                # node, keyed by the node's type (e.g. 'if_block').
                header_handlers[right] = handler
            elif right in RULE_CATEGORIES:
                rule_handlers.setdefault(left, {}).setdefault(right, []).append(handler)
            else:
                raise NotImplementedError(
                    f"Cannot register a method for {node_classifier}.\n"
                    "Node classifiers must be either in the form of "
                    "'{node_type}:{category}' where {category} is one of: "
                    f"{', '.join(RULE_CATEGORIES)}, or 'header:{{node_type}}'\n-or-\n"
                    "the node classifier must be the name of a recognized HcNode (in snake_case)."
                )
        else:
            node_handlers[node_classifier] = handler

    @classmethod
    def register(cls, node_classifier: str) -> Callable[[Callable], Callable]:
        """
        Register a render handler (or a pre/sym/num/post/header rule) for a given
        node classifier, at the class level. See ``_route_registration``.
        """

        def decorator(handler: Callable) -> Callable:
            cls._route_registration(
                node_classifier,
                handler,
                cls.node_handlers,
                cls.header_handlers,
                cls.rule_handlers,
            )
            return handler

        return decorator

    def register_handler(self, node_classifier: str, handler: RenderHandler) -> None:
        """Instance-scoped counterpart of ``register``. See ``_route_registration``."""
        self._route_registration(
            node_classifier,
            handler,
            self._handlers,
            self._header_handlers,
            self._rule_handlers,
        )

    def render_unknown(self, node: HcNode, base_context: BaseRenderContext) -> str:
        return str(node)

    def leading_sign(self, rendered: str) -> bool:
        """
        True if a rendered operand starts with a ``-`` or ``+`` sign (e.g. a
        negative value substituted in the numeric column), so the operator
        handlers parenthesize it: ``7·(-3)``, ``(-10.423)²``, ``-(-3)``.

        A renderer whose output wraps the text in markup (e.g. the Word
        renderer's OMML runs) overrides this to look past the markup.
        """
        return rendered.lstrip().startswith(("-", "+"))

    def format_param_grid(self, rows: list, base_context: BaseRenderContext) -> str:
        """
        Format a params grid (``rows`` of cells, each cell already rendered to a
        list of components like ``["f", "=", "1"]``, or ``None`` for padding) into
        the final text block.

        The base implementation is plain-text oriented: cell components are joined
        by the context space, columns are left-justified to a shared per-column
        width, columns are separated by a gap and rows by the context newline.
        Renderers that emit tabular markup (LaTeX array, HTML table) override this.
        """
        context = base_context.current
        _ = context.space
        nl = context.newline

        def parts(cell) -> list[str]:
            # [id, eq, value, comment]; a missing component is an empty string.
            if cell is None:
                return ["", "", "", ""]
            if isinstance(cell, (list, tuple, deque)):
                return ([str(part) for part in cell] + ["", "", "", ""])[:4]
            return [str(cell), "", "", ""]

        grid = [[parts(cell) for cell in row] for row in rows]
        ncols = max((len(row) for row in grid), default=0)
        # One width per (cell column, component) so identifiers right-align and the
        # ``=`` signs line up down each column, as in the LaTeX ``aligned`` grid.
        widths = [
            [
                max((len(row[c][k]) for row in grid if c < len(row)), default=0)
                for k in range(4)
            ]
            for c in range(ncols)
        ]
        gap = _ * 4  # between cells; wider than the single space before a comment
        lines = []
        for row in grid:
            texts = []
            for c, (ident, eq, val, comment) in enumerate(row):
                w = widths[c]
                text = f"{ident.rjust(w[0])}{_}{eq}{_}{val.ljust(w[2])}"
                if w[3]:
                    text += f"{_}{comment.ljust(w[3])}"
                texts.append(text)
            lines.append(gap.join(texts).rstrip())
        return nl.join(lines)

    def format_calc_grid(self, rows: list, base_context: BaseRenderContext) -> str:
        """
        Format a multi-line ("long") calc. ``rows`` are ``[id, eq, value]`` triples:
        the first carries the assignment target, the rest an empty id so every row
        aligns on ``eq``. A row with an empty ``eq`` continues the value of the row
        above (a line continuation in the source) and is indented by
        ``CONTINUATION_INDENT``.

        The base implementation is plain-text oriented: the id column is padded to a
        common width so the ``=`` signs line up, and rows are joined by the context
        newline. Renderers that emit tabular markup (HTML table, LaTeX aligned)
        override this.
        """
        context = base_context.current
        _ = context.space
        nl = context.newline
        id_width = max((len(str(ident)) for ident, _eq, _val in rows), default=0)
        lines = []
        for ident, eq, val in rows:
            padded_id = str(ident).ljust(id_width)
            if not eq:
                eq = " " * len(context.assign)
                val = f"{self.CONTINUATION_INDENT}{val}"
            lines.append(f"{padded_id}{_}{eq}{_}{val}".rstrip())
        return nl.join(lines)


## Register BaseRenderer basic node implementations

BR = BaseRenderer
BRC = RenderContext


@BaseRenderer.register("no_value")
def render_novalue(
    renderer: BaseRenderer, node: Constant, base_context: BaseRenderContext
) -> str:
    return ""


def is_source_number(node: Constant) -> bool:
    """True if ``node`` is a number literal written in the source."""
    return (
        not node.calculated
        and bool(node.source_text)
        and isinstance(node.value, (int, float, complex))
        and not isinstance(node.value, bool)
    )


def literal_text(node: Constant) -> str:
    """A number literal's source text without digit-grouping underscores."""
    return node.source_text.replace("_", "")


@BaseRenderer.register("constant")
def render_constant(
    renderer: BaseRenderer, node: Constant, base_context: BaseRenderContext
) -> Any:
    context = base_context.current
    fc = context.format_code
    # bool is an int subclass, so a numeric format code would render True as 1.
    if isinstance(node.value, bool):
        return f"{node.value}"
    # Dates and times pass a format spec to strftime, so a number format code
    # such as '.5g' would render literally instead of the value.
    if isinstance(node.value, (datetime.date, datetime.time)):
        return f"{node.value}"
    # A number literal from the source is shown as written: the format code is
    # for calculated values (substitutions and results), not the formula's own
    # coefficients and exponents.
    if is_source_number(node):
        return literal_text(node)
    if isinstance(node.value, float) and math.isinf(node.value):
        return "-∞" if node.value < 0 else "∞"
    try:
        return f"{node.value:{fc}}"
    except (ValueError, TypeError):  # Format code not implemented / not a scalar
        return f"{node.value}"


@BaseRenderer.register("list")
def render_list(
    renderer: BaseRenderer, node: List, base_context: BaseRenderContext
) -> Any:
    context = base_context.current
    _ = context.space
    rendered_elems = [renderer.render(elem, base_context) for elem in node.elems]
    return f"[{f',{_}'.join(rendered_elems)}]"


@BaseRenderer.register("set")
def render_list(
    renderer: BaseRenderer, node: Set, base_context: BaseRenderContext
) -> Any:
    context = base_context.current
    _ = context.space
    rendered_elems = [renderer.render(elem, base_context) for elem in node.elems]
    return f"{{{f',{_}'.join(rendered_elems)}}}"


@BaseRenderer.register("dictionary")
def render_list(
    renderer: BaseRenderer, node: Dictionary, base_context: BaseRenderContext
) -> Any:
    rendered_keys = [renderer.render(elem, base_context) for elem in node.keys]
    rendered_values = [renderer.render(elem, base_context) for elem in node.values]
    context = base_context.current
    _ = context.space
    rkv = zip(rendered_keys, rendered_values)
    items = [f":{_}".join(item) for item in rkv]
    return f"{{{f',{_}'.join(items)}}}"


@BaseRenderer.register("tuple")
def render_list(
    renderer: BaseRenderer, node: Tuple, base_context: BaseRenderContext
) -> Any:
    context = base_context.current
    _ = context.space
    rendered_elems = [renderer.render(elem, base_context) for elem in node.elems]
    return f"({f',{_}'.join(rendered_elems)})"


@BaseRenderer.register("inline_comment:pre")
@BaseRenderer.register("comment_line:pre")
@BaseRenderer.register("heading:pre")
def interpolate_jinja_strings(
    renderer: BaseRenderer,
    node: Union[InlineComment, CommentLine, Heading],
    base_context: BaseRenderContext,
) -> str:
    context = base_context.current
    if hasattr(context, "global_ns"):
        template = jinja_env.from_string(node.content)
        jinja_rendered = template.render(context.global_ns)
        node.content = jinja_rendered
    return node


@BaseRenderer.register("inline_comment")
def render_inline_comment(
    renderer: BaseRenderer, node: InlineComment, base_context: BaseRenderContext
) -> str:
    context = base_context.current
    return f"{context.lpar}{node.content}{context.rpar}"


@BaseRenderer.register("name")
def render_name(
    renderer: BaseRenderer, node: Name, base_context: BaseRenderContext
) -> str:
    context = base_context.current
    if not hasattr(context, "current_mode"):
        raise ContextKeyError(
            f"Attempting to render the Name node while context does not have a 'current_mode' key.\n"
            f"{context=}"
        )
    if context.current_mode == "sym":
        return node.identifier
    elif context.current_mode == "num":
        # The value may be a raw scalar or a collection; render_node reifies it
        # into the matching node so each element picks up the format code.
        return renderer.render_node(node.value, base_context)
    else:
        raise ContextValueError(
            f"The context.current_mode has an unrecognized value: {context.current_mode}"
        )


@BaseRenderer.register("attribute")
def render_attribute(
    renderer: BaseRenderer, node: Attribute, base_context: BaseRenderContext
) -> str:
    """
    Render an attribute access (e.g. ``math.pi``).

    Mirrors ``render_name``: the symbolic form is ``namespace.identifier`` (the
    ``__main__`` namespace is suppressed); the numeric form renders the captured
    value, falling back to the symbolic form when no value was captured.
    """
    context = base_context.current
    if not hasattr(context, "current_mode"):
        raise ContextKeyError(
            f"Attempting to render the Attribute node while context does not have a 'current_mode' key.\n"
            f"{context=}"
        )
    namespace = node.namespace
    if namespace in ("", "__main__", None):
        symbolic = node.identifier
    else:
        symbolic = f"{namespace}.{node.identifier}"
    if context.current_mode == "sym":
        return symbolic
    elif context.current_mode == "num":
        if isinstance(node.value, NoValue):
            # No runtime value was captured; fall back to the symbolic form.
            return symbolic
        # The value may be a raw scalar or a collection; render_node reifies it
        # into the matching node so each element picks up the format code.
        return renderer.render_node(node.value, base_context)
    else:
        raise ContextValueError(
            f"The context.current_mode has an unrecognized value: {context.current_mode}"
        )


@BaseRenderer.register("add_op")
def render_add_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    as_infix = infix_binop(node, renderer, True, base_context)
    return f"{node.pre}{as_infix}{node.post}"


@BaseRenderer.register("sub_op")
def render_sub_op(renderer: BR, node: SubOp, base_context: BaseRenderContext) -> str:
    as_infix = infix_binop(node, renderer, True, base_context)
    return f"{node.pre}{as_infix}{node.post}"


@BaseRenderer.register("mult_op")
def render_mult_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    as_infix = infix_binop(node, renderer, True, base_context)
    return f"{node.pre}{as_infix}{node.post}"


@BaseRenderer.register("div_op")
def render_div_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    as_infix = infix_binop(node, renderer, True, base_context)
    return f"{node.pre}{as_infix}{node.post}"


@BaseRenderer.register("floor_op")
def render_floor_op(
    renderer: BR, node: FloorOp, base_context: BaseRenderContext
) -> str:
    as_infix = infix_binop(node, renderer, True, base_context)
    return f"{node.pre}{as_infix}{node.post}"


@BaseRenderer.register("mat_mult_op")
@BaseRenderer.register("modulo_op")
def render_modulo_op(
    renderer: BR, node: ModuloOp, base_context: BaseRenderContext
) -> str:
    as_infix = infix_binop(node, renderer, True, base_context)
    return f"{node.pre}{as_infix}{node.post}"


@BaseRenderer.register("pow_op")
def render_pow_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    as_infix = infix_binop(node, renderer, True, base_context)
    return f"{node.pre}{as_infix}{node.post}"


@BaseRenderer.register("unary_op")
def render_unary_op(
    renderer: BR, node: HcUnaryOp, base_context: BaseRenderContext
) -> str:
    context = base_context.current
    rendered = renderer.render_node(node.operand, base_context)
    # Parenthesize the operand when it is a binary operator that binds looser
    # than the unary operator (e.g. -(a + b)); tighter operands such as a name, a
    # constant or a power (-a**b) need no parentheses. Also parenthesize a +/-
    # operand that renders with a leading sign so a numeric substitution reads as
    # -(-10.423) rather than the ambiguous --10.423.
    operand_pre = OP_PRECEDENCE.get(type(node.operand), float("inf"))
    needs_parens = operand_pre < UNARY_PRECEDENCE
    # Python's `not` binds looser than a comparison, so `not (a < b)` parses with
    # no parens in the AST. Re-add them: `not a < b` reads as `(not a) < b`.
    if isinstance(node.operand, (Compare, HcBoolOp)):
        needs_parens = True
    if node.symbol in ("-", "+") and renderer.leading_sign(rendered):
        needs_parens = True
    if needs_parens:
        rendered = f"{context.lpar}{rendered}{context.rpar}"
    return f"{node.pre}{node.symbol}{rendered}{node.post}"


@BaseRenderer.register("gt_op")
def render_gt_op(renderer: BR, node: GtOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"


@BaseRenderer.register("gte_op")
def render_gte_op(renderer: BR, node: GtEOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"


@BaseRenderer.register("lt_op")
def render_lt_op(renderer: BR, node: LtOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"


@BaseRenderer.register("lte_op")
def render_lte_op(renderer: BR, node: LtEOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"


@BaseRenderer.register("eq_op")
def render_eq_op(renderer: BR, node: EqOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"


@BaseRenderer.register("neq_op")
def render_neq_op(renderer: BR, node: NeqOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"


@BaseRenderer.register("is_op")
def render_is_op(renderer: BR, node: IsOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"


@BaseRenderer.register("is_not_op")
def render_is_not_op(
    renderer: BR, node: IsNotOp, base_context: BaseRenderContext
) -> str:
    return f"{node.symbol}"


@BaseRenderer.register("in_op")
def render_in_op(renderer: BR, node: InOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"


@BaseRenderer.register("not_in_op")
def render_not_in_op(
    renderer: BR, node: NotInOp, base_context: BaseRenderContext
) -> str:
    return f"{node.symbol}"


@BaseRenderer.register("and_op")
def render_and_op(renderer: BR, node: AndOp, base_context: BaseRenderContext) -> str:
    return infix_boolop(node, renderer, base_context)


@BaseRenderer.register("or_op")
def render_or_op(renderer: BR, node: OrOp, base_context: BaseRenderContext) -> str:
    return infix_boolop(node, renderer, base_context)


@BaseRenderer.register("compare")
def render_compare(renderer: BR, node: Compare, base_context: BaseRenderContext) -> str:
    acc = [renderer.render(elem, base_context) for elem in node.comparison]
    return f"".join(acc)


@BaseRenderer.register("function_call:pre")
def set_function_call_parens(
    renderer: BR, node: FunctionCall, base_context: BaseRenderContext
) -> FunctionCall:
    """
    Default a function call's argument delimiters to the context's lpar/rpar.

    Only fills in a delimiter that is still empty, so a renderer's own
    'function_call:pre' rule (which runs after this one) remains free to set
    something else (e.g. LaTeX's ``\\sqrt{...}``).
    """
    context = base_context.current
    # An emptied function name marks a call a renderer rule has already set
    # in its own notation (e.g. a postfix factorial, ``n!``, with no ``pre``).
    if getattr(node.function_name, "identifier", None) == "":
        return node
    if not node.pre:
        node.pre = context.lpar
    if not node.post:
        node.post = context.rpar
    return node


# The radical sign of each root function, for the text renderers.
ROOT_SYMBOLS = {"sqrt": "√", "cbrt": "∛"}

# The namespaces of a call whose function name is read as a maths function
# (``cbrt``, ``factorial``): none, or a maths module.
MATH_CALL_NAMESPACES = ("", "__main__", "math", "cmath", "numpy", "np", "scipy.special")


def math_call_name(node: FunctionCall) -> Optional[str]:
    """
    The function name of a call to a bare or maths-module function
    (``cbrt(x)``, ``math.factorial(n)``), or None for a method or another
    module's function.
    """
    namespace = node.namespace
    if namespace and not isinstance(namespace, Name):
        return None
    identifier = getattr(namespace, "identifier", "") if namespace else ""
    if identifier not in MATH_CALL_NAMESPACES:
        return None
    return getattr(node.function_name, "identifier", None)


def is_atom(node) -> bool:
    """True if ``node`` needs no brackets before a postfix operator (``n!``)."""
    return isinstance(node, (Name, Constant, Attribute, FunctionCall))


def postfix_factorial(node: FunctionCall, lpar: str, rpar: str, bang: str = "!"):
    """
    Set a ``factorial(n)`` call as the postfix ``n!``, bracketing an argument
    that is not an atom: ``(n + 1)!``. The function name and namespace are
    emptied, which keeps the rule from applying twice.
    """
    wrap = not (len(node.args) == 1 and is_atom(node.args[0]))
    node.namespace = deque()
    node.function_name = Name(identifier="", value="")
    node.pre = lpar if wrap else ""
    node.post = f"{rpar}{bang}" if wrap else bang
    return node


@BaseRenderer.register("function_call")
def render_function_call(
    renderer: BR, node: FunctionCall, base_context: BaseRenderContext
) -> str:
    context = base_context.current
    function_name = renderer.render(node.function_name, base_context)
    # Check for the '__main__' namespace before rendering it: a renderer's
    # 'name:sym' rules (e.g. subscript swaps) would otherwise mangle the
    # identifier and the suppression would never match. An empty namespace
    # (e.g. one a renderer rule has cleared) also renders nothing.
    if not node.namespace or getattr(node.namespace, "identifier", None) == "__main__":
        namespace = ""
    else:
        namespace = renderer.render(node.namespace, base_context)
        if receiver_needs_parens(node.namespace):
            namespace = f"{context.lpar}{namespace}{context.rpar}"
    args = [renderer.render(arg, base_context) for arg in node.args]
    arg_str = f",{context.space}".join(args)
    if namespace:
        rendered = f"{namespace}.{function_name}{node.pre}{arg_str}{node.post}"
    else:
        rendered = f"{function_name}{node.pre}{arg_str}{node.post}"
    return rendered


def receiver_needs_parens(namespace) -> bool:
    """
    True if the receiver of a method call is an expression that must be
    parenthesized before the ``.``, as in ``(a * b).to("mm")``. A name, call or
    collection is not.
    """
    return isinstance(namespace, (HcBinOp, HcBoolOp, HcUnaryOp, Compare, IfExp))


@BaseRenderer.register("if_exp")
def render_if_exp(renderer: BR, node: IfExp, base_context: BaseRenderContext) -> str:
    """
    A conditional expression, ``body if test else orelse``, with the keywords
    from the renderer's ``IF_EXP_KEYWORDS``. A conditional expression as the
    body or test is parenthesized; one as the ``orelse`` chains without them,
    as in Python.
    """
    context = base_context.current
    if_kw, else_kw = renderer.IF_EXP_KEYWORDS

    def part(child, wrap: bool) -> str:
        rendered = renderer.render_node(child, base_context)
        if wrap and isinstance(child, IfExp):
            return f"{context.lpar}{rendered}{context.rpar}"
        return rendered

    body = part(node.body, True)
    test = part(node.test, True)
    orelse = part(node.orelse, False)
    return f"{body}{if_kw}{test}{else_kw}{orelse}"


@BaseRenderer.register("keyword")
def render_keyword(renderer: BR, node: Keyword, base_context: BaseRenderContext) -> str:
    """A keyword argument, ``arg=value``, or ``**value`` for a mapping unpacking."""
    value = renderer.render(node.value, base_context)
    if node.arg is None:
        return f"**{value}"
    return f"{node.arg}={value}"


@BaseRenderer.register("comprehension")
def render_comprehension(
    renderer: BR, node: Comprehension, base_context: BaseRenderContext
) -> str:
    """
    Render a single ``for ... in ...`` clause of a comprehension, with the
    keywords (and their spaces) from the renderer's ``COMPREHENSION_KEYWORDS``.
    """
    for_kw, in_kw = renderer.COMPREHENSION_KEYWORDS
    targets = ", ".join(
        renderer.render(target, base_context) for target in node.assigns
    )
    iterator = "".join(renderer.render(part, base_context) for part in node.iterator)
    if node.is_async:
        for_kw = for_kw.replace("for", "async for")
    return f"{for_kw}{targets}{in_kw}{iterator}"


@BaseRenderer.register("comprehension_chain")
def render_comprehension_chain(
    renderer: BR, node: ComprehensionChain, base_context: BaseRenderContext
) -> str:
    """
    Render a list/set/dict/generator comprehension (best-guess).

    Comprehension internals are loop-scoped and have no substitutable runtime
    value, so they are rendered symbolically in both the symbolic and numeric
    columns; the surrounding brackets follow the comprehension kind.
    """
    prev_mode = getattr(base_context.line_context, "current_mode", None)
    base_context.line_context.current_mode = "sym"
    context = base_context.current
    _ = context.space
    try:
        if node.comp_type == "dict":
            key = "".join(renderer.render(part, base_context) for part in node.key)
            value = "".join(renderer.render(part, base_context) for part in node.value)
            head = f"{key}: {value}"
        else:
            head = "".join(renderer.render(part, base_context) for part in node.assign)
        # Each clause starts with its own spaced ``for`` keyword.
        clauses = "".join(
            renderer.render(comp, base_context) for comp in node.comprehensions
        )
        inner = f"{head}{clauses}".strip()
    finally:
        base_context.line_context.current_mode = prev_mode
    brackets = {
        "list": ("[", "]"),
        "set": ("{", "}"),
        "dict": ("{", "}"),
        "generator": ("(", ")"),
    }
    opener, closer = brackets.get(node.comp_type, ("[", "]"))
    return f"{opener}{inner}{closer}"


@BaseRenderer.register("comment_command")
def render_comment_command(
    renderer: BR, node: CommentCommand, base_context: BaseRenderContext
) -> str:
    context = base_context.current
    nl = context.newline
    # A standalone comment command updates the *global* render context with its
    # options so they persist to the following lines. 'line_break' is a one-shot
    # directive (insert a blank line here), so it is applied locally and never
    # merged into the global context. 'None' values are argparse defaults for
    # unset flags (e.g. an unset -f) and must not clobber the current context.
    line_break = node.commands.get("line_break", False)
    for key, value in node.commands.items():
        if key in ONE_SHOT_COMMANDS or value is None:
            continue
        setattr(base_context.global_context, key, value)
    if node.commands.get("page_break", False):
        return PAGE_BREAK
    if line_break:
        return f"{nl}"
    return ""


@BaseRenderer.register("comment_line")
def render_comment_line(
    renderer: BR, node: CommentLine, base_context: BaseRenderContext
) -> str:
    return node.content


@BaseRenderer.register("heading")
def render_heading(renderer: BR, node: Heading, base_context: BaseRenderContext) -> str:
    # A heading renders as a single markdown string in the master list, its
    # markdown level reproduced from the node's ``heading_level``.
    return f"{'#' * node.heading_level} {node.content}"


@BaseRenderer.register("inline_command")
def render_inline_command(
    renderer: BR, node: InlineCommand, base_context: BaseRenderContext
) -> str:
    # Only explicitly-set command options become line overrides; 'None' values are
    # argparse defaults for unset flags and must fall through to the global context.
    overrides = {k: v for k, v in node.commands.items() if v is not None}
    base_context.line_context = RenderContext.sparse(**overrides)
    return ""


@BaseRenderer.register("import")
def render_import(
    renderer: BR, node: Import, base_context: BaseRenderContext
) -> list[str]:
    # An import renders as a list of string components; the join step supplies
    # the single spaces between them.
    names = [
        (
            f"{name.identifier} as {name.value}"
            if name.value is not None
            else f"{name.identifier}"
        )
        for name in node.names
    ]
    rendered_names = ", ".join(names)
    components = ["[Python import]:"]
    if node.import_from:
        module = node.import_from_module
        dots = "." * (node.import_from_level or 0)
        components.append("from")
        if module is not None:
            components.append(f"{dots}{module}")
        elif dots:
            components.append(dots)
        components.append("import")
        components.append(rendered_names)
    else:
        components.append("import")
        components.append(rendered_names)
    return components


@BaseRenderer.register("calc_line")
def render_calcline(
    renderer: BaseRenderer, node: CalcLine, base_context: BaseRenderContext
) -> list[str] | str:
    """
    Render a CalcLine as a list of string components (columns interleaved with
    the equality symbol), e.g. ``["c", "=", "a+2", "=", "3+2", "=", "5"]``.

    Spaces, indent and the trailing newline are NOT embedded here; the join step
    inserts them. The columns present depend on ``context.mode``:
    ``ass`` (assignment target), ``sym`` (symbolic), ``num`` (numeric
    substitution) and ``res`` (result); ``full`` shows all of them. A param line
    (a bare value assignment) collapses to ``target = value``.
    """
    comment_render = None
    # The comment is rendered first because a command comment (e.g. ``# hc: -f``)
    # mutates the context that the expression columns below are rendered under.
    context = base_context.current
    param_line_pre_comment = getattr(context, "param_line", False)
    if node.comment is not None:
        comment_render = renderer.render(node.comment, base_context)
    context = base_context.current
    _ = context.space
    param_line_post_comment = getattr(context, "param_line", False)
    param_line = param_line_pre_comment or param_line_post_comment
    if getattr(context, "ignore", False):
        # Clear the line-specific context (as the normal return path does) so the
        # ignored line's command options -- e.g. a `format=None` left by an inline
        # command -- don't leak into the following lines.
        base_context.line_context = RenderContext.sparse()
        return ""

    shown = mode_columns(context.mode)
    base_context.line_context.break_nodes = breakable_ops(node.expression_tree)
    columns: deque = deque([])
    if "ass" in shown:
        base_context.line_context.current_mode = "sym"
        assign_nodes = [
            renderer.render(subnode, base_context) for subnode in node.assigns
        ]
        columns.append(",{_}".join(assign_nodes))
    if not param_line:
        if "sym" in shown:
            base_context.line_context.current_mode = "sym"
            symbolic = "".join(
                renderer.render(subnode, base_context)
                for subnode in node.expression_tree
            )
            columns.append(symbolic)
        if "num" in shown:
            base_context.line_context.current_mode = "num"
            numeric = "".join(
                renderer.render(subnode, base_context)
                for subnode in node.expression_tree
            )
            columns.append(numeric)
    if "res" in shown:
        base_context.line_context.current_mode = "num"
        result_nodes = [
            renderer.render(subnode, base_context) for subnode in node.assigns
        ]
        columns.append(f",{_}".join(result_nodes))

    # Drop a value column that repeats the one before it: a bare reference
    # (``q = y``, ``z = math.inf``) or a literal-only expression renders the same
    # in more than one column, which would otherwise show as ``= 3 = 3``.
    has_target = "ass" in shown
    head = [columns.popleft()] if has_target and columns else []
    values: list = []
    for column in columns:
        if not values or column != values[-1]:
            values.append(column)
    columns = deque(head + values)

    # Multi-line ("long") mode: break the one-liner into a grid of rows that all
    # align on the equality sign -- ``target = symbolic`` on the first row, then
    # ``= numeric`` and ``= result`` on their own rows (empty id cell). Only calcs
    # with an expression to substitute qualify (a param line, or a line reduced to
    # a single column, stays a one-liner). The trailing comment rides the last
    # (result) row, which is typically the shortest.
    #
    # A line continuation in the source (``\`` or a bracketed break, #259) also
    # lays the calc out as a grid: every column starts a row of its own and each
    # continued segment of a column gets a continuation row (with no ``=``).
    multiline = getattr(context, "multiline", False)
    broken = has_target and any(CONTINUATION_MARK in column for column in columns)
    if not broken:
        columns = deque(column.replace(CONTINUATION_MARK, _) for column in columns)
    if (multiline and not param_line and len(columns) > 2) or broken:
        eq = context.assign
        target, *value_cols = columns
        rows = []
        for column in value_cols:
            first, *rest = (seg.strip() for seg in column.split(CONTINUATION_MARK))
            rows.append(["" if rows else target, eq, first])
            rows += [["", "", seg] for seg in rest]
        if comment_render:
            rows[-1][2] = f"{rows[-1][2]}{_}{comment_render}"
        base_context.line_context = RenderContext.sparse()
        return renderer.format_calc_grid(rows, base_context)

    components: deque = deque([])
    for idx, column in enumerate(columns):
        if idx > 0:
            components.append(context.assign)
        components.append(column)
    if comment_render:
        components.append(comment_render)

    base_context.line_context = (
        RenderContext.sparse()
    )  # Clear any line-specific context
    return list(components)


@BaseRenderer.register("params_block")
def render_params_block(
    renderer: BaseRenderer, node: ParamsBlock, base_context: BaseRenderContext
) -> str:
    """
    Render a ParamsBlock (a run of consecutive ``;``-joined assignment lines) as a
    grid of ``identifier = value`` cells.

    Each child line is rendered as a param line (forced ``param_line=True``), so it
    collapses to a ``["id", "=", "value"]`` cell via the existing ``render_calcline``
    handler -- any trailing comment on the line is dropped. All cells are flattened
    and reflowed into ``param_cols`` columns (default 3, min 1, configurable via
    ``# hc: param_cols=N``); the final row is padded with ``None`` so the grid stays
    rectangular. ``format_param_grid`` turns the cell grid into the final text.
    """
    context = base_context.current
    cols = max(1, int(getattr(context, "param_cols", 3)))
    cells: list = []
    for line in node.lines:
        base_context.line_context.param_line = True
        rendered = renderer.render(line, base_context)
        # Keep the id / equality / value components, plus the line comment for a
        # ``# hc: -h`` block; a ``;`` block has no place for a comment, so it drops.
        if isinstance(rendered, list):
            rendered = rendered[: 4 if node.with_comments else 3]
        cells.append(rendered)
    rows = [cells[k : k + cols] for k in range(0, len(cells), cols)]
    if rows:
        rows[-1].extend([None] * (cols - len(rows[-1])))
    return renderer.format_param_grid(rows, base_context)


@BaseRenderer.register("expr_line")
def render_exprline(
    renderer: BaseRenderer, node: ExprLine, base_context: BaseRenderContext
) -> str:
    """
    Render a bare expression statement (an ExprLine).

    An ExprLine has no assignment target. The three kinds of ExprLine are
    classified and rendered honestly (no dangling equals, no fabricated result):

    - *docstring / bare string*: the expression tree is a single ``str`` (built
      by the parser for a string-literal statement); render it as a plain line.
    - *return statement* (``return_expr``): lives inside a symbolic function
      definition whose names have no runtime value, so render the symbolic form
      only -- no numeric substitution.
    - *ordinary expression statement* (e.g. ``print(x)``, ``x + y``): render the
      symbolic form and its numeric substitution joined by the equality, then the
      result if the parser could evaluate the expression (``node.value``, e.g.
      ``x + y = 1 + 2 = 3``). A column that repeats the one before it is dropped,
      as in a calc line (``2 + 2 = 4``).
    """

    # A bare string-literal statement (e.g. a module or block docstring) is a
    # single Constant holding a str; render it as a plain line, not a calc.
    tree = node.expression_tree
    if (
        len(tree) == 1
        and isinstance(tree[0], Constant)
        and isinstance(tree[0].value, str)
    ):
        line = [tree[0].value]
        if node.comment is not None:
            comment_render = renderer.render(node.comment, base_context)
            if comment_render:
                line.append(comment_render)
        return line

    # The comment is rendered first because a command comment (e.g. ``# hc: -f``)
    # mutates the context that the columns below are rendered under.
    comment_render = None
    if node.comment is not None:
        comment_render = renderer.render(node.comment, base_context)
    context = base_context.current

    def render_tree(mode: str) -> str:
        base_context.line_context.current_mode = mode
        return "".join(
            renderer.render(subnode, base_context) for subnode in node.expression_tree
        )

    shown = mode_columns(context.mode)
    columns = deque([])
    if "sym" in shown:
        columns.append(render_tree("sym"))
    # A return statement has no single runtime value; omit numeric substitution.
    # So does a line marked as a param line (``# hc: -p``), which shows its result.
    param_line = getattr(context, "param_line", False)
    if not node.return_expr and not param_line and "num" in shown:
        columns.append(render_tree("num"))
    if not isinstance(node.value, NoValue) and "res" in shown:
        base_context.line_context.current_mode = "num"
        columns.append(renderer.render_node(node.value, base_context))

    components = deque([])
    for column in columns:
        if components and column == components[-1]:
            continue
        if components:
            components.append(context.assign)
        components.append(column)

    if comment_render:
        components.append(comment_render)

    base_context.line_context = RenderContext.sparse()
    return list(components)


@BaseRenderer.register("elif_block")
def render_elifblock(
    renderer: BaseRenderer, node: ElifBlock, base_context: BaseRenderContext
) -> str:
    clauses: deque = node.lines
    context = base_context.current
    try:
        # Only IfBlock clauses carry ``is_true``; a trailing ElseBlock does not.
        true_clause: IfBlock = next(
            ib for ib in clauses if getattr(ib, "is_true", False)
        )
    except StopIteration:
        if len(clauses) >= 1 and isinstance(clauses[-1], ElseBlock):
            true_clause: ElseBlock = clauses[-1]
        else:
            true_clause = None

    if true_clause is None:
        return "No conditions were satisfied within the if-elif block"
    else:
        block_text = renderer.render(true_clause, base_context)
        return block_text


def render_condition(
    renderer: BaseRenderer,
    condition,
    base_context: BaseRenderContext,
    mode: str,
) -> str:
    """
    Render an if/elif condition in the given mode ('sym' or 'num') and return the
    joined string. Shared by the if/elif header handlers.

    ``condition`` may be the whole test node or a bare deque of comparison
    components. A ``Compare`` is unwrapped to its ``comparison`` deque (whose
    elements are joined tightly, matching the relational-operator symbols); any
    other test node (e.g. a boolean ``and``/``or`` op, or a lone ``Name``) is
    rendered directly.
    """
    base_context.line_context.current_mode = mode
    if isinstance(condition, Compare):
        condition = condition.comparison
    if isinstance(condition, (deque, list)):
        acc = [renderer.render(elem, base_context) for elem in condition]
        return "".join(acc)
    return renderer.render(condition, base_context)


def render_block_body(
    renderer: BaseRenderer,
    node: HcNode,
    base_context: BaseRenderContext,
) -> list[str, list]:
    """
    Render a block as ``[header_string, body_list]``: the header line as a
    string (the first element), followed by the block's body lines gathered
    into their own nested sublist. Indentation is applied by the join step,
    according to nesting depth, not embedded here.

    The header is produced by the handler registered under 'header:{node.type}'
    (empty string if none is registered), so a renderer customizes a block's
    intro line simply by registering its own 'header:...' handler.
    """
    header = renderer.render_header(node, base_context)
    body = [renderer.render(line, base_context) for line in node.lines]
    # A body of only strings (the lines of a comments block) is one line of
    # prose: wrap it so the join step reads it as a single all-string line. A
    # body that merely *starts* with a string (an ignored ``# hc: -i`` line, or a
    # comment before a calc) must not be wrapped, or the join step would read
    # the string as a block header and split the next line into its components.
    if body and all(isinstance(line, str) for line in body):
        body = [body]
    header = f"{node.header_pre}{header}{node.header_post}"
    if node.body_pre:
        body.insert(0, node.body_pre)
    if node.body_post:
        body.append(node.body_post)
    return [header, body]


@BaseRenderer.register("comments_block")
@BaseRenderer.register("calcs_block")
@BaseRenderer.register("if_block")
@BaseRenderer.register("for_block")
@BaseRenderer.register("else_block")
@BaseRenderer.register("function_block")
def render_generic_block(
    renderer: BaseRenderer, node: CommentsBlock, base_context: BaseRenderContext
) -> str:
    return render_block_body(renderer, node, base_context)


@BaseRenderer.register("header:comments_block")
def comments_block_header(
    renderer: BaseRenderer, node: CommentsBlock, base_context: BaseRenderContext
) -> Optional[str]:
    return ""


@BaseRenderer.register("header:calcs_block")
def calcs_block_header(
    renderer: BaseRenderer, node: CalcsBlock, base_context: BaseRenderContext
) -> Optional[str]:
    return ""


@BaseRenderer.register("header:else_block")
def else_block_header(
    renderer: BaseRenderer, node: ElseBlock, base_context: BaseRenderContext
) -> str:
    return "Otherwise:"


@BaseRenderer.register("header:function_block")
def function_block_header(
    renderer: BaseRenderer, node: FunctionBlock, base_context: BaseRenderContext
) -> str:
    """Best-guess header for a symbolic function definition block."""
    context = base_context.current
    _ = context.space
    base_context.line_context.current_mode = "sym"
    name_parts = [
        renderer.render(part, base_context) if hasattr(part, "type") else str(part)
        for part in node.function_name
    ]
    name = "".join(name_parts)
    params = f",{_}".join(str(param) for param in node.params)
    return f"Evaluating{_}{name}({params}):"


@BaseRenderer.register("header:if_block")
def if_block_header(
    renderer: BaseRenderer, node: IfBlock, base_context: BaseRenderContext
) -> str:
    context = base_context.current
    _ = context.space
    sym_expr = render_condition(renderer, node.test, base_context, "sym")
    num_expr = render_condition(renderer, node.test, base_context, "num")
    return f"Since{_}({sym_expr}){_}->{_}({num_expr}){_}is{_}True:"


@BaseRenderer.register("header:for_block")
def for_block_header(
    renderer: BaseRenderer, node: ForBlock, base_context: BaseRenderContext
) -> str:
    context = base_context.current
    _ = context.space
    base_context.line_context.current_mode = "sym"
    target = renderer.render(node.assigns[0], base_context)
    iterable = renderer.render(node.iterator[0], base_context)
    return f"Iterating{_}over{_}each{_}{target}{_}in{_}{iterable}:"


def is_literal_expr(node) -> bool:
    """
    True if ``node`` is a compile-time literal: a constant, a unary op or binary
    op whose operands are literals (e.g. ``-5``, ``3 + 4j``), or a collection
    whose elements are all literals. Used to decide whether a collection
    assignment is a param line.
    """
    if isinstance(node, Constant):
        return True
    if isinstance(node, HcUnaryOp):
        return is_literal_expr(node.operand)
    if isinstance(node, HcBinOp):
        return is_literal_expr(node.left) and is_literal_expr(node.right)
    if isinstance(node, (List, Tuple, Set)):
        return all(is_literal_expr(el) for el in node.elems)
    if isinstance(node, Dictionary):
        return all(is_literal_expr(el) for el in node.keys) and all(
            is_literal_expr(el) for el in node.values
        )
    return False


def _is_scalar_literal(node) -> bool:
    """
    A bare scalar literal, or a unary op applied to one (e.g. ``2``, ``-10.423``).
    Deliberately excludes bare binary ops so an ordinary calc like ``y = 2 + 3``
    still shows its symbolic/numeric substitution.
    """
    if isinstance(node, Constant):
        return True
    if isinstance(node, HcUnaryOp):
        return _is_scalar_literal(node.operand)
    return False


@BaseRenderer.register("calc_line:pre")
def toggle_param_line(
    renderer: BaseRenderer, node: CalcLine, base_context: BRC
) -> CalcLine:
    """
    A 'pre' rule on calc_line: decide whether the line is a "param line" (a bare
    value assignment that collapses to ``target = value``, hiding the symbolic
    and numeric-substitution columns). Runs before the calc_line handler reads
    ``context.param_line``.

    A line is a param line when its RHS is a single scalar literal (a constant or
    a unary-negated constant, e.g. ``-10.423``) or a literal collection (a
    ``list``/``tuple``/``set``/``dict`` whose every element is itself a literal).
    A collection containing a variable name still shows its substitution.
    """
    context = base_context.current
    if getattr(context, "param_line", False) == True:
        return node
    rhs = node.expression_tree[0] if len(node.expression_tree) == 1 else None
    is_literal_collection = isinstance(
        rhs, (List, Tuple, Set, Dictionary)
    ) and is_literal_expr(rhs)
    if rhs is not None and (_is_scalar_literal(rhs) or is_literal_collection):
        base_context.line_context.param_line = True
    else:
        base_context.line_context.param_line = node.pars_nesting
    return node


def infix_boolop(
    node: HcBoolOp,
    renderer: BaseRenderer,
    base_context: BRC = None,
) -> str:
    """
    Render an n-ary boolean operator (``and``/``or``) by joining its operands
    with the operator symbol, surrounded by the context space (``a and b``).

    An operand that binds looser than this operator is parenthesized -- in
    practice an ``or`` nested inside an ``and`` (``a and (b or c)``). Comparisons
    and arithmetic bind tighter, so they are never wrapped. Precedence and
    parenthesization mirror ``infix_binop``.
    """
    context = base_context.current
    _ = context.space
    lpar = context.lpar
    rpar = context.rpar
    this_pre = OP_PRECEDENCE.get(type(node), float("-inf"))
    parts = []
    for value in node.values:
        rendered = renderer.render_node(value, base_context)
        vpre = OP_PRECEDENCE.get(type(value), float("inf"))
        if vpre < this_pre:
            rendered = f"{lpar}{rendered}{rpar}"
        parts.append(rendered)
    joined = f"{_}{node.symbol}{_}".join(parts)
    return f"{node.pre}{joined}{node.post}"


def infix_binop(
    node: BinOp,
    renderer: BaseRenderer,
    allow_spaces=True,
    base_context: BRC = None,
) -> str:
    precedence = OP_PRECEDENCE
    associativity = {
        AddOp: "left",
        SubOp: "left",
        MultOp: "left",
        DivOp: "left",
        FloorOp: "left",
        ModuloOp: "left",
        MatMultOp: "left",
        PowOp: "right",
    }
    commutativity = {
        AddOp: 1,
        SubOp: 0,
        MultOp: 1,
        DivOp: 0,
        FloorOp: 0,
        ModuloOp: 0,
        MatMultOp: 0,
        PowOp: 0,
    }
    node_type = node.__class__
    pre = precedence.get(node_type)
    assoc = associativity.get(node_type)
    commut = commutativity.get(node_type)
    context = base_context.current
    lpar = context.lpar
    rpar = context.rpar
    left = node.left
    right = node.right
    symbol = node.symbol
    ltype = left.__class__
    rtype = right.__class__
    lpre = precedence.get(ltype, float("inf"))
    rpre = precedence.get(rtype, float("inf"))
    _ = context.space
    if not allow_spaces:
        _ = ""
    render_left = renderer.render_node(left, base_context)
    render_right = renderer.render_node(right, base_context)
    # A continuation inside an operand that gets brackets is dropped (see
    # ``breakable_ops``); this one is kept, beside the operator, if it is marked.
    brk = CONTINUATION_MARK if id(node) in getattr(context, "break_nodes", ()) else ""
    before = brk if brk and node.line_break == "before" else _
    after = brk if brk and node.line_break == "after" else _
    # A power's base that renders with a leading sign (e.g. b substituted as
    # -10.423) must be wrapped, otherwise -10.423² reads as -(10.423²).
    if lpre < pre or (node_type is PowOp and renderer.leading_sign(render_left)):
        left_portion = f"{lpar}{render_left.replace(CONTINUATION_MARK, _)}{rpar}"
    else:
        left_portion = render_left

    right_portion = render_right
    # A right operand that renders with a leading sign (a negative value
    # substituted in the numeric column) is wrapped: 7·(-3), not 7·-3.
    wrapped_right = f"{lpar}{render_right.replace(CONTINUATION_MARK, _)}{rpar}"
    if renderer.leading_sign(render_right):
        right_portion = wrapped_right
    elif rpre <= pre:
        if rpre < pre:
            right_portion = wrapped_right
        elif rpre == pre and not commut:
            right_portion = wrapped_right
    # An empty symbol means juxtaposition (e.g. a superscript power like b²), so
    # the operands butt together with no surrounding spaces.
    if symbol == "":
        return f"{left_portion}{right_portion}"
    return f"{left_portion}{before}{symbol}{after}{right_portion}"


# __init_subclass__ does not fire for BaseRenderer itself, so register it explicitly.
_RENDERER_REGISTRY.setdefault(BaseRenderer.name, BaseRenderer)
