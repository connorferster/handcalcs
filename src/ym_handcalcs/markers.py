"""
Light-weight values that render handlers put in the master list.

Handlers run before the nesting depth is known, so they return these markers
and ``ReportLabRenderer.join_item`` turns them into flowables. Each marker keeps
the shape the base renderer code expects: ``Tagged`` *is* a ``str``,
``CalcComponents`` *is* a ``list`` of ``str``, and ``Grid`` is neither (so it is
never mistaken for a line or a block).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class Tagged(str):
    """A whole-line string with a kind: 'heading', 'prose', 'import' or 'note'."""

    kind: str
    level: int

    def __new__(cls, text: str, kind: str, level: int = 0) -> "Tagged":
        obj = super().__new__(cls, text)
        obj.kind = kind
        obj.level = level
        return obj


class CalcComponents(list):
    """
    A rendered calc or expression line: ``[col, '=', col, '=', col, comment?]``.
    ``columns`` holds the value columns (target first) and ``comment`` the
    rendered inline comment, or None.
    """

    columns: list[str]
    comment: Optional[str]

    def __init__(self, components: list[str]) -> None:
        super().__init__(components)
        comps = list(components)
        # Columns interleave with the '=' sign, so the components of a line with
        # no comment always have an odd length; a trailing comment makes it even.
        self.comment = comps.pop() if len(comps) % 2 == 0 else None
        self.columns = comps[0::2]


@dataclass
class Grid:
    """A params grid ('params') or a multi-line calc grid ('calc')."""

    kind: str
    rows: list = field(default_factory=list)
