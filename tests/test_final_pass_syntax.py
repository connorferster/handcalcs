"""
Syntax added in the final pre-release pass: conditional expressions, method
calls on an expression (``(a * 3).to("mm")``), dotted call namespaces
(``np.linalg.norm``), skipped ``print`` statements and upright comprehension
keywords.
"""

import pytest

from handcalcs import HandCalcs
from handcalcs.parsing.ast_parser import AST_Parser
from handcalcs.parsing.inline_nodes import FunctionCall, IfExp
from handcalcs.parsing.line_nodes import CalcLine
from handcalcs.parsing.nodes import Name
from handcalcs.renderers.excel import ExcelRenderer
from handcalcs.renderers.excel.rows import CalcRow
from handcalcs.renderers.html import HTMLRenderer
from handcalcs.renderers.latex import LatexRenderer
from handcalcs.renderers.plaintext import PlainTextRenderer


def _render(renderer, source):
    names = {}
    exec(source, names)
    return HandCalcs(renderer)(source, names)


def _last_line(renderer, source):
    return _render(renderer, source).strip().splitlines()[-1]


# --- conditional expressions ---


def test_parser_builds_if_exp():
    line = AST_Parser(globals={"a": 1})("b = 2 if a > 0 else 3\n")[0]
    node = line.expression_tree[0]
    assert isinstance(node, IfExp)
    assert node.is_true is True


def test_if_exp_test_that_cannot_be_evaluated():
    node = AST_Parser(globals={})("b = 2 if a > 0 else 3\n")[0].expression_tree[0]
    assert node.is_true is None


def test_plaintext_if_exp():
    out = _last_line(PlainTextRenderer(), "a = 1\nb = 2 if a > 0 else 3\n")
    assert out == "b = 2 if a>0 else 3 = 2 if 1>0 else 3 = 2"


def test_if_exp_is_parenthesized_as_an_operand():
    out = _last_line(PlainTextRenderer(), "a = 1\nb = 3 * (2 if a > 0 else 3)\n")
    assert out.startswith("b = 3 * (2 if a>0 else 3)")


def test_chained_if_exp_needs_no_parentheses():
    out = _last_line(
        PlainTextRenderer(), "a = 1\nb = 1 if a > 2 else 2 if a > 0 else 3\n"
    )
    assert out.startswith("b = 1 if a>2 else 2 if a>0 else 3 =")
    assert out.endswith("= 2")


def test_latex_if_exp_keywords_are_upright():
    out = _render(LatexRenderer(), "a = 1\nb = 2 if a > 0 else 3\n")
    assert "b &= 2\\;\\mathrm{if}\\;a > 0\\;\\mathrm{else}\\;3" in out


def test_excel_if_exp_is_an_if_formula():
    rows = HandCalcs(ExcelRenderer())("a = 1\nb = 4 * (2 if a > 0 else 3)\n").rows
    calc = [row for row in rows if isinstance(row, CalcRow)][0]
    assert calc.formula == "=4*IF(a>0,2,3)"


# --- method calls on expressions and dotted namespaces (#226) ---


def test_parser_method_on_expression():
    line = AST_Parser(globals={})("b = (a * 3).to('mm')\n")[0]
    call = line.expression_tree[0]
    assert isinstance(call, FunctionCall)
    assert not isinstance(call.namespace, Name)
    assert call.function_name.identifier == "to"


def test_parser_dotted_namespace():
    line = AST_Parser(globals={})("n = np.linalg.norm(x)\n")[0]
    assert line.expression_tree[0].namespace.identifier == "np.linalg"


def test_parser_dotted_attribute():
    import types

    ns = types.SimpleNamespace(inner=types.SimpleNamespace(value=3))
    line = AST_Parser(globals={"ns": ns})("x = ns.inner.value\n")[0]
    attribute = line.expression_tree[0]
    assert attribute.namespace == "ns.inner"
    assert attribute.value == 3


pint = pytest.importorskip("pint")
SOURCE_TO = (
    "import pint\n"
    "ureg = pint.UnitRegistry()  # hc: -i\n"
    "a = 2 * ureg.m\n"
    "b = (a * 3).to('mm')\n"
)


def test_plaintext_method_on_expression():
    out = _last_line(PlainTextRenderer(), SOURCE_TO)
    assert out == "b = (a * 3).to(mm) = (2 meter * 3).to(mm) = 6000 millimeter"


def test_latex_method_on_expression():
    out = _render(LatexRenderer(), SOURCE_TO)
    assert "b &= \\left(a \\cdot 3\\right).\\mathrm{to}\\left(" in out


def test_html_method_on_expression():
    out = _render(HTMLRenderer(), SOURCE_TO)
    assert "(a · 3).to(mm)" in out


def test_numpy_dotted_namespace_renders():
    np = pytest.importorskip("numpy")
    source = "import numpy as np\nx = np.array([3.0, 4.0])\nn = np.linalg.norm(x)\n"
    out = _render(LatexRenderer(), source)
    assert "\\mathrm{np}.\\mathrm{linalg}.\\mathrm{norm}\\left(x\\right)" in out
    assert _last_line(PlainTextRenderer(), source).endswith("= 5")


def test_excel_method_on_expression_is_incompatible():
    from handcalcs.renderers.excel import ExcelRendererIncompatibleError

    source = "a = 2.0\nb = (a * 3).conjugate()\n"
    with pytest.raises(ExcelRendererIncompatibleError, match="no Excel equivalent"):
        HandCalcs(ExcelRenderer())(source)


# --- print statements ---


def test_print_statements_are_skipped():
    source = "J = 2\nprint(J)\nif J > 1:\n    print(f'ok {J}')\n    k = J + 1\n"
    out = _render(PlainTextRenderer(), source)
    assert "print" not in out
    assert "k = J + 1 = 2 + 1 = 3" in out


def test_print_keeps_preceding_comment():
    lines = AST_Parser(globals={})("# A note\nprint(1)\na = 1\n")
    assert [type(line).__name__ for line in lines] == ["CommentLine", "CalcLine"]


# --- comprehension keywords ---


def test_latex_comprehension_keywords_are_upright():
    out = _render(LatexRenderer(), "ts = [1, 2]\nsq = [t**2 for t in ts]\n")
    assert "[t^{2}\\;\\mathrm{for}\\;t\\;\\mathrm{in}\\;\\mathrm{ts}]" in out


def test_latex_set_comprehension_braces_are_escaped():
    out = _render(LatexRenderer(), "ts = [1, 2]\nss = {t for t in ts}\n")
    assert "\\{t\\;\\mathrm{for}\\;t\\;\\mathrm{in}\\;\\mathrm{ts}\\}" in out


def test_plaintext_comprehension_unchanged():
    out = _last_line(PlainTextRenderer(), "ts = [1, 2]\nsq = [t**2 for t in ts]\n")
    assert out == "sq = [t² for t in ts] = [1, 4]"
