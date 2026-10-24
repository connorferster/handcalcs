"""
Assignment and loop targets other than a single name: tuple unpacking
(``a, b = 1, 2``), chained assignment (``a = b = 3``) and starred targets.
"""
import io

import pytest

from handcalcs import HandCalcs
from handcalcs.parsing.nodes import Tuple
from handcalcs.parsing.sequence import HcSequence
from handcalcs.renderers import ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer

TEXT_RENDERERS = [ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer]


def ascii(source: str) -> str:
    return HandCalcs(ASCIIRenderer())(source)


def latex(source: str) -> str:
    return HandCalcs(LatexRenderer())(source)


@pytest.mark.parametrize("renderer_class", TEXT_RENDERERS)
@pytest.mark.parametrize(
    "source",
    [
        "a, b = 1, 2\nc = a + b\n",
        "x = [3, 4]\nm, n = x\n",
        "a, *rest = [1, 2, 3]\n",
        "a = b = 3\n",
        "for i, x in enumerate([4, 5]):\n    y = x * i\n",
    ],
)
def test_renders_without_error(renderer_class, source):
    assert HandCalcs(renderer_class())(source)


def test_tuple_target_is_a_bare_tuple():
    source = "a, b = 1, 2\n"
    namespace = {}
    exec(source, namespace)
    line = HcSequence.from_source(source, hc_globals=namespace, hc_locals={}).sequence[0].lines[0]
    (target,) = line.assigns
    assert isinstance(target, Tuple) and target.bare


def test_tuple_unpacking():
    assert "a, b = 1, 2" in ascii("a, b = 1, 2\n")
    assert "c = a + b = 1 + 2 = 3" in ascii("a, b = 1, 2\nc = a + b\n")
    assert "a, b &= 1, 2" in latex("a, b = 1, 2\n")


def test_unpacking_a_variable_shows_its_values():
    assert "m, n = x = [3, 4] = 3, 4" in ascii("x = [3, 4]\nm, n = x\n")


def test_unpacking_a_call():
    assert "u, v = f() = 2, 3" in ascii("def f():\n    return 2, 3\nu, v = f()\n")


def test_list_target_and_subscript_targets():
    assert "p, q = 1, 2" in ascii("[p, q] = [1, 2]\n")
    assert "\\mathrm{xs}_{0}, \\mathrm{xs}_{1} &= 5, 6" in latex("xs = [0, 0]\nxs[0], xs[1] = 5, 6\n")


def test_starred_target():
    assert "a, *rest = 1, *[2, 3]" in ascii("a, *rest = [1, 2, 3]\n")


def test_chained_assignment():
    assert "a = b = 10" in ascii("a = b = 1E1\n")
    assert "a &= b = 10" in latex("a = b = 1E1\n")
    assert "c = a * b = 10 * 10 = 100" in ascii("a = b = 10\nc = a * b\n")


def test_chained_assignment_with_an_expression():
    assert "a = b = 2 * c = 2 * 3 = 6" in ascii("c = 3\na = b = 2 * c\n")


def test_loop_with_several_targets():
    out = ascii("for i, x in enumerate([4, 5]):\n    y = x * i\n")
    assert "Iterating over each i, x in enumerate([4, 5]):" in out


def test_check_on_a_tuple_target_is_ignored():
    assert "a, b = 1, 2" in ascii("a, b = 1, 2  # hc: --check\n")


def test_word():
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    document = HandCalcs(WordRenderer())("a, b = 1, 2\nc = d = 3\nx, *r = [1, 2, 3]\n")
    document.save(io.BytesIO())
    xml = document.element.xml
    assert ">,<" in xml  # the targets are separated by a comma run, without brackets
