"""
Excel defined names for handcalcs variables.

Each assignment target becomes a worksheet-scoped defined name. Excel's naming
rules are stricter than Python's (no names that look like cell references, no
single ``c``/``r``), so identifiers are mangled into valid names here. A
``SymbolTable`` tracks the *current* Excel name of every Python identifier as
rows are emitted, versioning reassigned variables (``M_u``, ``M_u_2``).
"""

from __future__ import annotations
import re
from typing import Any, Optional

from .compat import ExcelRendererIncompatibleError

# Excel's limit on the length of a defined name.
MAX_NAME_LENGTH = 255

# A1-style references: 1-3 letters then digits (column XFD = 16384 at most,
# but Excel rejects anything shaped like a reference, so match the shape).
_A1_REF = re.compile(r"[A-Za-z]{1,3}[0-9]+")
# R1C1-style references: R, C, R1, C1, R1C1, RC1, R1C ...
_R1C1_REF = re.compile(r"[Rr][0-9]*[Cc]?[0-9]*|[Cc][0-9]*")
# Characters Excel allows after the first one.
_VALID_CHARS = re.compile(r"[A-Za-z0-9_.\\]+")
# Characters a name may start with (Unicode letters are allowed too).
_VALID_FIRST = re.compile(r"[A-Za-z_\\]")


# Names Excel reserves (boolean literals).
_RESERVED = {"true", "false"}


def _is_cell_reference(name: str) -> bool:
    return bool(_A1_REF.fullmatch(name) or _R1C1_REF.fullmatch(name))


def _is_reserved(name: str) -> bool:
    return _is_cell_reference(name) or name.lower() in _RESERVED


def _is_valid_char(char: str) -> bool:
    return bool(_VALID_CHARS.fullmatch(char)) or char.isalpha()


def is_valid_excel_name(name: str) -> bool:
    """True if Excel accepts ``name`` as a defined name."""
    if not name or len(name) > MAX_NAME_LENGTH:
        return False
    first = name[0]
    if not (_VALID_FIRST.fullmatch(first) or first.isalpha()):
        return False
    if not all(_is_valid_char(c) for c in name):
        return False
    return not _is_reserved(name)


def to_excel_name(identifier: str) -> str:
    """
    Convert a Python identifier to a valid Excel defined name.

    Python identifiers are already made of letters, digits and ``_``; the only
    problem is names that look like cell references (``x1``, ``AB12``, ``R1C1``),
    the single letters ``c``/``r``, and ``TRUE``/``FALSE``. Those get a trailing
    ``_`` (``x1`` -> ``x1_``), which no reference can end with.
    """
    if not isinstance(identifier, str) or not identifier:
        raise ExcelRendererIncompatibleError(f"{identifier!r} is not a variable name")
    if not all(_is_valid_char(c) for c in identifier):
        raise ExcelRendererIncompatibleError(
            f"the variable name '{identifier}' contains characters Excel names cannot hold"
        )
    name = identifier
    if _is_reserved(name):
        name += "_"
    if not is_valid_excel_name(name):
        raise ExcelRendererIncompatibleError(
            f"the variable name '{identifier}' cannot be made into a valid Excel name"
        )
    return name


class SymbolTable:
    """
    Maps Python identifiers to their current Excel defined names.

    ``assign(identifier)`` is called once per row that assigns a variable and
    returns the Excel name for that row. The first assignment uses the mangled
    identifier; each reassignment gets a new versioned name (``M_u_2``,
    ``M_u_3``) so earlier rows keep their own values and later formulas
    reference the latest one. ``lookup(identifier)`` returns the current name
    and raises if the variable was never assigned on the sheet.

    Excel names are case-insensitive, so collisions are checked without case.
    """

    def __init__(self) -> None:
        self._current: dict[str, str] = {}
        self._counts: dict[str, int] = {}
        self._taken: set[str] = set()

    def __contains__(self, identifier: str) -> bool:
        return identifier in self._current

    def __repr__(self) -> str:
        return f"SymbolTable({self._current!r})"

    @property
    def names(self) -> dict[str, str]:
        """A copy of identifier -> current Excel name."""
        return dict(self._current)

    def _claim(self, candidate: str) -> str:
        """Return ``candidate``, or the first free ``candidate_N`` (N >= 2)."""
        name = candidate
        n = 2
        while name.lower() in self._taken or not is_valid_excel_name(name):
            name = f"{candidate}_{n}"
            n += 1
        self._taken.add(name.lower())
        return name

    def assign(self, identifier: str) -> str:
        """Register an assignment to ``identifier`` and return its Excel name."""
        base = to_excel_name(identifier)
        count = self._counts.get(identifier, 0) + 1
        self._counts[identifier] = count
        candidate = base if count == 1 else f"{base}_{count}"
        name = self._claim(candidate)
        self._current[identifier] = name
        return name

    def lookup(self, identifier: str, node: Any = None) -> str:
        """The current Excel name of ``identifier``; raises if never assigned."""
        try:
            return self._current[identifier]
        except KeyError:
            raise ExcelRendererIncompatibleError(
                f"'{identifier}' is used before it is assigned on the sheet; "
                f"every variable in a formula must be defined in the same cell",
                node,
            ) from None

    def get(self, identifier: str) -> Optional[str]:
        """The current Excel name of ``identifier``, or ``None``."""
        return self._current.get(identifier)


def quote_sheet_name(sheet_name: str) -> str:
    """Quote a sheet name for use in a reference: ``'My sheet'``."""
    return "'" + sheet_name.replace("'", "''") + "'"


def scoped_name(sheet_name: str, name: str) -> str:
    """A worksheet-scoped defined name, as XlsxWriter's ``define_name`` expects."""
    return f"{quote_sheet_name(sheet_name)}!{name}"
