"""Notation recipes for the Markdown renderer (the same code works on LatexRenderer)."""
from handcalcs.renderers import MarkdownRenderer


class SigmaMarkdownRenderer(MarkdownRenderer):
    """sum(...) as a capital sigma, and a project function shown by its textbook name."""

    MATH_FUNCS = MarkdownRenderer.MATH_FUNCS | {
        "sum": "\\sum",
        "interp_table": "\\operatorname{interp}",
    }


class TimesMarkdownRenderer(MarkdownRenderer):
    """× instead of · for multiplication."""

    OPERATOR_SYMBOLS = MarkdownRenderer.OPERATOR_SYMBOLS | {"mult_op": "\\times"}


class UprightMarkdownRenderer(MarkdownRenderer):
    """Names that must not become Greek letters or subscripts."""

    UPRIGHT = {"psi", "ksi", "load_case_1"}


@UprightMarkdownRenderer.register("name:pre")
def keep_upright(renderer, node, base_context):
    if node.identifier in renderer.UPRIGHT:
        text = node.identifier.replace("_", "\\_")
        node.identifier = f"\\mathrm{{{text}}}"
    return node


class NoSubscriptMarkdownRenderer(MarkdownRenderer):
    """Show every underscore as an underscore: no subscripts at all."""


@NoSubscriptMarkdownRenderer.register("name:pre")
def literal_underscores(renderer, node, base_context):
    # '___' is the naming convention for a literal underscore.
    node.identifier = node.identifier.replace("_", "___")
    return node
