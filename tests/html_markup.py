"""
Helpers for tests that compare the HTMLRenderer's markup.
"""

import re

_SCRIPT = re.compile(r"<su[bp]>")


def var(markup: str) -> str:
    """
    ``markup`` for a name as the HTMLRenderer writes it: the name itself in
    ``<var>`` (italic), its subscripts and superscripts after it.
    ``"N<sub>pl</sub>"`` -> ``"<var>N</var><sub>pl</sub>"``.
    """
    match = _SCRIPT.search(markup)
    end = match.start() if match else len(markup)
    return f"<var>{markup[:end]}</var>{markup[end:]}"


def without_var(html: str) -> str:
    """``html`` without its ``<var>`` tags, for tests about other markup."""
    return html.replace("<var>", "").replace("</var>", "")
