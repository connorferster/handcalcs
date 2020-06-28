import inspect
from collections import deque
import handcalcs
import pytest

from handcalcs.handcalcs import ParameterLine, CalcLine, LongCalcLine, ConditionalLine
from handcalcs.handcalcs import ParameterCell, LongCalcCell

# When writing a new test create a new "cell" .py file
from test_handcalcs import cell_1
from test_handcalcs import cell_2
from test_handcalcs import cell_2b
from test_handcalcs import cell_3
from test_handcalcs import cell_4
from test_handcalcs import cell_5
from test_handcalcs import cell_6
from test_handcalcs import error_cell


def remove_imports_defs_and_globals(source: str):
    """
    For "cell" modules used in testing, this function removes
    content not intended to be rendered such as import statements,
    function definitions, and the calc_results = globals() line.
    """
    source_lines = source.split("\n")
    acc = []
    for line in source_lines:
        if (
            "import" not in line
            and "def" not in line
            and "globals" not in line
            and "return" not in line
        ):
            acc.append(line)
    return "\n".join(acc)


@handcalcs.handcalc
def func_1(x, y):
    a = 2 * x
    b = 3 * a + y
    return locals()


@handcalcs.handcalc
def error_func(x, y):
    a = 2 * x
    b = 3 * a + y
    return b  # Must return locals()


cell_1_source = remove_imports_defs_and_globals(inspect.getsource(cell_1))
cell_2_source = remove_imports_defs_and_globals(inspect.getsource(cell_2))
cell_2b_source = remove_imports_defs_and_globals(inspect.getsource(cell_2b))
cell_3_source = remove_imports_defs_and_globals(inspect.getsource(cell_3))
cell_4_source = remove_imports_defs_and_globals(inspect.getsource(cell_4))
cell_5_source = remove_imports_defs_and_globals(inspect.getsource(cell_5))
cell_6_source = remove_imports_defs_and_globals(inspect.getsource(cell_6))
error_cell_source = remove_imports_defs_and_globals(inspect.getsource(error_cell))

cell_1_renderer = handcalcs.handcalcs.LatexRenderer(cell_1_source, cell_1.calc_results)
cell_2_renderer = handcalcs.handcalcs.LatexRenderer(cell_2_source, cell_2.calc_results)
cell_2b_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_2b_source, cell_2b.calc_results
)
cell_3_renderer = handcalcs.handcalcs.LatexRenderer(cell_3_source, cell_3.calc_results)
cell_4_renderer = handcalcs.handcalcs.LatexRenderer(cell_4_source, cell_4.calc_results)
cell_5_renderer = handcalcs.handcalcs.LatexRenderer(cell_5_source, cell_5.calc_results)
cell_6_renderer = handcalcs.handcalcs.LatexRenderer(cell_6_source, cell_6.calc_results)
error_cell_renderer = handcalcs.handcalcs.LatexRenderer(
    error_cell_source, error_cell.calc_results
)

# Integration tests


def test_integration():
    assert (
        cell_1_renderer.render()
        == "\\[\n\\begin{aligned}\na &= 2\\;\\;\\textrm{(Comment)}\n\\\\[10pt]\ny &= 6\\;\\;\\textrm{(Comment)}\n\\\\[10pt]\n\\alpha_{\\eta_{\\psi}} &= \\frac{ 4 }{ \\left( y \\right) ^{ \\left( a + 1 \\right) } } = \\frac{ 4 }{ \\left( 6 \\right) ^{ \\left( 2 + 1 \\right) } } &= 0.019\\;\\;\\textrm{(Comment)}\n\\\\[10pt]\n\\alpha_{\\eta_{\\psi}} &= 0.019\\;\n\\end{aligned}\n\\]"
    )
    assert (
        cell_2_renderer.render()
        == "\\[\n\\begin{aligned}\nx &= 2\\;\n\\\\[10pt]\n&\\text{Since, }x > 1 \\rightarrow \\left( 2 > 1 \\right):\\;\\;\\textrm{(Comment)}\\end{aligned}\n\\]\n\\[\n\\begin{aligned}\nb &= x \\cdot 1 = 2 \\cdot 1 &= 2\n\\\\\nc &= 2\\;\n\\end{aligned}\n\\]"
    )
    assert (
        cell_2b_renderer.render()
        == "\\[\n\\begin{aligned}\nx &= 10\\;\n\\\\[10pt]\nb &= x \\cdot 1 = 10 \\cdot 1 &= 10\n\\\\\nc &= 10\\;\n\\end{aligned}\n\\]"
    )
    assert (
        cell_3_renderer.render()
        == "\\[\n\\begin{aligned}\ny &= -2\\;\n\\\\[10pt]\nb &= 3\\;\n\\\\[10pt]\nc &= 4\\;\n\\\\[10pt]\n\\alpha_{\\eta_{\\psi}} &= 23\\;\n\\\\[10pt]\nd &= \\sqrt{ \\left( \\frac{ 1 }{ \\frac{ b }{ c } } \\right) } = \\sqrt{ \\left( \\frac{ 1 }{ \\frac{ 3 }{ 4 } } \\right) } &= 1.155\n\\\\[10pt]\nf &= \\operatorname{ceil} \\left( \\left( \\alpha_{\\eta_{\\psi}} + 1 \\right) \\bmod 2 \\right) = \\operatorname{ceil} \\left( \\left( 23 + 1 \\right) \\bmod 2 \\right) &= 0\n\\\\[10pt]\ng &= \\int_{ y } ^ { b } \\left( x \\right) ^{ 2 } + 3 \\cdot x \\; dx = \\int_{ -2 } ^ { 3 } \\left( x \\right) ^{ 2 } + 3 \\cdot x \\; dx &= (19.166666666666664, 2.8705856290806517e-13)\n\\end{aligned}\n\\]"
    )
    assert (
        cell_4_renderer.render()
        == "\\[\n\\begin{aligned}\na &= 2 &b &= 3 &c &= 5\\\\\n y &= 6\n\\end{aligned}\n\\]"
    )
    assert (
        cell_5_renderer.render()
        == "\\[\n\\begin{aligned}\na &= 10000001\\;\\;\\textrm{(Comment)}\n\\\\[10pt]\nb &= 20000002\\;\n\\\\[10pt]\nc &= 30000003\\;\n\\\\[10pt]\ny &= \\sqrt{ \\left( \\frac{ a }{ b } \\right) } + \\arcsin{ \\left( \\sin{ \\left( \\frac{ b }{ c } \\right) } \\right) } + \\left( \\frac{ a }{ b } \\right) ^{ \\left( 0.5 \\right) } + \\sqrt{ \\left( \\frac{ a \\cdot b + b \\cdot c }{ \\left( b \\right) ^{ 2 } } \\right) } + \\sin{ \\left( \\frac{ a }{ b } \\right) } \\\\&= \\sqrt{ \\left( \\frac{ 10000001 }{ 20000002 } \\right) } + \\arcsin{ \\left( \\sin{ \\left( \\frac{ 20000002 }{ 30000003 } \\right) } \\right) } + \\left( \\frac{ 10000001 }{ 20000002 } \\right) ^{ \\left( 0.5 \\right) } + \\sqrt{ \\left( \\frac{ 10000001 \\cdot 20000002 + 20000002 \\cdot 30000003 }{ \\left( 20000002 \\right) ^{ 2 } } \\right) } + \\sin{ \\left( \\frac{ 10000001 }{ 20000002 } \\right) } \\\\&= 3.975\\;\\;\\textrm{(Comment)}\\\\\n\\end{aligned}\n\\]"
    )
    assert (
        cell_6_renderer.render()
        == "\\[\n\\begin{aligned}\na &= 2\\;\n\\\\[10pt]\nb &= 3 \\cdot a \\\\&= 3 \\cdot 2 \\\\&= 6\\\\\n\\\\[10pt]\ny &= 2 \\cdot a + 4 + 3 \\\\&= 2 \\cdot 2 + 4 + 3 \\\\&= 11\\\\\n\\end{aligned}\n\\]"
    )


def test_handcalc():
    assert func_1(4, 5) == (
        "\n\\begin{aligned}\na &= 2 \\cdot x = 2 \\cdot 4 &= 8\n\\\\[10pt]\nb &= 3 \\cdot a + y = 3 \\cdot 8 + 5 &= 29\n\\end{aligned}\n",
        {"x": 4, "y": 5, "a": 8, "b": 29},
    )


# Test expected exceptions


def test_error_cell():
    with pytest.raises(ValueError):
        error_cell_renderer.render()


def test_error_func():
    with pytest.raises(ValueError):
        error_func(4, 5)


def test_add_result_values_to_lines_error():
    with pytest.raises(TypeError):
        handcalcs.handcalcs.add_result_values_to_line("line", {"a": 1})


def test_convert_cell_error():
    with pytest.raises(TypeError):
        handcalcs.handcalcs.convert_cell(["Line 1", "Line 2"])


def test_convert_line_error():
    with pytest.raises(TypeError):
        handcalcs.handcalcs.convert_line(["line", "2"], {"a": 1})


def test_format_cell_error():
    with pytest.raises(TypeError):
        handcalcs.handcalcs.format_cell({"Cell Data": "data"})


def test_round_and_render_line_objects_to_latex_error():
    with pytest.raises(TypeError):
        handcalcs.handcalcs.round_and_render_line_objects_to_latex(
            ["Line data"], precision=3
        )


def test_convert_applicable_long_lines_error():
    with pytest.raises(TypeError):
        handcalcs.handcalcs.convert_applicable_long_lines(["line data", "data 2"])


def test_test_for_long_lines_error():
    with pytest.raises(TypeError):
        handcalcs.handcalcs.test_for_long_lines(["line data", "data"])


def test_format_lines_error():
    with pytest.raises(TypeError):
        handcalcs.handcalcs.format_lines(["Line data"])


# Unit tests


def test_categorize_line():
    assert handcalcs.handcalcs.categorize_line(
        "a = 2 # Comment", {"a": 2}, ""
    ) == ParameterLine(line=deque(["a", "=", 2]), comment=" Comment", latex="")
    assert handcalcs.handcalcs.categorize_line(
        "y = (a+4) # Comment", {"a": 2, "y": 6}, ""
    ) == ParameterLine(line=deque(["y", "=", 6]), comment=" Comment", latex="")
    assert handcalcs.handcalcs.categorize_line(
        "alpha_eta_psi = 4 / (y**(a + 1)) # Comment",
        {"a": 2, "y": 6, "alpha_eta_psi": 0.018518518518518517},
        "",
    ) == CalcLine(
        line=deque(
            ["alpha_eta_psi", "=", "4", "/", deque(["y", "**", deque(["a", "+", "1"])])]
        ),
        comment=" Comment",
        latex="",
    )
    assert handcalcs.handcalcs.categorize_line(
        "alpha_eta_psi", {"a": 2, "y": 6, "alpha_eta_psi": 0.018518518518518517}, ""
    ) == ParameterLine(
        line=deque(["alpha_eta_psi", "=", 0.018518518518518517]), comment="", latex=""
    )
    assert handcalcs.handcalcs.categorize_line(
        "if x < 1: b = x # Comment", {"x": 2, "b": 2}, ""
    ) == ConditionalLine(
        condition=deque(["x", "<", "1"]),
        condition_type="if",
        expressions=deque(
            [ParameterLine(line=deque(["b", "=", 2]), comment="", latex="")]
        ),
        raw_condition="x < 1",
        raw_expression="b = x",
        true_condition=deque([]),
        true_expressions=deque([]),
        comment=" Comment",
        latex="",
    )


def test_add_result_values_to_lines():
    assert handcalcs.handcalcs.add_result_values_to_line(
        CalcLine(
            line=deque(
                [
                    "alpha_eta_psi",
                    "=",
                    "4",
                    "/",
                    deque(["y", "**", deque(["a", "+", "1"])]),
                ]
            ),
            comment=" Comment",
            latex="",
        ),
        {"a": 2, "y": 6, "alpha_eta_psi": 0.018518518518518517},
    ) == CalcLine(
        line=deque(
            [
                "alpha_eta_psi",
                "=",
                "4",
                "/",
                deque(["y", "**", deque(["a", "+", "1"])]),
                deque(["=", 0.018518518518518517]),
            ]
        ),
        comment=" Comment",
        latex="",
    )

    assert handcalcs.handcalcs.add_result_values_to_line(
        ConditionalLine(
            condition=deque(["x", "<", "1"]),
            condition_type="if",
            expressions=deque(
                [ParameterLine(line=deque(["b", "=", 2]), comment="", latex="")]
            ),
            raw_condition="x < 1",
            raw_expression="b = x",
            true_condition=deque([]),
            true_expressions=deque([]),
            comment=" Comment",
            latex="",
        ),
        {"x": 2, "b": 2, "c": 2},
    ) == ConditionalLine(
        condition=deque(["x", "<", "1"]),
        condition_type="if",
        expressions=deque(
            [ParameterLine(line=deque(["b", "=", 2]), comment="", latex="")]
        ),
        raw_condition="x < 1",
        raw_expression="b = x",
        true_condition=deque([]),
        true_expressions=deque([]),
        comment=" Comment",
        latex="",
    )


def test_swap_values():
    assert handcalcs.handcalcs.swap_values(
        deque(["=", "A", "+", 23]), {"A": 43}
    ) == deque(["=", 43, "+", 23])
    assert handcalcs.handcalcs.swap_values(
        deque(["eta", "=", "beta", "+", "theta"]), {"eta": 3, "beta": 2, "theta": 1}
    ) == deque([3, "=", 2, "+", 1])


def test_swap_for_greek():
    assert handcalcs.handcalcs.swap_for_greek(
        deque(["eta", "=", "beta", "+", "theta"])
    ) == deque(["\\eta", "=", "\\beta", "+", "\\theta"])
    assert handcalcs.handcalcs.swap_for_greek(
        deque(["M_r", "=", "phi", "\\cdot", deque(["psi", "\\cdot", "F_y"])])
    ) == deque(["M_r", "=", "\\phi", "\\cdot", deque(["\\psi", "\\cdot", "F_y"])])
    assert handcalcs.handcalcs.swap_for_greek(deque(["lamb", "=", 3])) == deque(
        ["\\lambda", "=", 3]
    )

