"""Engineering notation and a zero tolerance for calculated values (#202, #109)."""
import math

from handcalcs.renderers import LatexRenderer, MarkdownRenderer
from handcalcs.renderers.base import is_source_number
from handcalcs.renderers.latex import format_latex_number


def engineering(value: float, digits: int) -> str:
    """182600000.0 -> '182.6 \\times 10^{6}': the exponent is a multiple of 3."""
    if value == 0 or not math.isfinite(value):
        return format_latex_number(value, "g")
    exponent = 3 * math.floor(math.log10(abs(value)) / 3)
    mantissa = f"{value / 10**exponent:.{digits}g}"
    return mantissa if exponent == 0 else f"{mantissa} \\times 10^{{{exponent}}}"


def number_handler(parent):
    """Wrap a renderer's 'constant' handler with two new context fields."""

    def render_constant(renderer, node, base_context):
        context = base_context.current
        value = node.value
        calculated = isinstance(value, float) and not is_source_number(node)
        if calculated:
            # '# hc: zero_tol = 1e-9' shows anything smaller as 0.
            zero_tol = getattr(context, "zero_tol", None)
            if zero_tol is not None and abs(value) < zero_tol:
                return "0"
            # '# hc: format_code = "eng4"' shows 4 significant digits, exponent a multiple of 3.
            if context.format_code.startswith("eng"):
                return engineering(value, int(context.format_code[3:] or 4))
        return parent(renderer, node, base_context)

    return render_constant


class EngMarkdownRenderer(MarkdownRenderer):
    name = "eng_markdown"


class EngLatexRenderer(LatexRenderer):
    name = "eng_latex"


EngMarkdownRenderer.register("constant")(number_handler(MarkdownRenderer.node_handlers["constant"]))
EngLatexRenderer.register("constant")(number_handler(LatexRenderer.node_handlers["constant"]))
