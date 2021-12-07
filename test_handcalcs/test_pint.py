import pint

from handcalcs.handcalcs import (
    CalcLine, round_and_render_line_objects_to_latex
)


def test_pint_rounding():
    ureg = pint.UnitRegistry(auto_reduce_dimensions=True)
    ureg.default_format = '~'
    ft = ureg.ft
    kip = ureg.kip

    L = (1.23456789 * kip)
    d = (2 * ft)
    M = L * d

    assert round_and_render_line_objects_to_latex(
        CalcLine([L], '', ''), precision=2, dec_sep='.'
    ).latex == '1.23\\ \\mathrm{kip}'

    assert round_and_render_line_objects_to_latex(
        CalcLine([d], '', ''), precision=2, dec_sep='.'
    ).latex == '2\\ \\mathrm{ft}'

    assert round_and_render_line_objects_to_latex(
        CalcLine([M], '', ''), precision=2, dec_sep='.'
    ).latex == '2.47\\ \\mathrm{ft} \\cdot \\mathrm{kip}'
