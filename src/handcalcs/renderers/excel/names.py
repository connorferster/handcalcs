"""
Excel defined names for handcalcs variables.

Each assignment target becomes a worksheet-scoped defined name. A Python
identifier is not always a valid Excel name (``x1`` looks like a cell
reference, ``c`` is reserved, Excel names are case-insensitive while Python's
are not), and a variable may be assigned more than once. ``SymbolTable`` maps
each Python identifier to its *current* Excel name as rows are emitted.
"""
from __future__ import annotations
import re
from collections import Counter
from typing import Optional

from .compat import ExcelRendererIncompatibleError

# Anything Excel could read as an A1 reference (letters then digits). Excel only
# treats it as a reference up to column XFD / row 1048576, but mangling every
# such name is simpler and always safe.
_A1_REFERENCE = re.compile(r"[A-Za-z]{1,3}[0-9]+")
# R1C1-style references: R, C, R1, C1, R1C1, RC1, R1C ...
_R1C1_REFERENCE = re.compile(r"[Rr][0-9]*(?:[Cc][0-9]*)?|[Cc][0-9]*")
_RESERVED = {"true", "false"}
MAX_NAME_LENGTH = 255


def is_valid_excel_name(name: str) -> bool:
    """
    True if ``name`` can be an Excel defined name: it starts with a letter or
    underscore, holds only letters, digits, ``_`` and ``.``, does not look like
    a cell reference, and is not ``TRUE``/``FALSE``.
    """
    if not name or len(name) > MAX_NAME_LENGTH:
        return False
    if not (name[0].isalpha() or name[0] == "_"):
        return False
    if not all(ch.isalnum() or ch in "_." for ch in name):
        return False
    if _A1_REFERENCE.fullmatch(name) or _R1C1_REFERENCE.fullmatch(name):
        return False
    return name.lower() not in _RESERVED


def excel_safe_name(identifier: str) -> str:
    """
    Turn a Python identifier into a valid Excel name by appending ``_`` when it
    would otherwise be rejected (``x1`` -> ``x1_``, ``c`` -> ``c_``).
    """
    name = identifier
    if not is_valid_excel_name(name):
        name = f"{name}_"
    if not is_valid_excel_name(name):
        raise ExcelRendererIncompatibleError(
            f"the variable name '{identifier}' cannot be made into an Excel defined name"
        )
    return name


class SymbolTable:
    """
    Maps Python identifiers to worksheet-scoped Excel defined names.

    ``assign`` is called once per emitted row, in sheet order. A variable
    assigned a second time gets a versioned name (``M_u``, then ``M_u_2``), so
    each row keeps its own cell and later formulas reference the latest version.
    Names are unique case-insensitively, as Excel requires (``L`` and ``l`` get
    ``L`` and ``l_``).
    """

    def __init__(self) -> None:
        self._current: dict[str, str] = {}
        self._versions: Counter = Counter()
        self._taken: set[str] = set()

    def assign(self, identifier: str) -> str:
        """Register a new assignment of ``identifier`` and return its Excel name."""
        self._versions[identifier] += 1
        version = self._versions[identifier]
        name = excel_safe_name(identifier)
        if version > 1:
            name = f"{name}_{version}"
        while name.casefold() in self._taken:
            name = f"{name}_"
        self._taken.add(name.casefold())
        self._current[identifier] = name
        return name

    def lookup(self, identifier: str) -> Optional[str]:
        """The current Excel name of ``identifier``, or None if never assigned."""
        return self._current.get(identifier)

    def require(self, identifier: str, node=None) -> str:
        """Like ``lookup`` but raises for a variable not assigned on the sheet."""
        name = self.lookup(identifier)
        if name is None:
            raise ExcelRendererIncompatibleError(
                f"'{identifier}' is used but never assigned on this sheet "
                "(every variable a formula references must be defined in the cell)",
                node,
            )
        return name

    def __contains__(self, identifier: str) -> bool:
        return identifier in self._current
