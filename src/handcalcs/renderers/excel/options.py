"""
Validation of the ``ExcelRenderer`` configuration given at instantiation.

Every option is checked here, when the renderer is created, so a bad colour or
sheet name fails immediately instead of when the workbook is written.
"""
from __future__ import annotations
import re
from typing import Any, Optional

# Cell-format keys accepted by ``value_format`` and ``formula_format``.
FORMAT_KEYS = ("bold", "text_color", "cell_color")

# Inputs on a light-yellow fill (the engineering "edit me" convention);
# formulas bold with no fill.
DEFAULT_VALUE_FORMAT = {"bold": False, "text_color": "#000000", "cell_color": "#FFF2CC"}
DEFAULT_FORMULA_FORMAT = {"bold": True, "text_color": "#000000", "cell_color": None}

_HEX_COLOR = re.compile(r"#?([0-9A-Fa-f]{6})")
_SHEET_NAME_FORBIDDEN = set("[]:*?/\\")


def normalize_color(value: Any, option: str) -> Optional[str]:
    """
    Normalize a colour to ``"#RRGGBB"`` (upper case).

    Accepts ``"#RRGGBB"``, ``"RRGGBB"``, an ``(r, g, b)`` tuple/list of 0-255
    ints, or ``None`` (no colour). Anything else raises ``ValueError`` naming
    the option.
    """
    if value is None:
        return None
    if isinstance(value, str):
        match = _HEX_COLOR.fullmatch(value.strip())
        if match:
            return f"#{match.group(1).upper()}"
        raise ValueError(
            f"{option}: {value!r} is not a hex colour; use '#RRGGBB', 'RRGGBB' or an (r, g, b) tuple."
        )
    if isinstance(value, (tuple, list)) and len(value) == 3:
        if all(isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= 255 for c in value):
            return "#{:02X}{:02X}{:02X}".format(*value)
        raise ValueError(f"{option}: {value!r} must hold three ints from 0 to 255.")
    raise ValueError(
        f"{option}: {value!r} is not a colour; use '#RRGGBB', 'RRGGBB' or an (r, g, b) tuple."
    )


def merge_cell_format(user: Optional[dict], defaults: dict, option: str) -> dict:
    """
    Merge a user's cell-format dict over the defaults and validate it.

    Every key is optional; unknown keys raise ``ValueError``.
    """
    if user is None:
        user = {}
    if not isinstance(user, dict):
        raise ValueError(f"{option} must be a dict, not {type(user).__name__}.")
    unknown = set(user) - set(FORMAT_KEYS)
    if unknown:
        raise ValueError(
            f"{option}: unknown key(s) {sorted(unknown)}; expected any of {list(FORMAT_KEYS)}."
        )
    merged = dict(defaults) | user
    if not isinstance(merged["bold"], bool):
        raise ValueError(f"{option}['bold'] must be True or False, not {merged['bold']!r}.")
    for key in ("text_color", "cell_color"):
        merged[key] = normalize_color(merged[key], f"{option}[{key!r}]")
    return merged


def validate_sheet_name(name: Any) -> str:
    """Check a worksheet name against Excel's rules and return it."""
    if not isinstance(name, str) or not name:
        raise ValueError("sheet_name must be a non-empty string.")
    if len(name) > 31:
        raise ValueError(f"sheet_name {name!r} is longer than Excel's 31-character limit.")
    bad = _SHEET_NAME_FORBIDDEN & set(name)
    if bad:
        raise ValueError(f"sheet_name {name!r} contains characters Excel forbids: {sorted(bad)}.")
    if name.startswith("'") or name.endswith("'"):
        raise ValueError(f"sheet_name {name!r} cannot begin or end with an apostrophe.")
    if name.lower() == "history":
        raise ValueError("'History' is a reserved Excel sheet name.")
    return name
