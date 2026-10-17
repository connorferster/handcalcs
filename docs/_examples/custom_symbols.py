"""Custom symbols and function names for the LaTeX family of renderers."""
from handcalcs.renderers import MarkdownRenderer

SYMBOLS = {
    "V_dot": "\\dot{V}",
    "N_star": "N^{*}",
    "M_r": "M_{r}",
}


class SymbolMarkdownRenderer(MarkdownRenderer):
    name = "symbol_markdown"
    MATH_FUNCS = MarkdownRenderer.MATH_FUNCS | {
        "ceil_to": "\\operatorname{ceil}",
    }


@SymbolMarkdownRenderer.register("name:pre")
def swap_custom_symbols(renderer, node, base_context):
    """Runs before the built-in 'name:sym' rule, which leaves LaTeX untouched."""
    if node.identifier in SYMBOLS:
        node.identifier = SYMBOLS[node.identifier]
    return node
