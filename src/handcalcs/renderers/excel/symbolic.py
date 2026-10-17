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
from handcalcs.renderers.base import OP_PRECEDENCE, BaseRenderContext, infix_binop
from .rich_text import escape

GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ϵ", "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "ϑ",
    "iota": "ι", "kappa": "κ", "lamb": "λ", "mu": "μ", "nu": "ν", "xi": "ξ",
    "omicron": "ο", "pi": "π", "varpi": "ϖ", "rho": "ρ", "varrho": "ϱ",
    "sigma": "σ", "varsigma": "ς", "tau": "τ", "upsilon": "υ", "phi": "φ",
    "varphi": "ϕ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Alpha": "Α", "Beta": "Β", "Gamma": "Γ", "Delta": "Δ", "Epsilon": "Ε",
    "Zeta": "Ζ", "Eta": "Η", "Theta": "Θ", "Iota": "Ι", "Kappa": "Κ",
    "Lamb": "Λ", "Mu": "Μ", "Nu": "Ν", "Xi": "Ξ", "Omicron": "Ο", "Pi": "Π",
    "Rho": "Ρ", "Sigma": "Σ", "Tau": "Τ", "Upsilon": "Υ", "Phi": "Φ",
    "Chi": "Χ", "Psi": "Ψ", "Omega": "Ω",
}

# Suffix components that decorate the component before them.
ACCENTS = {
    "hat": "̂",    # combining circumflex
    "bar": "̅",    # combining overline
    "prime": "′",  # prime
}
STAR = "star"

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


def symbolic_identifier(identifier: str) -> str:
    """
    A Python identifier as display markup.

    ``___`` is a literal underscore and ``__`` a space (as in the HTMLRenderer).
    Otherwise the first ``_``-separated component is the base and the rest form
    one subscript; Excel has a single subscript level, so ``a_b_c`` becomes
    a<sub>b,c</sub>. Greek names become Greek letters; ``hat``, ``bar`` and
    ``prime`` decorate the component before them and ``star`` adds a
    superscript ``*``.
    """
    if not identifier or identifier.startswith("_"):
        return escape(identifier)
    text = identifier.replace("___", "\x00").replace("__", " ")
    components: list[str] = []
    starred = False
    for comp in text.split("_"):
        if not comp:
            continue
        if comp in ACCENTS and components:
            components[-1] += ACCENTS[comp]
        elif comp == STAR and components:
            starred = True
        else:
            components.append(GREEK.get(comp, comp))
    components = [escape(c.replace("\x00", "_")) for c in components]
    if not components:
        return escape(identifier)
    base, subs = components[0], components[1:]
    markup = base
    if subs:
        markup += f"<sub>{','.join(subs)}</sub>"
    if starred:
        markup += "<sup>*</sup>"
    return markup


def _is_constant_exponent(node: Any) -> bool:
    if isinstance(node, Constant):
        return True
    return isinstance(node, HcUnaryOp) and isinstance(node.operand, Constant)


# --- rules (registered on the ExcelRenderer by ``register_symbolic_rules``) ---

def name_symbol(renderer, node: Name, base_context: BaseRenderContext) -> Name:
    """'name:sym': display form of the identifier, on a copy of the node."""
    return replace(node, identifier=symbolic_identifier(node.identifier))


def attribute_symbol(renderer, node: Attribute, base_context: BaseRenderContext) -> Any:
    """'attribute:sym': ``math.pi`` -> π, ``math.e`` -> e, ``math.tau`` -> τ."""
    if node.identifier in ("pi", "e", "tau") and isinstance(node.value, float):
        if node.value == getattr(math, node.identifier):
            return Name(identifier=GREEK.get(node.identifier, node.identifier), value=node.value)
    return node


def function_call_symbol(renderer, node: FunctionCall, base_context: BaseRenderContext) -> FunctionCall:
    """'function_call:pre': drop the module prefix; ``sqrt`` -> ``√``."""
    function_name = node.function_name
    if getattr(function_name, "identifier", None) == "sqrt":
        function_name = Name(identifier="√", value="√")
    return replace(node, namespace=deque(), function_name=function_name, pre="(", post=")")


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


def compare_symbol(renderer, node: HcCompOp, base_context: BaseRenderContext) -> HcCompOp:
    """``<=`` -> ``≤`` etc., spaced, and escaped so ``<`` is never read as a tag."""
    symbol = COMPARISON_SYMBOLS.get(node.symbol.strip())
    if symbol is None:
        return node
    return replace(node, symbol=f" {escape(symbol)} ")


def escape_constant(renderer, rendered: Any, node: Constant, base_context: BaseRenderContext) -> Any:
    """'constant:post': escape string literals so they cannot inject markup."""
    if isinstance(rendered, str) and isinstance(node.value, str):
        return escape(rendered)
    return rendered


def render_pow(renderer, node: HcBinOp, base_context: BaseRenderContext) -> str:
    """Powers render tight: a<sup>2</sup>, a^(b + 1)."""
    if node.symbol != "<sup>":
        return f"{node.pre}{infix_binop(node, renderer, False, base_context)}{node.post}"
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
    for node_type in ("add_op", "sub_op", "mult_op", "div_op", "floor_op", "modulo_op", "pow_op"):
        cls.register(f"{node_type}:pre")(binop_symbol)
    for node_type in ("eq_op", "neq_op", "lt_op", "lte_op", "gt_op", "gte_op"):
        cls.register(f"{node_type}:pre")(compare_symbol)
    cls.register("constant:post")(escape_constant)
    cls.register("pow_op")(render_pow)


def symbolic_markup(renderer, nodes: Iterable[Any], base_context: BaseRenderContext) -> str:
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
