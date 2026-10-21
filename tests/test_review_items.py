"""
Items S2-S12 of the v2.0rc1 release review (rc1_release_review.md): Python that
rendered as nothing or as garbage, and defaults that surprised.
"""
import io

import pytest

from handcalcs import HandCalcs
from handcalcs.renderers import ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer

TEXT_RENDERERS = [ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer]


def ascii(source: str) -> str:
    return HandCalcs(ASCIIRenderer())(source)


def latex(source: str) -> str:
    return HandCalcs(LatexRenderer())(source)


def word_xml(source: str) -> str:
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    document = HandCalcs(WordRenderer())(source)
    document.save(io.BytesIO())
    return document.element.xml


# --- S2: generator expressions and comprehension filters ------------------------

XS = "xs = [1, 2, 3]\n"


def test_generator_expression_as_the_only_argument():
    assert "s = sum(x² for x in xs) = 14" in ascii(XS + "s = sum(x**2 for x in xs)\n")
    assert (
        "s &= \\operatorname{sum}\\left(x^{2}\;\\mathrm{for}\;x\;\\mathrm{in}\;\\mathrm{xs}\\right) = 14"
        in latex(XS + "s = sum(x**2 for x in xs)\n")
    )


def test_generator_expression_beside_other_arguments_keeps_its_brackets():
    assert "max((x for x in xs), default=0) = 3" in ascii(
        XS + "t = max((x for x in xs), default=0)\n"
    )


def test_comprehension_filters():
    out = ascii(XS + "ys = [x * 2 for x in xs if x > 1 if x < 3]\n")
    assert "ys = [x * 2 for x in xs if x>1 if x<3] = [4]" in out
    assert "\;\\mathrm{if}\;x > 1" in latex(XS + "g = list(x for x in xs if x > 1)\n")


def test_comprehension_with_several_targets():
    out = ascii(XS + "ps = {i: x for i, x in enumerate(xs)}\n")
    assert "{i: x for i, x in enumerate(xs)}" in out


@pytest.mark.parametrize("renderer_class", TEXT_RENDERERS)
def test_generator_expression_renders(renderer_class):
    out = HandCalcs(renderer_class())(XS + "s = sum(x for x in xs if x > 1)\n")
    assert "sum" in out and "5" in out


def test_generator_expression_in_word():
    assert ">for<" in word_xml(XS + "s = sum(x**2 for x in xs)\n").replace(" ", "")
