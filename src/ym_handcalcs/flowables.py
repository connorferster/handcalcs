"""Custom flowables used by the ReportLab renderer."""
from __future__ import annotations

from reportlab.platypus import Flowable, Paragraph, Table


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


class _TableHost(Flowable):
    """
    Base for flowables that build a ``Table`` in ``wrap`` (when the frame width
    is known), then draw, split and space as that table.
    """

    align = "LEFT"

    def __init__(self, space_before: float = 0.0, space_after: float = 0.0):
        super().__init__()
        # The frame aligns a flowable by its ``hAlign`` (an instance attribute
        # set by ``Flowable.__init__``, so it must be set after it).
        self.hAlign = self.align
        self.spaceBefore = space_before
        self.spaceAfter = space_after
        self._table: Table | None = None

    def build_table(self, avail_width: float) -> Table:
        raise NotImplementedError

    def wrap(self, avail_width, avail_height):
        self._table = self.build_table(avail_width)
        self.width, self.height = self._table.wrap(avail_width, avail_height)
        return self.width, self.height

    def split(self, avail_width, avail_height):
        table = self.build_table(avail_width)
        return table.split(avail_width, avail_height)

    def draw(self):
        self._table.drawOn(self.canv, 0, 0)


def _column_widths(rows: list[list[Paragraph]], pad: float) -> list[float]:
    ncols = max((len(row) for row in rows), default=0)
    return [
        max((natural_width(row[c]) for row in rows if c < len(row)), default=0.0) + 2 * pad + 0.5
        for c in range(ncols)
    ]


class ParamGrid(_TableHost):
    """
    A params grid: ``id = value [comment]`` groups aligned on ``=``, centred.
    Starts with ``cols`` groups per row and steps down to 1 until it fits.
    """

    align = "CENTER"

    def __init__(self, cells: list, cols: int, styles: dict, table_style, gap: float,
                 pad: float, zebra=None, space_before: float = 0.0, space_after: float = 0.0):
        super().__init__(space_before, space_after)
        self.cells = [cell for cell in cells if cell is not None]
        self.cols = max(1, cols)
        self.styles = styles
        self.table_style = table_style
        self.gap = gap
        self.pad = pad
        self.zebra = zebra
        self.with_comments = any(len(cell) > 3 and cell[3] for cell in self.cells)
        self.cols_used = self.cols

    def _cell_paragraphs(self, cell) -> list[Paragraph]:
        parts = [str(part) for part in cell] + ["", "", "", ""]
        ident, eq, val, comment = parts[:4]
        paras = [
            Paragraph(ident, self.styles["right"]),
            Paragraph(eq, self.styles["center"]),
            Paragraph(val, self.styles["left"]),
        ]
        if self.with_comments:
            paras.append(Paragraph(comment, self.styles["comment"]))
        return paras

    def _table_for(self, cols: int) -> Table:
        per_cell = 4 if self.with_comments else 3
        groups = [self.cells[k:k + cols] for k in range(0, len(self.cells), cols)]
        rows = []
        for group in groups:
            row: list = []
            for idx in range(cols):
                if idx:
                    row.append("")  # spacer column between groups
                if idx < len(group):
                    row.extend(self._cell_paragraphs(group[idx]))
                else:
                    row.extend([""] * per_cell)
            rows.append(row)
        para_rows = [[c if isinstance(c, Paragraph) else Paragraph("", self.styles["left"]) for c in r] for r in rows]
        widths = _column_widths(para_rows, self.pad)
        spacer_cols = [idx * (per_cell + 1) - 1 for idx in range(1, cols)]
        for col in spacer_cols:
            widths[col] = self.gap
        commands = list(self.table_style.getCommands())
        if self.zebra is not None and len(rows) > 2:
            commands.append(("ROWBACKGROUNDS", (0, 0), (-1, -1), [None, self.zebra]))
        return Table(rows, colWidths=widths, style=commands)

    def build_table(self, avail_width: float) -> Table:
        for cols in range(min(self.cols, max(1, len(self.cells))), 0, -1):
            table = self._table_for(cols)
            width, _ = table.wrap(avail_width, 1e6)
            if width <= avail_width + 0.01 or cols == 1:
                self.cols_used = cols
                return table
        raise AssertionError("unreachable")


class CalcGrid(_TableHost):
    """
    A multi-line calc: ``target = sym`` / ``= num`` / ``= result`` rows aligned on
    ``=``. The id and ``=`` columns take their natural width and the value
    column the rest, wrapping inside it when it is too long.
    """

    def __init__(self, rows: list[list[str]], styles: dict, table_style, pad: float,
                 space_before: float = 0.0, space_after: float = 0.0):
        super().__init__(space_before, space_after)
        self.rows = rows
        self.styles = styles
        self.table_style = table_style
        self.pad = pad

    def build_table(self, avail_width: float) -> Table:
        rows = [
            [Paragraph(ident, self.styles["right"]), Paragraph(eq, self.styles["center"]),
             Paragraph(val, self.styles["value"])]
            for ident, eq, val in self.rows
        ]
        widths = _column_widths(rows, self.pad)
        widths[2] = max(self.pad * 4, min(widths[2], avail_width - widths[0] - widths[1]))
        return Table(rows, colWidths=widths, style=self.table_style)
