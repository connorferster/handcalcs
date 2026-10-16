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


class DepthGuides(Flowable):
    """
    Indent ``content`` by ``depth`` levels and draw one thin vertical guide per
    enclosing level in the left margin, like the indent guides of a code
    editor. Each guide also runs through the content's ``spaceBefore`` and
    ``spaceAfter``, so the guides of consecutive lines join into one line.

    The story stays flat (no nested tables), so nested blocks still split across
    pages: ``split`` splits the content and wraps each part again.
    """

    def __init__(self, content: Flowable, depth: int, indent: float, colors: list, line_width: float = 0.8):
        super().__init__()
        self.content = content
        self.depth = depth
        self.indent = indent
        self.colors = colors
        self.line_width = line_width
        self.keepWithNext = content.getKeepWithNext()

    @property
    def offset(self) -> float:
        return self.depth * self.indent

    def _canvas(self):
        return getattr(self, "canv", None)

    def wrap(self, avail_width, avail_height):
        canvas = self._canvas()
        inner = avail_width - self.offset
        if canvas is not None:
            width, height = self.content.wrapOn(canvas, inner, avail_height)
        else:
            width, height = self.content.wrap(inner, avail_height)
        self.width, self.height = width + self.offset, height
        return self.width, self.height

    def split(self, avail_width, avail_height):
        canvas = self._canvas()
        inner = avail_width - self.offset
        if canvas is not None:
            parts = self.content.splitOn(canvas, inner, avail_height)
        else:
            parts = self.content.split(inner, avail_height)
        return [DepthGuides(part, self.depth, self.indent, self.colors, self.line_width) for part in parts]

    def getSpaceBefore(self):
        return self.content.getSpaceBefore()

    def getSpaceAfter(self):
        return self.content.getSpaceAfter()

    def draw(self):
        canvas = self.canv
        bottom = -self.content.getSpaceAfter()
        top = self.height + self.content.getSpaceBefore()
        canvas.saveState()
        canvas.setLineWidth(self.line_width)
        for level in range(1, self.depth + 1):
            x = (level - 1) * self.indent + self.indent * 0.35
            canvas.setStrokeColor(self.colors[(level - 1) % len(self.colors)])
            canvas.line(x, bottom, x, top)
        canvas.restoreState()
        self.content.drawOn(canvas, self.offset, 0)
