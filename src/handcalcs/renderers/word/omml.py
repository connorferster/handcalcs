"""
Builders for Office Math Markup (OMML), the ``m:`` namespace Word stores
equations in.

The Word renderer's node handlers return OMML *fragments* as plain strings, the
way the LaTeX handlers return LaTeX strings, so the base renderer's string
machinery (``infix_binop``, ``render_calcline``, the continuation mark, the
column de-duplication) works unchanged. A fragment need not be well-formed on
its own: ``DELIM_OPEN`` / ``DELIM_CLOSE`` are the two halves of an ``m:d``
bracket and are always used as a pair, like LaTeX's ``\\left(`` / ``\\right)``.

Only ``to_element`` parses XML (with lxml, which python-docx brings in), when a
document is built. It also wraps any bare text a base handler emitted (an ``=``,
a ``,``, a ``.``) in a math run, so handlers can mix plain text and OMML.
"""

from __future__ import annotations

import re
from html import unescape

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = f'xmlns:m="{M_NS}" xmlns:w="{W_NS}"'

EM_SPACE = " "


def escape(text: str) -> str:
    """Escape the XML special characters of text going into an ``m:t``."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def run(text: str, upright: bool = False, normal: bool = False) -> str:
    """
    A math run (``m:r``). By default Word italicises its letters, the usual
    look of a variable. ``upright`` sets it in the math font without italics
    (a word identifier, a function name, an operator word); ``normal`` sets it
    as ordinary text (``m:nor``: units, comments, strings).
    """
    if not text:
        return ""
    if normal:
        props = "<m:rPr><m:nor/></m:rPr>"
    elif upright:
        props = '<m:rPr><m:sty m:val="p"/></m:rPr>'
    else:
        props = ""
    return f'<m:r>{props}<m:t xml:space="preserve">{escape(text)}</m:t></m:r>'


def upright(text: str) -> str:
    return run(text, upright=True)


def text(text: str) -> str:
    return run(text, normal=True)


def element(tag: str, *children: str) -> str:
    return f"<m:{tag}>{''.join(children)}</m:{tag}>"


def e(*parts: str) -> str:
    """An ``m:e`` argument slot."""
    return element("e", *parts)


def sub(base: str, subscript: str) -> str:
    return f"<m:sSub>{e(base)}{element('sub', subscript)}</m:sSub>"


def sup(base: str, superscript: str) -> str:
    return f"<m:sSup>{e(base)}{element('sup', superscript)}</m:sSup>"


def frac(numerator: str, denominator: str) -> str:
    return f"<m:f>{element('num', numerator)}{element('den', denominator)}</m:f>"


def rad(body: str, degree: str = "") -> str:
    """A radical: a square root, or a root of ``degree`` (e.g. a cube root)."""
    if not degree:
        return (
            '<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr>'
            f"<m:deg/>{e(body)}</m:rad>"
        )
    return f"<m:rad>{element('deg', degree)}{e(body)}</m:rad>"


def _delim_props(beg: str, end: str, sep: str = "") -> str:
    props = f'<m:begChr m:val="{escape(beg)}"/><m:endChr m:val="{escape(end)}"/>'
    if sep:
        props += f'<m:sepChr m:val="{escape(sep)}"/>'
    return f"<m:dPr>{props}</m:dPr>"


def delim_open(beg: str = "(", end: str = ")") -> str:
    """The opening half of a growing bracket around one expression."""
    return f"<m:d>{_delim_props(beg, end)}<m:e>"


DELIM_CLOSE = "</m:e></m:d>"


def delim(body: str, beg: str = "(", end: str = ")") -> str:
    """Growing brackets around one expression."""
    return f"{delim_open(beg, end)}{body}{DELIM_CLOSE}"


def delim_items(
    items: list[str], beg: str = "(", end: str = ")", sep: str = ","
) -> str:
    """
    Growing brackets around a list of items (call arguments, a collection), one
    ``m:e`` per item with ``sep`` drawn between them. No items -> empty brackets.
    """
    slots = "".join(e(item) for item in items) or e()
    return f"<m:d>{_delim_props(beg, end, sep)}{slots}</m:d>"


def func(name: str, argument: str) -> str:
    """A function application (``m:func``): ``name`` is set as a function name."""
    return f"<m:func>{element('fName', name)}{e(argument)}</m:func>"


def omath(*parts: str) -> str:
    return element("oMath", *parts)


# --- Parsing ---------------------------------------------------------------

# OMML elements whose children are math content, where bare text becomes a run.
_CONTENT_TAGS = {
    f"{{{M_NS}}}{tag}"
    for tag in ("oMath", "e", "num", "den", "sub", "sup", "deg", "fName", "lim")
}
_M_R = f"{{{M_NS}}}r"
_M_T = f"{{{M_NS}}}t"
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _text_run(content: str):
    from lxml import etree

    r = etree.Element(_M_R)
    t = etree.SubElement(r, _M_T)
    t.text = content
    t.set(_XML_SPACE, "preserve")
    return r


def _wrap_bare_text(node) -> None:
    """
    Turn bare text inside math content into ``m:r`` runs. Whitespace-only text
    is dropped: Word spaces math itself, and a bare space is not valid OMML.
    """
    if node.tag in _CONTENT_TAGS:
        if node.text is not None:
            if node.text.strip():
                node.insert(0, _text_run(node.text.strip()))
            node.text = None
        for child in list(node):
            if child.tail is not None:
                if child.tail.strip():
                    child.addnext(_text_run(child.tail.strip()))
                child.tail = None
    for child in node:
        if child.tag != _M_R:
            _wrap_bare_text(child)


def to_element(fragment: str):
    """
    Parse an OMML fragment into an ``m:oMath`` lxml element, wrapping any bare
    text in runs. The fragment's content need not have a single root.
    """
    from lxml import etree

    root = etree.fromstring(f"<m:oMath {NSMAP}>{fragment}</m:oMath>")
    _wrap_bare_text(root)
    return root


_TAG = re.compile(r"<[^>]*>")


def plain_text(fragment: str) -> str:
    """The text an OMML fragment shows, without its markup (``-3`` for a run of -3)."""
    return unescape(_TAG.sub("", fragment))
