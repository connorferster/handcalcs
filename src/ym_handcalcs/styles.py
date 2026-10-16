"""
Palette and stylesheet for the ReportLab renderer.

``build_stylesheet`` returns a fresh ``StyleSheet1`` holding every
``ParagraphStyle`` and ``TableStyle`` the story uses. Each style has an
``hc``-prefixed name (``hcCalc``) and a kebab-case alias (``hc-calc``).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.platypus import TableStyle

from .fonts import Fonts


@dataclass(frozen=True)
class Palette:
    # "Petrol": deep teal accent on cool slate greys.
    ink: str = "#1B2A2F"
    muted: str = "#647679"
    accent: str = "#0B5F66"
    accent_soft: str = "#E3F0EF"
    highlight: str = "#E8F3F2"
    code_bg: str = "#EFF3F3"
    rule: str = "#C2D4D3"
    zebra: str = "#F2F8F7"
    # Nested-block indent guides, one colour per level (cycled).
    guides: tuple[str, ...] = ("#86BDB8", "#D6B583", "#A7AFC6")

    def color(self, token: str) -> colors.Color:
        return colors.HexColor(getattr(self, token))

    def guide(self, level: int) -> colors.Color:
        return colors.HexColor(self.guides[(level - 1) % len(self.guides)])


@dataclass(frozen=True)
class Metrics:
    """Sizes derived from the base font size, so the whole block scales together."""
    base_size: float = 9.5

    @property
    def leading(self) -> float:
        return self.base_size * 1.35

    @property
    def indent(self) -> float:
        # Indentation per nested-block level.
        return self.base_size * 1.4

    @property
    def gap(self) -> float:
        # Vertical rhythm between lines of calcs.
        return self.base_size * 0.35

    @property
    def hang(self) -> float:
        # Hanging indent for wrapped calc lines.
        return self.base_size * 2


def _alias(name: str) -> str:
    # 'hcCalcGrid' -> 'hc-calc-grid'
    out = []
    for char in name:
        if char.isupper():
            out.append("-")
        out.append(char.lower())
    return "".join(out)


def build_stylesheet(
    palette: Palette = Palette(),
    fonts: Fonts = Fonts(),
    base_size: float = 9.5,
) -> StyleSheet1:
    """Build the default handcalcs stylesheet."""
    m = Metrics(base_size)
    ink = palette.color("ink")
    muted = palette.color("muted")
    accent = palette.color("accent")
    sheet = StyleSheet1()

    def add(style) -> None:
        sheet.add(style, alias=_alias(style.name))

    body = ParagraphStyle(
        "hcBody",
        fontName=fonts.sans.regular,
        fontSize=base_size,
        leading=m.leading,
        textColor=ink,
        spaceBefore=m.gap,
        spaceAfter=0,
    )
    add(body)

    heading_sizes = {1: 2.0, 2: 1.45, 3: 1.2}
    for level, scale in heading_sizes.items():
        add(ParagraphStyle(
            f"hcH{level}",
            parent=body,
            fontName=fonts.sans.bold,
            fontSize=base_size * scale,
            leading=base_size * scale * 1.2,
            textColor=accent if level < 3 else ink,
            spaceBefore=base_size * (1.6 if level == 1 else 1.3),
            spaceAfter=base_size * (0.2 if level < 3 else 0.35),
            keepWithNext=1,
        ))

    add(ParagraphStyle(
        "hcComment",
        parent=body,
        fontName=fonts.serif.regular,
        leading=base_size * 1.45,
        alignment=TA_JUSTIFY,
        spaceBefore=m.gap * 2,
        spaceAfter=m.gap,
    ))
    add(ParagraphStyle(
        "hcImport",
        parent=body,
        fontName=fonts.mono.regular,
        fontSize=base_size * 0.85,
        leading=base_size * 1.25,
        textColor=muted,
        spaceBefore=m.gap + 1,
        spaceAfter=1,
    ))
    add(ParagraphStyle(
        "hcCalc",
        parent=body,
        leading=base_size * 1.55,
        # Never chop a math token mid-way: CalcLine picks the break points.
        splitLongWords=0,
        leftIndent=m.hang,
        firstLineIndent=-m.hang,
        # Sub- and superscripts make a line taller instead of overlapping its neighbours.
        autoLeading="max",
    ))
    add(ParagraphStyle(
        "hcCalcComment",
        parent=body,
        fontName=fonts.sans.italic,
        fontSize=base_size * 0.9,
        textColor=muted,
        leftIndent=m.hang,
        spaceBefore=0,
    ))
    add(ParagraphStyle(
        "hcBlockHeader",
        parent=body,
        leading=base_size * 1.55,
        splitLongWords=0,
        # Hanging indent: a wrapped header continues under its text, not its
        # marker. The rounded background is drawn by the header flowable.
        leftIndent=m.hang,
        firstLineIndent=-m.hang,
        spaceBefore=m.gap * 2 + 3,
        spaceAfter=3,
        keepWithNext=1,
    ))
    add(ParagraphStyle(
        "hcNote",
        parent=body,
        fontName=fonts.sans.italic,
        textColor=muted,
    ))

    # Table cells: ids right-aligned, '=' centred, values left-aligned.
    cell = ParagraphStyle(
        "hcCell", parent=body, leading=base_size * 1.5, spaceBefore=0, spaceAfter=0, splitLongWords=0
    )
    add(cell)
    add(ParagraphStyle("hcCellRight", parent=cell, alignment=TA_RIGHT))
    add(ParagraphStyle("hcCellCenter", parent=cell, alignment=TA_CENTER))
    add(ParagraphStyle("hcCellLeft", parent=cell, alignment=TA_LEFT))
    # Calc value cells: a wrapped value continues with a small hanging indent.
    add(ParagraphStyle(
        "hcCellValue", parent=cell, alignment=TA_LEFT,
        leftIndent=m.hang * 0.5, firstLineIndent=-m.hang * 0.5,
    ))
    add(ParagraphStyle(
        "hcCellComment",
        parent=cell,
        fontName=fonts.sans.italic,
        fontSize=base_size * 0.9,
        textColor=muted,
    ))

    params = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), base_size * 0.3),
        ("RIGHTPADDING", (0, 0), (-1, -1), base_size * 0.3),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("BACKGROUND", (0, 0), (-1, -1), palette.color("accent_soft")),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ])
    params.name = "hcParams"
    add(params)

    calc_grid = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), base_size * 0.3),
        ("RIGHTPADDING", (0, 0), (-1, -1), base_size * 0.3),
        ("TOPPADDING", (0, 0), (-1, -1), 0.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LINEBEFORE", (0, 0), (0, -1), 1, accent),
    ])
    calc_grid.name = "hcCalcGrid"
    add(calc_grid)
    return sheet
