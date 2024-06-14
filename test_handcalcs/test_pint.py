import pint
import handcalcs.global_config

from handcalcs.handcalcs import CalcLine, round_and_render_line_objects_to_latex


ureg = pint.UnitRegistry(auto_reduce_dimensions=True)
ureg.default_format = "~"
ft = ureg.ft
kip = ureg.kip

config_options = handcalcs.global_config._config


def test_pint_rounding():
    L = 1.23456789 * kip
    d = 2 * ft
    M = L * d

    assert (
        round_and_render_line_objects_to_latex(
            CalcLine([L], "", ""),
            cell_precision=2,
            cell_notation=False,
            **config_options
        ).latex
        == "1.23\\ \\mathrm{kip}"
    )

    assert (
        round_and_render_line_objects_to_latex(
            CalcLine([d], "", ""),
            cell_precision=2,
            cell_notation=True,
            **config_options
        ).latex
        == "2.00\\times 10^{0}\\ \\mathrm{foot}"
    )

    assert (
        round_and_render_line_objects_to_latex(
            CalcLine([M], "", ""),
            cell_precision=2,
            cell_notation=False,
            **config_options
        ).latex
        == "2.47\\ \\mathrm{foot} \\cdot \\mathrm{kip}"
    )


def test_pint_with_sympy():
    # NOTE: This test fails because pint introduced breaking changes at some point and
    # the module path of pint.quantity._Quantity._sympy_ no longer exists. A cursory
    # review of the pint code could not locate it.
    # Because pint is still in 0.x.y, the API is likely to be volatile which makes
    # testing difficult.

    # ===============(Begin test)
    # import sympy
    # pint.quantity._Quantity._sympy_ = lambda s: sympy.sympify(f'({s.m})*{s.u}')
    # pint.quantity._Quantity._repr_latex_ = lambda s: (
    #     s.m._repr_latex_() + r'\ ' + s.u._repr_latex_()
    #     if hasattr(s.m, '_repr_latex_') else '${:~L}$'.format(s)
    # )
    # L = 1.23456789 * sympy.symbols('a') * kip

    # NOTE: Pint in sympy objects do not accept float format strings. While pint has its own
    # format strings which kinda work like float format strings, they DO NOT work
    # when pint objects are in sympy objects. Therefore, pint objects in sympy
    # objects will typically be rounded to one extra decimal place. This is just
    # the way it is.
    # assert round_and_render_line_objects_to_latex( # cell_precision=3 -> four decimal places
    #     CalcLine([L], '', ''), cell_precision=3, cell_notation=True, **config_options
    # ).latex == '\\mathtt{\\text{1.2346*a kip}}'
    # ===============(End test)
    pass
