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


def run(text: str, upright: bool = False, normal: bool = False, font: str = "") -> str:
    """
    A math run (``m:r``). By default Word italicises its letters, the usual
    look of a variable. ``upright`` sets it in the math font without italics
    (a word identifier, a function name, an operator word); ``normal`` sets it
    as ordinary text (``m:nor``: units, comments, strings). ``font`` is the
    text's formatting (``w:rPr`` content, e.g. ``<w:b/>`` for bold).
    """
    if not text:
        return ""
    if normal:
        props = "<m:rPr><m:nor/></m:rPr>"
    elif upright:
        props = '<m:rPr><m:sty m:val="p"/></m:rPr>'
    else:
        props = ""
    if font:
        props += f"<w:rPr>{font}</w:rPr>"
    return f'<m:r>{props}<m:t xml:space="preserve">{escape(text)}</m:t></m:r>'


def upright(text: str) -> str:
    return run(text, upright=True)


def text(text: str) -> str:
    return run(text, normal=True)


# The text formatting of each kind of prose span (see ``renderers.prose``).
PROSE_FONTS = {
    "text": "",
    "code": '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>',
    "strong": "<w:b/>",
    "em": "<w:i/>",
}


def prose(text: str) -> str:
    """
    Text runs for a comment written as prose: ``**bold**`` is bold, ``*italic*``
    italic and a `backtick` span in a code font.
    """
    from handcalcs.renderers.prose import prose_spans

    return "".join(
        run(span.text, normal=True, font=PROSE_FONTS[span.kind])
        for span in prose_spans(text)
    )


def element(tag: str, *children: str) -> str:
    return f"<m:{tag}>{''.join(children)}</m:{tag}>"


def e(*parts: str) -> str:
    """An ``m:e`` argument slot."""
    return element("e", *parts)


def sub(base: str, subscript: str) -> str:
    return f"<m:sSub>{e(base)}{element('sub', subscript)}</m:sSub>"


def sup(base: str, superscript: str) -> str:
    return f"<m:sSup>{e(base)}{element('sup', superscript)}</m:sSup>"


def sub_sup(base: str, subscript: str, superscript: str) -> str:
    """A base with both a subscript and a superscript, stacked (``m:sSubSup``)."""
    return (
        f"<m:sSubSup>{e(base)}{element('sub', subscript)}"
        f"{element('sup', superscript)}</m:sSubSup>"
    )


def acc(base: str, char: str) -> str:
    """An accent over a base: ``char`` is a combining mark (U+0302 is a hat)."""
    return f'<m:acc><m:accPr><m:chr m:val="{char}"/></m:accPr>{e(base)}</m:acc>'


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


def matrix(rows: list[list[str]], beg: str = "[", end: str = "]") -> str:
    """A matrix (``m:m``) of OMML cells in growing brackets."""
    body = "".join(element("mr", *(e(cell) for cell in row)) for row in rows)
    return delim(element("m", body), beg, end)


def func(name: str, argument: str) -> str:
    """A function application (``m:func``): ``name`` is set as a function name."""
    return f"<m:func>{element('fName', name)}{e(argument)}</m:func>"


def omath(*parts: str) -> str:
    return element("oMath", *parts)


# The alignment point of an equation-array row: a literal ``&`` run, which Word
# (like pandoc) reads as the column the rows line up on.
ALIGN = "<m:r><m:t>&amp;</m:t></m:r>"


def eq_arr(rows: list[str]) -> str:
    """An equation array (``m:eqArr``): one ``m:e`` per row."""
    return element("eqArr", *(e(row) for row in rows))


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
    is dropped (Word spaces math itself, and bare text is not valid OMML); other
    text keeps its spaces, so a base handler's ``" in "`` still reads as a word.
    """
    if node.tag in _CONTENT_TAGS:
        if node.text is not None:
            if node.text.strip():
                node.insert(0, _text_run(node.text))
            node.text = None
        for child in list(node):
            if child.tail is not None:
                if child.tail.strip():
                    child.addnext(_text_run(child.tail))
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


# --- Width estimate ---------------------------------------------------------
#
# Word's equation arrays (the "aligned" layout) never break, and Google Docs and
# LibreOffice don't break the equations of the "lines" layout, so the renderer
# estimates how wide each equation will be and re-lays out the ones that would
# overrun the text width (see ``WordRenderer.join_math_row``). Widths are in ems
# of the math font (Cambria Math, a little wider than TeX's Computer Modern);
# the estimate is rough, like the LaTeX one.

# Glyph widths; a math run adds the operator spacing on top.
_RELATIONS = {"=": 0.67, "<": 0.67, ">": 0.67, "≤": 0.67, "≥": 0.67, "≠": 0.67}
_RELATIONS |= {"≈": 0.67, "∈": 0.6, "∉": 0.6, "→": 0.9}
_BINOPS = {"+": 0.67, "-": 0.67, "−": 0.67, "×": 0.67, "±": 0.67, "∓": 0.67}
_BINOPS |= {"·": 0.28, "⋅": 0.28, "/": 0.5}
# Space around a relation (5/18 em each side) and a binary operator (4/18 em).
_RELATION_SPACE = 2 * 5 / 18
_BINOP_SPACE = 2 * 4 / 18
_NARROW = set("iljtfrIJ1.,:;'!|()[]")
_WIDE = set("mwMW")
# Scripts and the degree of a radical are set smaller.
SCRIPT_SCALE = 0.7


def _char_width(char: str) -> float:
    if char == "&":  # the alignment point of an equation-array row
        return 0.0
    if char in _NARROW:
        return 0.3
    if char in _WIDE:
        return 0.82
    if char == EM_SPACE:
        return 1.0
    if char == " ":
        return 0.25
    if char.isupper():
        return 0.68
    if char.isdigit():
        return 0.55
    return 0.52


def _run_width(run) -> float:
    props = run.find(f"{{{M_NS}}}rPr")
    normal = props is not None and props.find(f"{{{M_NS}}}nor") is not None
    text = "".join(t.text or "" for t in run.iter(_M_T))
    width = 0.0
    for char in text:
        if char in _RELATIONS:
            width += _RELATIONS[char] + (0 if normal else _RELATION_SPACE)
        elif char in _BINOPS:
            width += _BINOPS[char] + (0 if normal else _BINOP_SPACE)
        else:
            width += _char_width(char)
    return width


def _child(node, tag: str):
    return node.find(f"{{{M_NS}}}{tag}")


def _children_width(node) -> float:
    return sum(_width(child) for child in node)


def _prop(node, prop: str, default: str) -> str:
    """The ``m:val`` of a property of ``node`` (e.g. the ``m:begChr`` of an ``m:d``)."""
    for child in node:
        if child.tag.endswith("Pr"):
            found = _child(child, prop)
            if found is not None:
                return found.get(f"{{{M_NS}}}val", default)
    return default


def _width(node) -> float:
    tag = node.tag.rsplit("}", 1)[-1] if isinstance(node.tag, str) else ""
    if tag == "r":
        return _run_width(node)
    if tag.endswith("Pr") or tag in ("t", ""):
        return 0.0
    if tag == "f":
        num, den = _width(_child(node, "num")), _width(_child(node, "den"))
        if _prop(node, "type", "bar") in ("lin", "skw"):
            return num + den + 0.5
        return max(num, den) + 0.2
    if tag in ("sSup", "sSub"):
        script = _child(node, "sup" if tag == "sSup" else "sub")
        return _width(_child(node, "e")) + SCRIPT_SCALE * _width(script)
    if tag == "sSubSup":
        scripts = max(_width(_child(node, "sub")), _width(_child(node, "sup")))
        return _width(_child(node, "e")) + SCRIPT_SCALE * scripts
    if tag == "rad":
        return (
            _width(_child(node, "e")) + 0.8 + SCRIPT_SCALE * _width(_child(node, "deg"))
        )
    if tag == "d":
        slots = [child for child in node if child.tag == f"{{{M_NS}}}e"]
        brackets = sum(
            _char_width(_prop(node, prop, char)) + 0.1
            for prop, char in (("begChr", "("), ("endChr", ")"))
            if _prop(node, prop, char)
        )
        separators = 0.55 * max(len(slots) - 1, 0)
        return sum(_width(slot) for slot in slots) + brackets + separators
    if tag == "eqArr":
        return max((_width(row) for row in node), default=0.0)
    if tag == "m":
        columns: list[float] = []
        for row in node.iter(f"{{{M_NS}}}mr"):
            for k, cell in enumerate(row):
                width = _width(cell)
                if k < len(columns):
                    columns[k] = max(columns[k], width)
                else:
                    columns.append(width)
        return sum(columns) + 0.5 * max(len(columns) - 1, 0)
    if tag == "func":
        return _width(_child(node, "fName")) + _width(_child(node, "e")) + 0.17
    if tag == "borderBox":
        return _children_width(node) + 0.4
    if tag == "nary":
        limits = max(_width(_child(node, "sub")), _width(_child(node, "sup")))
        return 1.0 + SCRIPT_SCALE * limits + _width(_child(node, "e"))
    return _children_width(node)


def estimate_width(fragment: str) -> float:
    """The estimated width, in ems of the math font, of an OMML fragment."""
    return element_width(to_element(fragment))


def element_width(node) -> float:
    """The estimated width, in ems, of a parsed OMML element (see ``to_element``)."""
    if node is None:
        return 0.0
    return _width(node)


def scale_runs(node, half_points: int) -> None:
    """Set every math run in ``node`` in a font of ``half_points`` / 2 pt."""
    from lxml import etree

    w_rpr, w_sz = f"{{{W_NS}}}rPr", f"{{{W_NS}}}sz"
    for run in node.iter(_M_R):
        rpr = run.find(w_rpr)
        if rpr is None:
            rpr = etree.Element(w_rpr)
            m_rpr = run.find(f"{{{M_NS}}}rPr")
            if m_rpr is not None:
                m_rpr.addnext(rpr)
            else:
                run.insert(0, rpr)
        for tag in (w_sz, f"{{{W_NS}}}szCs"):
            size = rpr.find(tag)
            if size is None:
                size = etree.SubElement(rpr, tag)
            size.set(f"{{{W_NS}}}val", str(half_points))
