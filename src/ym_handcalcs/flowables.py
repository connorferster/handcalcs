"""Custom flowables used by the ReportLab renderer."""
from __future__ import annotations

from reportlab.platypus import Flowable, Paragraph, Table


def natural_width(paragraph: Paragraph) -> float:
    """Width of the widest line of ``paragraph`` when it is not wrapped."""
    paragraph.wrap(1e6, 1e6)
    return max(paragraph.getActualLineWidths0() or [0.0])


def fits_width(paragraph: Paragraph, width: float) -> bool:
    """
    True if ``paragraph`` wrapped at ``width`` has no line wider than the space
    that line has (the first line is offset by ``firstLineIndent``).
    """
    style = paragraph.style
    paragraph.wrap(width, 1e6)
    widths = paragraph.getActualLineWidths0() or [0.0]
    for idx, line_width in enumerate(widths):
        indent = style.leftIndent + (style.firstLineIndent if idx == 0 else 0)
        if line_width > width - indent - style.rightIndent + 0.01:
            return False
    return True


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
        return Table(rows, colWidths=widths, style=commands, hAlign=self.align)

    def build_table(self, avail_width: float) -> Table:
        for cols in range(min(self.cols, max(1, len(self.cells))), 0, -1):
            table = self._table_for(cols)
            width, _ = table.wrap(avail_width, 1e6)
            if width <= avail_width + 0.01 or cols == 1:
                self.cols_used = cols
                return table
        raise AssertionError("unreachable")


def _scaled(style, scale: float):
    if scale == 1:
        return style
    return style.clone(
        f"{style.name}@{scale:g}",
        fontSize=style.fontSize * scale,
        leading=style.leading * scale,
        leftIndent=style.leftIndent * scale,
        firstLineIndent=style.firstLineIndent * scale,
    )


class BreakingParagraph(Flowable):
    """
    A paragraph that wraps only at its best-ranked break points
    (``breaking.ranked_breaks``), allowing worse ones only when a piece between
    breaks is still wider than the frame. Used for block headers, which it can
    also set on a rounded ``background`` (drawn here rather than with the
    style's ``backColor`` so a hanging indent stays inside the box).
    """

    def __init__(self, markup: str, style, background=None, radius: float = 3.0,
                 pad: tuple[float, float] = (4.0, 2.5)):
        super().__init__()
        self.markup = markup
        self.style = style
        self.background = background
        self.radius = radius
        self.pad_x, self.pad_y = pad if background is not None else (0.0, 0.0)
        self.spaceBefore = style.spaceBefore
        self.spaceAfter = style.spaceAfter
        self.keepWithNext = getattr(style, "keepWithNext", 0)
        self._paragraph: Paragraph | None = None

    def _choose(self, inner_width: float) -> Paragraph:
        from .breaking import max_rank, with_breaks

        for rank in range(0, max_rank(self.markup) + 1):
            paragraph = Paragraph(with_breaks(self.markup, rank), self.style)
            if fits_width(paragraph, inner_width):
                return paragraph
        return Paragraph(self.markup, self.style)

    def wrap(self, avail_width, avail_height):
        inner = avail_width - 2 * self.pad_x
        self._paragraph = self._choose(inner)
        _, height = self._paragraph.wrap(inner, avail_height)
        self.width, self.height = avail_width, height + 2 * self.pad_y
        return self.width, self.height

    def split(self, avail_width, avail_height):
        if self.background is not None:
            return []  # a callout header is short; keep it whole
        return self._choose(avail_width).split(avail_width, avail_height)

    def draw(self):
        if self.background is not None:
            canvas = self.canv
            canvas.saveState()
            canvas.setFillColor(self.background)
            canvas.roundRect(0, 0, self.width, self.height, self.radius, stroke=0, fill=1)
            canvas.restoreState()
        self._paragraph.drawOn(self.canv, self.pad_x, self.pad_y)


class CalcLine(Flowable):
    """
    One calc line that picks its layout when it learns the frame width.

    ``columns`` are ``[target, sym, num, result]`` (or fewer) as paragraph
    markup; ``comment`` is the styled inline comment or None. ``wrap`` tries the
    layouts in order and keeps the first that fits:

    1. ``line``: one line (skipped when ``forced_grid``, i.e. ``# hc: -m``);
    2. ``line+comment``: one line, the comment on its own line underneath;
    3. ``grid``: rows aligned on ``=``, no wrapping inside a row;
    4. ``grid:breakN``: wrap value cells at break points up to rank N;
       then ``stack`` / ``stack:breakN``: the same with the target on a row of
       its own (for a target too wide to share its row);
    5. ``grid:elided``: long collections shortened around an ellipsis;
    6. ``shrink``: the above at ``min_scale`` font size;
    7. ``overflow``: the last attempt, wider than the frame.

    The numeric substitution row is never dropped here; that is the author's
    call, per line, with ``# hc: mode="no_num"``.

    ``layout`` records the choice (for the overflow report and tests).
    """

    def __init__(self, columns: list[str], comment, *, forced_grid: bool, styles: dict,
                 result_markup, table_style, pad: float,
                 min_scale: float = 0.85):
        super().__init__()
        self.columns = list(columns)
        self.comment = comment or ""
        self.forced_grid = forced_grid
        self.styles = styles
        self.result_markup = result_markup
        self.table_style = table_style
        self.pad = pad
        self.min_scale = min_scale
        self.has_result = len(self.columns) >= 3
        line_style = styles["line"]
        self.spaceBefore = line_style.spaceBefore
        self.spaceAfter = line_style.spaceAfter
        self.layout = ""
        self._flow = None
        self._cache: dict = {}

    # -- markup ---------------------------------------------------------

    def _values(self, columns: list[str], transform) -> list[str]:
        values = [transform(col) for col in columns]
        if self.has_result and len(values) >= 3:
            values[-1] = self.result_markup(values[-1])
        return values

    def _line_markup(self, columns: list[str], with_comment: bool) -> str:
        from .breaking import unbreakable

        values = self._values(columns, unbreakable)
        text = " = ".join(values)
        if with_comment and self.comment:
            text += f" {self.comment}"
        return text

    # -- layouts ----------------------------------------------------------

    def _line(self, avail_width: float, with_comment: bool, scale: float = 1.0):
        style = _scaled(self.styles["line"], scale)
        markup = self._line_markup(self.columns, with_comment)
        paragraph = Paragraph(markup, style)
        fits = natural_width(paragraph) <= avail_width
        if not with_comment and self.comment:
            comment_style = _scaled(self.styles["line"], scale)
            paragraph = Paragraph(f"{markup}<br/>{self.comment}", comment_style)
        return paragraph, fits

    def _grid(self, avail_width: float, columns: list[str], transform, scale: float = 1.0,
              stacked: bool = False):
        """
        Rows aligned on ``=``: ``target = v1`` / ``= v2`` / ... With ``stacked``,
        the target takes a row of its own (for a target too wide to share a row)
        and every value row starts with ``=``.
        """
        right = _scaled(self.styles["right"], scale)
        center = _scaled(self.styles["center"], scale)
        value_style = _scaled(self.styles["value"], scale)
        values = self._values(columns, transform)
        if len(values) == 1:
            rows = [["", "", values[0]]]
        elif stacked:
            rows = [[values[0], "", ""]] + [["", "=", value] for value in values[1:]]
        else:
            rows = [[values[0], "=", values[1]]] + [["", "=", value] for value in values[2:]]
        if self.comment:
            rows[-1][2] = f"{rows[-1][2]} {self.comment}"
        cells = [[Paragraph(i, right), Paragraph(e, center), Paragraph(v, value_style)] for i, e, v in rows]
        commands = list(self.table_style.getCommands())
        if stacked:
            cells[0][0] = Paragraph(rows[0][0], value_style)
            for row in cells[1:]:
                row[0] = ""
            cells[0][1] = cells[0][2] = ""
            commands.append(("SPAN", (0, 0), (-1, 0)))
            id_width = 2 * self.pad + 0.5
            target_fits = fits_width(cells[0][0], avail_width - 2 * self.pad)
        else:
            id_width = max(natural_width(row[0]) for row in cells) + 2 * self.pad + 0.5
            target_fits = True
        eq_width = max(natural_width(row[1]) for row in cells if isinstance(row[1], Paragraph)) + 2 * self.pad + 0.5
        val_natural = max(natural_width(row[2]) for row in cells[1 if stacked else 0:]) + 2 * self.pad + 0.5
        val_width = min(val_natural, avail_width - id_width - eq_width)
        inner = val_width - 2 * self.pad
        fits = target_fits and inner > 0 and all(
            fits_width(row[2], inner) for row in cells[1 if stacked else 0:]
        )
        table = Table(cells, colWidths=[id_width, eq_width, max(val_width, 4 * self.pad)],
                      style=commands, hAlign="LEFT")
        return table, fits

    def _attempts(self, avail_width: float):
        from .breaking import elide_collections, max_rank, unbreakable, with_breaks

        if not self.forced_grid:
            yield "line", lambda s: self._line(avail_width, True, s)
            if self.comment:
                yield "line+comment", lambda s: self._line(avail_width, False, s)
        column_sets = [("", self.columns)]
        elided = [elide_collections(col) for col in self.columns]
        if elided != self.columns:
            column_sets.append((":elided", elided))
        for suffix, columns in column_sets:
            top = max((max_rank(col) for col in columns), default=0)
            for stacked in (False, True):
                if stacked and len(columns) < 2:
                    continue
                name = f"{'stack' if stacked else 'grid'}{suffix}"
                yield name, lambda s, c=columns, st=stacked: self._grid(avail_width, c, unbreakable, s, st)
                for rank in range(0, top + 1):
                    yield (
                        f"{name}:break{rank}",
                        lambda s, c=columns, r=rank, st=stacked: self._grid(
                            avail_width, c, lambda m: with_breaks(m, r), s, st
                        ),
                    )

    def _choose(self, avail_width: float):
        key = round(avail_width, 2)
        if key in self._cache:
            return self._cache[key]
        attempts = list(self._attempts(avail_width))
        choice = None
        for name, build in attempts:
            flow, fits = build(1.0)
            if fits:
                choice = (name, flow)
                break
        if choice is None:
            for name, build in attempts:
                flow, fits = build(self.min_scale)
                if fits:
                    choice = (f"shrink:{name}", flow)
                    break
        if choice is None:
            name, build = attempts[-1]
            choice = (f"overflow:{name}", build(self.min_scale)[0])
        self._cache[key] = choice
        return choice

    def wrap(self, avail_width, avail_height):
        self.layout, self._flow = self._choose(avail_width)
        self.width, self.height = self._flow.wrap(avail_width, avail_height)
        return self.width, self.height

    # A calc grid with this many rows or fewer is never split across pages.
    keep_rows = 4

    def split(self, avail_width, avail_height):
        _, flow = self._choose(avail_width)
        if isinstance(flow, Table) and len(flow._cellvalues) <= self.keep_rows:
            return []
        return flow.split(avail_width, avail_height)

    def draw(self):
        self._flow.drawOn(self.canv, 0, 0)
