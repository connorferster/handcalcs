"""
Optional helper: build a stand-alone PDF from a ReportLabRenderer result.

The renderer itself only returns ``{"stylesheet", "story"}`` for a host
document (ymprint) to place. ``build_pdf`` is for quick previews and simple
documents: one frame per page, PDF bookmarks from the calc headings, and a
footer with the title and page number.
"""
from __future__ import annotations

import pathlib
from typing import Optional

from reportlab.lib.pagesizes import letter
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate


class HandcalcsDocTemplate(BaseDocTemplate):
    """A doc template that turns heading paragraphs' ``hc_outline`` into PDF bookmarks."""

    def __init__(self, filename, *, footer: str = "", footer_font: str = "DejaVuSans",
                 footer_color=None, frame_width: Optional[float] = None, **kwargs):
        super().__init__(filename, **kwargs)
        page_width, page_height = self.pagesize
        width = frame_width or (page_width - self.leftMargin - self.rightMargin)
        left = (page_width - width) / 2 if frame_width else self.leftMargin
        frame = Frame(left, self.bottomMargin, width, page_height - self.topMargin - self.bottomMargin, id="calcs")
        self.footer = footer
        self.footer_font = footer_font
        self.footer_color = footer_color
        self.addPageTemplates([PageTemplate(id="calcs", frames=[frame], onPage=self._draw_footer)])
        self._outline_level = -1

    def _draw_footer(self, canvas, doc) -> None:
        page_width, _ = self.pagesize
        canvas.saveState()
        canvas.setFont(self.footer_font, 7.5)
        if self.footer_color is not None:
            canvas.setFillColor(self.footer_color)
        y = self.bottomMargin / 2
        canvas.drawString(self.leftMargin, y, self.footer)
        canvas.drawRightString(page_width - self.rightMargin, y, f"{doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:
        outline = getattr(flowable, "hc_outline", None)
        if outline is None:
            return
        key, title, level = outline
        # The PDF outline cannot skip a level (e.g. a ### straight after a #).
        level = min(level, self._outline_level + 1)
        self._outline_level = level
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(title, key, level=level, closed=False)


def build_pdf(result: dict, path: str | pathlib.Path, *, title: str = "", pagesize=letter,
              frame_width: Optional[float] = None, margin: float = 54, palette=None,
              theme_color=None) -> pathlib.Path:
    """
    Write ``result["story"]`` to ``path``. ``frame_width`` centres a narrower
    text frame on the page (e.g. 252 pt to preview a half-width column). The
    story list is copied, because ReportLab's ``build`` consumes it.
    ``palette``/``theme_color`` only colour the footer; match the renderer's.
    """
    from .styles import Palette

    if palette is not None and theme_color is not None:
        raise ValueError("pass either palette or theme_color, not both")
    if palette is None:
        palette = Palette() if theme_color is None else Palette.from_theme(theme_color)
    path = pathlib.Path(path)
    doc = HandcalcsDocTemplate(
        str(path), pagesize=pagesize, leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin, title=title, footer=title,
        footer_color=palette.color("muted"), frame_width=frame_width,
    )
    doc.build(list(result["story"]))
    return path
