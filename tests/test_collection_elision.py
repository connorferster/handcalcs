"""
Long collections are shortened the same way in every renderer: more than the
``max_items`` render-context field shows the first and last ``edge_items``
around an ellipsis. ``max_items = 0`` shows every item.
"""
import pytest

from handcalcs import HandCalcs
from handcalcs.renderers import ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer

docx = pytest.importorskip("docx")
from handcalcs.renderers.word import WordRenderer  # noqa: E402

LONG = "xs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]\n"

TEXT_RENDERERS = [
    (ASCIIRenderer, "[1, 2, 3, …, 10, 11, 12]"),
    (HTMLRenderer, "[1, 2, 3, …, 10, 11, 12]"),
    (LatexRenderer, "[1, 2, 3, \\ldots, 10, 11, 12]"),
    (MarkdownRenderer, "[1, 2, 3, \\ldots, 10, 11, 12]"),
]


@pytest.mark.parametrize("renderer_class, expected", TEXT_RENDERERS)
def test_default_elides_long_collections(renderer_class, expected):
    assert expected in HandCalcs(renderer_class())(LONG)


@pytest.mark.parametrize("renderer_class, _", TEXT_RENDERERS)
def test_max_items_zero_shows_every_item(renderer_class, _):
    out = HandCalcs(renderer_class())("# hc: max_items = 0\n" + LONG)
    assert "12" in out and "4" in out and "…" not in out and "ldots" not in out


@pytest.mark.parametrize("renderer_class, _", TEXT_RENDERERS)
def test_edge_items(renderer_class, _):
    out = HandCalcs(renderer_class())("# hc: max_items = 4; edge_items = 1\nxs = [1, 2, 3, 4, 5]\n")
    assert ("[1, …, 5]" in out) or ("[1, \\ldots, 5]" in out)


def test_short_collections_are_kept():
    assert "[1, 2, 3]" in HandCalcs(ASCIIRenderer())("xs = [1, 2, 3]\n")


def test_tuples_sets_and_dicts_elide():
    source = "# hc: max_items = 2; edge_items = 1\nt = (1, 2, 3)\nd = {1: 2, 3: 4, 5: 6}\n"
    out = HandCalcs(ASCIIRenderer())(source)
    assert "(1, …, 3)" in out
    assert "{1: 2, …, 5: 6}" in out


def test_word_elides_with_the_same_fields():
    xml_default = HandCalcs(WordRenderer())(LONG).element.xml
    assert "…" in xml_default
    xml_all = HandCalcs(WordRenderer())("# hc: max_items = 0\n" + LONG).element.xml
    assert "…" not in xml_all and ">7<" in xml_all
