"""
The symbolic column: Python expressions as readable rich text.

These rules give the ExcelRenderer the HTMLRenderer's look -- subscripts,
superscript powers, Greek letters, accents, ``√``, ``·``, ``≤`` -- emitted as
light markup that ``rich_text.parse_markup`` turns into Excel rich-text runs.

Unlike the HTML rules, every rule here returns a *copy* of the node
(``dataclasses.replace``) and never mutates it: the formula pass and, for
conditionals, several display passes read the same nodes.
"""

from __future__ import annotations
import math
from collections import deque
from dataclasses import replace
from typing import Any, Iterable

from handcalcs.parsing.nodes import Attribute, Constant, Name
from handcalcs.parsing.inline_nodes import FunctionCall
from handcalcs.parsing.operator_nodes import HcBinOp, HcCompOp, HcUnaryOp, PowOp
from handcalcs.renderers.base import (
    OP_PRECEDENCE,
    BaseRenderContext,
    infix_binop,
    render_constant,
)
from handcalcs.renderers.identifiers import (
    GREEK_UNICODE,
    IdentifierOptions,
    Symbol,
    identifier_options,
    parse_identifier,
)
from .rich_text import escape

GREEK = GREEK_UNICODE

# The marks the accent components (``x_hat``) and primes add after a symbol.
ACCENTS = {
    "hat": "̂",  # combining circumflex
    "bar": "̅",  # combining overline
    "dot": "\u0307",  # combining dot above
    "ddot": "\u0308",  # combining diaeresis
    "prime": "′",  # prime
}

COMPARISON_SYMBOLS = {
    "==": "=",
    "!=": "≠",
    "<": "<",
    "<=": "≤",
    ">": ">",
    ">=": "≥",
}

BINOP_SYMBOLS = {
    "mult_op": "·",
    "div_op": "/",
    "add_op": "+",
    "sub_op": "-",
    "modulo_op": "mod",
}


def _symbol_text(symbol: Symbol) -> str:
    """A symbol's base with its Greek letters, accents and primes, escaped."""
    text = " ".join(
        "".join(GREEK[t] if is_greek else t for is_greek, t in pieces)
        for pieces in symbol.words
    )
    text += "".join(ACCENTS[accent] for accent in symbol.accents)
    text += ACCENTS["prime"] * symbol.primes
    return escape(text)


def _flatten(symbol: Symbol) -> tuple[list[str], list[str]]:
    """Every subscript and superscript below ``symbol``, in reading order."""
    subs: list[str] = []
    sups = [_symbol_text(sup) for sup in symbol.superscripts]
    for sub in symbol.subscripts:
        subs.append(_symbol_text(sub))
        more_subs, more_sups = _flatten(sub)
        subs += more_subs
        sups += more_sups
    return subs, sups


def symbolic_identifier(
    identifier: str, options: IdentifierOptions | None = None
) -> str:
    """
    A Python identifier as display markup, from its parsed ``Symbol`` (see
    ``identifiers.parse_identifier``).

    ``___`` is a literal underscore and ``__`` a space (as in the HTMLRenderer).
    Otherwise the first ``_``-separated component is the base and the rest form
    one subscript; Excel has a single subscript level, so ``a_b_c`` becomes
    a<sub>b,c</sub> in either subscript style. Greek names become Greek
    letters, in each ``__`` word too and, with ``greek_prefixes``, before an
    uppercase letter or a digit (``DeltaH`` -> ΔH); ``hat``, ``bar`` and
    ``prime`` decorate the component before them and ``star`` adds a
    superscript ``*``. An identifier in ``options.symbols`` is shown from its
    spec.
    """
    symbol = parse_identifier(identifier, options or IdentifierOptions())
    subs, sups = _flatten(symbol)
    markup = _symbol_text(symbol)
    if subs:
        markup += f"<sub>{','.join(subs)}</sub>"
    if sups:
        markup += f"<sup>{','.join(sups)}</sup>"
    return markup


def _is_constant_exponent(node: Any) -> bool:
    if isinstance(node, Constant):
        return True
    return isinstance(node, HcUnaryOp) and isinstance(node.operand, Constant)


# --- rules (registered on the ExcelRenderer by ``register_symbolic_rules``) ---


def name_symbol(renderer, node: Name, base_context: BaseRenderContext) -> Name:
    """'name:sym': display form of the identifier, on a copy of the node."""
    return replace(
        node,
        identifier=symbolic_identifier(
            node.identifier, identifier_options(renderer, base_context)
        ),
    )


def attribute_symbol(renderer, node: Attribute, base_context: BaseRenderContext) -> Any:
    """'attribute:sym': ``math.pi`` -> π, ``math.e`` -> e, ``math.tau`` -> τ."""
    if node.identifier in ("pi", "e", "tau") and isinstance(node.value, float):
        if node.value == getattr(math, node.identifier):
            return Name(
                identifier=GREEK.get(node.identifier, node.identifier), value=node.value
            )
    return node


def function_call_symbol(
    renderer, node: FunctionCall, base_context: BaseRenderContext
) -> FunctionCall:
    """'function_call:pre': drop the module prefix; ``sqrt`` -> ``√``."""
    function_name = node.function_name
    if getattr(function_name, "identifier", None) == "sqrt":
        function_name = Name(identifier="√", value="√")
    return replace(
        node, namespace=deque(), function_name=function_name, pre="(", post=")"
    )


def binop_symbol(renderer, node: HcBinOp, base_context: BaseRenderContext) -> HcBinOp:
    """Arithmetic operator display symbols; constant powers become superscripts."""
    if node.type == "pow_op":
        if _is_constant_exponent(node.right):
            return replace(node, symbol="<sup>", post="</sup>")
        return replace(node, symbol="^")
    if node.type == "floor_op":
        return replace(node, symbol="/", pre="⌊", post="⌋")
    symbol = BINOP_SYMBOLS.get(node.type)
    return replace(node, symbol=symbol) if symbol is not None else node


def compare_symbol(
    renderer, node: HcCompOp, base_context: BaseRenderContext
) -> HcCompOp:
    """``<=`` -> ``≤`` etc., spaced, and escaped so ``<`` is never read as a tag."""
    symbol = COMPARISON_SYMBOLS.get(node.symbol.strip())
    if symbol is None:
        return node
    return replace(node, symbol=f" {escape(symbol)} ")


def symbolic_constant(renderer, node: Constant, base_context: BaseRenderContext) -> Any:
    """
    'constant': numbers as written, not through ``format_code``. The number
    format belongs to the value cell; ``# hc: -f .3f`` must not turn
    ``b**2`` into b<sup>2.000</sup>.
    """
    value = node.value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return format(value, ".12g")
    return render_constant(renderer, node, base_context)


def escape_constant(
    renderer, rendered: Any, node: Constant, base_context: BaseRenderContext
) -> Any:
    """'constant:post': escape string literals so they cannot inject markup."""
    if isinstance(rendered, str) and isinstance(node.value, str):
        return escape(rendered)
    return rendered


def render_pow(renderer, node: HcBinOp, base_context: BaseRenderContext) -> str:
    """Powers render tight: a<sup>2</sup>, a^(b + 1)."""
    if node.symbol != "<sup>":
        return (
            f"{node.pre}{infix_binop(node, renderer, False, base_context)}{node.post}"
        )
    # A superscript exponent needs no parentheses (a<sup>-2</sup>); the base
    # keeps the infix rules: (a + b)<sup>2</sup>, (-a)<sup>2</sup>.
    context = base_context.current
    base = renderer.render_node(node.left, base_context)
    loose = OP_PRECEDENCE.get(type(node.left), math.inf) <= OP_PRECEDENCE[PowOp]
    if loose or base.lstrip().startswith(("-", "+")):
        base = f"{context.lpar}{base}{context.rpar}"
    exponent = renderer.render_node(node.right, base_context)
    return f"{base}{node.symbol}{exponent}{node.post}"


def register_symbolic_rules(cls) -> None:
    """Register the symbolic rules and handlers on a renderer class."""
    cls.register("name:sym")(name_symbol)
    cls.register("attribute:sym")(attribute_symbol)
    cls.register("function_call:pre")(function_call_symbol)
    for node_type in (
        "add_op",
        "sub_op",
        "mult_op",
        "div_op",
        "floor_op",
        "modulo_op",
        "pow_op",
    ):
        cls.register(f"{node_type}:pre")(binop_symbol)
    for node_type in ("eq_op", "neq_op", "lt_op", "lte_op", "gt_op", "gte_op"):
        cls.register(f"{node_type}:pre")(compare_symbol)
    cls.register("constant")(symbolic_constant)
    cls.register("constant:post")(escape_constant)
    cls.register("pow_op")(render_pow)


def symbolic_markup(
    renderer, nodes: Iterable[Any], base_context: BaseRenderContext
) -> str:
    """Render nodes in symbolic mode and join them into one markup string."""
    previous = getattr(base_context.line_context, "current_mode", None)
    base_context.line_context.current_mode = "sym"
    try:
        return "".join(renderer.render(node, base_context) for node in nodes)
    finally:
        if previous is None:
            del base_context.line_context.current_mode
        else:
            base_context.line_context.current_mode = previous
