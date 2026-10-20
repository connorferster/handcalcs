"""
Tests for the Python -> Excel formula translation ('xl' mode).

Each case is a small cell: every assignment before the last defines a name on
the sheet; the last line's expression is translated.
"""
import math

import pytest

from handcalcs.parsing.ast_parser import AST_Parser
from handcalcs.renderers.excel import ExcelRendererIncompatibleError
from handcalcs.renderers.excel.formulas import FormulaBuilder, format_number
from handcalcs.renderers.excel.names import SymbolTable

INPUTS = "a = 2.0\nb = 3.0\nd = 4.0\nx1 = 5.0\n"


def calc_lines(nodes) -> list:
    """Every CalcLine in a parsed tree, in order (descending into blocks)."""
    found = []
    for node in nodes:
        if node.type == "calc_line":
            found.append(node)
        elif hasattr(node, "lines"):
            found.extend(calc_lines(node.lines))
    return found


def formula(source: str, prefix: str = INPUTS, ns: dict | None = None) -> str:
    """Translate the last line of ``prefix + source``; ``ns`` pre-seeds globals."""
    full = prefix + source
    ns = dict(ns or {})
    exec(full, ns)
    lines = calc_lines(AST_Parser(globals=ns)(full))
    symbols = SymbolTable()
    for line in lines[:-1]:
        for target in line.assigns:
            symbols.assign(target.identifier)
    return FormulaBuilder(symbols, ns).build(lines[-1].expression_tree)


@pytest.mark.parametrize("source, expected", [
    # arithmetic and precedence
    ("y = a + b * d", "a+b*d"),
    ("y = (a + b) * d", "(a+b)*d"),
    ("y = a - (b - d)", "a-(b-d)"),
    ("y = a - b - d", "a-b-d"),
    ("y = a / (b * d)", "a/(b*d)"),
    ("y = a / b / d", "a/b/d"),
    ("y = a ** 2", "a^2"),
    ("y = a ** b ** d", "a^(b^d)"),
    ("y = (a ** b) ** d", "(a^b)^d"),
    ("y = (a + b) ** 2", "(a+b)^2"),
    ("y = a ** (b + 1)", "a^(b+1)"),
    # unary minus binds tighter than ^ in Excel
    ("y = -a ** 2", "-(a^2)"),
    ("y = (-a) ** 2", "(-a)^2"),
    ("y = -a", "-a"),
    ("y = -(a + b)", "-(a+b)"),
    ("y = -(-a)", "-(-a)"),
    ("y = +a", "a"),
    ("y = a - -b", "a-(-b)"),
    ("y = a * -b", "a*(-b)"),
    ("y = a ** -b", "a^(-b)"),
    ("y = (-b + (b**2 - 4*a*d)**0.5) / (2*a)", "(-b+(b^2-4*a*d)^0.5)/(2*a)"),
    # floor division and modulo
    ("y = a // b", "INT(a/b)"),
    ("y = (a + b) // (b * d)", "INT((a+b)/(b*d))"),
    ("y = a % b", "MOD(a,b)"),
    ("y = a % b * d", "MOD(a,b)*d"),
    # comparisons and booleans
    ("y = a < b", "a<b"),
    ("y = a == b", "a=b"),
    ("y = a != b", "a<>b"),
    ("y = a >= b", "a>=b"),
    ("y = a < b <= d", "AND(a<b,b<=d)"),
    ("y = a < b and b < d", "AND(a<b,b<d)"),
    ("y = a < b or not b < d", "OR(a<b,NOT(b<d))"),
    ("y = a < b and (b < d or a > d)", "AND(a<b,OR(b<d,a>d))"),
    ("y = a + b > d", "a+b>d"),
    ("y = True", "TRUE"),
    ("y = False", "FALSE"),
    # literals
    ("y = 0.00001 * a", "1E-05*a"),
    ("y = 2.0 * a", "2*a"),
    ("y = 1.5e20 * a", "1.5E+20*a"),
    ("y = 'say \"hi\"'", '"say ""hi"""'),
    ("y = 'it' + 's'", '"it"+"s"'),
    # names that Excel would read as cell references
    ("y = x1 * 2", "x1_*2"),
])
def test_operators(source, expected):
    assert formula(source) == expected


@pytest.mark.parametrize("source, expected", [
    ("y = sqrt(a)", "SQRT(a)"),
    ("y = math.sqrt(a)", "SQRT(a)"),
    ("y = m.sqrt(a)", "SQRT(a)"),
    ("y = root(a)", "SQRT(a)"),
    ("y = sin(a) + cos(b) + tan(d)", "SIN(a)+COS(b)+TAN(d)"),
    ("y = math.atan2(a, b)", "ATAN2(b,a)"),
    ("y = math.log(a)", "LN(a)"),
    ("y = math.log(a, 10)", "LOG(a,10)"),
    ("y = math.log10(a)", "LOG10(a)"),
    ("y = math.exp(-a)", "EXP(-a)"),
    ("y = math.floor(a)", "INT(a)"),
    ("y = math.ceil(a)", "CEILING.MATH(a)"),
    ("y = math.hypot(a, b)", "SQRT(SUMSQ(a,b))"),
    ("y = math.pow(a, b)", "POWER(a,b)"),
    ("y = pow(a, b)", "POWER(a,b)"),
    ("y = abs(a - b)", "ABS(a-b)"),
    ("y = min(a, b, d)", "MIN(a,b,d)"),
    ("y = max(a, 2 * b)", "MAX(a,2*b)"),
    ("y = round(a, 2)", "ROUND(a,2)"),
    ("y = round(a)", "ROUND(a,0)"),
    ("y = math.radians(a)", "RADIANS(a)"),
    ("y = math.pi * a", "PI()*a"),
    ("y = pi * a", "PI()*a"),
    ("y = a / math.tau", "a/(2*PI())"),
    ("y = math.e ** a", "EXP(1)^a"),
    ("y = sqrt(a + sqrt(b))", "SQRT(a+SQRT(b))"),
])
def test_functions(source, expected):
    imports = "import math\nimport math as m\nfrom math import sqrt, sin, cos, tan, pi\nfrom math import sqrt as root\n"
    assert formula(source, imports + INPUTS) == expected


def test_user_function_named_sqrt_is_not_math_sqrt():
    prefix = "def sqrt(x):\n    return x\n" + INPUTS
    with pytest.raises(ExcelRendererIncompatibleError, match=r"'sqrt\(\)' has no Excel equivalent"):
        formula("y = sqrt(a)", prefix)


def test_user_assigned_pi_shadows_math_pi():
    assert formula("y = pi * 2", INPUTS + "pi = 3.14\n") == "pi*2"


@pytest.mark.parametrize("source, match", [
    ("y = len('ab')", r"'len\(\)' has no Excel equivalent"),
    ("y = math.gcd(4, 6)", r"'math.gcd\(\)' has no Excel equivalent"),
    ("y = round(a, ndigits=2)", "keyword arguments"),
    ("y = min([a, b])", "argument"),
    ("y = math.inf * a", "attribute 'math.inf'"),
    ("y = [a, b]", "'list'"),
    ("y = a in (1, 2)", "'in' comparison"),
    ("y = a is b", "'is' comparison"),
    ("y = None", "None"),
    ("y = 2j * a", "literal"),
])
def test_incompatible(source, match):
    with pytest.raises(ExcelRendererIncompatibleError, match=match):
        formula(source, "import math\n" + INPUTS)


def test_name_not_assigned_on_the_sheet_raises():
    # 'z' comes from the namespace (e.g. supplied_globals), not from the cell.
    with pytest.raises(ExcelRendererIncompatibleError, match="'z' is used before it is assigned"):
        formula("y = a + z", ns={"z": 1.0})


def test_format_number():
    assert format_number(3) == "3"
    assert format_number(0.1) == "0.1"
    assert format_number(-2.0) == "-2"
    with pytest.raises(ExcelRendererIncompatibleError):
        format_number(math.inf)


def test_build_does_not_mutate_nodes():
    full = INPUTS + "y = -a ** 2 + sqrt(b)\n"
    ns: dict = {}
    exec("from math import sqrt\n" + full, ns)
    line = calc_lines(AST_Parser(globals=ns)(full))[-1]
    before = repr(line)
    symbols = SymbolTable()
    for name in "a b d x1".split():
        symbols.assign(name)
    FormulaBuilder(symbols, ns).build(line.expression_tree)
    assert repr(line) == before
