from collections import deque
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional
from handcalcs.renderers.base import (
    BaseRenderer,
    RenderContext,
    BaseRenderContext,
    ContextKeyError,
    ContextValueError,
    ROOT_SYMBOLS,
    math_call_name,
    postfix_factorial,
)

from handcalcs.renderers.identifiers import (
    GREEK_UNICODE,
    Symbol,
    greek_identifier,
    identifier_options,
    parse_identifier,
)

# Node type imports only used for typing
from handcalcs.parsing.nodes import (
    HcNode,
    Name,
    Constant,
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
    HcCompOp,
)
from handcalcs.parsing.inline_nodes import InlineComment, FunctionCall, Compare
from handcalcs.parsing.line_nodes import CalcLine, ExprLine, Import, Heading
from handcalcs.parsing.block_nodes import IfBlock, ElseBlock, ElifBlock


class AlignedText(str):
    """
    Pre-formatted rows (a long calc or a params grid) whose first row has its
    ``=`` sign ``lhs_width`` characters in. The join step shifts every row right
    by the same amount to line its ``=`` up with the calc lines around it.
    """

    lhs_width: int = 0


def aligned_text(text: str, lhs_width: int) -> AlignedText:
    aligned = AlignedText(text)
    aligned.lhs_width = lhs_width
    return aligned


class HeadingText(str):
    """A rendered heading: its text plus its underline (and overline)."""


class ASCIIRenderer(BaseRenderer):
    """
    Renders a calculation as monospaced text for terminals, logs and docstrings.

    Headings are underlined in the setext/reStructuredText style and set off by
    blank lines. Calc lines are aligned on their first ``=``: the left-hand sides
    are right-aligned to the widest one between two headings.
    """

    name = "ascii"

    # The underline character for each heading level and whether the heading
    # gets a matching overline too. Levels deeper than the last use the last.
    HEADING_RULES: ClassVar[dict[int, tuple[str, bool]]] = {
        1: ("=", True),
        2: ("=", False),
        3: ("-", False),
        4: ("~", False),
    }

    def complete(self, tree: list, base_context: BaseRenderContext) -> str:
        body = self.join(tree, base_context)
        return body

    def join(self, tree: list, base_context: Optional[BaseRenderContext] = None) -> str:
        if base_context is None:
            base_context = self.create_context()
        context = base_context.current
        aligned = align_equals(tree, context.assign, context.newline)
        return super().join(aligned, base_context)

    def join_item(self, item, depth: int, base_context: BaseRenderContext) -> list[str]:
        # A long calc is one multi-row string in a one-item line; join it as a
        # string so every row is indented to the line's depth, not just the first.
        if (
            isinstance(item, list)
            and len(item) == 1
            and isinstance(item[0], AlignedText)
        ):
            item = item[0]
        return super().join_item(item, depth, base_context)

    def format_calc_grid(self, rows: list, base_context: BaseRenderContext) -> str:
        id_width = max((len(str(ident)) for ident, _eq, _val in rows), default=0)
        return aligned_text(super().format_calc_grid(rows, base_context), id_width)

    def format_param_grid(self, rows: list, base_context: BaseRenderContext) -> str:
        context = base_context.current
        text = super().format_param_grid(rows, base_context)
        _ = context.space
        first_row = text.split(context.newline)[0]
        return aligned_text(text, max(first_row.find(f"{_}{context.assign}"), 0))


PTR = ASCIIRenderer
BRC = BaseRenderContext


## ALIGNMENT


def lhs_width(item, eq: str) -> Optional[int]:
    """
    The width of the text before an equation line's first ``eq`` sign, or None
    if ``item`` is not an equation line (a comment, an import, a block, ...).
    """
    if isinstance(item, AlignedText):
        return item.lhs_width
    if not isinstance(item, list) or not all(isinstance(part, str) for part in item):
        return None
    if len(item) == 1 and isinstance(item[0], AlignedText):
        return item[0].lhs_width
    if len(item) >= 3 and item[1] == eq:
        return len(item[0])
    return None


def is_block(item) -> bool:
    return isinstance(item, list) and bool(item) and isinstance(item[-1], list)


def is_headed_block(item) -> bool:
    return is_block(item) and isinstance(item[0], str) and bool(item[0].strip())


def pad_lhs(item, width: int, nl: str):
    """Shift an equation line right so its first ``=`` sits ``width`` characters in."""
    if isinstance(item, AlignedText):
        shift = " " * (width - item.lhs_width)
        return aligned_text(nl.join(shift + row for row in item.split(nl)), width)
    if len(item) == 1:
        return [pad_lhs(item[0], width, nl)]
    return [item[0].rjust(width), *item[1:]]


def section_widths(items: list, eq: str, widths: dict, section: list) -> list:
    """
    Walk a block body, grouping its equation lines into sections that end at each
    heading. Headerless blocks (runs of calcs or comments) belong to the body
    they sit in; a headed block's body (a conditional) is its own scope, so it is
    skipped here and aligned when it is rebuilt. Records each line's section
    width in ``widths`` (keyed by ``id``) and returns the open section.
    """
    for item in items:
        if isinstance(item, HeadingText):
            close_section(section, widths, eq)
            section = []
        elif is_block(item):
            if not is_headed_block(item):
                section = section_widths(item[-1], eq, widths, section)
        elif lhs_width(item, eq) is not None:
            section.append(item)
    return section


def close_section(section: list, widths: dict, eq: str) -> None:
    width = max((lhs_width(item, eq) for item in section), default=0)
    for item in section:
        widths[id(item)] = width


def rebuild(items: list, eq: str, nl: str, widths: dict) -> list:
    out: list = []
    for item in items:
        if isinstance(item, HeadingText):
            # A blank line before (unless the heading opens the output or follows
            # a blank line already) and after the heading.
            if any(out) and out[-1] != nl:
                out.append(nl)
            out += [item, nl]
        elif is_headed_block(item):
            out.append([*item[:-1], align_equals(item[-1], eq, nl)])
        elif is_block(item):
            out.append([*item[:-1], rebuild(item[-1], eq, nl, widths)])
        elif id(item) in widths:
            out.append(pad_lhs(item, widths[id(item)], nl))
        elif item == nl and out and out[-1] == nl:
            continue  # a `-b` line break right after a heading's blank line
        else:
            out.append(item)
    return out


def align_equals(items: list, eq: str, nl: str) -> list:
    """
    Return a copy of a rendered tree (or block body) with the left-hand sides of
    its equation lines right-aligned, section by section, so the first ``eq`` of
    every line in a section sits in the same column, and with blank lines around
    its headings.
    """
    widths: dict = {}
    close_section(section_widths(items, eq, widths, []), widths, eq)
    return rebuild(items, eq, nl, widths)


@ASCIIRenderer.register("heading")
def render_heading(renderer: PTR, node: Heading, base_context: BRC) -> HeadingText:
    """
    Underline a heading in the setext/reStructuredText style; the top level is
    overlined too::

        ===========
        Beam design
        ===========

        Loads
        =====

        Dead load
        ---------
    """
    rules = renderer.HEADING_RULES
    char, overline = rules.get(node.heading_level, rules[max(rules)])
    content = node.content or ""
    rule = char * len(content)
    lines = [rule, content, rule] if overline else [content, rule]
    return HeadingText(base_context.current.newline.join(lines))


BRC = BaseRenderContext


## SWAP RULES


def plain_symbol(symbol: Symbol) -> str:
    """A parsed ``Symbol`` as plain text: ``N_pl,Rd``, ``M^*``, ``ΔH``."""
    text = " ".join(
        "".join(GREEK_UNICODE[t] if is_greek else t for is_greek, t in pieces)
        for pieces in symbol.words
    )
    text += "'" * symbol.primes
    if symbol.superscripts:
        text += "^" + ",".join(plain_symbol(sup) for sup in symbol.superscripts)
    if symbol.subscripts:
        text += "_" + ",".join(plain_symbol(sub) for sub in symbol.subscripts)
    return text


@ASCIIRenderer.register("name:sym")
def swap_symbols(renderer: PTR, node: Name, base_context: BRC) -> HcNode:
    """
    Show an identifier listed in the ``symbols`` option from its spec
    (``{"N_plRd": "N_{pl,Rd}"}`` -> ``N_pl,Rd``). Other identifiers keep their
    underscores: plain text doesn't typeset subscripts.
    """
    options = identifier_options(renderer, base_context)
    if node.identifier in options.symbols:
        node.identifier = plain_symbol(parse_identifier(node.identifier, options))
    return node


@ASCIIRenderer.register("name:sym")
def swap_greeks(renderer: PTR, node: Name, base_context: BRC) -> HcNode:
    """
    Swap the Greek names in a Name's identifier for the letters: each
    ``_``-separated component and each ``__``-separated word of one, plus (with
    ``greek_prefixes``) a leading Greek name before an uppercase letter or a
    digit (``sigma_max`` -> ``σ_max``, ``DeltaH`` -> ``ΔH``). A ``__`` is shown
    as a space (``Delta__H`` -> ``Δ H``).

    Registered as a 'sym' rule on the Name node: the identifier is only shown in
    symbolic mode (numeric mode renders the Name's value instead).
    """
    identifier = greek_identifier(
        node.identifier, identifier_options(renderer, base_context).greek_prefixes
    )
    # Spaces for double underscores; a triple underscore is left as it is.
    words = identifier.split("___")
    node.identifier = "___".join(word.replace("__", " ") for word in words)
    return node


@ASCIIRenderer.register("mult_op:pre")
@ASCIIRenderer.register("pow_op:pre")
@ASCIIRenderer.register("div_op:pre")
@ASCIIRenderer.register("floor_op:pre")
@ASCIIRenderer.register("add_op:pre")
@ASCIIRenderer.register("sub_op:pre")
def swap_py_operators(renderer: PTR, node: HcBinOp, base_context: BRC) -> HcBinOp:
    """
    Rewrite a binary operator's display symbol/pre/post to the plain-text form.

    Registered as a 'pre' rule on each arithmetic operator node: the swap is
    mode-independent (the same symbol is shown in both the symbolic and numeric
    columns), so it must run before rendering regardless of mode. The mutation
    is idempotent, so re-running it on the second (numeric) pass is harmless.
    """
    context = base_context.current
    _ = context.space
    if node.type not in ("mult_op", "pow_op", "div_op", "floor_op", "add_op", "sub_op"):
        return node
    elif node.type == "mult_op":
        node.symbol = "*"
        node.pre = ""
        node.post = ""
        return node
    elif node.type == "div_op":
        # Division always renders with its '/' symbol. Any parentheses around an
        # operand come from the infix precedence logic (lpar/rpar), not from
        # pre/post, so pre/post stay empty regardless of operand type.
        node.symbol = "/"
        node.pre = ""
        node.post = ""
        return node
    elif node.type == "floor_op":
        node.symbol = "//"
        node.pre = ""
        node.post = ""
        return node
    elif node.type == "add_op":
        node.symbol = "+"
        return node
    elif node.type == "sub_op":
        node.symbol = "-"
        return node
    elif node.type == "pow_op" and isinstance(node.right, Constant):
        exp_str = str(node.right.value)
        node.symbol = ""
        superscript_integers = {
            "1": "¹",
            "2": "²",
            "3": "³",
            "4": "⁴",
            "5": "⁵",
            "6": "⁶",
            "7": "⁷",
            "8": "⁸",
            "9": "⁹",
            "0": "⁰",
            ".": "'",
        }
        acc = []
        for char in exp_str:
            acc.append(superscript_integers.get(char, char))

        node.right = Constant(value="".join(acc))
        return node
    else:
        return node


@ASCIIRenderer.register("function_call:pre")
def swap_sqrt_symbol(
    renderer: PTR, node: FunctionCall, base_context: BRC
) -> FunctionCall:
    """
    Swap a ``sqrt(...)`` call's function name for the '√' symbol.

    Registered as a 'pre' rule on function_call: the function name is shown in
    both symbolic and numeric columns, so the swap must be mode-independent. The
    mutation is idempotent across the two render passes.
    """
    name = math_call_name(node)
    if name == "":  # already set in its own notation
        return node
    node.pre = "("
    node.post = ")"
    if name == "factorial":
        return postfix_factorial(node, "(", ")")
    if name in ROOT_SYMBOLS:
        node.namespace = deque()
        node.function_name.identifier = ROOT_SYMBOLS[name]
        node.function_name.value = ROOT_SYMBOLS[name]
    return node
