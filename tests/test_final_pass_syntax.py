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
from handcalcs.renderers.ascii import ASCIIRenderer


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
    out = _last_line(ASCIIRenderer(), "a = 1\nb = 2 if a > 0 else 3\n")
    assert out == "b = 2 if a>0 else 3 = 2 if 1>0 else 3 = 2"


def test_if_exp_is_parenthesized_as_an_operand():
    out = _last_line(ASCIIRenderer(), "a = 1\nb = 3 * (2 if a > 0 else 3)\n")
    assert out.startswith("b = 3 * (2 if a>0 else 3)")


def test_chained_if_exp_needs_no_parentheses():
    out = _last_line(
        ASCIIRenderer(), "a = 1\nb = 1 if a > 2 else 2 if a > 0 else 3\n"
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
    out = _last_line(ASCIIRenderer(), SOURCE_TO)
    assert out == 'b = (a * 3).to("mm") = (2 meter * 3).to("mm") = 6000 millimeter'


def test_latex_method_on_expression():
    out = _render(LatexRenderer(), SOURCE_TO)
    assert "b &= \\left(a \\cdot 3\\right).\\mathrm{to}\\left(" in out


def test_html_method_on_expression():
    out = _render(HTMLRenderer(), SOURCE_TO)
    assert '(a · 3).to(“mm”)' in out


def test_numpy_dotted_namespace_renders():
    np = pytest.importorskip("numpy")
    source = "import numpy as np\nx = np.array([3.0, 4.0])\nn = np.linalg.norm(x)\n"
    out = _render(LatexRenderer(), source)
    assert "\\mathrm{np}.\\mathrm{linalg}.\\mathrm{norm}\\left(x\\right)" in out
    assert _last_line(ASCIIRenderer(), source).endswith("= 5")


def test_excel_method_on_expression_is_incompatible():
    from handcalcs.renderers.excel import ExcelRendererIncompatibleError

    source = "a = 2.0\nb = (a * 3).conjugate()\n"
    with pytest.raises(ExcelRendererIncompatibleError, match="no Excel equivalent"):
        HandCalcs(ExcelRenderer())(source)


# --- print statements ---


def test_print_statements_are_skipped():
    source = "J = 2\nprint(J)\nif J > 1:\n    print(f'ok {J}')\n    k = J + 1\n"
    out = _render(ASCIIRenderer(), source)
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
    out = _last_line(ASCIIRenderer(), "ts = [1, 2]\nsq = [t**2 for t in ts]\n")
    assert out == "sq = [t² for t in ts] = [1, 4]"


# --- numpy (#187) ---


def test_numpy_arrays_render_without_truth_value_error():
    pytest.importorskip("numpy")
    source = (
        "import numpy as np\n"
        "a = np.array([1, 2, 3])\n"
        "c = a * 2\n"
        "d = np.sum(a) + 1\n"
        "if d > 3:\n"
        "    h = c + a\n"
    )
    out = _render(ASCIIRenderer(), source)
    assert "c = a * 2 = [1 2 3] * 2 = [2 4 6]" in out
    assert "h = c + a = [2 4 6] + [1 2 3] = [3 6 9]" in out


def test_matrix_multiplication():
    pytest.importorskip("numpy")
    source = "import numpy as np\na = np.array([1.0, 2.0])\nf = a @ a\n"
    assert (
        _last_line(ASCIIRenderer(), source) == "f = a @ a = [1. 2.] @ [1. 2.] = 5"
    )
    assert "f &= a \\mathbin{@} a" in _render(LatexRenderer(), source)


# --- cube root (#225), factorial (#96), infinity (#166) ---

FUNCTIONS = (
    "import math\n"
    "from math import factorial, cbrt\n"
    "x = 27\n"
    "n = 4\n"
    "y = math.cbrt(x)\n"
    "f = math.factorial(n)\n"
    "g = factorial(n + 1) / factorial(n)\n"
    "i = float('inf')\n"
    "k = -math.inf\n"
    "l = 1 / (x + i)\n"
)


def test_plaintext_cbrt_factorial_infinity():
    out = _render(ASCIIRenderer(), FUNCTIONS)
    assert "y = ∛(x) = ∛(27) = 3" in out
    assert "f = n! = 4! = 24" in out
    assert "g = (n + 1)! / n! = (4 + 1)! / 4! = 5" in out
    assert "i = ∞" in out
    assert "k = -math.inf = -∞" in out
    assert "l = 1 / (x + i) = 1 / (27 + ∞) = 0" in out


def test_html_cbrt_factorial_infinity():
    out = _render(HTMLRenderer(), FUNCTIONS)
    assert "y = ∛(x) = ∛(27) =" in out
    assert "g = (n + 1)! / n! = (4 + 1)! / 4! =" in out
    assert '<div class="hc-line">i = ∞</div>' in out


def test_latex_cbrt_factorial_infinity():
    out = _render(LatexRenderer(), FUNCTIONS)
    assert "y &= \\sqrt[3]{x} = \\sqrt[3]{27} = 3" in out
    assert "f &= n! = 4! = 24" in out
    assert "g &= \\frac{\\left(n + 1\\right)!}{n!}" in out
    assert "i &= \\infty" in out
    assert "k &= -\\infty" in out


def test_word_cbrt_and_factorial():
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    doc = _render(WordRenderer(), FUNCTIONS)
    xml = doc.element.xml
    assert "m:deg" in xml  # the cube root's degree
    assert "!</m:t>" in xml


def test_float_inf_is_a_constant():
    line = AST_Parser(globals={})("i = float('-inf')\n")[0]
    assert line.expression_tree[0].value == float("-inf")


def test_excel_cbrt_and_factorial():
    rows = HandCalcs(ExcelRenderer())(
        "import math\nx = -27\nn = 4\ny = math.cbrt(x)\nf = math.factorial(n + 1)\n"
    ).rows
    calcs = {row.name: row for row in rows if isinstance(row, CalcRow)}
    assert calcs["y"].formula == "=SIGN(x)*ABS(x)^(1/3)"
    assert calcs["f"].formula == "=FACT(n+1)"
    assert "(n + 1)!" in str(calcs["f"].symbolic)


def test_excel_infinity_is_incompatible():
    from handcalcs.renderers.excel import ExcelRendererIncompatibleError

    with pytest.raises(ExcelRendererIncompatibleError, match="infinity"):
        HandCalcs(ExcelRenderer())("i = float('inf')\n")


def test_method_named_factorial_is_not_swapped():
    import types

    source = "obj = 1\n"
    names = {"obj": types.SimpleNamespace(factorial=lambda n: n)}
    out = HandCalcs(ASCIIRenderer())("y = obj.factorial(3)\n", names | {"y": 3})
    assert "obj.factorial(3)" in out


# --- page breaks (#233) ---

PAGE_BREAKS = "a = 1\n# hc: --pagebreak\nb = 2  # hc: --pagebreak\nc = 3\n"


def test_pagebreak_command_parses():
    from handcalcs.parsing.line_nodes import CommentCommand

    lines = AST_Parser(globals={})(PAGE_BREAKS)
    breaks = [line for line in lines if isinstance(line, CommentCommand)]
    assert len(breaks) == 2
    assert all(line.commands["page_break"] for line in breaks)


def test_plaintext_pagebreak_is_a_form_feed():
    out = HandCalcs(ASCIIRenderer())(PAGE_BREAKS)
    assert out == "a = 1\n\f\nb = 2\n\f\nc = 3\n"


def test_latex_pagebreak():
    out = HandCalcs(LatexRenderer())(PAGE_BREAKS)
    assert out.count("\\newpage") == 2


def test_markdown_and_html_pagebreak():
    from handcalcs.renderers.markdown import MarkdownRenderer

    assert HandCalcs(MarkdownRenderer())(PAGE_BREAKS).count("break-after: page") == 2
    assert HandCalcs(HTMLRenderer())(PAGE_BREAKS).count('class="hc-page-break"') == 2


def test_word_pagebreak():
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    doc = HandCalcs(WordRenderer())(PAGE_BREAKS)
    assert doc.element.xml.count('w:type="page"') == 2


def test_excel_pagebreak():
    openpyxl = pytest.importorskip("openpyxl")
    import io

    workbook = HandCalcs(ExcelRenderer())(PAGE_BREAKS)
    sheet = openpyxl.load_workbook(io.BytesIO(workbook.to_bytes())).active
    assert [brk.id for brk in sheet.row_breaks.brk] == [1, 2]


def test_pagebreak_does_not_persist():
    out = HandCalcs(ASCIIRenderer())("# hc: --pagebreak\na = 1\nb = 2\n")
    assert out.count("\f") == 1


# --- check marks (#251) ---

CHECKS = (
    "DoU = 0.85\n"
    "ok = DoU <= 1  # hc: --check\n"
    "fail = DoU > 1  # hc: --check\n"
    "plain = DoU > 1\n"
)


def test_plaintext_check_marks():
    # Stripped: a text renderer may pad lines to align them on "=".
    out = [line.strip() for line in _render(ASCIIRenderer(), CHECKS).splitlines()]
    assert out[1] == "ok = DoU<=1 = 0.85<=1 ✓"
    assert out[2] == "fail = DoU>1 = 0.85>1 ✗"
    assert out[3] == "plain = DoU>1 = 0.85>1 = False"


def test_check_on_a_bare_comparison():
    out = _last_line(ASCIIRenderer(), "S = 1.2\nS <= 1.5  # hc: --check\n")
    assert out == "S<=1.5 = 1.2<=1.5 ✓"


def test_standalone_check_applies_to_following_lines():
    out = _render(ASCIIRenderer(), "a = 2\n# hc: --check\nb = a > 1\nc = a + 1\n")
    assert "b = a>1 = 2>1 ✓" in out
    assert "c = a + 1 = 2 + 1 = 3" in out  # not a boolean: unchanged


def test_check_with_kwarg_syntax():
    out = _last_line(ASCIIRenderer(), "a = 2\nb = a > 1  # hc: check = True\n")
    assert out == "b = a>1 = 2>1 ✓"


def test_latex_check_marks():
    out = _render(LatexRenderer(), CHECKS)
    assert "0.85 \\le 1\\quad{\\color{green}\\checkmark}" in out
    assert "0.85 > 1\\quad{\\color{red}\\boldsymbol{\\times}}" in out


def test_html_check_marks():
    out = _render(HTMLRenderer(), CHECKS)
    assert '<span class="hc-check hc-pass">✓</span>' in out
    assert '<span class="hc-check hc-fail">✗</span>' in out


def test_word_check_marks():
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    xml = _render(WordRenderer(), CHECKS).element.xml
    assert "✓" in xml and "✗" in xml


def test_excel_check_rows_are_coloured():
    openpyxl = pytest.importorskip("openpyxl")
    import io

    workbook = HandCalcs(ExcelRenderer())(CHECKS)
    assert [row.check for row in workbook.rows] == [False, True, True, False]
    sheet = openpyxl.load_workbook(io.BytesIO(workbook.to_bytes())).active
    ranges = [str(cf.sqref) for cf in sheet.conditional_formatting]
    assert ranges == ["E2", "E3"]


# --- Unicode identifiers in LaTeX (#92, #93) ---


@pytest.mark.parametrize(
    "identifier, expected",
    [
        ("λ_2", "\\lambda_{2}"),
        ("σ_R", "\\sigma_{R}"),
        ("x̄", "\\bar{x}"),
        ("ŷ_2", "\\hat{y}_{2}"),
        ("σ̂", "\\hat{\\sigma}"),
        ("M_x̄", "M_{\\bar{x}}"),
    ],
)
def test_latex_unicode_identifiers(identifier, expected):
    from handcalcs.renderers.latex import latex_identifier

    assert latex_identifier(identifier) == expected


# --- # hc: -i on imports and bare expressions ---

IGNORED = (
    "import math  # hc: -i\n"
    "math.sqrt(4)  # hc: -i\n"
    "a = 2\n"
    "# hc: -i\n"
    "import os\n"
    "abs(a)\n"
    "# hc: ignore = False\n"
    "b = a + 1\n"
    "abs(b)\n"
)


def test_ignore_hides_imports_and_expressions():
    out = HandCalcs(ASCIIRenderer())(IGNORED)
    assert [line.strip() for line in out.splitlines()] == [
        "a = 2",
        "b = a + 1 = 2 + 1 = 3",
        "abs(b) = abs(3) = 3",
    ]


def test_ignore_hides_imports_in_latex():
    out = HandCalcs(LatexRenderer())(IGNORED)
    assert "import" not in out and "sqrt" not in out


def test_excel_ignored_import_is_skipped():
    rows = HandCalcs(ExcelRenderer())("import os  # hc: -i\na = 2\n").rows
    assert [row.name for row in rows] == ["a"]


# --- quantities with units ---


def _units(renderer, source, **names):
    exec(source, names)
    return HandCalcs(renderer)(source, names)


def test_latex_forallpeople_uses_format_code_and_upright_units():
    si = pytest.importorskip("forallpeople")
    si.environment("structural", top_level=False)
    source = "L = 6 * si.m\nw = 5 * si.kN / si.m\nM = w*L**2/8  # hc: -f .2f\n"
    out = _units(LatexRenderer(), source, si=si)
    assert "= 22.50\\ \\mathrm{kN} \\cdot \\mathrm{m}" in out
    assert "\\left(6.00\\ \\mathrm{m}\\right)^{2}" in out


@pytest.mark.parametrize(
    "default_format, latex_units, html_units",
    [
        ("~P", "\\mathrm{kN} \\cdot \\mathrm{m}", "kN⋅m"),
        ("~L", "\\mathrm{kN} \\cdot \\mathrm{m}", "kN⋅m"),
        ("", "\\mathrm{kilonewton} \\cdot \\mathrm{meter}", "kilonewton * meter"),
    ],
)
def test_pint_units_follow_the_registry_default_format(
    default_format, latex_units, html_units
):
    ureg = pint.UnitRegistry()
    ureg.formatter.default_format = default_format
    source = "L = 6 * u.m\nw = 5 * u.kN / u.m\nM = w*L**2/8\n"
    latex = _units(LatexRenderer(), source, u=ureg)
    assert f"= 22.5\\ {latex_units}" in latex
    assert "textbackslash" not in latex
    html = _units(HTMLRenderer(), source, u=ureg)
    # pint 0.25 (the last release for Python 3.11) joins units with "·", later ones with "⋅"
    assert f'<span class="hc-result">22.5 {html_units}</span>' in html.replace("·", "⋅")


def test_quantity_power_base_is_bracketed():
    ureg = pint.UnitRegistry()
    ureg.formatter.default_format = "~P"
    out = _units(ASCIIRenderer(), "L = 6 * u.m\nA = L**2\n", u=ureg)
    assert "A = L² = (6 m)² = 36 m²" in out
