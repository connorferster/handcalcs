"""
Tests for the symbolic column: identifier display, operator symbols and the
markup -> rich-text parser.
"""
import pytest

from handcalcs.parsing.ast_parser import AST_Parser
from handcalcs.renderers.excel import ExcelRenderer
from handcalcs.renderers.excel.rich_text import escape, parse_markup, plain_text, to_markup
from handcalcs.renderers.excel.symbolic import symbolic_identifier, symbolic_markup

from tests.test_excel_formulas import calc_lines


# --- identifiers ---

@pytest.mark.parametrize("identifier, expected", [
    ("x", "x"),
    ("M_u", "M<sub>u</sub>"),
    ("x_1", "x<sub>1</sub>"),
    ("a_b_c", "a<sub>b,c</sub>"),
    ("phi", "φ"),
    ("phi_b", "φ<sub>b</sub>"),
    ("sigma_max", "σ<sub>max</sub>"),
    ("Delta_x", "Δ<sub>x</sub>"),
    ("lamb", "λ"),
    ("x_hat", "x̂"),
    ("y_bar_i", "y̅<sub>i</sub>"),
    ("f_c_prime", "f<sub>c′</sub>"),
    ("M_star", "M<sup>*</sup>"),
    ("M_u_star", "M<sub>u</sub><sup>*</sup>"),
    ("long__name", "long name"),
    ("a___b", "a_b"),
    ("x_", "x"),
    ("_private", "_private"),
    ("alphabet", "alphabet"),
])
def test_symbolic_identifier(identifier, expected):
    assert symbolic_identifier(identifier) == expected


# --- rich text ---

@pytest.mark.parametrize("markup, expected", [
    ("x", [("x", None)]),
    ("M<sub>u</sub>", [("M", None), ("u", "sub")]),
    ("a<sup>2</sup> + b", [("a", None), ("2", "sup"), (" + b", None)]),
    ("a<sub>b<sub>c</sub></sub>", [("a", None), ("b,c", "sub")]),
    ("a<sub>b<sub>c<sub>d</sub></sub></sub>", [("a", None), ("b,c,d", "sub")]),
    ("a<sub>b<sup>*</sup></sub>", [("a", None), ("b*", "sub")]),
    ("x<sub>1</sub><sub>2</sub>", [("x", None), ("12", "sub")]),
    ("a &lt; b", [("a < b", None)]),
    ("&lt;sub&gt;", [("<sub>", None)]),
    ("", []),
])
def test_parse_markup(markup, expected):
    assert parse_markup(markup) == expected


def test_round_trip():
    rich = [("M", None), ("u", "sub"), (" < 2", None), ("2", "sup")]
    assert parse_markup(to_markup(rich)) == rich
    assert plain_text(rich) == "Mu < 22"
    assert escape("a<b&c") == "a&lt;b&amp;c"


# --- expressions in symbolic mode ---

def symbolic(source: str) -> str:
    """Markup of the last line's (target, expression)."""
    ns: dict = {}
    exec(source, ns)
    line = calc_lines(AST_Parser(globals=ns)(source))[-1]
    renderer = ExcelRenderer()
    context = renderer.create_context(global_ns=ns)
    target = symbolic_markup(renderer, line.assigns, context)
    expression = symbolic_markup(renderer, line.expression_tree, context)
    return f"{target} = {expression}"


PREFIX = (
    "import math\nfrom math import sqrt\n"
    "a = 2.0\nb = 3.0\nd = 4.0\nM_u = 1.0\nphi_b = 0.9\nF_y = 350.0\n"
)


@pytest.mark.parametrize("source, expected", [
    ("x_1 = a * b", "x<sub>1</sub> = a · b"),
    ("y = a / b - d", "y = a / b - d"),
    ("y = a ** 2", "y = a<sup>2</sup>"),
    ("y = (a + b) ** 2", "y = (a + b)<sup>2</sup>"),
    ("y = a ** -2", "y = a<sup>-2</sup>"),
    ("y = a ** (b + 1)", "y = a^(b + 1)"),
    ("y = sqrt(a)", "y = √(a)"),
    ("y = math.sqrt(a ** 2 + b ** 2)", "y = √(a<sup>2</sup> + b<sup>2</sup>)"),
    ("y = math.sin(a)", "y = sin(a)"),
    ("y = math.pi * a", "y = π · a"),
    ("y = a // b", "y = ⌊a / b⌋"),
    ("y = a % b", "y = a mod b"),
    ("M_r = phi_b * M_u", "M<sub>r</sub> = φ<sub>b</sub> · M<sub>u</sub>"),
    ("y = a <= b", "y = a ≤ b"),
    ("y = a < b", "y = a &lt; b"),
    ("y = a != b", "y = a ≠ b"),
    ("y = a == b", "y = a = b"),
    ("y = a < b and b >= d", "y = a &lt; b and b ≥ d"),
    ("y = -a", "y = -a"),
    ("s = '<sub>'", "s = &lt;sub&gt;"),
])
def test_expression_markup(source, expected):
    assert symbolic(PREFIX + source) == expected


def test_symbolic_render_does_not_mutate_nodes():
    source = PREFIX + "M_r = phi_b * math.sqrt(M_u) ** 2 + math.pi\n"
    ns: dict = {}
    exec(source, ns)
    line = calc_lines(AST_Parser(globals=ns)(source))[-1]
    renderer = ExcelRenderer()
    context = renderer.create_context(global_ns=ns)
    symbolic_markup(renderer, line.assigns, context)  # warm-up: base pre rules may fill defaults
    symbolic_markup(renderer, line.expression_tree, context)
    before = repr(line)
    symbolic_markup(renderer, line.assigns, context)
    symbolic_markup(renderer, line.expression_tree, context)
    assert repr(line) == before
    assert line.assigns[0].identifier == "M_r"


def test_markup_parses_to_runs():
    runs = parse_markup(symbolic(PREFIX + "M_r = phi_b * M_u ** 2"))
    assert runs == [
        ("M", None), ("r", "sub"), (" = φ", None), ("b", "sub"),
        (" · M", None), ("u", "sub"), ("2", "sup"),
    ]


@pytest.mark.parametrize("source, expected", [
    ("y = (-a) ** 2", "y = (-a)<sup>2</sup>"),
    ("y = (a ** b) ** 2", "y = (a^b)<sup>2</sup>"),
    ("y = -a ** 2", "y = -a<sup>2</sup>"),
])
def test_power_bases(source, expected):
    assert symbolic(PREFIX + source) == expected


def test_format_code_does_not_reach_symbolic_constants():
    from handcalcs.interfaces.object_oriented import HandCalcs
    from handcalcs.renderers.excel.rows import CalcRow
    source = "b = 3\n# hc: -f .3f\ny = (b**2 + 0.5) / 2.0\n"
    renderer = ExcelRenderer()
    hc = HandCalcs(renderer=renderer)
    hc(source)
    rows = renderer.render(hc.hc_ast, renderer.create_context(global_ns={"b": 3}))
    row = [r for r in rows if isinstance(r, CalcRow)][0]
    assert plain_text(row.symbolic) == "(b2 + 0.5) / 2"
    assert row.number_format == "0.000"
