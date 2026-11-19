"""
``# hc: -y``: a line ``x = f``, where ``f`` holds a SymPy expression, runs and
renders as ``x = <the expression>`` with the values its symbols have when it runs.
"""

import math
import re
import sys
import textwrap

import pytest

from handcalcs import HandCalcs, handcalc
from handcalcs.parsing.sympy_substitution import (
    SympySubstitutionError,
    find_marks,
    has_sympy_commands,
    is_sympy,
    namespace_lookup,
    substitute,
    to_python,
)
from handcalcs.renderers import ASCIIRenderer

sp = pytest.importorskip("sympy")

a, b = sp.symbols("a b")
SETUP = (
    "import sympy as sp\n"
    "a, b, c = sp.symbols('a b c')\n"
    "f = sp.integrate(a**2 + b * a, a)\n"
)


def render(source: str) -> list[str]:
    return [line.strip() for line in HandCalcs(ASCIIRenderer())(source).splitlines()]


def python(expr, **namespace) -> str:
    from handcalcs.parsing.sympy_substitution import Names

    return to_python(expr, Names(namespace_lookup(namespace)))


# --- Writing an expression as Python ---


@pytest.mark.parametrize(
    "expr, namespace, expected",
    [
        (a**3 / 3 + a**2 * b / 2, {}, "a**3/3 + b*a**2/2"),
        (sp.sqrt(a), {"sqrt": math.sqrt}, "sqrt(a)"),
        (1 / sp.sqrt(a), {"math": math}, "1/math.sqrt(a)"),
        (sp.sin(a) + sp.pi, {"sin": math.sin, "pi": math.pi}, "pi + sin(a)"),
        (sp.exp(a), {"math": math}, "math.exp(a)"),
        (sp.Abs(a) + sp.Max(a, b), {}, "abs(a) + max(a, b)"),
        (sp.ceiling(a), {"math": math}, "math.ceil(a)"),
        (sp.I * a, {}, "1j*a"),
        (a ** sp.Rational(1, 3), {}, "a**(1/3)"),
    ],
)
def test_to_python(expr, namespace, expected):
    assert python(expr, **namespace) == expected


def test_a_name_that_is_not_the_constant_goes_through_math():
    # 'e' is often an eccentricity, not Euler's number.
    assert python(sp.E * a, e=0.2, math=math) == "math.e*a"


def test_sympys_own_functions_are_not_used():
    assert python(sp.sqrt(a), sqrt=sp.sqrt, math=math) == "math.sqrt(a)"


@pytest.mark.parametrize(
    "expr, message",
    [
        (sp.sqrt(a), "import it before this line (from math import sqrt)"),
        (sp.Integral(a, b), "SymPy's Integral"),
        (sp.Piecewise((a, a > 0), (b, True)), "SymPy's Piecewise"),
        (sp.Symbol("\\alpha") + 1, "not a Python name"),
    ],
)
def test_to_python_errors(expr, message):
    with pytest.raises(SympySubstitutionError, match=re.escape(message)):
        python(expr)


def test_is_sympy():
    assert is_sympy(a + 1) and not is_sympy(1.0) and not is_sympy(sp)


# --- Finding the lines ---


def test_marks():
    marks = find_marks(
        "x = f  # hc: -y\n# hc: --sympy\ny = g\n# hc: sympy = False\nz = h\n"
    )
    assert marks.inline == {1}
    assert [marks.region_at(line) for line in (1, 3, 5)] == [False, True, False]
    assert not has_sympy_commands("x = f  # hc: -i\n")


# --- Scripts ---


def test_inline_line_is_substituted():
    out = render(SETUP + "a = 5\nb = 10\nx = f  # hc: -y\ny = 2 * x\n")
    assert "x = a³ / 3 + b * a² / 2 = 5³ / 3 + 10 * 5² / 2 = 166.67" in out
    assert "y = 2 * x = 2 * 166.67 = 333.33" in out


def test_the_variable_holds_the_number():
    namespace = {}
    source = SETUP + "a = 5\nb = 10\nx = f  # hc: -y\n"
    from handcalcs.interfaces.object_oriented import run_staged

    namespace, _, rewritten = run_staged(source, namespace)
    assert namespace["x"] == pytest.approx(166.6667, rel=1e-4)
    assert is_sympy(namespace["f"])  # the expression is unchanged
    assert "x = a**3/3 + b*a**2/2  # hc: -y" in rewritten


def test_each_line_uses_the_values_it_ran_with():
    out = render(
        SETUP + "a = 5\nb = 10\nx = f  # hc: -y\na = 7\nw = f  # hc: -y\na = 9\n"
    )
    assert "x = a³ / 3 + b * a² / 2 = 5³ / 3 + 10 * 5² / 2 = 166.67" in out
    assert "w = a³ / 3 + b * a² / 2 = 7³ / 3 + 10 * 7² / 2 = 359.33" in out


def test_region_substitutes_only_sympy_expressions():
    out = render(
        SETUP + "a = 2\nb = 3\n# hc: -y\nx = f\nk = b\n# hc: sympy = False\ny = f\n"
    )
    assert "x = a³ / 3 + b * a² / 2 = 2³ / 3 + 3 * 2² / 2 = 8.6667" in out
    assert "k = b = 3" in out
    assert any(line.startswith("y = f = ") for line in out)


def test_equation_and_solve_results():
    out = render(
        "import sympy as sp\n"
        "R, w, L = sp.symbols('R w L')\n"
        "eq = sp.Eq(R, w * L / 2)\n"
        "sol = sp.solve(R * L - w * L**2 / 2, R)\n"
        "w = 4\nL = 6\n"
        "R_1 = eq  # hc: -y\n"
        "R_2 = sol  # hc: -y\n"
    )
    assert "R_1 = L * w / 2 = 6 * 4 / 2 = 12" in out
    assert "R_2 = L * w / 2 = 6 * 4 / 2 = 12" in out


def test_functions_from_math():
    out = render(
        SETUP
        + "from math import sqrt\ng = sp.sqrt(a**2 + b**2)\na = 3\nb = 4\nh = g  # hc: -y\n"
    )
    assert "h = √(a² + b²) = √(3² + 4²) = 5" in out


def test_in_a_block():
    out = render(SETUP + "b = 1\nfor a in [1, 2]:\n    x = f  # hc: -y\n")
    assert any("x = a³ / 3 + b * a² / 2 = 2³ / 3" in line for line in out)


@pytest.mark.parametrize(
    "lines, message",
    [
        ("a = 5\nx = f  # hc: -y\n", "'b', which is still a SymPy symbol"),
        ("x = g  # hc: -y\n", "'g' is not defined"),
        ("k = 3\nx = k  # hc: -y\n", "holds a int, not a SymPy expression"),
        ("a = 1\nb = 2\nx = f + 1  # hc: -y\n", "must be 'name = expression_name'"),
    ],
)
def test_errors(lines, message):
    with pytest.raises(SympySubstitutionError, match=message):
        HandCalcs(ASCIIRenderer())(SETUP + lines)


def test_not_with_inputs_or_supplied_globals():
    source = SETUP + "a = 1\nb = 2\nx = f  # hc: -y\n"
    with pytest.raises(ValueError, match="can't be combined"):
        HandCalcs(ASCIIRenderer())(source, inputs={"a": 2})
    with pytest.raises(ValueError, match="can't be combined"):
        HandCalcs(ASCIIRenderer())(source, {})


def test_without_line_values(monkeypatch, tmp_path):
    from handcalcs import config

    monkeypatch.setenv("HANDCALCS_CONFIG", str(tmp_path / "config.json"))
    config.reset_config()
    config.set_option("line_values", False)
    try:
        out = render(SETUP + "a = 5\nb = 10\nx = f  # hc: -y\n")
    finally:
        config.reset_config()
    assert "x = a³ / 3 + b * a² / 2 = 5³ / 3 + 10 * 5² / 2 = 166.67" in out


def test_substitute_keeps_line_numbers():
    source = "x = f  # hc: -y\ny = 1\n"
    out, subs = substitute(source, namespace_lookup({"f": a + b, "a": 1, "b": 2}))
    assert out == "x = a + b  # hc: -y\ny = 1\n"
    assert subs[0].line == 1 and subs[0].names == {"a", "b"}


# --- The decorator ---


@pytest.fixture
def beam_module(tmp_path, monkeypatch):
    """A module with decorated functions: the decorator reads their source."""
    path = tmp_path / "sympy_beam.py"
    path.write_text(
        textwrap.dedent('''
            import sympy as sp
            from handcalcs import handcalc

            w, L = sp.symbols("w L")
            M_mid = w * L**2 / 8


            @handcalc()
            def midspan(w, L):
                """Midspan moment."""
                M = M_mid  # hc: -y
                M_f = 1.5 * M
                return M_f


            @handcalc()
            def general(expr, w, L=6):
                M = expr  # hc: -y
                return M
            '''),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    import importlib

    module = importlib.import_module("sympy_beam")
    yield module
    sys.modules.pop("sympy_beam", None)


def test_decorator(beam_module):
    value, rendered = beam_module.midspan(4, 6)
    assert value == 27
    assert "M = w * L² / 8 = 4 * 6² / 8 = 18" in rendered
    assert beam_module.midspan(2, 10)[0] == 37.5


def test_decorator_expression_as_an_argument(beam_module):
    value, rendered = beam_module.general(beam_module.M_mid, 4)
    assert value == 18
    assert "M = w * L² / 8 = 4 * 6² / 8 = 18" in rendered
    value, _ = beam_module.general(beam_module.w * beam_module.L, 2, L=3)
    assert value == 6


def test_decorator_refuses_a_closure():
    def outer():
        expr = a + b

        @handcalc()
        def inner(a, b):
            y = expr  # hc: -y
            return y

        return inner

    with pytest.raises(SympySubstitutionError, match="variables of the function"):
        outer()
