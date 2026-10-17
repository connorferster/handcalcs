"""
Tests for the ExcelRenderer's row model: each node type becomes the right row
record, and every incompatible statement raises before anything is written.
"""
import pytest

from handcalcs import HandCalcs
from handcalcs.renderers import demo
from handcalcs.renderers.excel import ExcelRenderer, ExcelRendererIncompatibleError
from handcalcs.renderers.excel.rich_text import plain_text
from handcalcs.renderers.excel.rows import BlankRow, CalcRow, CommentRow, HeadingRow, ParamRow


def rows(source: str, **kwargs) -> list:
    return HandCalcs(renderer=ExcelRenderer(**kwargs))(source).rows


def test_param_and_calc_rows():
    a, b = rows("a = 2  # length\nb = 3 * a\n")
    assert a == ParamRow(name="a", symbol=[("a", None)], value=2, number_format="General", comment="length")
    assert isinstance(b, CalcRow)
    assert b.name == "b"
    assert b.formula == "=3*a"
    assert b.cached == 6
    assert plain_text(b.symbolic) == "3 · a"


def test_negative_literal_is_a_param():
    (k,) = rows("k = -2.5\n")
    assert isinstance(k, ParamRow)
    assert k.value == -2.5
    assert k.formula is None


def test_string_and_bool_literals_are_params():
    s, t = rows("s = 'steel'\nt = True\n")
    assert (s.value, t.value) == ("steel", True)


def test_bare_reference_is_a_calc():
    _, b = rows("a = 2\nb = a\n")
    assert isinstance(b, CalcRow)
    assert b.formula == "=a"


def test_symbolic_rich_text():
    _, _, m = rows("M_u = 2.0\nphi_b = 0.9\nM_r = phi_b * M_u ** 2\n")
    assert m.symbol == [("M", None), ("r", "sub")]
    assert m.symbolic == [("φ", None), ("b", "sub"), (" · M", None), ("u", "sub"), ("2", "sup")]


def test_reassignment_is_versioned_with_its_own_cached_value():
    a, m1, m2, z = rows("a = 2\nM_u = a * 2\nM_u = M_u * 10\nz = M_u + 1\n")
    assert (m1.name, m1.formula, m1.cached) == ("M_u", "=a*2", 4)
    assert (m2.name, m2.formula, m2.cached) == ("M_u_2", "=M_u*10", 40)
    assert (z.formula, z.cached) == ("=M_u_2+1", 41)
    assert m1.symbol == m2.symbol


def test_reference_like_names_are_mangled():
    x1, y = rows("x1 = 2\ny = x1 * 2\n")
    assert x1.name == "x1_"
    assert y.formula == "=x1_*2"
    assert plain_text(x1.symbol) == "x1"


def test_format_commands():
    a, b, d = rows("a = 2.0  # hc: -f .3f\nb = a * 2  # hc: -f ,.1f\nd = a * 3\n")
    assert a.number_format == "0.000"
    assert b.number_format == "#,##0.0"
    assert d.number_format == "General"  # inline -f is line-scoped


def test_standalone_format_command_persists():
    *_, b, d = rows("# hc: -f .2e\na = 2.0\nb = a * 2\nd = a * 3\n")
    assert b.number_format == d.number_format == "0.00E+00"


def test_general_format_option():
    (a,) = rows("a = 2.0\n", general_format="0.000")
    assert a.number_format == "0.000"


def test_ignored_line_is_hidden_but_kept():
    a, b, d = rows("a = 2\nb = a * 2  # hc: -i\nd = b + 1\n")
    assert b.hidden and not d.hidden
    assert d.formula == "=b+1"


def test_param_command_keeps_formula():
    _, L = rows("a = 2\nL = a * 150  # hc: -p\n")
    assert isinstance(L, ParamRow)
    assert (L.formula, L.value) == ("=a*150", 300)


def test_blank_rows():
    result = rows("a = 1\n# hc: -b\nb = 2\n")
    assert [type(r) for r in result] == [ParamRow, BlankRow, ParamRow]


def test_inline_blank_row():
    result = rows("a = 1  # hc: -b\nb = 2\n")
    assert [type(r) for r in result] == [ParamRow, BlankRow, ParamRow]


def test_params_blocks():
    result = rows("x = 1; y = 2; z = 3\n")
    assert [r.name for r in result] == ["x", "y", "z"]
    assert all(isinstance(r, ParamRow) for r in result)
    result = rows("# hc: -h\np = 1  # first\nq = 2  # second\n")
    assert [(r.name, r.comment) for r in result] == [("p", "first"), ("q", "second")]


def test_headings_comments_and_docstrings():
    result = rows('"""Beam check."""\n## Loads\n### Dead\n# line one\n# line two\na = 1\n')
    assert result[:4] == [
        CommentRow("Beam check."),
        HeadingRow("Loads", 1),
        HeadingRow("Dead", 2),
        CommentRow("line one line two"),
    ]


def test_math_imports_are_skipped():
    result = rows("import math\nfrom math import sqrt, pi\na = sqrt(pi)\nb = math.cos(a)\n")
    assert [r.formula for r in result] == ["=SQRT(PI())", "=COS(a)"]


def test_rows_do_not_mutate_the_tree():
    renderer = ExcelRenderer()
    hc = HandCalcs(renderer=renderer)
    source = "from math import sqrt\nM_u = 2.0\nphi_b = 0.9\nM_r = phi_b * sqrt(M_u) ** 2\n"
    first = hc(source).rows
    assert hc(source).rows == first


@pytest.mark.parametrize("source, match", [
    ("for i in range(3):\n    a = i\n", "for loops"),
    ("def f(x):\n    return x\n", "function or class definition"),
    ("print(1)\n", "expression statement"),
    ("a = 1\na + 1\n", "expression statement"),
    ("import os\n", "importing 'os'"),
    ("from os import path\n", "importing 'os'"),
    ("import math, os\n", "importing 'os'"),
    ("a = 1\na += 1\n", "augmented assignment"),
    ("i = 0\nwhile i < 1:\n    i = i + 1\n", "while"),
    ("a = b = 1\n", "chained assignment"),
    ("a, b = 1, 2\n", "tuple unpacking"),
    ("a = [1, 2]\n", "'list'"),
    ("a = 1\nb = a if a else 2\n", "does not parse"),
    ("a = len('ab')\n", r"'len\(\)'"),
    ("a = 1\nif a > 0:\n    b = 1\nelse:\n    b = 2\n", "if/elif/else"),
])
def test_incompatible(source, match):
    with pytest.raises(ExcelRendererIncompatibleError, match=match):
        rows(source)


def test_error_names_the_assignment_target():
    with pytest.raises(ExcelRendererIncompatibleError) as info:
        rows("a = 1\nb = len('x') + a\n")
    assert info.value.target == "b"
    assert "in the assignment to 'b'" in str(info.value)


def test_base_demo_is_incompatible():
    with pytest.raises(ExcelRendererIncompatibleError):
        HandCalcs(renderer=ExcelRenderer())(demo.source)
