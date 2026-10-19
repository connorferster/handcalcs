"""
The Word renderer's inline handlers and rules: names, values, operators,
function calls and collections, each returning an OMML fragment.
"""

from __future__ import annotations

import datetime
from collections import deque

from handcalcs.parsing.inline_nodes import FunctionCall, InlineComment, Keyword
from handcalcs.parsing.nodes import (
    Attribute,
    Constant,
    Dictionary,
    HcNode,
    List,
    Name,
    NoValue,
    Set,
    Tuple,
)
from handcalcs.parsing.operator_nodes import DivOp, FloorOp, HcUnaryOp, PowOp
from handcalcs.renderers.base import (
    OP_PRECEDENCE,
    BaseRenderContext,
    is_source_number,
    literal_text,
)
from . import omml
from .renderer import WordRenderer

WR = WordRenderer
BRC = BaseRenderContext

MINUS = "−"

# Greek letter names usable as identifier components, and their letters.
# ``lamb`` stands in for ``lambda``, a Python keyword.
GREEK_LOWER = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "varepsilon": "ϵ",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "vartheta": "ϑ",
    "iota": "ι",
    "kappa": "κ",
    "lamb": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "omicron": "ο",
    "pi": "π",
    "varpi": "ϖ",
    "rho": "ρ",
    "varrho": "ϱ",
    "sigma": "σ",
    "varsigma": "ς",
    "tau": "τ",
    "upsilon": "υ",
    "phi": "φ",
    "varphi": "ϕ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
}
GREEK_UPPER = {
    "Alpha": "Α",
    "Beta": "Β",
    "Gamma": "Γ",
    "Delta": "Δ",
    "Epsilon": "Ε",
    "Zeta": "Ζ",
    "Eta": "Η",
    "Theta": "Θ",
    "Iota": "Ι",
    "Kappa": "Κ",
    "Lamb": "Λ",
    "Mu": "Μ",
    "Nu": "Ν",
    "Xi": "Ξ",
    "Omicron": "Ο",
    "Pi": "Π",
    "Rho": "Ρ",
    "Sigma": "Σ",
    "Tau": "Τ",
    "Upsilon": "Υ",
    "Phi": "Φ",
    "Chi": "Χ",
    "Psi": "Ψ",
    "Omega": "Ω",
}

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


def is_omml(text: str) -> bool:
    return text.startswith("<m:")


def word_identifier(identifier: str) -> str:
    """
    Typeset a Python identifier as OMML, with the rules of ``latex_identifier``:

    - single underscores are nested subscripts: ``x_a_b`` -> x with subscript
      a, which has subscript b;
    - double underscores are spaces and triple underscores literal underscores;
    - a component that names a Greek letter becomes that letter
      (``omega_2`` -> ω₂); a capital is set upright, as in print;
    - any other component longer than one character is a word, set upright in
      one run (``M_max`` -> M with subscript "max").

    Identifiers that are already OMML are returned unchanged, so the swap is
    idempotent.
    """
    if not identifier or is_omml(identifier):
        return identifier
    identifier = identifier.replace("___", "\0").replace("__", "\1")
    components = []
    for component in identifier.split("_"):
        if component in GREEK_LOWER:
            components.append(omml.run(GREEK_LOWER[component]))
            continue
        if component in GREEK_UPPER:
            components.append(omml.upright(GREEK_UPPER[component]))
            continue
        text = component.replace("\0", "_").replace("\1", " ")
        if len(component) > 1 and not component.isdigit():
            components.append(omml.upright(text))
        else:
            components.append(omml.run(text))
    rendered = components[-1]
    for component in reversed(components[:-1]):
        rendered = omml.sub(component, rendered)
    return rendered


## NAMES


@WR.register("name:sym")
def swap_identifier(renderer: WR, node: Name, base_context: BRC) -> Name:
    """Typeset a Name's identifier (see ``word_identifier``)."""
    node.identifier = word_identifier(node.identifier)
    return node


@WR.register("attribute")
def render_attribute(renderer: WR, node: Attribute, base_context: BRC) -> str:
    """
    An attribute access. Math-library namespaces are dropped so that constants
    read as symbols (``math.pi`` -> π); any other namespace is kept and typeset
    like a Name. The numeric column shows the captured value, as for a Name.
    """
    context = base_context.current
    if context.current_mode == "num" and not isinstance(node.value, NoValue):
        return renderer.render_node(node.value, base_context)
    namespace = node.namespace
    if namespace in ("", "__main__", None) or namespace in MATH_NAMESPACES:
        if namespace in MATH_NAMESPACES and node.identifier in MATH_CONSTANTS:
            return MATH_CONSTANTS[node.identifier]
        return word_identifier(node.identifier)
    parts = [word_identifier(part) for part in namespace.split(".")]
    return omml.run(".").join([*parts, word_identifier(node.identifier)])


@WR.register("keyword")
def render_keyword(renderer: WR, node: Keyword, base_context: BRC) -> str:
    """A keyword argument (``days = 3``), or ``**mapping``."""
    value = renderer.render(node.value, base_context)
    if node.arg is None:
        return f"{omml.run('**')}{value}"
    return f"{word_identifier(node.arg)}{omml.run('=')}{value}"


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
    # Anything else (e.g. a quantity with units) is shown as formatted text.
    try:
        formatted = f"{value:{fc}}"
    except (ValueError, TypeError):
        formatted = f"{value}"
    return omml.text(formatted)


def join_items(renderer: WR, items: list[str]) -> list[str]:
    """
    A collection's rendered items. An equation row cannot break, so more than
    MAX_ITEMS items are elided to the first and last EDGE_ITEMS around "…".
    """
    edge = renderer.EDGE_ITEMS
    if len(items) > renderer.MAX_ITEMS:
        items = [*items[:edge], omml.run("…"), *items[-edge:]]
    return items


@WR.register("list")
def render_list(renderer: WR, node: List, base_context: BRC) -> str:
    elems = [renderer.render(elem, base_context) for elem in node.elems]
    return omml.delim_items(join_items(renderer, elems), "[", "]")


@WR.register("tuple")
def render_tuple(renderer: WR, node: Tuple, base_context: BRC) -> str:
    elems = [renderer.render(elem, base_context) for elem in node.elems]
    return omml.delim_items(join_items(renderer, elems), "(", ")")


@WR.register("set")
def render_set(renderer: WR, node: Set, base_context: BRC) -> str:
    elems = [renderer.render(elem, base_context) for elem in node.elems]
    return omml.delim_items(join_items(renderer, elems), "{", "}")


@WR.register("dictionary")
def render_dictionary(renderer: WR, node: Dictionary, base_context: BRC) -> str:
    keys = [renderer.render(elem, base_context) for elem in node.keys]
    values = [renderer.render(elem, base_context) for elem in node.values]
    items = [f"{key}{omml.run(':')}{value}" for key, value in zip(keys, values)]
    return omml.delim_items(join_items(renderer, items), "{", "}")


@WR.register("inline_comment")
def render_inline_comment(renderer: WR, node: InlineComment, base_context: BRC) -> str:
    return omml.run(omml.EM_SPACE) + omml.text(f"({node.content})")


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
    if base_pre <= OP_PRECEDENCE[PowOp] or renderer.leading_sign(base):
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
        if identifier in BRACKET_FUNCS:
            return omml.delim(joined, *BRACKET_FUNCS[identifier])
        if identifier in MATH_FUNCS:
            return omml.func(omml.upright(MATH_FUNCS[identifier]), omml.delim(joined))
    name = omml.upright(identifier)
    if namespace and not is_math:
        prefix = omml.run(".").join(word_identifier(p) for p in namespace.split("."))
        name = f"{prefix}{omml.run('.')}{name}"
    return f"{name}{omml.delim_items(args)}"
