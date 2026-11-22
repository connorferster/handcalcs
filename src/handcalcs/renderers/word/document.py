"""
The Word document side of the renderer: the items the handlers put in the
render tree besides plain strings and calc rows, and ``DocumentWriter``, which
writes the tree's items as paragraphs, equations and tables of a python-docx
``Document``.

python-docx (and lxml) are imported only here and in ``omml.to_element``, when a
document is built.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from typing import Any

from . import omml
from ..prose import prose_spans

LAYOUTS = ("aligned", "lines")

# Twips (1/1440 inch) per block level, and the extra indent of a row with no
# left-hand side in the "lines" layout (a continuation or a numeric row).
INDENT = 720
ROW_INDENT = 360
TWIPS_PER_POINT = 20

# An equation still wider than the text after its row is split is set in a
# smaller font, down to MIN_MATH_SCALE of the paragraph's size.
MIN_MATH_SCALE = 0.6
# The left and right margins of a table cell, in ems (Word's 0.08 inch each).
CELL_PADDING = 1.0
DEFAULT_FONT_SIZE = 11.0

MATH_STYLE = "HC Math"
CODE_STYLE = "HC Code"
CODE_FONT = "Consolas"


@dataclass
class Heading:
    text: str
    level: int


@dataclass
class Code:
    """A line of Python source (an import), set in a monospace font."""

    text: str


@dataclass
class ParamsTable:
    """
    A params grid: rows of cells, each ``[id, eq, value, comment]`` or ``None``.
    ``reflow`` is True for a ``# hc: -g`` grid, which may be set in fewer
    columns if it is too wide for the page; a ``;`` grid keeps its rows.
    """

    rows: list
    reflow: bool = False


@dataclass
class CalcGrid:
    """A multiline calc (``-m`` or a line continuation): ``[id, eq, value]`` rows."""

    rows: list


@dataclass
class MathGroup:
    """Opens the body of a CalcsBlock: its rows form one group of equations."""

    layout: str = "aligned"


@dataclass
class Row:
    """One equation row: the left-hand side and the rest from the ``=`` on."""

    lhs: str
    rhs: str


@dataclass
class Prose:
    """A run of text paragraphs inside a math group (e.g. a docstring line)."""

    text: str


def validate_layout(layout: Any) -> str:
    if layout not in LAYOUTS:
        raise ValueError(f"layout must be one of {LAYOUTS}, not {layout!r}")
    return layout


_W_NAMESPACE = {"w": omml.W_NS}

_INLINE_MATH = re.compile(r"(<m:oMath>.*?</m:oMath>)", re.DOTALL)


def inline_math(fragment: str) -> str:
    """Mark an OMML fragment as inline math inside a line of prose."""
    return omml.omath(fragment)


# The w:pPr children that follow w:contextualSpacing, in schema order.
_AFTER_CONTEXTUAL_SPACING = (
    "w:mirrorIndents",
    "w:suppressOverlap",
    "w:jc",
    "w:textDirection",
    "w:textAlignment",
    "w:textboxTightWrap",
    "w:outlineLvl",
    "w:divId",
    "w:cnfStyle",
    "w:rPr",
    "w:sectPr",
    "w:pPrChange",
)


def add_styles(document) -> None:
    """
    Add the renderer's own styles to a document that doesn't define them, so a
    template can restyle equations and code by defining them itself:

    - ``HC Math`` (paragraph, based on Normal): the paragraphs holding display
      equations, 6 pt before and after a group of them. Equations take the
      paragraph's font size.
    - ``HC Code`` (character): the source of an import, in Consolas.
    """
    from docx.enum.style import WD_STYLE_TYPE
    from docx.oxml import OxmlElement
    from docx.shared import Pt

    styles = document.styles
    names = {style.name for style in styles}
    if MATH_STYLE not in names:
        style = styles.add_style(MATH_STYLE, WD_STYLE_TYPE.PARAGRAPH)
        if "Normal" in names:
            style.base_style = styles["Normal"]
        style.paragraph_format.space_before = Pt(6)
        style.paragraph_format.space_after = Pt(6)
        # No space between consecutive equation paragraphs (the "lines" layout).
        ppr = style.element.get_or_add_pPr()
        ppr.insert_element_before(
            OxmlElement("w:contextualSpacing"), *_AFTER_CONTEXTUAL_SPACING
        )
    if CODE_STYLE not in names:
        style = styles.add_style(CODE_STYLE, WD_STYLE_TYPE.CHARACTER)
        style.font.name = CODE_FONT


@dataclass
class DocumentWriter:
    """Appends paragraphs, equations and tables to a python-docx ``Document``."""

    document: Any

    def __post_init__(self) -> None:
        add_styles(self.document)
        self.styles = {style.name for style in self.document.styles}

    def paragraph(self, depth: int = 0, style: str | None = None):
        from docx.shared import Twips

        paragraph = self.document.add_paragraph(style=style)
        if depth:
            paragraph.paragraph_format.left_indent = Twips(INDENT * depth)
        return paragraph

    def font_size(self) -> float:
        """The size, in points, of the equations' paragraph style (``HC Math``)."""
        style = self.document.styles[MATH_STYLE]
        while style is not None:
            if style.font.size is not None:
                return style.font.size.pt
            style = style.base_style
        defaults = self.document.styles.element.find(
            ".//w:docDefaults//w:rPr/w:sz", namespaces=_W_NAMESPACE
        )
        if defaults is not None:
            return int(defaults.get(f"{{{omml.W_NS}}}val")) / 2
        return DEFAULT_FONT_SIZE

    def max_math_width(self, depth: int = 0, extra: int = 0) -> float | None:
        """
        The width, in ems of the equations' font, of the text column at block
        ``depth`` (less ``extra`` twips of indent), or None if the document has
        no page size.
        """
        section = self.document.sections[-1]
        if section.page_width is None:
            return None
        width = section.page_width.pt
        width -= (section.left_margin.pt if section.left_margin else 0) + (
            section.right_margin.pt if section.right_margin else 0
        )
        width -= (INDENT * depth + extra) / TWIPS_PER_POINT
        return max(width, 0) / self.font_size()

    def heading(self, item: Heading) -> None:
        """
        A heading paragraph in the ``Heading N`` style. A template without that
        style gets a bold paragraph instead, with a warning.
        """
        level = min(max(item.level, 1), 9)
        style = f"Heading {level}"
        if style in self.styles:
            self.add_prose_runs(self.document.add_heading("", level=level), item.text)
            return
        warnings.warn(
            f"The Word document has no {style!r} style; the heading "
            f"{item.text!r} is set as a bold paragraph."
        )
        for run in self.add_prose_runs(self.paragraph(), item.text):
            run.bold = True

    def add_prose_runs(self, paragraph, text: str) -> list:
        """
        Add ``text`` to ``paragraph`` as runs of its light markup (see
        ``renderers.prose``): ``**bold**`` bold, ``*italic*`` italic and a
        `backtick` span in the ``HC Code`` style. Returns the runs.
        """
        runs = []
        for span in prose_spans(text):
            if span.kind == "code":
                runs.append(paragraph.add_run(span.text, style=CODE_STYLE))
                continue
            run = paragraph.add_run(span.text)
            if span.kind == "strong":
                run.bold = True
            elif span.kind == "em":
                run.italic = True
            runs.append(run)
        return runs

    def prose(self, text: str, depth: int = 0) -> None:
        """
        A text paragraph. ``text`` may hold inline equations (``inline_math``),
        which become ``m:oMath`` elements between the text runs.
        """
        paragraph = self.paragraph(depth)
        for piece in _INLINE_MATH.split(text):
            if not piece:
                continue
            if piece.startswith("<m:oMath>"):
                inner = piece[len("<m:oMath>") : -len("</m:oMath>")]
                paragraph._p.append(omml.to_element(inner))
            else:
                self.add_prose_runs(paragraph, piece)

    def code(self, item: Code, depth: int = 0) -> None:
        self.paragraph(depth).add_run(item.text, style=CODE_STYLE)

    def line_break(self, depth: int = 0) -> None:
        self.paragraph(depth)

    def page_break(self) -> None:
        self.document.add_page_break()

    def display_math(self, fragment: str, depth: int = 0, extra: int = 0) -> None:
        """
        A paragraph holding one flush-left display equation (``m:oMathPara``).
        An equation estimated wider than the text column is set in a smaller
        font, to fit, but not below ``MIN_MATH_SCALE`` of the normal size.
        """
        from docx.oxml import parse_xml
        from docx.shared import Twips

        paragraph = self.paragraph(depth, style=MATH_STYLE)
        if extra:
            paragraph.paragraph_format.left_indent = Twips(INDENT * depth + extra)
        para = parse_xml(
            f"<m:oMathPara {omml.NSMAP}>"
            '<m:oMathParaPr><m:jc m:val="left"/></m:oMathParaPr></m:oMathPara>'
        )
        equation = omml.to_element(fragment)
        max_width = self.max_math_width(depth, extra)
        width = omml.element_width(equation)
        if max_width and width > max_width:
            scale = max(max_width / width, MIN_MATH_SCALE)
            omml.scale_runs(equation, round(self.font_size() * 2 * scale))
        para.append(equation)
        paragraph._p.append(para)

    def math_group(self, rows: list[Row | Prose], layout: str, depth: int) -> None:
        """
        A CalcsBlock's equations. In the "aligned" layout, each run of rows is
        one equation array aligned before the first ``=`` (a prose row ends the
        run, and a row too wide for the page is an array of its own); in the
        "lines" layout every row is an equation of its own, and a row with no
        left-hand side is indented a little further.
        """
        pending: list[Row] = []
        max_width = self.max_math_width(depth)

        def too_wide(row: Row) -> bool:
            return bool(max_width) and (
                omml.estimate_width(f"{row.lhs}{row.rhs}") > max_width
            )

        def flush() -> None:
            if pending:
                arr = omml.eq_arr(
                    [f"{row.lhs}{omml.ALIGN}{row.rhs}" for row in pending]
                )
                self.display_math(arr, depth)
                pending.clear()

        for row in rows:
            if isinstance(row, Prose):
                flush()
                self.prose(row.text, depth)
            elif layout == "lines":
                self.display_math(
                    f"{row.lhs}{row.rhs}", depth, 0 if row.lhs else ROW_INDENT
                )
            elif too_wide(row):
                # Set on its own, so that only this row is made smaller.
                flush()
                pending.append(row)
                flush()
            else:
                pending.append(row)
        flush()

    def fit_params(self, item: ParamsTable, depth: int = 0) -> list:
        """
        The rows of a params grid: as written if they fit the text column, or
        if the grid is a ``;`` grid; otherwise the cells, in reading order, in
        the most columns that fit (one at the least).
        """
        rows = item.rows
        max_width = self.max_math_width(depth)
        if not item.reflow or not max_width:
            return rows
        cells = [cell for row in rows for cell in row if cell is not None]
        widths = [
            omml.estimate_width("".join(map(str, c))) + CELL_PADDING for c in cells
        ]
        n_cols = max((len(row) for row in rows), default=0)
        for cols in range(n_cols, 1, -1):
            columns = [max(widths[k::cols]) for k in range(min(cols, len(widths)))]
            if sum(columns) <= max_width:
                if cols == n_cols:
                    return rows
                return [cells[k : k + cols] for k in range(0, len(cells), cols)]
        return [[cell] for cell in cells]

    def params_table(self, item: ParamsTable, depth: int = 0) -> None:
        """
        A params grid as a borderless table, one inline equation per cell, so
        the grid keeps its columns. A nested block indents the table.
        """
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml import parse_xml
        from docx.oxml.ns import qn

        rows = self.fit_params(item, depth)
        ncols = max((len(row) for row in rows), default=0)
        if not ncols:
            return
        table = self.document.add_table(rows=len(rows), cols=ncols)
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        if depth:
            # tblPr children keep the schema order: ... jc, tblInd, ...
            table._tbl.tblPr.find(qn("w:jc")).addnext(
                parse_xml(
                    f'<w:tblInd {omml.NSMAP} w:w="{INDENT * depth}" w:type="dxa"/>'
                )
            )
        for i, row in enumerate(rows):
            for j, cell in enumerate(row):
                if cell is None:
                    continue
                paragraph = table.cell(i, j).paragraphs[0]
                paragraph._p.append(omml.to_element("".join(map(str, cell))))
