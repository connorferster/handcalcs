"""
The row model: what the ExcelRenderer produces and the writer lays out.

``ExcelRenderer.render()`` turns a handcalcs sequence into a flat list of these
records. They hold everything the writer needs (names, formulas, cached values,
rich text, formats) and nothing about cell positions, so all handcalcs logic is
testable without opening a workbook.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

from .rich_text import RichText


@dataclass
class CalcRow:
    """``| symbol | = | symbolic | = | formula | unit | comment |``"""
    name: str
    symbol: RichText
    symbolic: RichText
    formula: str
    cached: Any
    number_format: str
    unit: Optional[str] = None
    comment: Optional[str] = None
    hidden: bool = False


@dataclass
class ParamRow:
    """
    ``| symbol | = | comment | = | value | unit |``

    ``formula`` is ``None`` for a literal input (the value cell holds
    ``value``); a calculation forced to the param layout with ``# hc: -p``
    keeps its formula, with ``value`` as the cached result.
    """
    name: str
    symbol: RichText
    value: Any
    number_format: str
    formula: Optional[str] = None
    unit: Optional[str] = None
    comment: Optional[str] = None
    hidden: bool = False


@dataclass
class HeadingRow:
    text: str
    level: int = 1


@dataclass
class CommentRow:
    """One paragraph: the lines of a CommentsBlock (or a docstring)."""
    text: str


@dataclass
class BlankRow:
    """A ``# hc: -b`` line break."""


Row = CalcRow | ParamRow | HeadingRow | CommentRow | BlankRow
