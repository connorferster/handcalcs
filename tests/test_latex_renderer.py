"""
Tests for the LatexRenderer's swap rules, run through the full HandCalcs
pipeline (source -> parser -> HcSequence -> LatexRenderer).

LatexRenderer does not yet join its output, so these assert against the
rendered tree: ``[import_line, ['', [calc_line, ...]]]`` where each calc line
is ``[target, '=', symbolic, '=', numeric, ..., '=', result]``.
"""
from handcalcs import HandCalcs, PlainTextRenderer
from handcalcs.renderers.latex import LatexRenderer


def _calc_lines(source):
    *_, (_, lines) = HandCalcs(LatexRenderer())(source)
    return {line[0]: line for line in lines}


def test_math_namespace_dropped_for_floor_ceil_sqrt():
    lines = _calc_lines(
        "import math\n"
        "x = 2.5\n"
        "a = math.floor(x)\n"
        "b = math.ceil(x)\n"
        "c = math.sqrt(x)\n"
    )
    assert lines["a"][2:5] == ["\\lfloor x\\rfloor", "=", "\\lfloor 2.5\\rfloor"]
    assert lines["b"][2:5] == ["\\lceil x\\rceil", "=", "\\lceil 2.5\\rceil"]
    assert lines["c"][2:5] == ["\\sqrt{x}", "=", "\\sqrt{2.5}"]


def test_math_namespace_kept_for_other_functions():
    lines = _calc_lines("import math\nx = 2.5\nr = math.sin(x)\n")
    assert lines["r"][2] == "\\mathrm{math}.\\sin\\left(x\\right)"


def test_func_symbols_not_rewrapped_on_numeric_pass():
    # The function_call:pre rule runs on both the symbolic and numeric passes
    # over the same node; the second pass must not wrap \sqrt or \sin in
    # \operatorname{} or reset floor's delimiters.
    lines = _calc_lines(
        "from math import sqrt, sin, floor\n"
        "x = 2.5\n"
        "r = sqrt(x) + sin(x) + floor(x)\n"
    )
    assert lines["r"][4] == (
        "\\sqrt{2.5}\\ +\\ \\sin\\left(2.5\\right)\\ +\\ \\lfloor 2.5\\rfloor"
    )


def test_user_function_wrapped_in_operatorname():
    lines = _calc_lines("def f(x):\n    return x\ny = 3\nr = f(y)\n")
    assert lines["r"][2] == "\\operatorname{f} \\left(y\\right)"


def test_comparison_symbols_are_latex_commands_with_separator():
    lines = _calc_lines(
        "a = 2\nb = 3\n"
        "t = a != b\n"
        "u = a <= b\n"
        "v = a >= b\n"
    )
    assert lines["t"][2] == "a\\ne b"
    assert lines["u"][2] == "a\\le b"
    assert lines["v"][2] == "a\\ge b"


def test_comparison_symbol_swap_does_not_leak_to_other_renderers():
    # Operator symbols are rewritten in place, so a LaTeX render must not
    # change what a later plaintext render of the same source shows.
    source = "a = 2\nb = 3\nt = a != b\nu = a <= b\n"
    HandCalcs(LatexRenderer())(source)
    out = HandCalcs(PlainTextRenderer())(source)
    assert "t = a!=b" in out
    assert "u = a<=b" in out


def test_subscripts_and_long_names():
    lines = _calc_lines("alpha_c = 2\nRate_annual = 3\nx__y = 4\n")
    assert "\\alpha_{c}" in lines
    assert "\\mathrm{Rate}_{\\mathrm{annual}}" in lines
    assert "\\mathrm{x\\ y}" in lines
