"""A LatexRenderer that sets each calculation group as a centred display."""
from handcalcs.renderers import LatexRenderer


class DisplayLatexRenderer(LatexRenderer):
    name = "display_latex"

    MATH_OPEN = "\\[\n\\begin{aligned}"
    MATH_CLOSE = "\\end{aligned}\n\\]"
    MATH_SKIP = ""
    OPERATOR_SYMBOLS = LatexRenderer.OPERATOR_SYMBOLS | {"mult_op": "\\times"}
