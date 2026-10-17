"""
A plain-text renderer with nicer Unicode math: Unicode subscripts, a centred dot
for multiplication and proper comparison signs. Built from rules only.
"""
from handcalcs.renderers import PlainTextRenderer

SUBSCRIPTS = str.maketrans(
    "0123456789aehijklmnoprstuvx+-=()",
    "₀₁₂₃₄₅₆₇₈₉ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ₊₋₌₍₎",
)
COMPARISONS = {"lte_op": " ≤ ", "gte_op": " ≥ ", "neq_op": " ≠ ", "lt_op": " < ", "gt_op": " > "}


class UnicodeRenderer(PlainTextRenderer):
    name = "unicode"


@UnicodeRenderer.register("name:sym")
def unicode_subscripts(renderer, node, base_context):
    """``I_y`` -> ``Iᵧ`` when every character has a subscript form, else unchanged."""
    head, *subscripts = node.identifier.split("_")
    if not subscripts:
        return node
    tail = "".join(subscripts)
    if all(char.translate(SUBSCRIPTS) != char for char in tail):
        node.identifier = head + tail.translate(SUBSCRIPTS)
    return node


@UnicodeRenderer.register("mult_op:pre")
def centred_dot(renderer, node, base_context):
    node.symbol = "·"
    return node


@UnicodeRenderer.register("lte_op:pre")
@UnicodeRenderer.register("gte_op:pre")
@UnicodeRenderer.register("neq_op:pre")
@UnicodeRenderer.register("lt_op:pre")
@UnicodeRenderer.register("gt_op:pre")
def comparison_signs(renderer, node, base_context):
    node.symbol = COMPARISONS[node.type]
    return node
