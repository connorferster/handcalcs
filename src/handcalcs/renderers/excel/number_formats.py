"""
Python format specs (handcalcs format codes) -> Excel number formats.

=========  ============
Python     Excel
=========  ============
``.3f``    ``0.000``
``,.2f``   ``#,##0.00``
``.2e``    ``0.00E+00``
``.1%``    ``0.0%``
``d``      ``0``
``.5g``    ``General``
=========  ============

``g``/``n`` (significant figures) have no exact Excel equivalent, so they map to
``general_format`` (``General`` by default). Width, fill and alignment have no
meaning in a cell and are ignored.
"""
from __future__ import annotations
import re
import warnings
from typing import Optional

_FORMAT_SPEC = re.compile(
    r"(?:(?P<fill>.)?(?P<align>[<>=^]))?"
    r"(?P<sign>[+\- ])?"
    r"(?P<z>z)?"
    r"(?P<alt>#)?"
    r"(?P<zero>0)?"
    r"(?P<width>\d+)?"
    r"(?P<grouping>[,_])?"
    r"(?:\.(?P<precision>\d+))?"
    r"(?P<type>[bcdeEfFgGnosxX%])?"
)


def _decimals(precision: int) -> str:
    return "." + "0" * precision if precision > 0 else ""


def to_excel_format(format_code: Optional[str], general_format: str = "General") -> str:
    """
    Map a Python format spec to an Excel number format.

    A spec that does not parse, or uses a presentation type with no Excel
    counterpart (``x``, ``b``, ``s``, ...), falls back to ``general_format``
    with a warning.
    """
    if not format_code:
        return general_format
    match = _FORMAT_SPEC.fullmatch(format_code)
    if match is None:
        warnings.warn(
            f"Format code {format_code!r} is not a Python format spec; using {general_format!r}."
        )
        return general_format
    kind = match["type"]
    precision = int(match["precision"]) if match["precision"] is not None else 6
    integer = "#,##0" if match["grouping"] else "0"

    if kind in (None, "g", "G", "n"):
        return general_format
    if kind in ("f", "F"):
        excel = integer + _decimals(precision)
    elif kind in ("e", "E"):
        excel = "0" + _decimals(precision) + "E+00"
    elif kind == "%":
        excel = integer + _decimals(precision) + "%"
    elif kind == "d":
        excel = integer
    else:
        warnings.warn(
            f"Format code {format_code!r} has no Excel number format; using {general_format!r}."
        )
        return general_format

    if match["sign"] == "+":
        # Excel sections: positive;negative;zero
        excel = f"+{excel};-{excel};{excel}"
    return excel
