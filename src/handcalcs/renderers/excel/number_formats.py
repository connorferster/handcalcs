"""
Python format specs -> Excel number formats.

handcalcs format codes are Python format specs (``.5g`` by default, or a
``# hc: -f`` override). Fixed, scientific, percent and integer codes have exact
Excel equivalents; ``g`` (and no type) has none, so it maps to the renderer's
``general_format`` (``General`` unless configured). Fill, alignment and width
are layout concerns the worksheet handles itself, so they are ignored.
"""

from __future__ import annotations
import re
import warnings

# [[fill]align][sign][z][#][0][width][grouping][.precision][type]
_FORMAT_SPEC = re.compile(
    r"(?:(?P<fill>.)?(?P<align>[<>=^]))?"
    r"(?P<sign>[-+ ])?"
    r"(?P<z>z)?"
    r"(?P<alt>\#)?"
    r"(?P<zero>0)?"
    r"(?P<width>[0-9]+)?"
    r"(?P<grouping>[,_])?"
    r"(?:\.(?P<precision>[0-9]+))?"
    r"(?P<type>[bcdeEfFgGnosxX%])?"
)

# Python's default precision for the f, e and % types.
_DEFAULT_PRECISION = 6


def _digits(precision: int) -> str:
    return "0." + "0" * precision if precision else "0"


def _with_sign(fmt: str) -> str:
    """Excel shows '-' already; '+' needs explicit positive;negative;zero sections."""
    return f"+{fmt};-{fmt};{fmt}"


def to_excel_number_format(format_code: str, general_format: str = "General") -> str:
    """
    Map a Python format spec to an Excel number format.

    ======  ============
    Python  Excel
    ======  ============
    .3f     0.000
    ,.2f    #,##0.00
    .2e     0.00E+00
    .1%     0.0%
    d       0
    .5g     general_format
    ======  ============

    Unparseable or non-numeric codes (``s``, ``x``, ...) fall back to
    ``general_format`` with a warning.
    """
    if not isinstance(format_code, str):
        warnings.warn(
            f"Format code {format_code!r} is not a string; using {general_format!r}."
        )
        return general_format
    match = _FORMAT_SPEC.fullmatch(format_code)
    if match is None:
        warnings.warn(
            f"Cannot parse format code {format_code!r}; using {general_format!r}."
        )
        return general_format
    kind = match["type"]
    precision = int(match["precision"]) if match["precision"] is not None else None
    integer = "#,##0" if match["grouping"] else "0"

    if kind in (None, "g", "G", "n"):
        return general_format
    if kind in ("f", "F"):
        fmt = (
            integer
            + _digits(precision if precision is not None else _DEFAULT_PRECISION)[1:]
        )
    elif kind in ("e", "E"):
        mantissa = _digits(precision if precision is not None else _DEFAULT_PRECISION)
        fmt = f"{mantissa}E+00"
    elif kind == "%":
        fmt = (
            integer
            + _digits(precision if precision is not None else _DEFAULT_PRECISION)[1:]
            + "%"
        )
    elif kind == "d":
        fmt = integer
    else:
        warnings.warn(
            f"Format code {format_code!r} has no Excel number format; using {general_format!r}."
        )
        return general_format
    return _with_sign(fmt) if match["sign"] == "+" else fmt
