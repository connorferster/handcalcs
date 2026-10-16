"""
Font names used by the ReportLab renderer.

ymprint bundles the full DejaVu suite and registers it under the standard
ReportLab names, so the renderer only *refers* to those names. It never
registers TTFs itself. ``ensure_dejavu_registered`` is a dev/test helper for
running the renderer outside ymprint.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Optional

from reportlab.lib.fonts import tt2ps
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


@dataclass(frozen=True)
class FontFamily:
    regular: str
    bold: str
    italic: str
    bold_italic: str

    @property
    def faces(self) -> tuple[str, str, str, str]:
        return (self.regular, self.bold, self.italic, self.bold_italic)


@dataclass(frozen=True)
class Fonts:
    """The three families the renderer uses: sans for math, serif for prose, mono for code."""
    sans: FontFamily = FontFamily(
        "DejaVuSans", "DejaVuSans-Bold", "DejaVuSans-Oblique", "DejaVuSans-BoldOblique"
    )
    serif: FontFamily = FontFamily(
        "DejaVuSerif", "DejaVuSerif-Bold", "DejaVuSerif-Italic", "DejaVuSerif-BoldItalic"
    )
    # ymprint bundles no DejaVuSansMono-BoldOblique, so bold italic code uses the bold face.
    mono: FontFamily = FontFamily(
        "DejaVuSansMono", "DejaVuSansMono-Bold", "DejaVuSansMono-Oblique", "DejaVuSansMono-Bold"
    )

    @property
    def families(self) -> tuple[FontFamily, FontFamily, FontFamily]:
        return (self.sans, self.serif, self.mono)


def missing_fonts(fonts: Fonts) -> list[str]:
    """Face names in ``fonts`` that are not registered with ReportLab."""
    registered = set(pdfmetrics.getRegisteredFontNames())
    return [face for family in fonts.families for face in family.faces if face not in registered]


def register_families(fonts: Fonts) -> None:
    """
    Map each family's bold/italic faces so ``<b>``/``<i>`` work inside
    paragraphs. A family that already has a mapping (e.g. set up by ymprint) is
    left alone. No TTFs are registered here.
    """
    for family in fonts.families:
        try:
            tt2ps(family.regular, 1, 0)
        except ValueError:
            pdfmetrics.registerFontFamily(
                family.regular,
                normal=family.regular,
                bold=family.bold,
                italic=family.italic,
                boldItalic=family.bold_italic,
            )


_DEJAVU_DIRS = (
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/TTF",
    "/Library/Fonts",
    "C:/Windows/Fonts",
)


def _search_dirs(dirs: tuple[str, ...]) -> list[pathlib.Path]:
    found = [pathlib.Path(d) for d in dirs]
    try:  # matplotlib ships every DejaVu face, including the italics distros often omit
        import matplotlib
        found.append(pathlib.Path(matplotlib.get_data_path()) / "fonts" / "ttf")
    except ImportError:
        pass
    return [d for d in found if d.is_dir()]


def ensure_dejavu_registered(fonts: Fonts = Fonts(), dirs: tuple[str, ...] = _DEJAVU_DIRS) -> None:
    """
    **Dev/test only.** Register any face in ``fonts`` that is not registered yet,
    from ``<face name>.ttf`` found in ``dirs`` (or matplotlib's bundled fonts, if
    matplotlib happens to be installed). A face with no file (system DejaVu
    packages often omit the italics) is registered from its family's regular
    file, so dev output shows it upright. Inside ymprint the fonts are already
    registered and this is never needed.
    """
    search = _search_dirs(dirs)

    def find(face: str) -> Optional[pathlib.Path]:
        return next((d / f"{face}.ttf" for d in search if (d / f"{face}.ttf").exists()), None)

    missing = set(missing_fonts(fonts))
    for family in fonts.families:
        for face in family.faces:
            if face not in missing:
                continue
            path = find(face) or find(family.regular)
            if path is None:
                raise FileNotFoundError(
                    f"Could not find {face}.ttf or {family.regular}.ttf in any of: "
                    f"{', '.join(map(str, search))}"
                )
            pdfmetrics.registerFont(TTFont(face, str(path)))
            missing.discard(face)
