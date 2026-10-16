"""
Math-aware line breaking for rendered paragraph markup.

ReportLab breaks a paragraph at any space and never at a non-breaking space
(U+00A0). ``ranked_breaks`` gives every space in a rendered expression a
*rank*: low ranks are good places to break (before a top-level ``+`` or
``and``), high ranks poor ones (inside nested brackets), and ``None`` never
(the space after an operator, so an operator always starts the continuation
line). ``with_breaks(markup, max_rank)`` keeps the spaces up to ``max_rank``
and makes every other one non-breaking.

The rank is ``bracket_depth * CLASSES + operator_class``, so every break
outside brackets beats every break inside them, and within one bracket level
looser-binding operators win:

- class 0: relations and boolean words (``=``, ``→``, ``and``, ``or``, ``in``,
  ``is``, ``not``) and the spaces between plain words (block headers);
- class 1: ``+``, ``-`` and the space after a comma (collections, arguments);
- class 2: ``·``, ``/``, ``//``, ``%``.

Tags (``<font color="...">``) are skipped, so their attribute spaces are never
touched.
"""
from __future__ import annotations

import re
from typing import Optional

NBSP = " "
CLASSES = 3
OPERATOR_CLASS = {
    "=": 0, "→": 0, "and": 0, "or": 0, "in": 0, "is": 0, "not": 0,
    "+": 1, "-": 1, "−": 1,
    "·": 2, "/": 2, "//": 2, "%": 2, "*": 2,
}
OPENERS = "([{"
CLOSERS = ")]}"


def _visible(markup: str) -> list[tuple[int, str]]:
    """``(index, char)`` for every character of ``markup`` outside a tag."""
    chars, in_tag = [], False
    for idx, char in enumerate(markup):
        if char == "<":
            in_tag = True
        elif char == ">" and in_tag:
            in_tag = False
        elif not in_tag:
            chars.append((idx, char))
    return chars


def _token_after(chars: list[tuple[int, str]], pos: int) -> str:
    """The visible token (up to the next space) starting at ``chars[pos]``."""
    token = []
    for _, char in chars[pos:]:
        if char in (" ", NBSP):
            break
        token.append(char)
    return "".join(token)


def ranked_breaks(markup: str) -> dict[int, Optional[int]]:
    """Map the index of every visible space in ``markup`` to its break rank (or None)."""
    chars = _visible(markup)
    ranks: dict[int, Optional[int]] = {}
    depth = 0
    previous_token = ""
    for pos, (idx, char) in enumerate(chars):
        if char in OPENERS:
            depth += 1
        elif char in CLOSERS:
            depth = max(0, depth - 1)
        if char != " ":
            continue
        before = "".join(c for _, c in chars[max(0, pos - 3):pos])
        token_before = previous_token
        token_after = _token_after(chars, pos + 1)
        previous_token = token_after
        if token_before in OPERATOR_CLASS and not before.endswith(","):
            ranks[idx] = None  # keep an operator with its right operand
        elif token_after in OPERATOR_CLASS:
            ranks[idx] = depth * CLASSES + OPERATOR_CLASS[token_after]
        elif before.endswith(","):
            ranks[idx] = depth * CLASSES + 1
        else:
            ranks[idx] = depth * CLASSES
    return ranks


def _first_token(markup: str) -> str:
    chars = _visible(markup)
    return _token_after(chars, 0)


def max_rank(markup: str) -> int:
    ranks = [rank for rank in ranked_breaks(markup).values() if rank is not None]
    return max(ranks, default=0)


def with_breaks(markup: str, allowed: int) -> str:
    """Keep the spaces of rank <= ``allowed`` and make every other one non-breaking."""
    ranks = ranked_breaks(markup)
    out = list(markup)
    for idx, rank in ranks.items():
        if rank is None or rank > allowed:
            out[idx] = NBSP
    return "".join(out)


def unbreakable(markup: str) -> str:
    return with_breaks(markup, -1)


_ITEM_SPLIT = re.compile(r", ")


def elide_collections(markup: str, max_items: int = 10, edge: int = 3) -> str:
    """
    Shorten every bracketed collection with more than ``max_items`` items to its
    first and last ``edge`` items around an ellipsis. Only collections whose
    items contain no nested brackets or tags are touched.
    """
    def shorten(match: re.Match) -> str:
        opener, body, closer = match.group(1), match.group(2), match.group(3)
        items = _ITEM_SPLIT.split(body)
        if len(items) <= max_items:
            return match.group(0)
        kept = items[:edge] + ["…"] + items[-edge:]
        return f"{opener}{', '.join(kept)}{closer}"

    return re.sub(r"([\[{(])([^\[\]{}()<>]*)([\]})])", shorten, markup)
