import pint

from handcalcs.handcalcs import (
    CalcLine, round_and_render_line_objects_to_latex
)

ureg = pint.UnitRegistry(auto_reduce_dimensions=True)
ureg.default_format = '~'
ft = ureg.ft
kip = ureg.kip


def test_pint_rounding():
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


def test_pint_with_sympy():
    import sympy
    pint.quantity._Quantity._sympy_ = lambda s: sympy.sympify(f'({s.m})*{s.u}')
    pint.quantity._Quantity._repr_latex_ = lambda s: (
        s.m._repr_latex_() + r'\ ' + s.u._repr_latex_()
        if hasattr(s.m, '_repr_latex_') else '${:~L}$'.format(s)
    )
    L = 1.23456789 * sympy.symbols('a') * kip
    assert round_and_render_line_objects_to_latex(
        CalcLine([L], '', ''), precision=3, dec_sep='.'
    ).latex == r'\displaystyle 1.235 a\ \mathrm{kip}'
