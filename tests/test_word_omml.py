"""Tests for the OMML string builders of the Word renderer (#222)."""

import pytest

pytest.importorskip("lxml")

from lxml import etree

from handcalcs.renderers.word import omml

M = f"{{{omml.M_NS}}}"


def tags(fragment: str) -> list[str]:
    """The local tag names of a parsed fragment, in document order (root excluded)."""
    root = omml.to_element(fragment)
    return [el.tag.removeprefix(M) for el in root.iter() if el is not root]


def texts(fragment: str) -> list[str]:
    return [t.text for t in omml.to_element(fragment).iter(f"{M}t")]


def test_run_escapes_xml_specials():
    fragment = omml.run("a<b & c>d")
    assert texts(fragment) == ["a<b & c>d"]


def test_run_styles():
    assert "<m:sty" not in omml.run("x")
    assert '<m:sty m:val="p"/>' in omml.upright("max")
    assert "<m:nor/>" in omml.text("kN")
    assert omml.run("") == ""


def test_builders_are_well_formed():
    fragment = "".join(
        [
            omml.sub(omml.run("M"), omml.run("r")),
            omml.sup(omml.run("d"), omml.run("2")),
            omml.frac(omml.run("1"), omml.run("2")),
            omml.rad(omml.run("x")),
            omml.rad(omml.run("27"), omml.run("3")),
            omml.delim(omml.run("a")),
            omml.delim_items([omml.run("1"), omml.run("2")], "[", "]"),
            omml.func(omml.upright("sin"), omml.run("x")),
        ]
    )
    assert tags(fragment).count("r") == 14
    for tag in ("sSub", "sSup", "f", "rad", "d", "func"):
        assert tag in tags(fragment)


def test_delim_open_and_close_pair_up():
    fragment = omml.delim_open() + omml.run("a") + omml.DELIM_CLOSE
    assert fragment == omml.delim(omml.run("a"))
    root = omml.to_element(fragment)
    (d,) = root.iter(f"{M}d")
    assert len(d.findall(f"{M}e")) == 1


def test_delim_items_one_slot_per_item_with_separator():
    root = omml.to_element(omml.delim_items([omml.run("a"), omml.run("b")]))
    (d,) = root.iter(f"{M}d")
    assert len(d.findall(f"{M}e")) == 2
    assert d.find(f"{M}dPr/{M}sepChr").get(f"{M}val") == ","


def test_empty_delim_items_still_valid():
    assert tags(omml.delim_items([])) == ["d", "dPr", "begChr", "endChr", "sepChr", "e"]


def test_rad_hides_degree_for_square_root():
    root = omml.to_element(omml.rad(omml.run("x")))
    assert root.find(f".//{M}degHide").get(f"{M}val") == "1"


def test_bare_text_becomes_runs():
    # A base handler joins components with bare text (the assignment, commas).
    fragment = f"{omml.run('a')}={omml.run('b')}, {omml.frac('1', '2')}"
    assert texts(fragment) == ["a", "=", "b", ", ", "1", "2"]
    root = omml.to_element(fragment)
    assert all(el.tail is None for el in root.iter())
    assert root.text is None


def test_whitespace_only_text_is_dropped():
    fragment = f"  {omml.run('a')}   {omml.run('b')} "
    assert texts(fragment) == ["a", "b"]


def test_bare_text_inside_slots():
    root = omml.to_element(omml.frac("x", "y"))
    assert [t.text for t in root.iter(f"{M}t")] == ["x", "y"]


def test_plain_text():
    assert omml.plain_text(omml.run("-3")) == "-3"
    assert omml.plain_text(omml.run("a<b")) == "a<b"
    assert omml.plain_text(omml.frac(omml.run("-1"), omml.run("2"))) == "-12"


def test_to_element_serialises_in_math_namespace():
    xml = etree.tostring(omml.to_element(omml.run("x"))).decode()
    assert xml.startswith("<m:oMath")


# --- width estimate -----------------------------------------------------------


def test_fraction_is_as_wide_as_its_wider_part():
    wide, narrow = omml.run("abcdef"), omml.run("x")
    assert omml.estimate_width(omml.frac(wide, narrow)) == pytest.approx(
        omml.estimate_width(wide) + 0.2
    )


def test_scripts_are_narrower_than_the_base():
    base = omml.estimate_width(omml.run("x"))
    script = omml.estimate_width(omml.run("2"))
    assert omml.estimate_width(omml.sup(omml.run("x"), omml.run("2"))) == pytest.approx(
        base + omml.SCRIPT_SCALE * script
    )


def test_relations_get_math_spacing_but_text_does_not():
    assert omml.estimate_width(omml.run("=")) > omml.estimate_width(omml.text("="))


def test_alignment_point_has_no_width():
    assert omml.estimate_width(omml.ALIGN) == 0


def test_equation_array_is_as_wide_as_its_widest_row():
    rows = [omml.run("a"), omml.run("abcdef")]
    assert omml.estimate_width(omml.eq_arr(rows)) == pytest.approx(
        omml.estimate_width(rows[1])
    )


def test_scale_runs_sets_the_size_of_every_run():
    element = omml.to_element(omml.upright("sin") + omml.run("x", font="<w:b/>"))
    omml.scale_runs(element, 18)
    w = "{%s}" % omml.W_NS
    runs = list(element.iter(f"{{{omml.M_NS}}}r"))
    assert all(r.find(f"{w}rPr/{w}sz").get(f"{w}val") == "18" for r in runs)
    # w:rPr follows m:rPr in a run, and keeps the bold.
    first = [child.tag.rsplit("}")[-1] for child in runs[0]]
    assert first == ["rPr", "rPr", "t"]
    assert runs[1].find(f"{w}rPr/{w}b") is not None
