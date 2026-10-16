"""
ym_handcalcs: a ymprint block module that renders handcalcs to ReportLab.

    from handcalcs import HandCalcs
    from ym_handcalcs import ReportLabRenderer

    result = HandCalcs(renderer=ReportLabRenderer())(source)
    result["stylesheet"]  # reportlab.lib.styles.StyleSheet1
    result["story"]       # list of flowables
"""
from .fonts import Fonts, FontFamily, ensure_dejavu_registered
from .styles import Palette, build_stylesheet
from .renderer import ReportLabRenderer
from .pdf import build_pdf
