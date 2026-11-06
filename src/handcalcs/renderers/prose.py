"""
The light markup of a comment written as prose (headings, comment lines and inline
comments), shared by the renderers.

``prose_spans`` splits a comment into spans:

- ``code``: a pair of backticks, `` `M_f` `` (an unpaired backtick is text);
- ``strong`` and ``em``: ``**bold**`` and ``*italic*``, as in Markdown. The opening
  marker must start a word (at the start, or after a space or punctuation) and be
  followed by a non-space; the closing marker must end one (be preceded by a
  non-space, and followed by the end, a space or punctuation). So ``w*L**2/8`` and
  ``a * b * c`` stay as written. ``_`` is not emphasis: it is in too many names
  (``a_b``). ``\\*`` is a literal ``*``;
- ``math`` (only with ``math=True``, which the LaTeX and Markdown renderers pass
  unless their ``comment_math`` is off): ``$x^y$`` or ``$$x^y$$``, kept as written for
  the renderer to typeset. As in Pandoc, the opening ``$`` must be followed by a
  non-space and the closing ``$`` preceded by a non-space and not followed by a
  digit, so prices stay text ("costs $5 to $10"). ``\\$`` is a literal ``$``. A span
  with unbalanced braces is text, so it cannot break the document;
- ``text``: everything else.

A span does not nest: the text of a ``strong`` or ``em`` span is plain text. Each
renderer escapes the text of each span for its own format.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

__all__ = ["Span", "prose_spans", "plain_prose"]

SpanKind = Literal["text", "code", "math", "strong", "em"]


@dataclass(frozen=True)
class Span:
    kind: SpanKind
    text: str


def prose_spans(text: str, *, math: bool = False) -> list[Span]:
    """
    The spans of the comment ``text`` (see the module docstring). Neighbouring
    text is one span, and ``"".join`` of the spans' text, with the markers put
    back, is ``text`` again (apart from the backslash of an escape).
    """
    spans: list[Span] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            spans.append(Span("text", "".join(buffer)))
            buffer.clear()

    index = 0
    while index < len(text):
        char = text[index]
        escaped = text[index + 1 : index + 2]
        if char == "\\" and (escaped == "*" or (math and escaped == "$")):
            buffer.append(text[index + 1])
            index += 2
            continue
        found: Optional[tuple[Span, int]] = None
        if char == "`":
            close = text.find("`", index + 1)
            if close != -1:
                found = Span("code", text[index + 1 : close]), close + 1
        elif char == "$" and math:
            found = _math_at(text, index)
            if found is None and text.startswith("$$", index):
                # An unmatched "$$" is text as a pair, not a "$" and a new opener.
                buffer.append("$$")
                index += 2
                continue
        elif char == "*":
            found = _emphasis_at(text, index)
            if found is None and text.startswith("**", index):
                buffer.append("**")
                index += 2
                continue
        if found is None:
            buffer.append(char)
            index += 1
            continue
        flush()
        span, index = found
        spans.append(span)
    flush()
    return spans


def plain_prose(spans: list[Span]) -> str:
    """The spans as text with the emphasis markers removed (code and math kept)."""
    markers = {"code": "`", "math": "$"}
    return "".join(
        f"{markers.get(span.kind, '')}{span.text}{markers.get(span.kind, '')}"
        for span in spans
    )


def _math_at(text: str, index: int) -> Optional[tuple[Span, int]]:
    """The math span opened by the ``$`` (or ``$$``) at ``index``, and its end."""
    delim = "$$" if text.startswith("$$", index) else "$"
    start = index + len(delim)
    if start >= len(text) or text[start].isspace():
        return None
    close = start
    while True:
        close = text.find(delim, close)
        if close == -1:
            return None
        after = close + len(delim)
        if (
            close > start
            and not text[close - 1].isspace()
            and text[close - 1] != "\\"
            and not text[after : after + 1].isdigit()
        ):
            content = text[start:close]
            return (Span("math", content), after) if _balanced(content) else None
        close += 1


def _emphasis_at(text: str, index: int) -> Optional[tuple[Span, int]]:
    """The ``**strong**`` or ``*em*`` span opened at ``index``, and its end."""
    delim = "**" if text.startswith("**", index) else "*"
    if text.startswith("***", index):
        return None
    before = text[index - 1] if index else " "
    if before.isalnum() or before in "*\\":
        return None
    start = index + len(delim)
    if start >= len(text) or text[start].isspace() or text[start] == "*":
        return None
    close = start
    while True:
        close = text.find(delim, close)
        if close == -1:
            return None
        after = close + len(delim)
        following = text[after : after + 1]
        if (
            close > start
            and not text[close - 1].isspace()
            and text[close - 1] not in "*\\"
            and following != "*"
            and not following.isalnum()
        ):
            kind = "strong" if delim == "**" else "em"
            return Span(kind, text[start:close]), after
        close += 1


def _balanced(tex: str) -> bool:
    """True if the unescaped braces of ``tex`` are balanced."""
    depth = 0
    index = 0
    while index < len(tex):
        char = tex[index]
        if char == "\\":
            index += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return False
        index += 1
    return depth == 0
