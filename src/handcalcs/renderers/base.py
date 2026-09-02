from collections import deque, ChainMap
from dataclasses import dataclass, field
from typing import ClassVar, Callable, Optional, Any
from handcalcs.parsing.nodes import HcNode
from handcalcs.parsing.sequence import HcSequence

# Node type imports only used for typing
from handcalcs.parsing.nodes import (
    HcNode,
    Name,
    Constant,
    List,
    Dictionary,
    Tuple,
    Set,
    
)
from handcalcs.parsing.operator_nodes import (
    AddOp,
    MultOp,
    SubOp,
    DivOp,
    ModuloOp,
    FloorOp,
    PowOp,
    HcBinOp,
    EqOp,
    GtOp,
    GtEOp,
    LtOp,
    LtEOp,
    NeqOp,
    HcCompOp
)
from handcalcs.parsing.inline_nodes import (
    InlineComment,
    FunctionCall,
    Compare,
    InlineCommand
)
from handcalcs.parsing.line_nodes import (
    CalcLine,
    ExprLine,
    Import,
    CommentCommand,
    Heading,
    CommentLine
)
from handcalcs.parsing.block_nodes import (
    IfBlock,
    ElseBlock,
    ElifBlock,
    ForBlock
)

RenderHandler = Callable

# The rule sub-categories that may be registered against a particular node type,
# in the order they execute within ``render_node``:
#   pre  -> transform the node before it is rendered (any mode)
#   sym  -> transform the node while ``context.current_mode == 'sym'``
#   num  -> transform the node while ``context.current_mode == 'num'``
#   post -> transform the rendered result (string or list of strings)
RULE_CATEGORIES = ("pre", "sym", "num", "post")


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

class ContextKeyError(Exception):
    pass

class RenderContext:
    def __init__(
        self, 
        space: str = ' ', 
        newline: str = '\n', 
        indent: str = "    ",
        equality: str = "=",
        mode: str = 'full',
        format_code: str = ".5g",
        param_line: bool = False,
        **kwargs
    ):
        self.space = space
        self.newline = newline
        self.indent = indent
        self.equality = equality
        self.mode = mode
        self.format = format_code
        self.param_line = param_line

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        attrs = [f"{k}={v}" for k, v in self.__dict__.items() if not k.startswith("_") and k.islower()]
        repr_attrs = ", ".join(attrs)
        return f"{__class__.__name__}({repr_attrs})"

    def __or__(self, other):
        if not isinstance(other, self.__class__):
            raise ValueError(f"Can only union between two RenderContexts, not {type(other)}.")
        else:
            return RenderContext(**(self.__dict__ | other.__dict__))


class BaseRenderContext:
    def __init__(self, global_context: RenderContext, line_context: RenderContext):

        self.global_context = global_context
        self.line_context = line_context

    
    @property
    def current(self):
        return RenderContext(**ChainMap(self.line_context.__dict__, self.global_context.__dict__))


class BaseRenderer:
    name: ClassVar[str] = 'base'
    node_handlers: ClassVar[dict[str, Callable]] = {}
    header_handlers: ClassVar[dict[str, Callable]] = {}
    # Rules keyed by node type, then by category ('pre'/'sym'/'num'/'post'),
    # each an ordered list executed in registration order. The node type is the
    # master category and the pre/sym/num/post are the sub-categories (mirroring
    # the 'header:{node_type}' block-header registration). The pseudo node type
    # 'root' carries the sequence-level pre/post renderers.
    rule_handlers: ClassVar[dict[str, dict[str, list[Callable]]]] = {}

    def __init__(self) -> None:
        self._handlers: dict[str, Callable] = dict(self.node_handlers)
        self._header_handlers: dict[str, Callable] = dict(self.header_handlers)
        self._rule_handlers: dict[str, dict[str, list[Callable]]] = _copy_rule_handlers(self.rule_handlers)


    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.node_handlers = dict(cls.node_handlers)
        cls.header_handlers = dict(cls.header_handlers)
        cls.rule_handlers = _copy_rule_handlers(cls.rule_handlers)

    def create_context(self, **kwargs) -> RenderContext:
        return BaseRenderContext(RenderContext(**kwargs), RenderContext())


    def render(self, node: HcNode, base_context: Optional[BaseRenderContext] = None) -> str:
        """
        Render a node.

        If 'context' is None, a new context is created.
        """
        if base_context is None:
            base_context = self.create_context()
        if node.type == 'root':
            return self.render_root(node, base_context)
        return self.render_node(node, base_context)


    def render_root(self, root: HcSequence, base_context: BaseRenderContext) -> list:
        """
        Render an HcSequence (root node) into the master list.

        The sequence-level pre/post renderers are registered against the pseudo
        node type 'root' (i.e. 'root:pre' and 'root:post'); they run before and
        after the sequence body and contribute leading/trailing items.
        """
        root_rules = self._rule_handlers.get('root', {})
        parts = [pre(self, root, base_context) for pre in root_rules.get('pre', [])]
        for node in root.sequence:
            parts.append(self.render(node, base_context))
        parts.extend(
            post(self, root, base_context) for post in root_rules.get('post', [])
        )
        return parts

    def join(self, tree: list, context: Optional[RenderContext] = None) -> str:
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
        """
        if context is None:
            context = RenderContext()
        return "".join(self._join_items(tree, 0, context))

    def _join_items(self, items: list, depth: int, context: RenderContext) -> list[str]:
        lines: list[str] = []
        for item in items:
            lines.extend(self._join_item(item, depth, context))
        return lines

    def _join_item(self, item, depth: int, context: RenderContext) -> list[str]:
        if not item:
            return []
        indent = context.indent * depth
        nl = context.newline
        if isinstance(item, str):
            return [f"{indent}{item}{nl}"]
        # A block is ``[header_string, body_list]`` -- detected by its body being
        # a list. An all-string list is a rendered line.
        if isinstance(item[-1], list):
            header, body = item[0], item[-1]
            lines = [f"{indent}{header}{nl}"]
            lines.extend(self._join_items(body, depth + 1, context))
            return lines
        return [f"{indent}{context.space.join(item)}{nl}"]

    def render_node(self, node: HcNode, base_context: BaseRenderContext) -> str:
        """
        Render one node with an existing context.

        Rules registered against this node type run in category order: 'pre'
        (always), then 'sym' or 'num' gated on ``context.current_mode``, then the
        node handler, then 'post' on the rendered result. Multiple rules in a
        category run in registration order.
        """
        node_rules = self._rule_handlers.get(node.type, {})
        current_mode = getattr(base_context.current, 'current_mode', None)

        for rule in node_rules.get('pre', []):
            node = rule(self, node, base_context)
        if current_mode == 'sym':
            for rule in node_rules.get('sym', []):
                node = rule(self, node, base_context)
        elif current_mode == 'num':
            for rule in node_rules.get('num', []):
                node = rule(self, node, base_context)

        handler = self._handlers.get(node.type)
        if handler is None:
            raise NotImplementedError(
                f"A handler for node type = '{node.type}' has not been registered in this renderer."
            )
        rendered = handler(self, node, base_context)

        for rule in node_rules.get('post', []):
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
                node_classifier, handler, cls.node_handlers, cls.header_handlers, cls.rule_handlers
            )
            return handler
        return decorator

    def register_handler(self, node_classifier: str, handler: RenderHandler) -> None:
        """Instance-scoped counterpart of ``register``. See ``_route_registration``."""
        self._route_registration(
            node_classifier, handler, self._handlers, self._header_handlers, self._rule_handlers
        )


    def render_unknown(self, node: HcNode, base_context: BaseRenderContext) -> str:
        return str(node)


## Register BaseRenderer basic node implementations

BR = BaseRenderer
BRC = RenderContext


@BaseRenderer.register('no_value')
def render_novalue(renderer: BaseRenderer, node: Constant, base_context: BaseRenderContext) -> str:
    return ''


@BaseRenderer.register('constant')
def render_constant(renderer: BaseRenderer, node: Constant, base_context: BaseRenderContext) -> Any:
    context = base_context.current
    fc = context.format
    try:
        return f"{node.value:{fc}}"
    except ValueError: # Format code not implemented
        return f"{node.value}"

@BaseRenderer.register('list')
def render_list(renderer: BaseRenderer, node: List, base_context: BaseRenderContext) -> Any:
    rendered_elems = [renderer.render(elem, base_context) for elem in node.elems]
    return f"[{', '.join(rendered_elems)}]"

@BaseRenderer.register('set')
def render_list(renderer: BaseRenderer, node: Set, base_context: BaseRenderContext) -> Any:
    rendered_elems = [renderer.render(elem, base_context) for elem in node.elems]
    return f"{{{', '.join(rendered_elems)}}}"

@BaseRenderer.register('dictionary')
def render_list(renderer: BaseRenderer, node: Dictionary, base_context: BaseRenderContext) -> Any:
    rendered_keys = [renderer.render(elem, base_context) for elem in node.keys]
    rendered_values = [renderer.render(elem, base_context) for elem in node.values]
    rkv = zip(rendered_keys, rendered_values)
    items = [": ".join(item) for item in rkv]
    return f"{{{', '.join(items)}}}"

@BaseRenderer.register('tuple')
def render_list(renderer: BaseRenderer, node: Tuple, base_context: BaseRenderContext) -> Any:
    rendered_elems = [renderer.render(elem, base_context) for elem in node.elems]
    return f"({', '.join(rendered_elems)})"

@BaseRenderer.register('inline_comment')
def render_inline_comment(renderer: BaseRenderer, node: InlineComment, base_context: BaseRenderContext) -> str:
    # A component atom: the separating space before it is supplied by the join
    # step (which joins a line's components with a single space).
    return f"({node.content})"

@BaseRenderer.register('name')
def render_name(renderer: BaseRenderer, node: Name, base_context: BaseRenderContext) -> str:
    context = base_context.current
    if not hasattr(context, 'current_mode'):
        raise ContextKeyError(
            f"Attempting to render the Name node while context does not have a 'current_mode' key.\n"
            f"{context=}"
        )
    if context.current_mode == 'sym':
        return node.identifier
    elif context.current_mode == 'num':

        fc = context.format
        # TODO: Handle non-scalar Name values (e.g. list/tuple/ndarray). A Name
        # bound to a list raises TypeError ("unsupported format string passed to
        # list.__format__") here, since only ValueError is caught. Decide how
        # such values should render numerically (element-wise, repr, etc.).
        try:
            return renderer.render_node(node.value, base_context)
        except (AttributeError, NotImplementedError):
            try:
                return f"{node.value:{fc}}"
            except (ValueError, TypeError): # Format code not implemented
                return f"{node.value}"
    else:
        raise ContextValueError(
            f"The context.current_mode has an unrecognized value: {context.current_mode}"
        )

@BaseRenderer.register('add_op')
def render_add_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    return f"{node.pre}{renderer.render(node.left, base_context)}{node.symbol}{renderer.render(node.right, base_context)}{node.post}"


@BaseRenderer.register('sub_op')
def render_sub_op(renderer: BR, node: SubOp, base_context: BaseRenderContext) -> str:
    return f"{node.pre}{renderer.render(node.left, base_context)}{node.symbol}{renderer.render(node.right, base_context)}{node.post}"


@BaseRenderer.register('mult_op')
def render_mult_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    return f"{node.pre}{renderer.render(node.left, base_context)}{node.symbol}{renderer.render(node.right, base_context)}{node.post}"


@BaseRenderer.register('div_op')
def render_div_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    return f"{node.pre}{renderer.render(node.left, base_context)}{node.symbol}{renderer.render(node.right, base_context)}{node.post}"


@BaseRenderer.register('pow_op')
def render_pow_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    return f"{node.pre}{renderer.render(node.left, base_context)}{node.symbol}{renderer.render(node.right, base_context)}{node.post}"

@BaseRenderer.register('gt_op')
def render_gt_op(renderer: BR, node: GtOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('gte_op')
def render_gte_op(renderer: BR, node: GtEOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('lt_op')
def render_lt_op(renderer: BR, node: LtOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('lte_op')
def render_lte_op(renderer: BR, node: LtEOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('eq_op')
def render_eq_op(renderer: BR, node: EqOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('neq_op')
def render_neq_op(renderer: BR, node: NeqOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('compare')
def render_compare(renderer: BR, node: Compare, base_context: BaseRenderContext) -> str:
    acc = [renderer.render(elem, base_context) for elem in node.comparison]
    return f"".join(acc)

@BaseRenderer.register('function_call')
def render_function_call(renderer: BR, node: FunctionCall, base_context: BaseRenderContext) -> str:
    context = base_context.current
    function_name = renderer.render(node.function_name, base_context)
    namespace = renderer.render(node.namespace, base_context)
    args = [renderer.render(arg, base_context) for arg in node.args]
    arg_str = f",{context.space}".join(args)
    if namespace == '__main__':
        namespace = ''
    if namespace:
        rendered = f"{context.space}{namespace}.{function_name}({arg_str}){context.space}"
    else:
        rendered = f"{context.space}{function_name}({arg_str}){context.space}"
    return rendered


@BaseRenderer.register('comment_command')
def render_comment_command(renderer: BR, node: CommentCommand, base_context: BaseRenderContext) -> str:
    base_context.global_context = base_context.global_context | RenderContext(**node.commands)
    return ''

@BaseRenderer.register('comment_line')
def render_comment_line(renderer: BR, node: CommentLine, base_context: BaseRenderContext) -> str:
    # A standalone comment renders as a plain-text line (a single string in the
    # master list). The trailing newline is inserted by the join step, not here.
    return node.content

@BaseRenderer.register('heading')
def render_heading(renderer: BR, node: Heading, base_context: BaseRenderContext) -> str:
    # A heading renders as a single markdown string in the master list, its
    # markdown level reproduced from the node's ``heading_level``.
    return f"{'#' * node.heading_level} {node.content}"


@BaseRenderer.register('inline_command')
def render_inline_command(renderer: BR, node: InlineCommand, base_context: BaseRenderContext) -> str:
    base_context.line_context =  RenderContext(**node.commands)
    return ''


@BaseRenderer.register('import')
def render_import(renderer: BR, node: Import, base_context: BaseRenderContext) -> list[str]:
    # An import renders as a list of string components; the join step supplies
    # the single spaces between them.
    names = [
        f"{name.identifier} as {name.value}" if name.value is not None
        else f"{name.identifier}"
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


@BaseRenderer.register('calc_line')
def render_calcline(renderer: BaseRenderer, node: CalcLine, base_context: BaseRenderContext) -> list[str] | str:
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
    param_line_pre_comment = getattr(context, 'param_line', False)
    if node.comment is not None:
        comment_render = renderer.render(node.comment, base_context)
    context = base_context.current
    param_line_post_comment = getattr(context, 'param_line', False)
    param_line = param_line_pre_comment or param_line_post_comment
    if getattr(context, 'ignore', False):
        base_context.line_context.ignore = False
        return ''

    columns: deque = deque([])
    if context.mode == 'full' or 'ass' in context.mode:
        base_context.line_context.current_mode = 'sym'
        assign_nodes = [renderer.render(subnode, base_context) for subnode in node.assigns]
        columns.append(", ".join(assign_nodes))
    if not param_line:
        if context.mode == 'full' or 'sym' in context.mode:
            base_context.line_context.current_mode = 'sym'
            symbolic = "".join(renderer.render(subnode, base_context) for subnode in node.expression_tree)
            columns.append(symbolic)
        if context.mode == "full" or "num" in context.mode:
            base_context.line_context.current_mode = "num"
            numeric = "".join(renderer.render(subnode, base_context) for subnode in node.expression_tree)
            columns.append(numeric)
    if context.mode == "full" or "res" in context.mode:
        base_context.line_context.current_mode = "num"
        result_nodes = [renderer.render(subnode, base_context) for subnode in node.assigns]
        columns.append(", ".join(result_nodes))

    components: deque = deque([])
    for idx, column in enumerate(columns):
        if idx > 0:
            components.append(context.equality)
        components.append(column)
    if comment_render:
        components.append(comment_render)

    base_context.line_context = RenderContext()  # Clear any line-specific context
    return list(components)


@BaseRenderer.register('expr_line')
def render_exprline(renderer: BaseRenderer, node: ExprLine, base_context: BaseRenderContext) -> str:
    """
    Render a bare expression statement (an ExprLine).

    An ExprLine has no assignment target, so there is no result column. Until a
    value-capture pass exists, the three kinds of ExprLine are classified and
    rendered honestly (no dangling equals, no fabricated result):

    - *docstring / bare string*: the expression tree is a single ``str`` (built
      by the parser for a string-literal statement); render it as a plain line.
    - *return statement* (``return_expr``): lives inside a symbolic function
      definition whose names have no runtime value, so render the symbolic form
      only -- no numeric substitution.
    - *ordinary expression statement* (e.g. ``print(x)``, ``x + y``): render the
      symbolic form and its numeric substitution joined by the equality, with no
      trailing equals and no result.
    """
    context = base_context.current

    # A bare string-literal statement (e.g. a module or block docstring) is a
    # single Constant holding a str; render it as a plain line, not a calc.
    tree = node.expression_tree
    if len(tree) == 1 and isinstance(tree[0], Constant) and isinstance(tree[0].value, str):
        line = [tree[0].value]
        if node.comment is not None:
            comment_render = renderer.render(node.comment, base_context)
            if comment_render:
                line.append(comment_render)
        return line

    def render_tree(mode: str) -> str:
        base_context.line_context.current_mode = mode
        return "".join(renderer.render(subnode, base_context) for subnode in node.expression_tree)

    columns = deque([])
    if context.mode == 'full' or 'sym' in context.mode:
        columns.append(render_tree('sym'))
    # A return statement has no single runtime value; omit numeric substitution.
    if not node.return_expr and (context.mode == 'full' or 'num' in context.mode):
        columns.append(render_tree('num'))

    components = deque([])
    for idx, column in enumerate(columns):
        if idx > 0:
            components.append(context.equality)
        components.append(column)

    if node.comment is not None:
        comment_render = renderer.render(node.comment, base_context)
        if comment_render:
            components.append(comment_render)

    return list(components)


@BaseRenderer.register('elif_block')
def render_elifblock(renderer: BaseRenderer, node: ElifBlock, base_context: BaseRenderContext) -> str:
    clauses: deque = node.lines
    context = base_context.current
    try:
        true_clause: IfBlock = next(ib for ib in clauses if ib.is_true)
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
    condition: deque,
    base_context: BaseRenderContext,
    mode: str,
) -> str:
    """
    Render a comparison/condition (a deque of nodes) in the given mode
    ('sym' or 'num') and return the joined string. Shared by the if/elif
    header handlers.
    """
    base_context.line_context.current_mode = mode
    acc = [renderer.render(elem, base_context) for elem in condition]
    return "".join(acc)


def render_block_body(
    renderer: BaseRenderer,
    node: HcNode,
    base_context: BaseRenderContext,
) -> list:
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
    return [header, body]


@BaseRenderer.register('if_block')
def render_if_block(renderer: BaseRenderer, node: IfBlock, base_context: BaseRenderContext) -> str:
    return render_block_body(renderer, node, base_context)


@BaseRenderer.register('for_block')
def render_for_block(renderer: BaseRenderer, node: ForBlock, base_context: BaseRenderContext) -> str:
    return render_block_body(renderer, node, base_context)


@BaseRenderer.register("header:if_block")
def if_block_header(renderer: BaseRenderer, node: IfBlock, base_context: BaseRenderContext) -> str:
    context = base_context.current
    _ = context.space
    sym_expr = render_condition(renderer, node.test.comparison, base_context, 'sym')
    num_expr = render_condition(renderer, node.test.comparison, base_context, 'num')
    return f"Since{_}({sym_expr}){_}->{_}({num_expr}){_}is{_}True:"


@BaseRenderer.register("header:for_block")
def for_block_header(renderer: BaseRenderer, node: ForBlock, base_context: BaseRenderContext) -> str:
    context = base_context.current
    _ = context.space
    base_context.line_context.current_mode = 'sym'
    target = renderer.render(node.assigns[0], base_context)
    iterable = renderer.render(node.iterator[0], base_context)
    return f"Iterating{_}over{_}each{_}{target}{_}in{_}{iterable}:"


@BaseRenderer.register("calc_line:pre")
def toggle_param_line(renderer: BaseRenderer, node: CalcLine, base_context: BRC) -> CalcLine:
    """
    A 'pre' rule on calc_line: decide whether the line is a "param line" (a bare
    value assignment that collapses to ``target = value``, hiding the symbolic
    and numeric-substitution columns). Runs before the calc_line handler reads
    ``context.param_line``.
    """
    context = base_context.current
    if getattr(context, 'param_line', False) == True:
        return node
    if (
        len(node.expression_tree) == 1
        and isinstance(node.expression_tree[0], Constant)
    ):
        base_context.line_context.param_line = True
    else:
        base_context.line_context.param_line = node.pars_nesting
    return node




