"""
A pint quantity of a numpy array (issue #384) is drawn by handcalcs like any
numpy array, with its units after it as a scalar quantity shows them: the
format code and ``max_items`` apply to its elements in every renderer. (pint's
own LaTeX format put the format code in place of each element, ``.5g``.)
"""

import pytest

np = pytest.importorskip("numpy")
pint = pytest.importorskip("pint")

from handcalcs import HandCalcs  # noqa: E402
from handcalcs.parsing.nodes import ArrayQuantity, Constant, List, Matrix  # noqa: E402
from handcalcs.renderers import (  # noqa: E402
    ASCIIRenderer,
    HTMLRenderer,
    LatexRenderer,
    MarkdownRenderer,
)
from handcalcs.renderers.base import _reify  # noqa: E402

ureg = pint.UnitRegistry()
ureg.formatter.default_format = "~P"


def render(renderer, source: str):
    """Render ``source``, run here so the arrays and registry need no imports in it."""
    namespace = {"array": np.array, "arange": np.arange, "ureg": ureg}
    exec(source, namespace)
    return HandCalcs(renderer)(source, namespace, namespace)


ISSUE = "F = array([2, 4]) * ureg.kN\nl_1 = array([10, 5]) * ureg.mm\nM_1 = F * l_1\n"


@pytest.mark.parametrize(
    "renderer_class, expected",
    [
        (ASCIIRenderer, ["[2, 4] kN * [10, 5] mm = [20, 20] kN⋅mm"]),
        (HTMLRenderer, ["[2, 4] kN · [10, 5] mm", "[20, 20] kN⋅mm"]),
        (
            LatexRenderer,
            [
                "[2, 4]\\ \\mathrm{kN} \\cdot [10, 5]\\ \\mathrm{mm}",
                "[20, 20]\\ \\mathrm{kN} \\cdot \\mathrm{mm}",
            ],
        ),
        (MarkdownRenderer, ["[20, 20]\\ \\mathrm{kN} \\cdot \\mathrm{mm}"]),
    ],
)
def test_issue_384_values_shown(renderer_class, expected):
    out = render(renderer_class(), ISSUE)
    assert ".5g" not in out
    for text in expected:
        assert text in out


def test_word_values_shown():
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer
    from handcalcs.testing import output_text

    text = output_text(render(WordRenderer(), ISSUE))
    assert ".5g" not in text
    # The units follow the array as text, abbreviated as the registry's default is.
    assert text.rstrip().endswith("20 20  kN⋅mm")


@pytest.mark.parametrize(
    "renderer_class", [ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer]
)
def test_format_code_applies_to_elements(renderer_class):
    out = render(renderer_class(), "a = array([1.23456, 2.5]) * ureg.m  # hc: -f .2f\n")
    assert "[1.23, 2.50]" in out


@pytest.mark.parametrize(
    "renderer_class, ellipsis",
    [(ASCIIRenderer, "…"), (HTMLRenderer, "…"), (LatexRenderer, "\\ldots")],
)
def test_long_arrays_elided(renderer_class, ellipsis):
    out = render(renderer_class(), "big = arange(20) * ureg.mm\n")
    assert f"[0, 1, 2, {ellipsis}, 17, 18, 19]" in out


def test_matrix_quantity_latex():
    out = render(LatexRenderer(), "A = array([[1, 2], [3, 4]]) * ureg.m\n")
    assert "\\end{bmatrix}\\ \\mathrm{m}" in out


def test_dimensionless_quantity_has_no_units():
    out = render(ASCIIRenderer(), "r = array([1.0, 2.0]) * ureg.m / ureg.m\n")
    assert out.rstrip().endswith("= [1, 2]")


def test_long_unit_names_follow_registry_default():
    registry = pint.UnitRegistry()
    namespace = {"array": np.array, "ureg": registry}
    source = "F = array([2, 4]) * ureg.kN\n"
    exec(source, namespace)
    out = HandCalcs(LatexRenderer())(source, namespace, namespace)
    assert "[2, 4]\\ \\mathrm{kilonewton}" in out


def test_reify_splits_array_from_units():
    node = _reify(np.array([2, 4]) * ureg.kN)
    assert isinstance(node, ArrayQuantity)
    assert isinstance(node.magnitude, List)
    assert node.units == Constant(value=ureg.kN, calculated=True)
    assert isinstance(_reify(np.ones((2, 2)) * ureg.m).magnitude, Matrix)
    # A scalar quantity is still a constant.
    assert isinstance(_reify(3 * ureg.m), Constant)
