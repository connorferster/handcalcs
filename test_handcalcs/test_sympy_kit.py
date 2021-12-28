import inspect
from collections import deque
from handcalcs.handcalcs import (
    CalcLine, round_and_render_line_objects_to_latex
)
import handcalcs.sympy_kit as sk
import pathlib
import pytest
import nbconvert
import filecmp
import sympy as sp

a, b = sp.symbols("a b")
c = a + b
d = sp.Eq(2 * a + b, 14)


def test_sympy_cell_line_lists():
    assert sk.sympy_cell_line_lists("x = 9\ny = 10") == [["x", "9"], ["y", "10"]]


def test_test_sympy_parents():
    assert sk.test_sympy_parents("Base", ("Relational", "Equation", "Base")) == True
    assert sk.test_sympy_parents("Expression", ("Equation", "Base")) == False


def test_test_for_sympy_expr():
    assert sk.test_for_sympy_expr("x", {"x": 9, "y": 10}) == False
    assert sk.test_for_sympy_expr("c", {"a": a, "b": b, "c": a + b}) == True


def test_test_for_sympy_eqn():
    assert sk.test_for_sympy_eqn("x", {"x": 9, "y": 10}) == False
    assert sk.test_for_sympy_eqn("d", {"x": 9, "y": 10, "d": d}) == True


def test_get_sympy_object():
    assert sk.get_sympy_obj("d", {"x": 9, "y": 10, "d": d}) == d


def test_convert_sympy_cell_to_py_cell():
    assert (
        sk.convert_sympy_cell_to_py_cell("x = 9\ny = 10", {"x": 9, "y": 10})
        == "x = 9\ny = 10"
    )
    assert (
        sk.convert_sympy_cell_to_py_cell("d", {"x": 9, "y": 10, "d": d}) == "2*a + b=14"
    )
    assert (
        sk.convert_sympy_cell_to_py_cell("k = c", {"x": 9, "y": 10, "c": c})
        == "k =a + b"
    )
    with pytest.raises(ValueError):
        sk.convert_sympy_cell_to_py_cell("c", {"x": 9, "y": 10, "c": c})


def test_sympy_rounding():
    expr = 12.3456789 * a + 1.23456789e-55 * b

    assert round_and_render_line_objects_to_latex(
        CalcLine([expr], '', ''), precision=3, dec_sep='.'
    ).latex == r'\displaystyle 12.346 a + 1.235 \cdot 10^{-55} b'

    assert round_and_render_line_objects_to_latex(
        CalcLine([expr], '', ''), precision=4, dec_sep='.'
    ).latex == r'\displaystyle 12.3457 a + 1.2346 \cdot 10^{-55} b'
