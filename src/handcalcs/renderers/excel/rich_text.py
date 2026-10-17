"""
Light ``<sub>``/``<sup>`` markup -> Excel rich-text runs.

The symbolic handlers emit the same lightweight markup as the HTMLRenderer, so
the base string-building helpers (``infix_binop`` and friends) can be reused.
``parse_markup`` turns that markup into ``RichText``: a list of
``(text, style)`` runs, where style is ``None``, ``"sub"`` or ``"sup"``.

Excel allows one level of sub/superscript per character, so nested markup is
flattened: a subscript inside a subscript is joined with ``,``
(``a<sub>b<sub>c</sub></sub>`` -> a, then ``b,c`` subscripted), and any other
nesting keeps the outer style. Text leaves are escaped with ``escape`` before
they are placed in markup, so a literal ``<sub>`` in a string survives.
"""
from __future__ import annotations
import html
import re
from typing import Optional

Run = tuple[str, Optional[str]]
RichText = list[Run]

STYLES = ("sub", "sup")
_TAG = re.compile(r"(</?su[bp]>)")


def escape(text: str) -> str:
    """Escape a text leaf so it cannot be read as markup."""
    return html.escape(text, quote=False)


def parse_markup(markup: str) -> RichText:
    """Parse markup into merged ``(text, style)`` runs."""
    runs: RichText = []
    stack: list[str] = []
    pending_comma = False

    def append(text: str, style: Optional[str]) -> None:
        if not text:
            return
        if runs and runs[-1][1] == style:
            runs[-1] = (runs[-1][0] + text, style)
        else:
            runs.append((text, style))

    for token in _TAG.split(markup):
        if not token:
            continue
        match = re.fullmatch(r"<(/?)(su[bp])>", token)
        if match is None:
            style = stack[0] if stack else None
            if pending_comma:
                append(",", style)
                pending_comma = False
            append(html.unescape(token), style)
        elif match[1]:  # closing tag
            if stack:
                stack.pop()
            pending_comma = False
        else:  # opening tag
            # A subscript nested in a subscript continues the outer one, with a
            # separator before its first character.
            if stack and stack[0] == "sub" and match[2] == "sub":
                pending_comma = True
            stack.append(match[2])
    return runs


def plain_text(rich: RichText) -> str:
    """The text of the runs, styles dropped (for widths and tests)."""
    return "".join(text for text, _ in rich)


def to_markup(rich: RichText) -> str:
    """Runs back to markup (for tests and debugging)."""
    parts = []
    for text, style in rich:
        text = escape(text)
        parts.append(f"<{style}>{text}</{style}>" if style else text)
    return "".join(parts)
