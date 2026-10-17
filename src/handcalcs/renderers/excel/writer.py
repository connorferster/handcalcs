"""
The XlsxWriter backend: lays a list of rows out as a formatted worksheet.

Columns (§4.1 of the plan)::

    calc row   | symbol | = | symbolic | = | formula | unit | comment |
    param row  | symbol | = | comment  | = | value   | unit |

Headings and comment paragraphs are merged across A–E. Every calc and param
row defines a worksheet-scoped name for its column-E cell, which is what the
formulas reference. Formula cells carry the Python result as their cached
value, so viewers that do not recalculate still show numbers.

XlsxWriter is imported lazily so the renderer stays importable without it.
"""
from __future__ import annotations
import io
import math
import pathlib
from typing import Any, Optional

from .names import quote_sheet_name, scoped_name
from .rich_text import RichText, plain_text
from .rows import BlankRow, CalcRow, CommentRow, HeadingRow, ParamRow, Row

SYMBOL, EQ1, MIDDLE, EQ2, VALUE, UNIT, COMMENT = range(7)
MERGE_LAST = VALUE  # headings and paragraphs span A–E

BODY_SIZE = 10
COMMENT_COLOR = "#808080"
# Major-second scale from the 10 pt body, rounded to Excel's 0.5 pt steps.
HEADING_SIZES = {1: 16, 2: 14, 3: 12.5, 4: 11.5}
SCRIPTS = {"sup": 1, "sub": 2}  # XlsxWriter font_script values
LINE_HEIGHT = 1.32  # row height (pt) per font point, per wrapped line

# (min, max) width in characters, per column.
WIDTH_LIMITS = {
    SYMBOL: (6, 30),
    EQ1: (2, 2),
    MIDDLE: (12, 50),
    EQ2: (2, 2),
    VALUE: (10, 20),
    UNIT: (4, 12),
    COMMENT: (10, 60),
}


def heading_size(level: int) -> float:
    return HEADING_SIZES.get(level, HEADING_SIZES[4])


def _import_xlsxwriter():
    try:
        import xlsxwriter
    except ImportError:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "The ExcelRenderer needs XlsxWriter to write workbooks: "
            "pip install handcalcs[excel]"
        ) from None
    return xlsxwriter


class ExcelWorkbook:
    """
    The result of ``ExcelRenderer.complete()``: an .xlsx file in memory, plus
    the ``rows`` it was written from (for inspection and tests).
    """

    def __init__(self, data: bytes, sheet_name: str, rows: Optional[list[Row]] = None) -> None:
        self._data = data
        self.sheet_name = sheet_name
        self.rows = list(rows or [])

    def __repr__(self) -> str:
        return f"ExcelWorkbook(sheet_name={self.sheet_name!r}, size={len(self._data)} bytes)"

    def to_bytes(self) -> bytes:
        return self._data

    def save(self, path: str | pathlib.Path) -> pathlib.Path:
        """Write the workbook to ``path`` and return it as a Path."""
        path = pathlib.Path(path)
        path.write_bytes(self._data)
        return path


class FormatCache:
    """One XlsxWriter Format per distinct property dict (Excel caps the count)."""

    def __init__(self, workbook) -> None:
        self.workbook = workbook
        self._formats: dict[tuple, Any] = {}

    def get(self, **props) -> Any:
        props = {"font_size": BODY_SIZE, **{k: v for k, v in props.items() if v is not None}}
        key = tuple(sorted(props.items()))
        if key not in self._formats:
            self._formats[key] = self.workbook.add_format(props)
        return self._formats[key]


def _user_format(options: dict) -> dict:
    """A value_format/formula_format option dict as XlsxWriter properties."""
    props: dict = {"bold": bool(options.get("bold"))}
    if options.get("text_color"):
        props["font_color"] = options["text_color"]
    if options.get("cell_color"):
        props["bg_color"] = options["cell_color"]
        props["pattern"] = 1
    return props


def _value_text(value: Any) -> str:
    """Roughly how a value displays, for column widths."""
    if isinstance(value, bool):
        return "FALSE" if not value else "TRUE"
    if isinstance(value, float):
        return f"{value:.6g}"
    return "" if value is None else str(value)


class SheetWriter:
    """Writes rows into one worksheet of an open XlsxWriter workbook."""

    def __init__(self, workbook, sheet_name: str, value_format: dict, formula_format: dict) -> None:
        self.workbook = workbook
        self.sheet_name = sheet_name
        self.sheet = workbook.add_worksheet(sheet_name)
        self.formats = FormatCache(workbook)
        self.value_props = _user_format(value_format)
        self.formula_props = _user_format(formula_format)
        self.widths = {col: 0 for col in WIDTH_LIMITS}

    # --- formats ---

    def text_format(self, align: str = "left", **props) -> Any:
        return self.formats.get(align=align, valign="top", **props)

    def comment_format(self) -> Any:
        return self.text_format(italic=True, font_color=COMMENT_COLOR, text_wrap=True)

    # --- cells ---

    def _measure(self, col: int, text: str) -> None:
        longest = max((len(line) for line in text.split("\n")), default=0)
        self.widths[col] = max(self.widths[col], longest)

    def write_rich(self, row: int, col: int, rich: RichText, cell_format: Any) -> None:
        """Write runs as an Excel rich string (a plain string for a single run)."""
        self._measure(col, plain_text(rich))
        if not rich:
            self.sheet.write_blank(row, col, None, cell_format)
            return
        if len(rich) == 1:
            # XlsxWriter needs two fragments for a rich string; one run is a
            # plain string (a lone sub/superscript run is not worth styling).
            self.sheet.write_string(row, col, rich[0][0], cell_format)
            return
        fragments: list = []
        for text, style in rich:
            if style is not None:
                fragments.append(self.formats.get(font_script=SCRIPTS[style]))
            fragments.append(text)
        self.sheet.write_rich_string(row, col, *fragments, cell_format)

    def write_value(self, row: int, value: Any, formula: Optional[str], props: dict, number_format: str) -> None:
        cell_format = self.formats.get(align="right", valign="top", num_format=number_format, **props)
        self._measure(VALUE, _value_text(value))
        if formula is not None:
            if value is None:
                self.sheet.write_formula(row, VALUE, formula, cell_format)
            else:
                self.sheet.write_formula(row, VALUE, formula, cell_format, value)
        elif isinstance(value, bool):
            self.sheet.write_boolean(row, VALUE, value, cell_format)
        elif isinstance(value, (int, float)):
            self.sheet.write_number(row, VALUE, value, cell_format)
        elif isinstance(value, str):
            self.sheet.write_string(row, VALUE, value, cell_format)
        else:
            self.sheet.write_blank(row, VALUE, None, cell_format)

    def define(self, row: int, name: str) -> None:
        reference = f"={quote_sheet_name(self.sheet_name)}!$E${row + 1}"
        self.workbook.define_name(scoped_name(self.sheet_name, name), reference)

    def write_equals(self, row: int) -> None:
        center = self.text_format(align="center")
        self.sheet.write_string(row, EQ1, "=", center)
        self.sheet.write_string(row, EQ2, "=", center)

    def write_unit(self, row: int, unit: Optional[str]) -> None:
        if unit:
            self._measure(UNIT, unit)
            self.sheet.write_string(row, UNIT, unit, self.text_format())

    # --- rows ---

    def write_calc(self, row: int, record: CalcRow) -> None:
        self.write_rich(row, SYMBOL, record.symbol, self.text_format())
        self.write_equals(row)
        self.write_rich(row, MIDDLE, record.symbolic,
                        self.text_format(align="center", text_wrap=True))
        self.write_value(row, record.cached, record.formula, self.formula_props, record.number_format)
        self.write_unit(row, record.unit)
        if record.comment:
            self._measure(COMMENT, record.comment)
            self.sheet.write_string(row, COMMENT, record.comment, self.comment_format())
        self.define(row, record.name)

    def write_param(self, row: int, record: ParamRow) -> None:
        self.write_rich(row, SYMBOL, record.symbol, self.text_format())
        self.write_equals(row)
        if record.comment:
            self._measure(MIDDLE, record.comment)
            self.sheet.write_string(row, MIDDLE, record.comment,
                                    self.text_format(align="center", italic=True,
                                                     font_color=COMMENT_COLOR, text_wrap=True))
        props = self.formula_props if record.formula is not None else self.value_props
        self.write_value(row, record.value, record.formula, props, record.number_format)
        self.write_unit(row, record.unit)
        self.define(row, record.name)

    def write_heading(self, row: int, record: HeadingRow) -> None:
        size = heading_size(record.level)
        cell_format = self.formats.get(bold=True, font_size=size, valign="vcenter")
        self.sheet.merge_range(row, SYMBOL, row, MERGE_LAST, record.text, cell_format)
        self.sheet.set_row(row, round(size * LINE_HEIGHT + 4, 1))

    def write_comment(self, row: int, record: CommentRow) -> None:
        cell_format = self.text_format(text_wrap=True)
        self.sheet.merge_range(row, SYMBOL, row, MERGE_LAST, record.text, cell_format)

    def write_rows(self, rows: list[Row]) -> None:
        paragraphs: list[tuple[int, str]] = []
        wrapped: list[tuple[int, str]] = []
        hidden: list[int] = []
        r = 0
        for record in rows:
            if isinstance(record, CalcRow):
                self.write_calc(r, record)
                wrapped.append((r, plain_text(record.symbolic)))
            elif isinstance(record, ParamRow):
                self.write_param(r, record)
                wrapped.append((r, record.comment or ""))
            elif isinstance(record, HeadingRow):
                self.write_heading(r, record)
            elif isinstance(record, CommentRow):
                self.write_comment(r, record)
                paragraphs.append((r, record.text))
            elif isinstance(record, BlankRow):
                pass
            else:
                raise TypeError(f"Unknown row record: {record!r}")
            if getattr(record, "hidden", False):
                hidden.append(r)
            r += 1
        widths = self.set_widths()
        merged = sum(widths[col] for col in range(SYMBOL, MERGE_LAST + 1))
        # Excel never auto-fits merged rows, and does not re-fit wrapped rows on
        # open, so heights are estimated from text length / column width.
        for row, text in paragraphs:
            self.set_height(row, text, merged)
        for row, text in wrapped:
            self.set_height(row, text, widths[MIDDLE])
        for row in hidden:
            self.sheet.set_row(row, None, None, {"hidden": True})

    def set_height(self, row: int, text: str, width: float) -> None:
        lines = sum(max(1, math.ceil(len(part) / max(width - 1, 1))) for part in text.split("\n"))
        if lines > 1:
            self.sheet.set_row(row, round(lines * BODY_SIZE * LINE_HEIGHT, 1))

    def set_widths(self) -> dict[int, float]:
        widths = {}
        for col, (low, high) in WIDTH_LIMITS.items():
            width = min(max(self.widths[col] + 2, low), high)
            self.sheet.set_column(col, col, width)
            widths[col] = width
        return widths


def write_sheet(workbook, rows: list[Row], sheet_name: str, value_format: dict, formula_format: dict):
    """Write ``rows`` as a new sheet of an open ``xlsxwriter.Workbook``; return the worksheet."""
    writer = SheetWriter(workbook, sheet_name, value_format, formula_format)
    writer.write_rows(rows)
    return writer.sheet


def build_workbook(rows: list[Row], sheet_name: str, value_format: dict, formula_format: dict) -> ExcelWorkbook:
    """A one-sheet workbook of ``rows``, in memory."""
    xlsxwriter = _import_xlsxwriter()
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    write_sheet(workbook, rows, sheet_name, value_format, formula_format)
    workbook.close()
    return ExcelWorkbook(buffer.getvalue(), sheet_name, rows)
