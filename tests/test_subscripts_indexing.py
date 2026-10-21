"""
Index and key lookups (``xs[0]``, ``loads["dead"]``, ``A[i, j]``): the
``Subscript`` node, the element lookup without ``eval``, and how each renderer
shows it.
"""
from collections import deque

import pytest

from handcalcs import HandCalcs
from handcalcs.parsing.nodes import Constant, Name, Slice, Subscript
from handcalcs.parsing.null_values import NoValue
from handcalcs.parsing.sequence import HcSequence
from handcalcs.renderers import ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer

np = pytest.importorskip("numpy")


def parse_expression(source: str, namespace: dict | None = None):
    """The expression tree of the last line of 'source', run in 'namespace'."""
    namespace = {} if namespace is None else namespace
    exec(source, namespace)
    sequence = HcSequence.from_source(source, hc_globals=namespace, hc_locals={})
    block = sequence.sequence[-1]
    line = block.lines[-1] if hasattr(block, "lines") else block
    return line.expression_tree[0]


def render(renderer, source: str, namespace: dict | None = None) -> str:
    if namespace is None:
        return HandCalcs(renderer)(source)
    return HandCalcs(renderer)(source, namespace, {})


# --- parsing and the element lookup -----------------------------------------


@pytest.mark.parametrize(
    "source, value, labels",
    [
        ("xs = [1, 2, 3]\ny = xs[0]\n", 1, [("0", False)]),
        ("xs = [1, 2, 3]\ny = xs[-1]\n", 3, [("-1", False)]),
        ("d = {'dead': 5}\ny = d['dead']\n", 5, [("dead", False)]),
        ("d = {'live load': 2}\ny = d['live load']\n", 2, [("live load", False)]),
        ("xs = [1, 2, 3]\ni = 1\ny = xs[i]\n", 2, [("i", True)]),
        ("import numpy as np\nA = np.eye(2)\ni = 1\ny = A[i, 0]\n", 0.0, [("i", True), ("0", False)]),
        ("xs = [1, 2, 3]\ny = xs[1:3]\n", [2, 3], None),
        ("d = {'a-b': 1}\ny = d['a-b']\n", 1, None),
        ("d = {True: 1}\ny = d[True]\n", 1, None),
    ],
)
def test_subscript_node(source, value, labels):
    node = parse_expression(source)
    assert isinstance(node, Subscript)
    assert node.labels == labels
    if isinstance(value, list):
        assert node.value == value
    else:
        assert node.value == value


def test_slice_node():
    node = parse_expression("xs = [1, 2, 3, 4]\ny = xs[1:3:2]\n")
    (index,) = node.index
    assert index == Slice(
        lower=Constant(value=1, source_text="1"),
        upper=Constant(value=3, source_text="3"),
        step=Constant(value=2, source_text="2"),
    )
    assert node.value == [2]


def test_nested_subscripts():
    node = parse_expression("A = [[1, 2], [3, 4]]\ny = A[1][0]\n")
    assert node.value == 3
    assert isinstance(node.container, Subscript)
    assert node.container.value == [3, 4]
    assert node.labels is None  # the container is not a name


def test_dotted_container_and_index():
    source = (
        "from types import SimpleNamespace as N\n"
        "sec = N(props={'A': 1200}, key='A')\n"
        "y = sec.props[sec.key]\n"
    )
    assert parse_expression(source).value == 1200


@pytest.mark.parametrize(
    "source",
    [
        "xs = [1, 2, 3]\ni = 1\ny = xs[i + 1]\n",  # an index that is an expression
        "def f():\n    return [1, 2]\ny = f()[0]\n",  # a container that is a call
    ],
)
def test_no_element_without_evaluating_code(source):
    assert isinstance(parse_expression(source).value, NoValue)


class Counting:
    """A container whose __getitem__ has a side effect."""

    calls = 0

    def __getitem__(self, key):
        Counting.calls += 1
        return 7


def test_user_containers_are_not_indexed_again():
    namespace = {"s": Counting()}
    Counting.calls = 0
    node = parse_expression("y = s[0]\n", namespace)
    assert Counting.calls == 1  # only when the source ran
    assert isinstance(node.value, NoValue)
    # The lookup is shown as written, with the result from the namespace.
    out = render(ASCIIRenderer(), "y = s[0]\n", namespace)
    assert "y = s[0] = 7" in out
    assert Counting.calls == 1


def test_assignment_target():
    out = render(LatexRenderer(), "xs = [1, 2]\nxs[0] = 4\n")
    assert "\\mathrm{xs}_{0} &= 4" in out


# --- display, by renderer -----------------------------------------------------

SOURCE = """\
xs = [1, 2, 3]
loads = {'dead': 5, 'live load': 2}
M_Ed = [90, 120]
alpha = [1, 2]
i = 1
y = xs[0] + xs[-1] + loads['dead'] + loads['live load'] + M_Ed[i] + alpha[i]
"""

DISPLAY = {
    LatexRenderer: (
        "\\mathrm{xs}_{0} + \\mathrm{xs}_{-1} + \\mathrm{loads}_{\\mathrm{dead}}"
        " + \\mathrm{loads}_{\\mathrm{live\\ load}} + M_{\\mathrm{Ed},i} + \\alpha_{i}"
    ),
    MarkdownRenderer: (
        "\\mathrm{xs}_{0} + \\mathrm{xs}_{-1} + \\mathrm{loads}_{\\mathrm{dead}}"
        " + \\mathrm{loads}_{\\mathrm{live\\ load}} + M_{\\mathrm{Ed},i} + \\alpha_{i}"
    ),
    HTMLRenderer: (
        "xs<sub>0</sub> + xs<sub>-1</sub> + loads<sub>dead</sub>"
        " + loads<sub>live load</sub> + M<sub>Ed,i</sub> + α<sub>i</sub>"
    ),
    ASCIIRenderer: "xs[0] + xs[-1] + loads[dead] + loads[live load] + M_Ed[i] + α[i]",
}


@pytest.mark.parametrize("renderer_class", DISPLAY)
def test_symbolic_display(renderer_class):
    assert DISPLAY[renderer_class] in render(renderer_class(), SOURCE)


@pytest.mark.parametrize("renderer_class", DISPLAY)
def test_numeric_column_shows_elements(renderer_class):
    assert "1 + 3 + 5 + 2 + 120 + 2" in render(renderer_class(), SOURCE)


BRACKETS = """\
xs = [1, 2, 3]
i = 1
y = xs[1:3][0] + xs[i + 1]
"""


@pytest.mark.parametrize(
    "renderer_class, symbolic, numeric",
    [
        (ASCIIRenderer, "xs[1:3][0] + xs[i + 1]", "2 + xs[1 + 1]"),
        (HTMLRenderer, "xs[1:3][0] + xs[i + 1]", "2 + xs[1 + 1]"),
        (LatexRenderer, "\\mathrm{xs}[1:3][0] + \\mathrm{xs}[i + 1]", "2 + \\mathrm{xs}[1 + 1]"),
    ],
)
def test_other_lookups_use_brackets(renderer_class, symbolic, numeric):
    out = render(renderer_class(), BRACKETS)
    assert symbolic in out
    assert numeric in out


def test_numpy_two_dimensional_index():
    out = render(LatexRenderer(), "import numpy as np\nA = np.array([[1, 2], [3, 4]])\ny = A[1, 0] * 2\n")
    assert "A_{1,0} \\cdot 2 = 3 \\cdot 2 = 6" in out


def test_format_code_applies_to_the_element():
    out = render(ASCIIRenderer(), "xs = [1.23456, 2.5]\ny = xs[0] * 2  # hc: -f .2f\n")
    assert "y = xs[0] * 2 = 1.23 * 2 = 2.47" in out


def test_subscript_in_an_if_test():
    out = render(ASCIIRenderer(), "xs = [1, 5]\nif xs[1] > 2:\n    z = 1\n")
    assert "(xs[1]>2) -> (5>2)" in out


def test_subscript_in_a_comprehension():
    out = render(ASCIIRenderer(), "xs = [1, 5]\nys = [x * 2 for x in xs[0:2]]\n")
    assert "[x * 2 for x in xs[0:2]]" in out


def test_symbols_option_and_index():
    source = '# hc: symbols = {"F_v": "F_{v}"}\nF_v = [1, 2]\ny = F_v[0]\n'
    assert "y &= F_{v,0} = 1" in render(LatexRenderer(), source)


def test_units_in_a_list():
    pytest.importorskip("pint")
    source = (
        "import pint  # hc: -i\n"
        "ureg = pint.UnitRegistry()  # hc: -i\n"
        "Ls = [2 * ureg.m, 3 * ureg.m]\n"
        "A = Ls[0] * Ls[1]\n"
    )
    out = render(LatexRenderer(), source)
    assert "A &= \\mathrm{Ls}_{0} \\cdot \\mathrm{Ls}_{1} = 2\\ \\mathrm{meter} \\cdot 3\\ \\mathrm{meter}" in out


def test_word_subscript_and_brackets():
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    xml = HandCalcs(WordRenderer())(BRACKETS.replace("y =", "y = xs[0] +")).element.xml
    assert "<m:sSub>" in xml  # xs[0]
    assert '<m:begChr m:val="["/>' in xml  # xs[i + 1]


def test_excel_names_the_lookup():
    pytest.importorskip("xlsxwriter")
    from handcalcs.renderers.excel import ExcelRenderer, ExcelRendererIncompatibleError

    with pytest.raises(ExcelRendererIncompatibleError, match="index or key lookup"):
        HandCalcs(ExcelRenderer())("s = 'abc'\ny = s[0]\n")
