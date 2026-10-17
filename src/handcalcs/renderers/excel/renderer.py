from __future__ import annotations
import pathlib
from typing import Optional

from handcalcs.renderers.base import BaseRenderer
from .symbolic import register_symbolic_rules
from .options import (
    DEFAULT_FORMULA_FORMAT,
    DEFAULT_VALUE_FORMAT,
    merge_cell_format,
    validate_sheet_name,
)


class ExcelRenderer(BaseRenderer):
    """
    Renders a HandCalcs sequence as a live, formula-based Excel worksheet.

    Every calculation becomes a real Excel formula that references other rows
    through worksheet-scoped defined names, so editing an input in Excel
    recalculates the sheet.

    Options (all validated here, at instantiation):

    - ``sheet_name``: the worksheet name (Excel's naming rules apply).
    - ``value_format`` / ``formula_format``: dicts with any of ``bold``,
      ``text_color`` and ``cell_color``, merged over the defaults. The value
      format styles the value cell of param rows (the inputs); the formula format
      styles the formula cell of calc rows. Colours are ``"#RRGGBB"``,
      ``"RRGGBB"`` or an ``(r, g, b)`` tuple.
    - ``filepath``: if given, ``complete()`` also saves the workbook there.
    - ``general_format``: the Excel number format used for format codes that
      have no exact Excel equivalent (e.g. the default ``.5g``).
    """
    name = 'excel'

    def __init__(
        self,
        sheet_name: str = "Calculations",
        value_format: Optional[dict] = None,
        formula_format: Optional[dict] = None,
        filepath: Optional[str | pathlib.Path] = None,
        general_format: str = "General",
    ) -> None:
        super().__init__()
        self.sheet_name = validate_sheet_name(sheet_name)
        self.value_format = merge_cell_format(value_format, DEFAULT_VALUE_FORMAT, "value_format")
        self.formula_format = merge_cell_format(formula_format, DEFAULT_FORMULA_FORMAT, "formula_format")
        self.filepath = pathlib.Path(filepath) if filepath is not None else None
        if not isinstance(general_format, str) or not general_format:
            raise ValueError("general_format must be a non-empty Excel number format string.")
        self.general_format = general_format

    def __repr__(self) -> str:
        return f"ExcelRenderer(sheet_name={self.sheet_name!r})"


register_symbolic_rules(ExcelRenderer)
