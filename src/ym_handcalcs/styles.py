"""
Palette and stylesheet for the ReportLab renderer.

``build_stylesheet`` returns a fresh ``StyleSheet1`` holding every
``ParagraphStyle`` and ``TableStyle`` the story uses. Each style has an
``hc``-prefixed name (``hcCalc``) and a kebab-case alias (``hc-calc``).
"""
from __future__ import annotations

import colorsys
from dataclasses import dataclass, field

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.platypus import TableStyle

from .fonts import Fonts


DEFAULT_THEME = "#0B5F66"


def _rgb(color) -> tuple[float, float, float]:
    """A '#RRGGBB' string (the '#' is optional) or a ReportLab Color, as 0-1 floats."""
    if isinstance(color, colors.Color):
        return color.red, color.green, color.blue
    text = str(color).strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"theme colour must be '#RRGGBB', got {color!r}")
    try:
        return tuple(int(text[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        raise ValueError(f"theme colour must be '#RRGGBB', got {color!r}") from None


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(round(min(max(v, 0.0), 1.0) * 255) for v in rgb)


def _tint(rgb, amount: float) -> str:
    """Mix ``amount`` of the colour into white (0 = white, 1 = the colour)."""
    return _hex(1 - amount * (1 - v) for v in rgb)


def _hls(hue: float, lightness: float, saturation: float) -> str:
    return _hex(colorsys.hls_to_rgb(hue % 1, lightness, saturation))


@dataclass(frozen=True)
class Palette:
    """
    Every colour the renderer uses. The defaults are ``Palette.from_theme(DEFAULT_THEME)``
    ("petrol"); build a palette from another dark theme colour with ``from_theme``.
    """
    ink: str = "#1B2B2C"
    muted: str = "#637778"
    accent: str = "#0B5F66"
    accent_soft: str = "#E7EFF0"
    highlight: str = "#EAF1F2"
    code_bg: str = "#EFF3F3"
    rule: str = "#BDD4D6"
    zebra: str = "#F3F7F7"
    # Nested-block indent guides, one colour per level (cycled).
    guides: tuple[str, ...] = ("#85B8BD", "#D5B386", "#A8B0C7")

    @classmethod
    def from_theme(cls, theme) -> "Palette":
        """
        Derive a palette from one dark theme colour (``'#RRGGBB'`` or a ReportLab
        ``Color``), which becomes the accent. Backgrounds and hairlines are tints
        of it (mixed with white); text colours keep its hue at a fixed lightness
        with most of the saturation removed. The second and third indent guides
        turn the hue (+210 and +40 degrees) so neighbouring levels stay distinct.
        Saturation scales with the theme's, so a grey theme gives a grey palette.
        """
        rgb = _rgb(theme)
        hue, _, sat = colorsys.rgb_to_hls(*rgb)
        return cls(
            ink=_hls(hue, 0.14, sat * 0.30),
            muted=_hls(hue, 0.43, sat * 0.12),
            accent=_hex(rgb),
            accent_soft=_tint(rgb, 0.10),
            highlight=_tint(rgb, 0.085),
            code_bg=_hls(hue, 0.945, sat * 0.17),
            rule=_tint(rgb, 0.27),
            zebra=_tint(rgb, 0.05),
            guides=(
                _hls(hue, 0.63, sat * 0.37),
                _hls(hue + 210 / 360, 0.68, sat * 0.60),
                _hls(hue + 40 / 360, 0.72, sat * 0.27),
            ),
        )

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
