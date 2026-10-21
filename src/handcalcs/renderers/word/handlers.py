"""
The Word renderer's handlers and rules: names, values, operators, function
calls and collections, each returning an OMML fragment, and the line and block
handlers (headings, imports, block headers with inline equations).
"""

from __future__ import annotations

import datetime
import re
from html import unescape

from handcalcs.parsing.block_nodes import CalcsBlock, ForBlock, IfBlock
from handcalcs.parsing.inline_nodes import FunctionCall, InlineComment, Keyword
from handcalcs.parsing.line_nodes import Heading as HeadingLine, Import
from handcalcs.parsing.nodes import (
    Attribute,
    Constant,
    Dictionary,
    HcNode,
    List,
    Name,
    NoValue,
    Set,
    Slice,
    Subscript,
    Tuple,
)
from handcalcs.parsing.operator_nodes import DivOp, FloorOp, HcUnaryOp, PowOp
from handcalcs.renderers.base import (
    elide_items,
    render_symbolic,
    subscript_value,
    OP_PRECEDENCE,
    BaseRenderContext,
    is_source_number,
    is_atom,
    literal_text,
    quantity_power_base,
    receiver_needs_parens,
    render_condition,
)
from handcalcs.renderers.identifiers import (
    GREEK_UNICODE,
    IdentifierOptions,
    Symbol,
    identifier_options,
    indexed_symbol,
    is_identifier,
    parse_identifier,
)
from handcalcs.renderers.latex import import_source
from . import omml
from .document import Code, Heading, MathGroup, inline_math, validate_layout
from .renderer import WordRenderer

WR = WordRenderer
BRC = BaseRenderContext

MINUS = "−"

# The combining mark Word draws for each identifier accent (``m:acc``).
ACCENT_MARKS = {"hat": "\u0302", "bar": "\u0305", "dot": "\u0307", "ddot": "\u0308"}
PRIME_MARK = "\u2032"

# Namespaces whose attributes are mathematical constants (``math.pi``); the
# namespace is dropped when the attribute is shown symbolically.
MATH_NAMESPACES = ("math", "cmath", "numpy", "np", "scipy.constants")
MATH_CONSTANTS = {
    "pi": omml.run("π"),
    "tau": omml.run("τ"),
    "e": omml.run("e"),
    "inf": omml.run("∞"),
    "nan": omml.upright("NaN"),
}

# The OMML symbol of each operator node type (see ``swap_operator_symbols``).
# Word spaces binary operators and relations itself; operator words carry
# their own spaces.
OPERATOR_SYMBOLS = {
    "mult_op": omml.run("⋅"),
    "add_op": omml.run("+"),
    "sub_op": omml.run(MINUS),
    "modulo_op": omml.upright(" mod "),
    "lt_op": omml.run("<"),
    "gt_op": omml.run(">"),
    "lte_op": omml.run("≤"),
    "gte_op": omml.run("≥"),
    "eq_op": omml.run("=="),
    "neq_op": omml.run("≠"),
    "in_op": omml.run("∈"),
    "not_in_op": omml.run("∉"),
    "is_op": omml.upright(" is "),
    "is_not_op": omml.upright(" is not "),
    "and_op": omml.upright(" and "),
    "or_op": omml.upright(" or "),
}

# Python math functions set as Word function names (``m:func``), and the name
# each is shown with.
MATH_FUNCS = {
    "sin": "sin",
    "cos": "cos",
    "tan": "tan",
    "exp": "exp",
    "log": "log",
    "log10": "log",
    "ln": "ln",
    "sinh": "sinh",
    "cosh": "cosh",
    "tanh": "tanh",
    "asin": "arcsin",
    "acos": "arccos",
    "atan": "arctan",
    "atan2": "arctan",
    "asinh": "arcsinh",
    "acosh": "arccosh",
    "atanh": "arctanh",
}

# Functions drawn as brackets around their argument.
BRACKET_FUNCS = {"floor": ("⌊", "⌋"), "ceil": ("⌈", "⌉"), "abs": ("|", "|")}


def word_text(text: str) -> str:
    """One character in math italic; a longer word (not a number) upright."""
    if len(text) > 1 and not text.isdigit():
        return omml.upright(text)
    return omml.run(text)


def word_greek(name: str) -> str:
    """A Greek letter; a capital is set upright, as in print."""
    letter = GREEK_UNICODE[name]
    return omml.upright(letter) if name[0].isupper() else omml.run(letter)


# One upright run and its (escaped) text.
_UPRIGHT_RUN = re.compile(
    "([^<]*)".join(map(re.escape, omml.upright("\0").split("\0")))
)


def word_subscripts(parts: list[str]) -> str:
    """
    Sibling subscripts separated by commas, with neighbouring upright words set
    as one run ("pl,Rd", as in Eurocode notation).
    """
    joined: list[str] = []
    for part in parts:
        upright = _UPRIGHT_RUN.fullmatch(part)
        previous = _UPRIGHT_RUN.fullmatch(joined[-1]) if joined else None
        if upright and previous:
            joined[-1] = omml.upright(
                unescape(f"{previous.group(1)},{upright.group(1)}")
            )
        else:
            joined.append(part)
    return omml.run(",").join(joined)


def word_symbol(symbol: Symbol) -> str:
    """Typeset a parsed ``Symbol`` as OMML (see ``word_identifier``)."""
    if symbol.is_text:
        # No Greek letter: the base is one symbol or one upright word.
        rendered = word_text(symbol.text())
    else:
        rendered = omml.upright(" ").join(
            "".join(
                word_greek(text) if is_greek else word_text(text)
                for is_greek, text in pieces
            )
            for pieces in symbol.words
        )
    for accent in symbol.accents:
        rendered = omml.acc(rendered, ACCENT_MARKS[accent])
    superscripts = omml.run(",").join(word_symbol(sup) for sup in symbol.superscripts)
    primes = PRIME_MARK * symbol.primes
    if primes and not superscripts:
        rendered += omml.run(primes)
    elif superscripts:
        superscripts = omml.run(primes) + superscripts
    subscripts = word_subscripts([word_symbol(sub) for sub in symbol.subscripts])
    if subscripts and superscripts:
        return omml.sub_sup(rendered, subscripts, superscripts)
    if subscripts:
        return omml.sub(rendered, subscripts)
    if superscripts:
        return omml.sup(rendered, superscripts)
    return rendered


def word_identifier(identifier: str, options: IdentifierOptions | None = None) -> str:
    """
    Typeset a Python identifier as OMML from its parsed ``Symbol`` (see
    ``identifiers.parse_identifier``), with the rules of ``latex_identifier``:

    - single underscores are subscripts: ``N_pl_Rd`` -> N with subscript
      "pl,Rd" in the comma style (the default), ``x_a_b`` -> x with subscript
      a, which has subscript b, in the nested style;
    - double underscores are spaces and triple underscores literal underscores;
    - Greek names, Unicode letters and (with ``greek_prefixes``) Greek prefixes
      become letters (``omega_2`` -> ω₂, ``DeltaH`` -> ΔH); a capital is set
      upright, as in print;
    - ``hat``, ``bar``, ``dot`` and ``ddot`` are accents (``m:acc``), ``prime``
      a prime and ``star`` a superscript ``*``;
    - any other component longer than one character is a word, set upright in
      one run (``M_max`` -> M with subscript "max");
    - an identifier in ``options.symbols`` is typeset from its spec.

    Text that isn't an identifier (OMML from a ``name:pre`` rule or an earlier
    pass) is returned unchanged, so the swap is idempotent.
    """
    options = options or IdentifierOptions()
    if identifier not in options.symbols and not is_identifier(identifier):
        return identifier
    return word_symbol(parse_identifier(identifier, options))


## NAMES


@WR.register("name:sym")
def swap_identifier(renderer: WR, node: Name, base_context: BRC) -> Name:
    """Typeset a Name's identifier (see ``word_identifier``)."""
    node.identifier = word_identifier(
        node.identifier, identifier_options(renderer, base_context)
    )
    return node


@WR.register("attribute")
def render_attribute(renderer: WR, node: Attribute, base_context: BRC) -> str:
    """
    An attribute access. Math-library namespaces are dropped so that constants
    read as symbols (``math.pi`` -> π); any other namespace is kept and typeset
    like a Name. The numeric column shows the captured value, as for a Name.
    """
    context = base_context.current
    options = identifier_options(renderer, base_context)
    if node.receiver is not None:
        receiver = renderer.render(node.receiver, base_context)
        if receiver_needs_parens(node.receiver):
            receiver = omml.delim(receiver)
        return f"{receiver}{omml.run('.')}{word_identifier(node.identifier, options)}"
    if context.current_mode == "num" and not isinstance(node.value, NoValue):
        return renderer.render_node(node.value, base_context)
    namespace = node.namespace
    if namespace in ("", "__main__", None) or namespace in MATH_NAMESPACES:
        if namespace in MATH_NAMESPACES and node.identifier in MATH_CONSTANTS:
            return MATH_CONSTANTS[node.identifier]
        return word_identifier(node.identifier, options)
    parts = [word_identifier(part, options) for part in namespace.split(".")]
    return omml.run(".").join([*parts, word_identifier(node.identifier, options)])


@WR.register("subscript")
def render_subscript(renderer: WR, node: Subscript, base_context: BRC) -> str:
    """
    An index or key lookup. A name indexed by integers, short strings or names
    shows each index as a subscript (``xs[0]`` -> xs with subscript 0); any
    other lookup is shown in brackets, with the index substituted in the
    numeric column when there is no element. The numeric column shows the
    element, as for a Name.
    """
    value = subscript_value(renderer, node, base_context)
    if value is not None:
        return value
    if node.labels is not None:
        options = identifier_options(renderer, base_context)
        return word_symbol(
            indexed_symbol(node.container.identifier, node.labels, options)
        )
    container = render_symbolic(renderer, node.container, base_context)
    index = [renderer.render(item, base_context) for item in node.index]
    return container + omml.delim_items(index, "[", "]")


@WR.register("slice")
def render_slice(renderer: WR, node: Slice, base_context: BRC) -> str:
    """A slice in a subscript: ``1:3``, ``:n``, ``::2``."""
    parts = [
        "" if part is None else renderer.render(part, base_context)
        for part in (node.lower, node.upper, node.step)
    ]
    if node.step is None:
        parts.pop()
    return omml.run(":").join(parts)


@WR.register("keyword")
def render_keyword(renderer: WR, node: Keyword, base_context: BRC) -> str:
    """A keyword argument (``days = 3``), or ``**mapping``."""
    value = renderer.render(node.value, base_context)
    if node.arg is None:
        return f"{omml.run('**')}{value}"
    options = identifier_options(renderer, base_context)
    return f"{word_identifier(node.arg, options)}{omml.run('=')}{value}"


## VALUES


def typeset_number(formatted: str) -> str:
    """
    Typeset a number already written out as text: a minus sign for ``-``, any
    exponent as × 10ⁿ, and infinities and NaN as their math symbols.
    """
    sign = ""
    if formatted.startswith(("-", "+")):
        sign, formatted = formatted[0], formatted[1:]
    sign = omml.run(MINUS if sign == "-" else sign)
    if formatted == "inf":
        return f"{sign}{omml.run('∞')}"
    if formatted == "nan":
        return omml.upright("NaN")
    mantissa, sep, exponent = formatted.lower().partition("e")
    try:
        power = int(exponent) if sep else None
    except ValueError:
        power = None
    if power is None:
        return f"{sign}{omml.run(formatted)}"
    power_text = f"{MINUS}{abs(power)}" if power < 0 else f"{power}"
    ten = omml.sup(omml.run("10"), omml.run(power_text))
    if mantissa in ("1", "1.0"):
        return f"{sign}{ten}"
    return f"{sign}{omml.run(mantissa)}{omml.run('×')}{ten}"


# The number at the start of a formatted quantity ("2.5e+03 kN/m").
LEADING_NUMBER = re.compile(r"[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?")


def format_number(value, format_code: str) -> str:
    try:
        formatted = f"{value:{format_code}}"
    except (ValueError, TypeError):
        formatted = f"{value}"
    return typeset_number(formatted)


@WR.register("constant")
def render_constant(renderer: WR, node: Constant, base_context: BRC) -> str:
    value = node.value
    fc = base_context.current.format_code
    if isinstance(value, bool) or value is None:
        return omml.upright(f"{value}")
    if isinstance(value, (datetime.date, datetime.time)):
        return omml.text(f"{value}")
    # A number literal from the source keeps its digits as written (the format
    # code is for calculated values); only an exponent is typeset. A hex,
    # octal or binary literal has no exponent (0xe5 is not 0x × 10⁵).
    if is_source_number(node):
        text = literal_text(node)
        if isinstance(value, complex) or text.lower().startswith(("0x", "0o", "0b")):
            return omml.run(text)
        return typeset_number(text)
    if isinstance(value, str):
        return omml.text(f"“{value}”")
    if isinstance(value, complex):
        imag = f"{format_number(abs(value.imag), fc)}{omml.run('j')}"
        if value.real == 0:
            return f"{omml.run(MINUS) if value.imag < 0 else ''}{imag}"
        sign = omml.run(MINUS if value.imag < 0 else "+")
        return f"{format_number(value.real, fc)}{sign}{imag}"
    if isinstance(value, (int, float)):
        return format_number(value, fc)
    # A pint quantity: its magnitude takes the format code and its units the
    # registry's format (a format spec of ".5g" would reset that to pint's
    # long default, "millimeter ** 2").
    magnitude, units = getattr(value, "magnitude", None), getattr(value, "units", None)
    if isinstance(magnitude, (int, float)) and units is not None:
        return format_number(magnitude, fc) + omml.text(f" {units}")
    # Anything else is shown as formatted text. A quantity with units (e.g.
    # forallpeople) keeps its number as math, followed by the units as text.
    try:
        formatted = f"{value:{fc}}"
    except (ValueError, TypeError):
        formatted = f"{value}"
    number = LEADING_NUMBER.match(formatted)
    if number and formatted[number.end() :].startswith(" "):
        return typeset_number(number.group()) + omml.text(formatted[number.end() :])
    return omml.text(formatted)


def join_items(renderer: WR, items: list[str], base_context: BRC) -> list[str]:
    """
    A collection's rendered items, shortened around "…" by the ``max_items``
    and ``edge_items`` render-context fields (an equation row cannot break).
    """
    return elide_items(items, base_context, omml.run("…"))


@WR.register("list")
def render_list(renderer: WR, node: List, base_context: BRC) -> str:
    elems = [renderer.render(elem, base_context) for elem in node.elems]
    return omml.delim_items(join_items(renderer, elems, base_context), "[", "]")


@WR.register("tuple")
def render_tuple(renderer: WR, node: Tuple, base_context: BRC) -> str:
    elems = [renderer.render(elem, base_context) for elem in node.elems]
    if node.bare:
        return omml.run(",").join(elems)
    return omml.delim_items(join_items(renderer, elems, base_context), "(", ")")


@WR.register("set")
def render_set(renderer: WR, node: Set, base_context: BRC) -> str:
    elems = [renderer.render(elem, base_context) for elem in node.elems]
    return omml.delim_items(join_items(renderer, elems, base_context), "{", "}")


@WR.register("dictionary")
def render_dictionary(renderer: WR, node: Dictionary, base_context: BRC) -> str:
    keys = [renderer.render(elem, base_context) for elem in node.keys]
    values = [renderer.render(elem, base_context) for elem in node.values]
    items = [f"{key}{omml.run(':')}{value}" for key, value in zip(keys, values)]
    return omml.delim_items(join_items(renderer, items, base_context), "{", "}")


@WR.register("inline_comment")
def render_inline_comment(renderer: WR, node: InlineComment, base_context: BRC) -> str:
    return renderer.COMMENT_OPEN + omml.text(f"({node.content})")


## OPERATORS


@WR.register("mult_op:pre")
@WR.register("add_op:pre")
@WR.register("sub_op:pre")
@WR.register("modulo_op:pre")
@WR.register("lt_op:pre")
@WR.register("gt_op:pre")
@WR.register("lte_op:pre")
@WR.register("gte_op:pre")
@WR.register("eq_op:pre")
@WR.register("neq_op:pre")
@WR.register("in_op:pre")
@WR.register("not_in_op:pre")
@WR.register("is_op:pre")
@WR.register("is_not_op:pre")
@WR.register("and_op:pre")
@WR.register("or_op:pre")
def swap_operator_symbols(renderer: WR, node: HcNode, base_context: BRC) -> HcNode:
    """
    Swap an operator's Python symbol for its OMML run, looked up by node type so
    the swap is idempotent across the symbolic and numeric passes.
    """
    node.symbol = OPERATOR_SYMBOLS[node.type]
    return node


@WR.register("unary_op:post")
def swap_unary_symbol(
    renderer: WR, rendered: str, node: HcUnaryOp, base_context: BRC
) -> str:
    """
    Set a unary operator's symbol as a math run. This is a 'post' rule because
    the base handler looks at the Python symbol (``-``) to decide on brackets.
    """
    symbol = node.symbol.strip()
    prefix = f"{node.pre}{node.symbol}"
    if not rendered.startswith(prefix):
        return rendered
    rest = rendered[len(prefix) :]
    if symbol == "-":
        return f"{node.pre}{omml.run(MINUS)}{rest}"
    if symbol == "not":
        return f"{node.pre}{omml.upright('not ')}{rest}"
    return f"{node.pre}{omml.run(symbol)}{rest}"


@WR.register("pow_op")
def render_pow_op(renderer: WR, node: PowOp, base_context: BRC) -> str:
    """
    A superscript. The exponent needs no brackets; the base gets them when it
    binds no tighter than the power (including a left-nested power, since
    ``**`` is right-associative) or renders with a sign.
    """
    base = renderer.render_node(node.left, base_context)
    exponent = renderer.render_node(node.right, base_context)
    base_pre = OP_PRECEDENCE.get(type(node.left), float("inf"))
    if (
        base_pre <= OP_PRECEDENCE[PowOp]
        or renderer.leading_sign(base)
        or quantity_power_base(node, base_context)
    ):
        base = omml.delim(base)
    return omml.sup(base, exponent)


@WR.register("div_op")
def render_div_op(renderer: WR, node: DivOp, base_context: BRC) -> str:
    """A fraction: the bar groups both operands, so they need no brackets."""
    numerator = renderer.render_node(node.left, base_context)
    denominator = renderer.render_node(node.right, base_context)
    return omml.frac(numerator, denominator)


@WR.register("floor_op")
def render_floor_op(renderer: WR, node: FloorOp, base_context: BRC) -> str:
    numerator = renderer.render_node(node.left, base_context)
    denominator = renderer.render_node(node.right, base_context)
    return omml.delim(omml.frac(numerator, denominator), "⌊", "⌋")


## FUNCTION CALLS


@WR.register("function_call")
def render_function_call(renderer: WR, node: FunctionCall, base_context: BRC) -> str:
    """
    A function call. The name and namespace are symbols in both columns, not
    values. ``sqrt`` and ``cbrt`` are radicals, ``floor``/``ceil``/``abs``
    brackets, math functions Word function names (sin x), and anything else an
    upright name with its arguments in brackets.
    """
    identifier = node.function_name.identifier
    namespace_node = node.namespace
    if namespace_node and not isinstance(namespace_node, Name):
        # A method of an expression, (a * b).to("mm"): the receiver is
        # rendered like any operand, substituted in the numeric column.
        args = [renderer.render(arg, base_context) for arg in node.args]
        receiver = renderer.render(namespace_node, base_context)
        if receiver_needs_parens(namespace_node):
            receiver = omml.delim(receiver)
        name = f"{receiver}{omml.run('.')}{omml.upright(identifier)}"
        return f"{name}{omml.delim_items(args)}"
    namespace = getattr(namespace_node, "identifier", "") if namespace_node else ""
    if namespace == "__main__":
        namespace = ""
    is_math = namespace in MATH_NAMESPACES
    args = [renderer.render(arg, base_context) for arg in node.args]
    joined = omml.run(",").join(args)
    if is_math or not namespace:
        if identifier == "sqrt":
            return omml.rad(joined)
        if identifier == "cbrt":
            return omml.rad(joined, omml.run("3"))
        if identifier == "factorial" and len(node.args) == 1:
            if not is_atom(node.args[0]):
                joined = omml.delim(joined)
            return f"{joined}{omml.run('!')}"
        if identifier in BRACKET_FUNCS:
            return omml.delim(joined, *BRACKET_FUNCS[identifier])
        if identifier in MATH_FUNCS:
            return omml.func(omml.upright(MATH_FUNCS[identifier]), omml.delim(joined))
    name = omml.upright(identifier)
    if namespace and not is_math:
        options = identifier_options(renderer, base_context)
        prefix = omml.run(".").join(
            word_identifier(part, options) for part in namespace.split(".")
        )
        name = f"{prefix}{omml.run('.')}{name}"
    return f"{name}{omml.delim_items(args)}"


## LINES AND BLOCKS


@WR.register("heading")
def render_heading(renderer: WR, node: HeadingLine, base_context: BRC) -> Heading:
    return Heading(node.content, node.heading_level)


@WR.register("import")
def render_import(renderer: WR, node: Import, base_context: BRC) -> Code:
    """An import is one line of its Python source, in a monospace font."""
    return Code(import_source(node))


@WR.register("calcs_block:pre")
def mark_math_group(renderer: WR, node: CalcsBlock, base_context: BRC) -> CalcsBlock:
    """
    Open the body of a CalcsBlock with a ``MathGroup``, so ``write_item`` sets
    its rows out as one group of equations. The group keeps the layout in
    effect here (the renderer's, or a ``# hc: layout = ...`` comment's).
    """
    layout = getattr(base_context.current, "layout", renderer.layout)
    node.body_pre = MathGroup(validate_layout(layout))
    return node


@WR.register("header:if_block")
def if_block_header(renderer: WR, node: IfBlock, base_context: BRC) -> str:
    sym_expr = render_condition(renderer, node.test, base_context, "sym")
    num_expr = render_condition(renderer, node.test, base_context, "num")
    condition = f"{omml.delim(sym_expr)}{omml.run('→')}{omml.delim(num_expr)}"
    return f"Since {inline_math(condition)} is True:"


@WR.register("header:for_block")
def for_block_header(renderer: WR, node: ForBlock, base_context: BRC) -> str:
    base_context.line_context.current_mode = "sym"
    target = renderer.render(node.assigns[0], base_context)
    iterable = renderer.render(node.iterator[0], base_context)
    return f"Iterating over each {inline_math(target)} in {inline_math(iterable)}:"
