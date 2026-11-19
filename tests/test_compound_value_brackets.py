"""
A substituted value that is itself a sum (a complex number with a real and an
imaginary part, or a SymPy sum, product or power) is bracketed where a sum would
be (#224): ``2 * (3+4j)``, not ``2 * 3+4j``.
"""

import pytest

from handcalcs import HandCalcs
from handcalcs.renderers import ASCIIRenderer, HTMLRenderer, LatexRenderer
from handcalcs.renderers.base import value_precedence

COMPLEX = "z1 = 3 + 4j\nz2 = -4 + 3j\n"


def ascii_lines(source: str, namespace: dict | None = None) -> list[str]:
    namespace = dict(namespace or {})
    exec(source, namespace)
    rendered = HandCalcs(ASCIIRenderer()).render_run(source, namespace)
    return [line.strip() for line in rendered.splitlines()]


@pytest.mark.parametrize(
    "line, expected",
    [
        ("z = z1 * z2", "z = z1 * z2 = (3+4j) * (-4+3j) = -24-7j"),
        ("z = z2 * z1", "z = z2 * z1 = (-4+3j) * (3+4j) = -24-7j"),
        ("z = z1**2", "z = z1² = (3+4j)² = -7+24j"),
        ("z = -z1", "z = -z1 = -(3+4j) = -3-4j"),
        ("z = 2 * z1", "z = 2 * z1 = 2 * (3+4j) = 6+8j"),
        ("z = z1 / z2", "z = z1 / z2 = (3+4j) / (-4+3j) = -0-1j"),
        # A sum needs none.
        ("z = z1 - z2", "z = z1 - z2 = 3+4j - (-4+3j) = 7+1j"),
        ("z = 1 + z1", "z = 1 + z1 = 1 + 3+4j = 4+4j"),
    ],
)
def test_complex_values_in_ascii(line, expected):
    assert expected in ascii_lines(COMPLEX + line + "\n")


def test_complex_values_in_latex():
    source = COMPLEX + "z = z2 * z1\nw = z1**2\n"
    namespace: dict = {}
    exec(source, namespace)
    latex = HandCalcs(LatexRenderer()).render_run(source, namespace)
    assert "\\left(-4 + 3j\\right) \\cdot \\left(3 + 4j\\right)" in latex
    assert "\\left(3 + 4j\\right)^{2}" in latex


def test_complex_values_in_html():
    source = COMPLEX + "z = 2 * z1\nw = z1**2\n"
    namespace: dict = {}
    exec(source, namespace)
    html = HandCalcs(HTMLRenderer()).render_run(source, namespace)
    assert "= (3+4j)<sup>2</sup>" in html
    assert "2 · (3+4j)" in html or "2 &middot; (3+4j)" in html


@pytest.mark.parametrize(
    "value, bracketed", [(3 + 4j, True), (4j, False), (3 + 0j, False), (2.5, False)]
)
def test_value_precedence_of_numbers(value, bracketed):
    assert (value_precedence(value) < float("inf")) is bracketed


def test_names_are_not_bracketed_in_the_symbolic_column():
    assert "z = 2 * z1 = 2 * (3+4j) = 6+8j" in ascii_lines(COMPLEX + "z = 2 * z1\n")


# --- SymPy values ---

sp = pytest.importorskip("sympy")
SYMPY = "z1 = 3 + I * 4\nz2 = -4 + I * 3\nz3 = z1 * z2\n"


def test_sympy_values_in_ascii():
    lines = ascii_lines(SYMPY + "p = z1 * z2\nq = 2 * z1\nr = z3**2\n", {"I": sp.I})
    assert "p = z1 * z2 = (3 + 4*I) * (-4 + 3*I) = (-4 + 3*I)*(3 + 4*I)" in lines
    assert "q = 2 * z1 = 2 * (3 + 4*I) = 6 + 8*I" in lines
    assert any(line.startswith("r = z3² = ((-4 + 3*I)*(3 + 4*I))²") for line in lines)


def test_sympy_values_in_latex_are_bracketed_only_where_needed():
    source = SYMPY + "d = z1 - z2\n"
    namespace = {"I": sp.I}
    exec(source, namespace)
    latex = HandCalcs(LatexRenderer()).render_run(source, namespace)
    # Not around a value on its own, as v2 did before.
    assert "\\mathrm{z1} &= 3 + I \\cdot 4 = 3 + i \\cdot 4 = 3 + 4 i" in latex
    assert "3 + 4 i - \\left(-4 + 3 i\\right) = 7 + i" in latex
    assert "\\left(3 + 4 i\\right) \\cdot \\left(-4 + 3 i\\right)" in latex


@pytest.mark.parametrize(
    "expr, level",
    [("a + 1", "add"), ("2 * a", "mult"), ("a**2", "pow"), ("a", None)],
)
def test_value_precedence_of_sympy(expr, level):
    from handcalcs.renderers.base import OP_PRECEDENCE
    from handcalcs.parsing.operator_nodes import AddOp, MultOp, PowOp

    value = sp.sympify(expr)
    expected = {"add": AddOp, "mult": MultOp, "pow": PowOp}.get(level)
    assert value_precedence(value) == (
        OP_PRECEDENCE[expected] if expected else float("inf")
    )
