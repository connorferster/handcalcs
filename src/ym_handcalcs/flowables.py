"""Custom flowables used by the ReportLab renderer."""
from __future__ import annotations

from reportlab.platypus import Flowable, Paragraph


def natural_width(paragraph: Paragraph) -> float:
    """Width of the widest line of ``paragraph`` when it is not wrapped."""
    paragraph.wrap(1e6, 1e6)
    return max(paragraph.getActualLineWidths0() or [0.0])


class Chip(Flowable):
    """
    A paragraph on a rounded background that is only as wide as its text (up to
    the frame width, where it wraps). Used for imports.
    """

    def __init__(self, paragraph: Paragraph, background, radius: float = 2.5, pad: tuple[float, float] = (3.0, 2.0)):
        super().__init__()
        self.paragraph = paragraph
        self.background = background
        self.radius = radius
        self.pad_x, self.pad_y = pad
        style = paragraph.style
        self.spaceBefore = style.spaceBefore
        self.spaceAfter = style.spaceAfter

    def wrap(self, avail_width, avail_height):
        inner = min(natural_width(self.paragraph) + 0.5, avail_width - 2 * self.pad_x)
        self._inner_width, self._inner_height = self.paragraph.wrap(inner, avail_height)
        self.width = self._inner_width + 2 * self.pad_x
        self.height = self._inner_height + 2 * self.pad_y
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(self.background)
        canvas.roundRect(0, 0, self.width, self.height, self.radius, stroke=0, fill=1)
        canvas.restoreState()
        self.paragraph.drawOn(canvas, self.pad_x, self.pad_y)
