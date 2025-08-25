#    Copyright 2020 Connor Ferster

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


import inspect
from collections import deque

import handcalcs
import pytest
import forallpeople as si


si.environment("default")

from handcalcs.handcalcs import ParameterLine, CalcLine, LongCalcLine, ConditionalLine
from handcalcs.handcalcs import ParameterCell, LongCalcCell, CalcCell
from handcalcs.decorator import handcalc
import handcalcs.global_config


# When writing a new test create a new "cell" .py file
from test_handcalcs import cell_1
from test_handcalcs import cell_2
from test_handcalcs import cell_2b
from test_handcalcs import cell_3
from test_handcalcs import cell_4
from test_handcalcs import cell_5
from test_handcalcs import cell_6
from test_handcalcs import cell_7
from test_handcalcs import cell_7b
from test_handcalcs import cell_8
from test_handcalcs import cell_9
from test_handcalcs import cell_10
from test_handcalcs import cell_11
from test_handcalcs import error_cell

config_options = {
    "decimal_separator": ".",
    "latex_block_start": "\\[",
    "latex_block_end": "\\]",
    "math_environment_start": "aligned",
    "math_environment_end": "aligned",
    "line_break": "\\\\[10pt]",
    "use_scientific_notation": False,
    "display_precision": 3,
    "underscore_subscripts": True,
    "zero_tolerance": 16,
    "greek_exclusions": [],
    "param_columns": 3,
    "preferred_string_formatter": "L",
    "custom_symbols": {"V_dot": "\\dot{V}"},
    "custom_brackets": {
        "parenthesis": "ˉ",
        "square_brackets": "ˍ",
        "angle_brackets": "ˆ",
        "curly_brackets": "ǂ",
        "pipes": "ǀ",
        "double_pipes": "ǁ",
    }
}

config_underscore_spaces = config_options.copy()
config_underscore_spaces["underscore_subscripts"] = False

# TODO: Integration tests with nested log, nested exponents


class MockLatexObj1:
    def __init__(self, s: str):
        self.s = s
        self.a = "{"
        self.b = "}"

    def __format__(self, formatter: str):
        if "L" in formatter:
            return f"\\mathrm{self.a}{self.s}{self.b}"


class MockLatexObj2:
    def __init__(self, s: str):
        self.a = "{"
        self.b = "}"
        self.s = s

    def _repr_latex_(self):
        return f"\\text{self.a}{self.s}{self.b}"


def int_func(x):
    return x**2 + 3 * x


def quad(f, a, b):
    return (f(b) - f(a), 0.001)


# def test_import_render():
#     with pytest.raises(ImportError):
#         import handcalcs.render


def remove_imports_defs_and_globals(source: str):
    """
    For "cell" modules used in testing, this function removes
    content not intended to be rendered such as import statements,
    function definitions, and the calc_results = globals() line.
    """
    source_lines = source.split("\n")
    acc = []
    doc_string = False
    for line in source_lines:
        if (
            not doc_string
            and line.lstrip(" \t").startswith('"""')
            and line.lstrip(" \t").rstrip().endswith('"""', 3)
        ):
            doc_string = False
            continue
        elif (
            not doc_string
            and line.lstrip(" \t").startswith('"""')
            and not line.lstrip(" \t").rstrip().endswith('"""', 3)
        ):
            doc_string = True
            continue
        elif doc_string and '"""' in line:
            doc_string = False
            continue
        if (
            "def" not in line
            and not doc_string
            and "return" not in line
            and "@" not in line
            and "globals" not in line
            and "import" not in line
            and line
        ):
            acc.append(line)
    return "\n".join(acc)


@handcalc()
def func_1(x, y):
    a = 2 * x
    b = 3 * a + y
    return b


@handcalc(jupyter_display=True)
def func_2(x, y):
    """
    My doc string
    Line 2 of doc string
    """
    a = 2 * x
    b = 3 * a + y
    return locals()  # not necessary, but allowed


@handcalc(jupyter_display=True)
def func_3(x, y):
    """My single line docstring"""
    a = 2 * x
    b = 3 * a + y
    return locals()  # not necessary, but allowed


line_args = {"override": "", "precision": None, "sci_not": False}
line_args_params = {"override": "params", "precision": None, "sci_not": False}
line_args_symbolic = {"override": "symbolic", "precision": None, "sci_not": False}
line_args_long = {"override": "long", "precision": 2, "sci_not": False}
line_args_short = {"override": "short", "precision": 3, "sci_not": False}
line_args_1 = {"override": "", "precision": 5, "sci_not": True}
line_args_2 = {"override": "", "precision": None, "sci_not": False}
line_args_3 = {"override": "", "precision": 3, "sci_not": True}
line_args_4 = {"override": "params", "precision": None, "sci_not": False}
line_args_10 = {"override": "", "precision": None, "sci_not": True}

cell_1_source = remove_imports_defs_and_globals(inspect.getsource(cell_1))
cell_2_source = remove_imports_defs_and_globals(inspect.getsource(cell_2))
cell_2b_source = remove_imports_defs_and_globals(inspect.getsource(cell_2b))
cell_3_source = remove_imports_defs_and_globals(inspect.getsource(cell_3))
cell_4_source = remove_imports_defs_and_globals(inspect.getsource(cell_4))
cell_5_source = remove_imports_defs_and_globals(inspect.getsource(cell_5))
cell_6_source = remove_imports_defs_and_globals(inspect.getsource(cell_6))
cell_7_source = remove_imports_defs_and_globals(inspect.getsource(cell_7))
cell_7b_source = remove_imports_defs_and_globals(inspect.getsource(cell_7b))
cell_8_source = remove_imports_defs_and_globals(inspect.getsource(cell_8))
cell_9_source = remove_imports_defs_and_globals(inspect.getsource(cell_9))
cell_10_source = remove_imports_defs_and_globals(inspect.getsource(cell_10))
cell_11_source = remove_imports_defs_and_globals(inspect.getsource(cell_11))
error_cell_source = remove_imports_defs_and_globals(inspect.getsource(error_cell))

cell_1_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_1_source,
    cell_1.calc_results,
    line_args_1,
)
cell_2_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_2_source,
    cell_2.calc_results,
    line_args_2,
)
cell_2b_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_2b_source,
    cell_2b.calc_results,
    line_args_2,
)
cell_3_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_3_source,
    cell_3.calc_results,
    line_args_3,
)
cell_4_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_4_source,
    cell_4.calc_results,
    line_args_params,
)
cell_5_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_5_source,
    cell_5.calc_results,
    line_args,
)
cell_6_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_6_source,
    cell_6.calc_results,
    line_args,
)
cell_7_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_7_source,
    cell_7.calc_results,
    line_args_long,
)
cell_7b_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_7b_source,
    cell_7b.calc_results,
    line_args_short,
)
cell_8_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_8_source,
    cell_8.calc_results,
    line_args,
)
cell_9_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_9_source,
    cell_9.calc_results,
    line_args_symbolic,
)
cell_10_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_10_source,
    cell_10.calc_results,
    line_args_10,
)
cell_11_renderer = handcalcs.handcalcs.LatexRenderer(
    cell_11_source,
    cell_11.calc_results,
    line_args,
)

# error_cell_renderer = handcalcs.handcalcs.LatexRenderer(
error_cell_renderer = handcalcs.handcalcs.LatexRenderer(
    error_cell_source,
    error_cell.calc_results,
    line_args,
)

# Integration tests
# Majority of test coverage primarily comes from these...


def test_integration():
    assert (
        cell_1_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\na &= 2 \\; \\;\\textrm{(Comment)}\n\\\\[10pt]\ny &= 6 \\; \\;\\textrm{(Comment)}\n\\\\[10pt]\n\\alpha_{\\eta_{\\psi}} &= \\frac{ 4 }{ \\left( y \\right) ^{ \\left( a + 1 \\right) } }  = \\frac{ 4 }{ \\left( 6 \\right) ^{ \\left( 2 + 1 \\right) } } &= 1.85185 \\times 10 ^ {-2} \\; \\;\\textrm{(Comment)}\n\\\\[10pt]\n\\alpha_{\\eta_{\\psi}} &= 1.85185 \\times 10 ^ {-2} \\; \n\\end{aligned}\n\\]"
    )
    assert (
        cell_2_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\nx &= 2 \\; \n\\\\[10pt]\n&\\text{Since, } x \\geq 1 \\rightarrow \\left( 2 \\geq 1 \\right) : \\; \\;\\textrm{(Comment)} \\\\[10pt]\nb &= x \\cdot 1  = 2 \\cdot 1 &= 2  \n\\\\[10pt]\nc &= 2 \\; \n\\end{aligned}\n\\]"
    )
    assert (
        cell_2b_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\nx &= 10 \\; \n\\\\[10pt]\nb &= x \\cdot 1  = 10 \\cdot 1 &= 10  \n\\\\[10pt]\nc &= 10 \\; \n\\end{aligned}\n\\]"
    )
    assert (
        cell_3_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\ny &= -2 \\; \n\\\\[10pt]\nb &= 3 \\; \n\\\\[10pt]\nc &= 4 \\; \n\\\\[10pt]\n\\alpha_{\\eta_{\\psi}} &= 23 \\; \n\\\\[10pt]\nd &= \\sqrt { \\frac{ 1 }{ b } \\cdot \\frac{1} { c } }  = \\sqrt { \\frac{ 1 }{ 3 } \\cdot \\frac{1} { 4 } } &= 2.887 \\times 10 ^ {-1}  \n\\\\[10pt]\nf &= \\left \\lceil \\left( \\alpha_{\\eta_{\\psi}} + 1 \\right) \\bmod 2 \\right \\rceil  = \\left \\lceil \\left( 23 + 1 \\right) \\bmod 2 \\right \\rceil &= 0  \n\\\\[10pt]\ng &= \\int_{ y } ^ { b } \\left( x \\right) ^{ 2 } + 3 \\cdot x \\; dx  = \\int_{ -2 } ^ { 3 } \\left( x \\right) ^{ 2 } + 3 \\cdot x \\; dx &= [42,\ 1.000 \\times 10 ^ {-3}]  \n\\end{aligned}\n\\]"
    )
    assert (
        cell_4_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\na &= 2 \\; \\;\\textrm{(Comment)}\n &b &= 3 \\; \n &c &= 5 \\; \n\\\\[10pt]\n y &= 6 \\; \\;\\textrm{(Comment)}\n\\end{aligned}\n\\]"
    )
    assert (
        cell_5_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\na &= 10000001 \\; \\;\\textrm{(Comment)}\n\\\\[10pt]\nb &= 20000002 \\; \n\\\\[10pt]\nc &= 30000003 \\; \n\\\\[10pt]\nx &= 5 \\; \n\\\\[10pt]\ny &= \\sqrt { \\frac{ a }{ b } } + \\arcsin \\left( \\sin \\left( \\frac{ b }{ c } \\right) \\right) + \\left( \\frac{ a }{ b } \\right) ^{ 0.5 } + \\sqrt { \\frac{ a \\cdot b + b \\cdot c }{ \\left( b \\right) ^{ 2 } } } + \\sin \\left( \\frac{ a }{ b } \\right) \\\\&= \\sqrt { \\frac{ 10000001 }{ 20000002 } } + \\arcsin \\left( \\sin \\left( \\frac{ 20000002 }{ 30000003 } \\right) \\right) + \\left( \\frac{ 10000001 }{ 20000002 } \\right) ^{ 0.5 } + \\sqrt { \\frac{ 10000001 \\cdot 20000002 + 20000002 \\cdot 30000003 }{ \\left( 20000002 \\right) ^{ 2 } } } + \\sin \\left( \\frac{ 10000001 }{ 20000002 } \\right) \\\\&= 3.975 \\; \\;\\textrm{(Comment)}\\\\[10pt]\n\\end{aligned}\n\\]"
    )
    assert (
        cell_6_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\na &= 2 \\; \n\\\\[10pt]\nb &= 3 \\cdot a \\\\&= 3 \\cdot 2 \\\\&= 6  \\\\[10pt]\n\\\\[10pt]\ny &= 2 \\cdot a + 4 + 3 \\\\&= 2 \\cdot 2 + 4 + 3 \\\\&= 11  \\\\[10pt]\n\\end{aligned}\n\\]"
    )
    assert (
        cell_7_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\na &= 23 \\; \n\\\\[10pt]\nb &= 43 \\; \n\\\\[10pt]\nc &= 52 \\; \n\\\\[10pt]\nf &= \\frac{ c }{ a } + b \\\\&= \\frac{ 52 }{ 23 } + 43 \\\\&= 45.26 \\; \\;\\textrm{(Comment)}\\\\[10pt]\n\\\\[10pt]\ng &= c \\cdot \\frac{ f }{ a } \\\\&= 52 \\cdot \\frac{ 45.26 }{ 23 } \\\\&= 102.33 \\; \\;\\textrm{(Comment)}\\\\[10pt]\n\\\\[10pt]\nd &= \\sqrt { \\frac{ a }{ b } } + \\arcsin \\left( \\sin \\left( \\frac{ b }{ c } \\right) \\right) + \\left( \\frac{ a }{ b } \\right) ^{ 0.5 } + \\sqrt { \\frac{ a \\cdot b + b \\cdot c }{ \\left( b \\right) ^{ 2 } } } + \\sin \\left( \\frac{ a }{ b } \\right) \\\\&= \\sqrt { \\frac{ 23 }{ 43 } } + \\arcsin \\left( \\sin \\left( \\frac{ 43 }{ 52 } \\right) \\right) + \\left( \\frac{ 23 }{ 43 } \\right) ^{ 0.5 } + \\sqrt { \\frac{ 23 \\cdot 43 + 43 \\cdot 52 }{ \\left( 43 \\right) ^{ 2 } } } + \\sin \\left( \\frac{ 23 }{ 43 } \\right) \\\\&= 4.12 \\; \\;\\textrm{(Comment)}\\\\[10pt]\n\\end{aligned}\n\\]"
    )
    assert (
        cell_7b_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\n\\alpha_{\\zeta} &= 0.984 \\; \n\\\\[10pt]\nb'_{c} &= 43 \\; \n\\\\[10pt]\n\\mathrm{causal} &= 4.200+3.200j \\; \n\\\\[10pt]\nf &= \\frac{ \\mathrm{causal} }{ \\alpha_{\\zeta} } + b'_{c}  = \\frac{ 4.200+3.200j }{ 0.984 } + 43 &= 47.268+3.252j \\; \\;\\textrm{(Comment)}\n\\\\[10pt]\ng &= \\mathrm{causal} \\cdot \\frac{ f }{ \\alpha_{\\zeta} }  = 4.200+3.200j \\cdot \\frac{ 47.268+3.252j }{ 0.984 } &= 191.179+167.599j \\; \\;\\textrm{(Comment)}\n\\\\[10pt]\nd &= \\sqrt { \\frac{ \\alpha_{\\zeta} }{ b'_{c} } } + \\Sigma \\left( 1 ,\\  2 ,\\  3 \\right) + \\left( \\frac{ \\alpha_{\\zeta} }{ b'_{c} } \\right) ^{ 0.5 } + \\sqrt { \\frac{ \\alpha_{\\zeta} \\cdot b'_{c} + b'_{c} }{ \\left( 1.23 \\times 10 ^ {3} \\right) ^{ 2 } } } + \\sin \\left( \\frac{ \\alpha_{\\zeta} }{ b'_{c} } \\right)  = \\sqrt { \\frac{ 0.984 }{ 43 } } + \\Sigma \\left( 1 ,\\  2 ,\\  3 \\right) + \\left( \\frac{ 0.984 }{ 43 } \\right) ^{ 0.5 } + \\sqrt { \\frac{ 0.984 \\cdot 43 + 43 }{ \\left( 1.23 \\times 10 ^ {3} \\right) ^{ 2 } } } + \\sin \\left( \\frac{ 0.984 }{ 43 } \\right) &= 6.333 \\; \\;\\textrm{(Comment)}\n\\end{aligned}\n\\]"
    )
    assert (
        cell_8_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\na &= 23 \\; \n\\\\[10pt]\n\\dot{V} &= 43 \\; \n\\\\[10pt]\nc &= 52 \\; \n\\\\[10pt]\nf &= \\frac{ c }{ a } + \\dot{V}  = \\frac{ 52 }{ 23 } + 43 &= 45.261 \\; \\;\\textrm{(Comment)}\n\\\\[10pt]\ng &= c \\cdot \\frac{ f }{ a }  = 52 \\cdot \\frac{ 45.261 }{ 23 } &= 102.329 \\; \\;\\textrm{(Comment)}\n\\\\[10pt]\nd &= \\sqrt { \\frac{ a }{ \\dot{V} } + \\arcsin \\left( \\sin \\left( \\frac{ \\dot{V} }{ c } \\right) \\right) + \\left( \\frac{ a }{ \\dot{V} } \\right) ^{ 0.5 } + \\sqrt { \\frac{ a \\cdot \\dot{V} + \\dot{V} \\cdot c }{ \\left( \\dot{V} \\right) ^{ 2 } } } + \\sin \\left( \\frac{ a }{ \\dot{V} } \\right) } \\\\&= \\sqrt { \\frac{ 23 }{ 43 } + \\arcsin \\left( \\sin \\left( \\frac{ 43 }{ 52 } \\right) \\right) + \\left( \\frac{ 23 }{ 43 } \\right) ^{ 0.5 } + \\sqrt { \\frac{ 23 \\cdot 43 + 43 \\cdot 52 }{ \\left( 43 \\right) ^{ 2 } } } + \\sin \\left( \\frac{ 23 }{ 43 } \\right) } \\\\&= 1.981 \\; \\;\\textrm{(Comment)}\\\\[10pt]\n\\end{aligned}\n\\]"
    )
    assert (
        cell_9_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\n\\mu &= 0.44 \\; \n\\\\[10pt]\n\\mathrm{CritSeg} &= 1.5 \\; \\;\\textrm{(sendo extramemente)}\n\\\\[10pt]\n\\Delta_{h} &= 9.641 \\; \n\\\\[10pt]\n\\mathrm{Raio} &= \\left( \\frac{ 200 }{ 2 } \\right) \\; \\;\\textrm{(Config)}\n\\\\[10pt]\n\\mathrm{Raio}_{Minimo} &= \\mathrm{CritSeg} \\cdot \\frac{ \\Delta_{h} }{ \\left( \\sin \\left( \\arctan \\left( \\mu + 1 \\right) + 1 \\right) \\right) ^{ 2 } } \\; \n\\end{aligned}\n\\]"
    )
    assert (
        cell_10_renderer.render(config_options=config_options)
        == '\\[\n\\begin{aligned}\n\\mu &= 45 + \\frac{ \\sin \\left( 34 + 2 \\right) }{ 2 } &= 4.450 \\times 10 ^ {1} \\; \\;\\textrm{(Comment)}\n\\\\[10pt]\n\\tau &= \\sin \\left( \\log_{2} \\left( \\log_{9} \\left( 3 \\right) \\right) \\right) &= -8.415 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\eta &= \\sqrt { \\frac{ 1 }{ \\log_{10} \\left( 6 \\right) } \\cdot \\frac{1} { \\ln \\left( 32 \\right) } } &= 6.089 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\kappa &= \\left \\lfloor \\frac{ 23 }{ 4.5 } \\right \\rfloor &= 5 \\; \\;\\textrm{(Last comment)}\n\\\\[10pt]\n\\varepsilon &= 45 + \\frac{ \\sin \\left( 34 + 2 \\right) }{ 2 } &= 4.450 \\times 10 ^ {1} \\; \\;\\textrm{(Comment)}\n\\\\[10pt]\n\\epsilon &= \\sin \\left( \\log_{2} \\left( \\log_{9} \\left( 3 \\right) \\right) \\right) &= -8.415 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\vartheta &= \\sqrt { \\frac{ 1 }{ \\log_{10} \\left( 6 \\right) } \\cdot \\frac{1} { \\ln \\left( 32 \\right) } } &= 6.089 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\theta &= \\sqrt { \\frac{ 1 }{ \\log_{10} \\left( 6 \\right) } \\cdot \\frac{1} { \\ln \\left( 32 \\right) } } &= 6.089 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\varpi &= \\sqrt { \\frac{ 1 }{ \\log_{10} \\left( 6 \\right) } \\cdot \\frac{1} { \\ln \\left( 32 \\right) } } &= 6.089 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\pi &= \\sqrt { \\frac{ 1 }{ \\log_{10} \\left( 6 \\right) } \\cdot \\frac{1} { \\ln \\left( 32 \\right) } } &= 6.089 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\varrho &= \\sqrt { \\frac{ 1 }{ \\log_{10} \\left( 6 \\right) } \\cdot \\frac{1} { \\ln \\left( 32 \\right) } } &= 6.089 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\rho &= \\sqrt { \\frac{ 1 }{ \\log_{10} \\left( 6 \\right) } \\cdot \\frac{1} { \\ln \\left( 32 \\right) } } &= 6.089 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\varsigma &= \\sqrt { \\frac{ 1 }{ \\log_{10} \\left( 6 \\right) } \\cdot \\frac{1} { \\ln \\left( 32 \\right) } } &= 6.089 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\sigma &= \\sqrt { \\frac{ 1 }{ \\log_{10} \\left( 6 \\right) } \\cdot \\frac{1} { \\ln \\left( 32 \\right) } } &= 6.089 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\varphi &= \\sqrt { \\frac{ 1 }{ \\log_{10} \\left( 6 \\right) } \\cdot \\frac{1} { \\ln \\left( 32 \\right) } } &= 6.089 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\phi &= \\sqrt { \\frac{ 1 }{ \\log_{10} \\left( 6 \\right) } \\cdot \\frac{1} { \\ln \\left( 32 \\right) } } &= 6.089 \\times 10 ^ {-1}  \n\\\\[10pt]\n\\Omega &= \\varepsilon + \\epsilon + \\vartheta + \\theta + \\varpi + \\pi + \\varrho + \\rho + \\varsigma + \\sigma + \\varphi + \\phi \\\\&= 4.450 \\times 10 ^ {1} + -8.415 \\times 10 ^ {-1} + 6.089 \\times 10 ^ {-1} + 6.089 \\times 10 ^ {-1} + 6.089 \\times 10 ^ {-1} + 6.089 \\times 10 ^ {-1} + 6.089 \\times 10 ^ {-1} + 6.089 \\times 10 ^ {-1} + 6.089 \\times 10 ^ {-1} + 6.089 \\times 10 ^ {-1} + 6.089 \\times 10 ^ {-1} + 6.089 \\times 10 ^ {-1} \\\\&= 4.975 \\times 10 ^ {1}  \\\\[10pt]\n\\end{aligned}\n\\]'
    )
    assert (
        cell_11_renderer.render(config_options=config_options)
        == "\\[\n\\begin{aligned}\nF_{e_{x}} &= \\frac{ \\operatorname{euler\\ buckling\\ load} \\left( E ,\\  I_{x} ,\\  k_{x} ,\\  L \\right) }{ \\mathrm{area} }  = \\frac{ \\operatorname{euler\\ buckling\\ load} \\left( 200000.000 ,\\  300000000.000 ,\\  1.000 ,\\  3500 \\right) }{ 1000 } &= 4.500  \n\\\\[10pt]\nF_{e_{y}} &= \\frac{ \\operatorname{euler\\ buckling\\ load} \\left( E ,\\  I_{y} ,\\  k_{y} ,\\  L \\right) }{ \\mathrm{area} }  = \\frac{ \\operatorname{euler\\ buckling\\ load} \\left( 200000.000 ,\\  150000000.000 ,\\  1.000 ,\\  3500 \\right) }{ 1000 } &= 4.500  \n\\\\[10pt]\nF_{e} &= \\operatorname{min} \\left( F_{e_{x}} ,\\  F_{e_{y}} \\right)  = \\operatorname{min} \\left( 4.500 ,\\  4.500 \\right) &= 4.500  \n\\\\[10pt]\n\\lambda &= \\sqrt { \\frac{ f_{y} }{ F_{e} } }  = \\sqrt { \\frac{ 350 }{ 4.500 } } &= 8.819  \n\\\\[10pt]\nP_{r} &= \\phi \\cdot \\mathrm{area} \\cdot f_{y} \\cdot \\left( 1 + \\left( \\lambda \\right) ^{ \\left( 2 \\cdot n \\right) } \\right) ^{ \\left( \\frac{ \\left( - 1 \\right) }{ n } \\right) } \\\\&= 0.900 \\cdot 1000 \\cdot 350 \\cdot \\left( 1 + \\left( 8.819 \\right) ^{ \\left( 2 \\cdot 1.340 \\right) } \\right) ^{ \\left( \\frac{ \\left( - 1 \\right) }{ 1.340 } \\right) } \\\\&= 4041.179  \\\\[10pt]\n\\end{aligned}\n\\]"
    )


# Test decorator.py


def test_handcalc():
    assert func_1(4, 5) == (
        "\n\\begin{aligned}\na &= 2 \\cdot x  = 2 \\cdot 4 &= 8  \n\\\\[10pt]\nb &= 3 \\cdot a + y  = 3 \\cdot 8 + 5 &= 29  \n\\end{aligned}\n",
        29,
    )


def test_handcalc2():
    assert func_2(4, 5) == {"x": 4, "y": 5, "a": 8, "b": 29}


def test_handcalcs3():
    assert func_3(4, 5) == {"x": 4, "y": 5, "a": 8, "b": 29}


# Test expected exceptions


def test_error_cell():
    with pytest.raises(ValueError):
        error_cell_renderer.render()


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
            ["Line data"], cell_precision=3, cell_notation=False, **config_options
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


# def test_categorize_line():
#     assert handcalcs.handcalcs.categorize_line(
#         "a = 2 # Comment", {"a": 2}, ""
#     ) == ParameterLine(line=deque(["a", "=", 2]), comment=" Comment", latex="")
#     assert handcalcs.handcalcs.categorize_line(
#         "y = (a+4) # Comment", {"a": 2, "y": 6}, ""
#     ) == ParameterLine(line=deque(["y", "=", 6]), comment=" Comment", latex="")
#     assert handcalcs.handcalcs.categorize_line(
#         "alpha_eta_psi = 4 / (y**(a + 1)) # Comment",
#         {"a": 2, "y": 6, "alpha_eta_psi": 0.018518518518518517},
#         "",
#     ) == CalcLine(
#         line=deque(
#             ["alpha_eta_psi", "=", "4", "/", deque(["y", "**", deque(["a", "+", "1"])])]
#         ),
#         comment=" Comment",
#         latex="",
#     )
#     assert handcalcs.handcalcs.categorize_line(
#         "alpha_eta_psi", {"a": 2, "y": 6, "alpha_eta_psi": 0.018518518518518517}, ""
#     ) == ParameterLine(
#         line=deque(["alpha_eta_psi", "=", 0.018518518518518517]), comment="", latex=""
#     )
#     assert handcalcs.handcalcs.categorize_line(
#         "if x < 1: b = x # Comment", {"x": 2, "b": 2}, ""
#     ) == ConditionalLine(
#         condition=deque(["x", "<", "1"]),
#         condition_type="if",
#         expressions=deque(
#             [ParameterLine(line=deque(["b", "=", 2]), comment="", latex="")]
#         ),
#         raw_condition="x < 1",
#         raw_expression="b = x",
#         true_condition=deque([]),
#         true_expressions=deque([]),
#         comment=" Comment",
#         latex="",
#     )


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
            latex_expressions="",
            latex_condition="",
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
        latex_expressions="",
        latex_condition="",
        latex="",
    )


def test_round_and_render_line_objects_to_latex():
    assert handcalcs.handcalcs.round_and_render_line_objects_to_latex(
        CalcLine(
            line=deque(
                [
                    "\\alpha_{\\eta_{\\psi}}",
                    "=",
                    "\\frac{",
                    "4",
                    "}{",
                    "\\left(",
                    "y",
                    "\\right)",
                    "^{",
                    "\\left(",
                    "a",
                    "+",
                    "1",
                    "\\right)",
                    "}",
                    "}",
                    "=",
                    "\\frac{",
                    "4",
                    "}{",
                    "\\left(",
                    6,
                    "\\right)",
                    "^{",
                    "\\left(",
                    2,
                    "+",
                    "1",
                    "\\right)",
                    "}",
                    "}",
                    "=",
                    0.018518518518518517,
                ]
            ),
            comment=" Comment",
            latex="",
        ),
        cell_precision=3,
        cell_notation=True,
        **config_options,
    ) == CalcLine(
        line=deque(
            [
                "\\alpha_{\\eta_{\\psi}}",
                "=",
                "\\frac{",
                "4",
                "}{",
                "\\left(",
                "y",
                "\\right)",
                "^{",
                "\\left(",
                "a",
                "+",
                "1",
                "\\right)",
                "}",
                "}",
                "=",
                "\\frac{",
                "4",
                "}{",
                "\\left(",
                "6",
                "\\right)",
                "^{",
                "\\left(",
                "2",
                "+",
                "1",
                "\\right)",
                "}",
                "}",
                "=",
                "1.852 \\times 10 ^ {-2}",
            ]
        ),
        comment=" Comment",
        latex="\\alpha_{\\eta_{\\psi}} = \\frac{ 4 }{ \\left( y \\right) ^{ \\left( a + 1 \\right) } } = \\frac{ 4 }{ \\left( 6 \\right) ^{ \\left( 2 + 1 \\right) } } = 1.852 \\times 10 ^ {-2}",
    )

    assert handcalcs.handcalcs.round_and_render_line_objects_to_latex(
        ParameterLine(
            line=deque(["\\alpha_{\\eta_{\\psi}}", "=", 0.018518518518518517]),
            comment="",
            latex="",
        ),
        cell_precision=3,
        cell_notation=True,
        **config_options,
    ) == ParameterLine(
        line=deque(["\\alpha_{\\eta_{\\psi}}", "=", "1.852 \\times 10 ^ {-2}"]),
        comment="",
        latex="\\alpha_{\\eta_{\\psi}} = 1.852 \\times 10 ^ {-2}",
    )

    assert handcalcs.handcalcs.round_and_render_line_objects_to_latex(
        ParameterLine(line=deque(["y", "=", -2]), comment="", latex=""),
        cell_precision=3,
        cell_notation=True,
        **config_options,
    ) == ParameterLine(line=deque(["y", "=", "-2"]), comment="", latex="y = -2")

    assert handcalcs.handcalcs.round_and_render_line_objects_to_latex(
        CalcLine(
            line=deque(
                [
                    "y",
                    "=",
                    "\\sqrt{",
                    "\\left(",
                    "\\frac{",
                    "a",
                    "}{",
                    "b",
                    "}",
                    "\\right)",
                    "}",
                    "+",
                    "\\arcsin{",
                    "\\left(",
                    "\\sin{",
                    "\\left(",
                    "\\frac{",
                    "b",
                    "}{",
                    "c",
                    "}",
                    "\\right)",
                    "}",
                    "\\right)",
                    "}",
                    "+",
                    "\\left(",
                    "\\frac{",
                    "a",
                    "}{",
                    "b",
                    "}",
                    "\\right)",
                    "^{",
                    "\\left(",
                    "0.5",
                    "\\right)",
                    "}",
                    "+",
                    "\\sqrt{",
                    "\\left(",
                    "\\frac{",
                    "a",
                    "\\cdot",
                    "b",
                    "+",
                    "b",
                    "\\cdot",
                    "c",
                    "}{",
                    "\\left(",
                    "b",
                    "\\right)",
                    "^{",
                    "2",
                    "}",
                    "}",
                    "\\right)",
                    "}",
                    "+",
                    "\\sin{",
                    "\\left(",
                    "\\frac{",
                    "a",
                    "}{",
                    "b",
                    "}",
                    "\\right)",
                    "}",
                    "=",
                    "\\sqrt{",
                    "\\left(",
                    "\\frac{",
                    10000001,
                    "}{",
                    20000002,
                    "}",
                    "\\right)",
                    "}",
                    "+",
                    "\\arcsin{",
                    "\\left(",
                    "\\sin{",
                    "\\left(",
                    "\\frac{",
                    20000002,
                    "}{",
                    30000003,
                    "}",
                    "\\right)",
                    "}",
                    "\\right)",
                    "}",
                    "+",
                    "\\left(",
                    "\\frac{",
                    10000001,
                    "}{",
                    20000002,
                    "}",
                    "\\right)",
                    "^{",
                    "\\left(",
                    "0.5",
                    "\\right)",
                    "}",
                    "+",
                    "\\sqrt{",
                    "\\left(",
                    "\\frac{",
                    10000001,
                    "\\cdot",
                    20000002,
                    "+",
                    20000002,
                    "\\cdot",
                    30000003,
                    "}{",
                    "\\left(",
                    20000002,
                    "\\right)",
                    "^{",
                    "2",
                    "}",
                    "}",
                    "\\right)",
                    "}",
                    "+",
                    "\\sin{",
                    "\\left(",
                    "\\frac{",
                    10000001,
                    "}{",
                    20000002,
                    "}",
                    "\\right)",
                    "}",
                    "=",
                    3.97451933001706,
                ]
            ),
            comment=" Comment",
            latex="",
        ),
        cell_precision=3,
        cell_notation=False,
        **config_options,
    ) == CalcLine(
        line=deque(
            [
                "y",
                "=",
                "\\sqrt{",
                "\\left(",
                "\\frac{",
                "a",
                "}{",
                "b",
                "}",
                "\\right)",
                "}",
                "+",
                "\\arcsin{",
                "\\left(",
                "\\sin{",
                "\\left(",
                "\\frac{",
                "b",
                "}{",
                "c",
                "}",
                "\\right)",
                "}",
                "\\right)",
                "}",
                "+",
                "\\left(",
                "\\frac{",
                "a",
                "}{",
                "b",
                "}",
                "\\right)",
                "^{",
                "\\left(",
                "0.5",
                "\\right)",
                "}",
                "+",
                "\\sqrt{",
                "\\left(",
                "\\frac{",
                "a",
                "\\cdot",
                "b",
                "+",
                "b",
                "\\cdot",
                "c",
                "}{",
                "\\left(",
                "b",
                "\\right)",
                "^{",
                "2",
                "}",
                "}",
                "\\right)",
                "}",
                "+",
                "\\sin{",
                "\\left(",
                "\\frac{",
                "a",
                "}{",
                "b",
                "}",
                "\\right)",
                "}",
                "=",
                "\\sqrt{",
                "\\left(",
                "\\frac{",
                "10000001",
                "}{",
                "20000002",
                "}",
                "\\right)",
                "}",
                "+",
                "\\arcsin{",
                "\\left(",
                "\\sin{",
                "\\left(",
                "\\frac{",
                "20000002",
                "}{",
                "30000003",
                "}",
                "\\right)",
                "}",
                "\\right)",
                "}",
                "+",
                "\\left(",
                "\\frac{",
                "10000001",
                "}{",
                "20000002",
                "}",
                "\\right)",
                "^{",
                "\\left(",
                "0.5",
                "\\right)",
                "}",
                "+",
                "\\sqrt{",
                "\\left(",
                "\\frac{",
                "10000001",
                "\\cdot",
                "20000002",
                "+",
                "20000002",
                "\\cdot",
                "30000003",
                "}{",
                "\\left(",
                "20000002",
                "\\right)",
                "^{",
                "2",
                "}",
                "}",
                "\\right)",
                "}",
                "+",
                "\\sin{",
                "\\left(",
                "\\frac{",
                "10000001",
                "}{",
                "20000002",
                "}",
                "\\right)",
                "}",
                "=",
                "3.975",
            ]
        ),
        comment=" Comment",
        latex="y = \\sqrt{ \\left( \\frac{ a }{ b } \\right) } + \\arcsin{ \\left( \\sin{ \\left( \\frac{ b }{ c } \\right) } \\right) } + \\left( \\frac{ a }{ b } \\right) ^{ \\left( 0.5 \\right) } + \\sqrt{ \\left( \\frac{ a \\cdot b + b \\cdot c }{ \\left( b \\right) ^{ 2 } } \\right) } + \\sin{ \\left( \\frac{ a }{ b } \\right) } = \\sqrt{ \\left( \\frac{ 10000001 }{ 20000002 } \\right) } + \\arcsin{ \\left( \\sin{ \\left( \\frac{ 20000002 }{ 30000003 } \\right) } \\right) } + \\left( \\frac{ 10000001 }{ 20000002 } \\right) ^{ \\left( 0.5 \\right) } + \\sqrt{ \\left( \\frac{ 10000001 \\cdot 20000002 + 20000002 \\cdot 30000003 }{ \\left( 20000002 \\right) ^{ 2 } } \\right) } + \\sin{ \\left( \\frac{ 10000001 }{ 20000002 } \\right) } = 3.975",
    )


def format_lines():
    assert handcalcs.handcalcs.format_lines(
        ParameterLine(line=deque(["y", "=", "6"]), comment=" Comment", latex="y = 6")
    ) == ParameterLine(
        line=deque(["y", "=", "6"]),
        comment=" Comment",
        latex="y &= 6\\;\\;\\textrm{(Comment)}\n",
    )
    assert handcalcs.handcalcs.format_lines(
        CalcLine(
            line=deque(
                [
                    "\\alpha_{\\eta_{\\psi}}",
                    "=",
                    "\\frac{",
                    "4",
                    "}{",
                    "\\left(",
                    "y",
                    "\\right)",
                    "^{",
                    "\\left(",
                    "a",
                    "+",
                    "1",
                    "\\right)",
                    "}",
                    "}",
                    "=",
                    "\\frac{",
                    "4",
                    "}{",
                    "\\left(",
                    "6",
                    "\\right)",
                    "^{",
                    "\\left(",
                    "2",
                    "+",
                    "1",
                    "\\right)",
                    "}",
                    "}",
                    "=",
                    "0.019",
                ]
            ),
            comment=" Comment",
            latex="\\alpha_{\\eta_{\\psi}} = \\frac{ 4 }{ \\left( y \\right) ^{ \\left( a + 1 \\right) } } = \\frac{ 4 }{ \\left( 6 \\right) ^{ \\left( 2 + 1 \\right) } } = 0.019",
        )
    ) == CalcLine(
        line=deque(
            [
                "\\alpha_{\\eta_{\\psi}}",
                "=",
                "\\frac{",
                "4",
                "}{",
                "\\left(",
                "y",
                "\\right)",
                "^{",
                "\\left(",
                "a",
                "+",
                "1",
                "\\right)",
                "}",
                "}",
                "=",
                "\\frac{",
                "4",
                "}{",
                "\\left(",
                "6",
                "\\right)",
                "^{",
                "\\left(",
                "2",
                "+",
                "1",
                "\\right)",
                "}",
                "}",
                "=",
                "0.019",
            ]
        ),
        comment=" Comment",
        latex="\\alpha_{\\eta_{\\psi}} &= \\frac{ 4 }{ \\left( y \\right) ^{ \\left( a + 1 \\right) } } = \\frac{ 4 }{ \\left( 6 \\right) ^{ \\left( 2 + 1 \\right) } } &= 0.019\\;\\;\\textrm{(Comment)}\n",
    )
    assert handcalcs.handcalcs.format_lines(
        ConditionalLine(
            condition=deque(["x", ">", "1"]),
            condition_type="elif",
            expressions=deque(
                [
                    CalcLine(
                        line=deque(
                            [
                                "b",
                                "=",
                                "x",
                                "\\cdot",
                                "1",
                                "=",
                                "2",
                                "\\cdot",
                                "1",
                                "=",
                                "2",
                            ]
                        ),
                        comment="",
                        latex="b = x \\cdot 1 = 2 \\cdot 1 = 2",
                    ),
                    ParameterLine(
                        line=deque(["c", "=", "2"]), comment="", latex="c = 2"
                    ),
                ]
            ),
            raw_condition="x > 1",
            raw_expression="b = x*1; c = b",
            true_condition=deque(
                ["x", ">", "1", "\\rightarrow", "\\left(", "2", ">", "1", "\\right)"]
            ),
            true_expressions=deque(
                [
                    CalcLine(
                        line=deque(
                            [
                                "b",
                                "=",
                                "x",
                                "\\cdot",
                                "1",
                                "=",
                                "2",
                                "\\cdot",
                                "1",
                                "=",
                                "2",
                            ]
                        ),
                        comment="",
                        latex="b = x \\cdot 1 = 2 \\cdot 1 = 2",
                    ),
                    ParameterLine(
                        line=deque(["c", "=", "2"]), comment="", latex="c = 2"
                    ),
                ]
            ),
            comment=" Comment",
            latex="b = x \\cdot 1 = 2 \\cdot 1 = 2\\\\\nc = 2",
        )
    ) == ConditionalLine(
        condition=deque(["x", ">", "1"]),
        condition_type="elif",
        expressions=deque(
            [
                CalcLine(
                    line=deque(
                        [
                            "b",
                            "=",
                            "x",
                            "\\cdot",
                            "1",
                            "=",
                            "2",
                            "\\cdot",
                            "1",
                            "=",
                            "2",
                        ]
                    ),
                    comment="",
                    latex="b &= x \\cdot 1 = 2 \\cdot 1 &= 2\n",
                ),
                ParameterLine(
                    line=deque(["c", "=", "2"]), comment="", latex="c &= 2\\;\n"
                ),
            ]
        ),
        raw_condition="x > 1",
        raw_expression="b = x*1; c = b",
        true_condition=deque(
            ["x", ">", "1", "\\rightarrow", "\\left(", "2", ">", "1", "\\right)"]
        ),
        true_expressions=deque(
            [
                CalcLine(
                    line=deque(
                        [
                            "b",
                            "=",
                            "x",
                            "\\cdot",
                            "1",
                            "=",
                            "2",
                            "\\cdot",
                            "1",
                            "=",
                            "2",
                        ]
                    ),
                    comment="",
                    latex="b &= x \\cdot 1 = 2 \\cdot 1 &= 2\n",
                ),
                ParameterLine(
                    line=deque(["c", "=", "2"]), comment="", latex="c &= 2\\;\n"
                ),
            ]
        ),
        comment=" Comment",
        latex="&\\text{Since, }x > 1 \\rightarrow \\left( 2 > 1 \\right):\\;\\;\\textrm{(Comment)}\n\\end{aligned}\n\\]\n\\[\n\\begin{aligned}\nb &= x \\cdot 1 = 2 \\cdot 1 &= 2\n\\\\\nc &= 2\\;\n",
    )
    assert handcalcs.handcalcs.format_lines(
        ConditionalLine(
            condition=deque([""]),
            condition_type="else",
            expressions=deque(
                [
                    CalcLine(
                        line=deque(
                            [
                                "b",
                                "=",
                                "x",
                                "\\cdot",
                                "1",
                                "=",
                                "10",
                                "\\cdot",
                                "1",
                                "=",
                                "10",
                            ]
                        ),
                        comment="",
                        latex="b = x \\cdot 1 = 10 \\cdot 1 = 10",
                    ),
                    ParameterLine(
                        line=deque(["c", "=", "10"]), comment="", latex="c = 10"
                    ),
                ]
            ),
            raw_condition="",
            raw_expression="b = x*1; c = b",
            true_condition=deque([""]),
            true_expressions=deque(
                [
                    CalcLine(
                        line=deque(
                            [
                                "b",
                                "=",
                                "x",
                                "\\cdot",
                                "1",
                                "=",
                                "10",
                                "\\cdot",
                                "1",
                                "=",
                                "10",
                            ]
                        ),
                        comment="",
                        latex="b = x \\cdot 1 = 10 \\cdot 1 = 10",
                    ),
                    ParameterLine(
                        line=deque(["c", "=", "10"]), comment="", latex="c = 10"
                    ),
                ]
            ),
            comment="Comment",
            latex="b = x \\cdot 1 = 10 \\cdot 1 = 10\\\\\nc = 10",
        )
    ) == ConditionalLine(
        condition=deque([""]),
        condition_type="else",
        expressions=deque(
            [
                CalcLine(
                    line=deque(
                        [
                            "b",
                            "=",
                            "x",
                            "\\cdot",
                            "1",
                            "=",
                            "10",
                            "\\cdot",
                            "1",
                            "=",
                            "10",
                        ]
                    ),
                    comment="",
                    latex="b &= x \\cdot 1 = 10 \\cdot 1 &= 10\n",
                ),
                ParameterLine(
                    line=deque(["c", "=", "10"]), comment="", latex="c &= 10\\;\n"
                ),
            ]
        ),
        raw_condition="",
        raw_expression="b = x*1; c = b",
        true_condition=deque([""]),
        true_expressions=deque(
            [
                CalcLine(
                    line=deque(
                        [
                            "b",
                            "=",
                            "x",
                            "\\cdot",
                            "1",
                            "=",
                            "10",
                            "\\cdot",
                            "1",
                            "=",
                            "10",
                        ]
                    ),
                    comment="",
                    latex="b &= x \\cdot 1 = 10 \\cdot 1 &= 10\n",
                ),
                ParameterLine(
                    line=deque(["c", "=", "10"]), comment="", latex="c &= 10\\;\n"
                ),
            ]
        ),
        comment="Comment",
        latex="b &= x \\cdot 1 = 10 \\cdot 1 &= 10\n\\\\\nc &= 10\\;\n",
    )
    assert handcalcs.handcalcs.format_lines(
        LongCalcLine(
            line=deque(
                ["b", "=", "3", "\\cdot", "a", "=", "3", "\\cdot", "2", "=", "6"]
            ),
            comment="",
            latex="b = 3 \\cdot a = 3 \\cdot 2 = 6",
        )
    ) == LongCalcLine(
        line=deque(["b", "=", "3", "\\cdot", "a", "=", "3", "\\cdot", "2", "=", "6"]),
        comment="",
        latex="b &= 3 \\cdot a \\\\&= 3 \\cdot 2 \\\\&= 6\\\\\n",
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
        deque(["eta", "=", "beta", "+", "theta"]), **config_options
    ) == deque(["\\eta", "=", "\\beta", "+", "\\theta"])
    assert handcalcs.handcalcs.swap_for_greek(
        deque(["M_r", "=", "phi", "\\cdot", deque(["psi", "\\cdot", "F_y"])]),
        **config_options,
    ) == deque(["M_r", "=", "\\phi", "\\cdot", deque(["\\psi", "\\cdot", "F_y"])])
    assert handcalcs.handcalcs.swap_for_greek(
        deque(["lamb", "=", 3]), **config_options
    ) == deque(["\\lambda", "=", 3])

def test_swap_custom_brackets():
    assert handcalcs.handcalcs.swap_custom_brackets(
        deque(["myvarˉ1ˉ", "=", "1"]), **config_options # Test round brackets
    ) == deque(["myvar(1)", "=", "1"])
    assert handcalcs.handcalcs.swap_custom_brackets(
        deque(["myvarˍ2ˍ", "=", "1"]), **config_options # Test square brackets
    ) == deque(["myvar[2]", "=", "1"])
    assert handcalcs.handcalcs.swap_custom_brackets(
        deque(["myvarˆ3ˆ", "=", "1"]), **config_options # Test angle brackets
    ) == deque([r"myvar\langle3\rangle", "=", "1"])
    assert handcalcs.handcalcs.swap_custom_brackets(
        deque(["myvarǂ4ǂ", "=", "1"]), **config_options # Test curly brackets
    ) == deque([r"myvar\lbrace4\rbrace", "=", "1"])
    assert handcalcs.handcalcs.swap_custom_brackets(
        deque(["myvarǀ5ǀ", "=", "1"]), **config_options # Test pipes
    ) == deque(["myvar|5|", "=", "1"])
    assert handcalcs.handcalcs.swap_custom_brackets(
        deque(["myvarǁ6ǁ", "=", "1"]), **config_options # Test double pipes
    ) == deque([r"myvar\|6\|", "=", "1"])
    assert handcalcs.handcalcs.swap_custom_brackets(
        deque(["myvarˉˆ7ˆˉ_ǁAǁ", "=", "1"]), **config_options # Test mixed brackets
    ) == deque([r"myvar(\langle7\rangle)_\|A\|", "=", "1"])

def test_test_for_scientific_float():
    assert handcalcs.handcalcs.test_for_scientific_float("1.233e-3") == True
    assert handcalcs.handcalcs.test_for_scientific_float("0.090e10") == True
    assert handcalcs.handcalcs.test_for_scientific_float("e10") == False
    assert handcalcs.handcalcs.test_for_scientific_float("-1.23e4") == True


def test_swap_scientific_notation_float():
    assert handcalcs.handcalcs.swap_scientific_notation_float(
        deque([0.0000001, +0.132]), 3
    ) == deque(["1.000e-7", 0.132])
    assert handcalcs.handcalcs.swap_scientific_notation_float(
        deque([0.000000135, +2.30]), 3
    ) == deque(["1.350e-7", 2.30])
    assert handcalcs.handcalcs.swap_scientific_notation_float(
        deque([0.013546, +0.132]), 5
    ) == deque(["1.35460e-2", 0.132])


def test_swap_scientific_notation_float():
    # assert handcalcs.handcalcs.swap_scientific_notation_complex(
    #     deque([j, "+", ])
    pass


def test_swap_comparison_ops():
    assert handcalcs.handcalcs.swap_comparison_ops(deque(["3", ">", "1"])) == deque(
        ["3", "\\gt", "1"]
    )
    assert handcalcs.handcalcs.swap_comparison_ops(deque(["3", ">=", "1"])) == deque(
        ["3", "\\geq", "1"]
    )
    assert handcalcs.handcalcs.swap_comparison_ops(deque(["3", "==", "1"])) == deque(
        ["3", "=", "1"]
    )
    assert handcalcs.handcalcs.swap_comparison_ops(deque(["3", "!=", "1"])) == deque(
        ["3", "\\neq", "1"]
    )
    assert handcalcs.handcalcs.swap_comparison_ops(
        deque(["a", "=", deque(["1", "<", "5"])])
    ) == deque(["a", "=", deque(["1", "\\lt", "5"])])
    assert handcalcs.handcalcs.swap_comparison_ops(
        deque(["a", "=", deque(["1", "<=", "5"])])
    ) == deque(["a", "=", deque(["1", "\\leq", "5"])])


def test_test_for_long_var_strs():
    assert (
        handcalcs.handcalcs.test_for_long_var_strs("x_y_a", **config_options) == False
    )
    assert (
        handcalcs.handcalcs.test_for_long_var_strs("Rate_annual", **config_options)
        == True
    )
    assert (
        handcalcs.handcalcs.test_for_long_var_strs("x_rake_red", **config_options)
        == False
    )
    assert (
        handcalcs.handcalcs.test_for_long_var_strs("AB_x_y", **config_options) == True
    )
    assert (
        handcalcs.handcalcs.test_for_long_var_strs("category_x", **config_options)
        == True
    )
    assert handcalcs.handcalcs.test_for_long_var_strs("x", **config_options) == False
    assert handcalcs.handcalcs.test_for_long_var_strs("xy", **config_options) == True
    assert handcalcs.handcalcs.test_for_long_var_strs(234.21, **config_options) == False
    assert (
        handcalcs.handcalcs.test_for_long_var_strs("\\frac{", **config_options) == False
    )
    assert (
        handcalcs.handcalcs.test_for_long_var_strs("\\sin", **config_options) == False
    )


def test_swap_long_var_strs():
    assert handcalcs.handcalcs.swap_long_var_strs(
        deque(["cat_xy_u", "+", 4]), **config_options
    ) == deque(["\\mathrm{cat}_xy_u", "+", 4])
    assert handcalcs.handcalcs.swap_long_var_strs(
        deque(["RATE", "*", "4"]), **config_options
    ) == deque(["\\mathrm{RATE}", "*", "4"])
    assert handcalcs.handcalcs.swap_long_var_strs(
        deque(["\\sin", "\\left(", "apple_cart", "\\right)"]), **config_options
    ) == deque(["\\sin", "\\left(", "\\mathrm{apple}_cart", "\\right)"])
    assert handcalcs.handcalcs.swap_long_var_strs(
        deque(["x", "=", "a", "*", deque(["b", "+", "annual_x"])]), **config_options
    ) == deque(["x", "=", "a", "*", deque(["b", "+", "\\mathrm{annual}_x"])])


def test_test_for_function_name():
    assert handcalcs.handcalcs.test_for_function_name(deque(["sin", "45"])) == True
    assert (
        handcalcs.handcalcs.test_for_function_name(
            deque(["sin", deque(["a", "/", "b"])])
        )
        == True
    )
    assert handcalcs.handcalcs.test_for_function_name(deque(["1", "+", "b"])) == False
    assert handcalcs.handcalcs.test_for_function_name(deque(["-", "a"])) == False
    assert (
        handcalcs.handcalcs.test_for_function_name(
            deque(["sin", deque(["tan", deque(["a", "/", "b"])])])
        )
        == True
    )


def test_get_function_name():
    assert handcalcs.handcalcs.get_function_name(deque(["sin", "45"])) == "sin"
    assert (
        handcalcs.handcalcs.get_function_name(deque(["sin", deque(["a", "/", "b"])]))
        == "sin"
    )
    assert handcalcs.handcalcs.get_function_name(deque(["1", "+", "b"])) == ""
    assert handcalcs.handcalcs.get_function_name(deque(["-", "a"])) == ""
    assert (
        handcalcs.handcalcs.get_function_name(
            deque(["double", deque(["tan", deque(["a", "/", "b"])])])
        )
        == "double"
    )
    assert handcalcs.handcalcs.get_function_name(deque(["1", "+", "b", "*", "4"])) == ""
    assert (
        handcalcs.handcalcs.get_function_name(
            deque(["quad", deque(["int_func", ",", "a", ",", "b"])])
        )
        == "quad"
    )


def test_test_for_fraction_exception():
    assert (
        handcalcs.handcalcs.test_for_fraction_exception(deque(["sin", "45"]), "/")
        == True
    )
    assert (
        handcalcs.handcalcs.test_for_fraction_exception("/", deque(["a", "+", "b"]))
        == True
    )
    assert (
        handcalcs.handcalcs.test_for_fraction_exception(deque(["a", "+", "b"]), "*")
        == False
    )
    assert (
        handcalcs.handcalcs.test_for_fraction_exception(deque(["-", "1"]), "/") == True
    )


def test_insert_function_parentheses():
    assert handcalcs.handcalcs.insert_function_parentheses(
        deque(["sin", "45"])
    ) == deque(["sin", "\\left(", "45", "\\right)"])
    assert handcalcs.handcalcs.insert_function_parentheses(
        deque(["sin", deque(["a", "/", "b"])])
    ) == deque(["sin", deque(["\\left(", "a", "/", "b", "\\right)"])])
    assert handcalcs.handcalcs.insert_function_parentheses(
        deque(["double", deque(["tan", deque(["4", "/", "a"])])])
    ) == deque(
        ["double", deque(["\\left(", "tan", deque(["4", "/", "a"]), "\\right)"])]
    )


def test_test_for_unary():
    assert handcalcs.handcalcs.test_for_unary(deque(["-", "1"])) == True
    assert handcalcs.handcalcs.test_for_unary(deque(["+", "5"])) == True
    assert handcalcs.handcalcs.test_for_unary(deque(["1", "+", "5"])) == False
    assert (
        handcalcs.handcalcs.test_for_unary(deque(["-", deque(["sin", "45"])])) == True
    )


def test_insert_unary_parentheses():
    assert handcalcs.handcalcs.insert_unary_parentheses(deque(["-", "1"])) == deque(
        ["\\left(", "-", "1", "\\right)"]
    )
    assert handcalcs.handcalcs.insert_unary_parentheses(deque(["+", "1"])) == deque(
        ["\\left(", "+", "1", "\\right)"]
    )
    assert handcalcs.handcalcs.insert_unary_parentheses(
        deque(["1", "+", "sin", "45"])
    ) == deque(["\\left(", "1", "+", "sin", "45", "\\right)"])


def test_insert_func_braces():
    assert handcalcs.handcalcs.insert_func_braces(
        deque(["sin", "\\left(", "45", "\\right)"])
    ) == deque(["sin", "{", "\\left(", "45", "\\right)", "}"])
    assert handcalcs.handcalcs.insert_func_braces(
        deque(["sin", "\\left(", deque(["a", "/", "b"]), "\\right)"])
    ) == deque(["sin", "{", "\\left(", deque(["a", "/", "b"]), "\\right)", "}"])
    assert handcalcs.handcalcs.insert_func_braces(
        deque(["sqrt", deque(["b", "+", "b"])])
    ) == deque(["sqrt", "{", deque(["b", "+", "b"]), "}"])


def test_insert_parentheses():
    expr_parser = handcalcs.handcalcs.expr_parser
    assert handcalcs.handcalcs.insert_parentheses(
        expr_parser("a = 1 / (2*m*(3**2*2+4*3))")
    ) == deque(
        [
            "a",
            "=",
            "1",
            "/",
            deque(
                [
                    "2",
                    "*",
                    "m",
                    "*",
                    deque(
                        [
                            "\\left(",
                            deque(["3", "**", "2"]),
                            "*",
                            "2",
                            "+",
                            "4",
                            "*",
                            "3",
                            "\\right)",
                        ]
                    ),
                ]
            ),
        ]
    )


def test_get_func_latex():
    assert handcalcs.handcalcs.get_func_latex("sin") == "\\sin"
    assert handcalcs.handcalcs.get_func_latex("sum") == "\\Sigma"
    assert handcalcs.handcalcs.get_func_latex("double2") == "double2"


def test_func_name():
    assert handcalcs.handcalcs.swap_func_name(
        deque(["sin", deque(["a", "/", "b"])]), "sin"
    ) == deque(["\\sin", deque(["a", "/", "b"])])
    assert handcalcs.handcalcs.swap_func_name(deque(["tan", "45"]), "tan") == deque(
        ["\\tan", "45"]
    )
    assert handcalcs.handcalcs.swap_func_name(
        deque(["sum", deque(["a", ",", "b", ",", "c", ",", "d"])]), "sum"
    ) == deque(["\\Sigma", deque(["a", ",", "b", ",", "c", ",", "d"])])


def test_swap_math_funcs():
    calc_results = {"int_func": int_func, "a": 3, "b": 2}

    assert handcalcs.handcalcs.swap_math_funcs(
        deque(
            ["z", "=", deque(["double", deque(["\\left(", "a", "/", "b", "\\right)"])])]
        ),
        dict(),
    ) == deque(
        [
            "z",
            "=",
            deque(
                [
                    "\\operatorname{double}",
                    deque(["\\left(", "a", "/", "b", "\\right)"]),
                ]
            ),
        ]
    )
    assert handcalcs.handcalcs.swap_math_funcs(
        deque(["rate", "=", deque(["sin", "\\left(", "a", "\\right)"])]), dict()
    ) == deque(["rate", "=", deque(["\\sin", "\\left(", "a", "\\right)"])])
    assert handcalcs.handcalcs.swap_math_funcs(
        deque(["test", "=", deque(["sqrt", deque(["b", "+", "b"])])]), dict()
    ) == deque(["test", "=", deque(["\\sqrt", "{", deque(["b", "+", "b"]), "}"])])
    assert handcalcs.handcalcs.swap_math_funcs(
        deque([deque(["quad", deque(["int_func", ",", "a", ",", "b"])])]), calc_results
    ) == deque(
        [
            deque(
                [
                    "\\int_{",
                    "a",
                    "}",
                    "^",
                    "{",
                    "b",
                    "}",
                    deque([deque(["x", "**", "2"]), "+", "3", "*", "x"]),
                    "\\; dx",
                ]
            )
        ]
    )


def test_test_for_typ_arithmetic():
    assert handcalcs.handcalcs.test_for_typ_arithmetic(deque(["sin", "45"])) == False
    assert (
        handcalcs.handcalcs.test_for_typ_arithmetic(
            deque(["sin", deque(["a", "/", "b"])])
        )
        == False
    )
    assert handcalcs.handcalcs.test_for_typ_arithmetic(deque(["1", "+", "b"])) == True
    assert handcalcs.handcalcs.test_for_typ_arithmetic(deque(["-", "a"])) == False
    assert (
        handcalcs.handcalcs.test_for_typ_arithmetic(
            deque(["sin", deque(["tan", deque(["a", "/", "b"])])])
        )
        == False
    )
    assert (
        handcalcs.handcalcs.test_for_typ_arithmetic(deque(["1", "+", "b", "*", "4"]))
        == True
    )
    assert (
        handcalcs.handcalcs.test_for_typ_arithmetic(
            deque([deque(["-", "a"]), "+", "b"])
        )
        == True
    )
    assert (
        handcalcs.handcalcs.test_for_typ_arithmetic(
            deque(["\\left(", "able", "+", "b", "\\right)"])
        )
        == True
    )
    assert (
        handcalcs.handcalcs.test_for_typ_arithmetic(
            deque(["double", "\\left(", deque(["a", "/", "b"]), "\\right)"])
        )
        == False
    )
    assert handcalcs.handcalcs.test_for_typ_arithmetic(deque(["c", "**", "2"])) == True
    # assert handcalcs.handcalcs.test_for_typ_arithmetic(deque([deque(['sin', deque(['atan', 'mu'])]), '**', '2'])) == False


def test_expr_parser():
    assert handcalcs.handcalcs.expr_parser("z = sqrt(5)") == deque(
        ["z", "=", deque(["sqrt", "5"])]
    )
    assert handcalcs.handcalcs.expr_parser("z = (sqrt(5))") == deque(
        ["z", "=", deque(["sqrt", "5"])]
    )
    assert handcalcs.handcalcs.expr_parser("z = x**2/sqrt(2)") == deque(
        ["z", "=", deque(["x", "**", "2"]), "/", deque(["sqrt", "2"])]
    )
    assert handcalcs.handcalcs.expr_parser(
        "e1_nu = 1.25e-5 +-1 **2/sum(3,4,5)"
    ) == deque(
        [
            "e1_nu",
            "=",
            "1.25e-5",
            "+",
            deque(["-", deque(["1", "**", "2"])]),
            "/",
            deque(["sum", deque(["3", ",", "4", ",", "5"])]),
        ]
    )
    assert handcalcs.handcalcs.expr_parser("e1_nu = -1.25e5 +- 1") == deque(
        ["e1_nu", "=", deque(["-", "1.25e5"]), "+", deque(["-", "1"])]
    )
    assert handcalcs.handcalcs.expr_parser("e1_nu = kN.to('ksf')") == deque(
        ["e1_nu", "=", "kN.to"]
    )
    assert handcalcs.handcalcs.expr_parser(
        "e1_nu = 1.25e5+1.25e-5j **(a/b**2)/sum(3,4,5)"
    ) == deque(
        [
            "e1_nu",
            "=",
            deque(
                ["1.25e5+1.25e-5j", "**", deque(["a", "/", deque(["b", "**", "2"])])]
            ),
            "/",
            deque(["sum", deque(["3", ",", "4", ",", "5"])]),
        ]
    )


def test_swap_prime_notation():
    assert handcalcs.handcalcs.swap_prime_notation(
        deque(["sin", deque(["tan", deque(["a", "/", 4])])])
    ) == deque(["sin", deque(["tan", deque(["a", "/", 4])])])
    assert handcalcs.handcalcs.swap_prime_notation(
        deque(
            [
                "f_prime_c",
                "=" "eta_prime_prime_c",
                "*",
                deque(["phi_prime_prime_prime_c", "+", "zeta_pr"]),
            ]
        )
    ) == deque(["f'_c", "=" "eta''_c", "*", deque(["phi'''_c", "+", "zeta_pr"])])


def test_format_strings():
    assert (
        handcalcs.handcalcs.format_strings(" test string ", comment=False)
        == "\\textrm{test string}"
    )
    assert (
        handcalcs.handcalcs.format_strings(" another test string", comment=True)
        == "\\;\\textrm{(another test string)}"
    )


def test_latex_repr():
    mock_obj_1 = MockLatexObj1("test string")
    mock_obj_2 = MockLatexObj2("23 23")
    assert (
        handcalcs.handcalcs.latex_repr(
            123, precision=3, use_scientific_notation=True, preferred_formatter="L"
        )
        == "123"
    )
    assert (
        handcalcs.handcalcs.latex_repr(
            20 * si.Pa,
            precision=3,
            use_scientific_notation=True,
            preferred_formatter="L",
        )
        == "2.000 \\times 10^ {1}\\ \\mathrm{Pa}"
    )
    assert (
        handcalcs.handcalcs.latex_repr(
            mock_obj_1,
            precision=3,
            use_scientific_notation=True,
            preferred_formatter="L",
        )
        == "\\mathrm{test string}"
    )
    assert (
        handcalcs.handcalcs.latex_repr(
            mock_obj_2,
            precision=3,
            use_scientific_notation=True,
            preferred_formatter="L",
        )
        == "\\text{23 23}"
    )


def test_swap_integrals():
    calc_results = {"int_func": int_func, "a": 3, "b": 2}
    assert handcalcs.handcalcs.swap_integrals(
        deque(["quad", deque(["int_func", ",", "a", ",", "b"])]), calc_results
    ) == deque(
        [
            "\\int_{",
            "a",
            "}",
            "^",
            "{",
            "b",
            "}",
            deque([deque(["x", "**", "2"]), "+", "3", "*", "x"]),
            "\\; dx",
        ]
    )


def test_swap_dec_sep():
    assert handcalcs.handcalcs.swap_dec_sep(
        deque(["1.234", "\\times 10^{", "2", "}"]), ","
    ) == deque(["1{,}234", "\\times 10^{", "2", "}"])
    assert handcalcs.handcalcs.swap_dec_sep(
        deque(["sin", "\\left(", "45", "\\right)"]), ","
    ) == deque(["sin", "\\left(", "45", "\\right)"])


def test_replace_underscores():
    assert handcalcs.handcalcs.replace_underscores(
        deque(["cat_a", "+", deque(["\\Delta_T", "\\cdot", 234.4])])
    ) == deque(["cat\\ a", "+", deque(["\\Delta\\ T", "\\cdot", 234.4])])


def test_swap_chained_fracs():
    assert handcalcs.handcalcs.swap_chained_fracs(  # Test for basic functionality
        deque(["d", "=", "a", "/", "b", "/", "3"])
    ) == deque(["d", "=", "a", "/", "b", "\\cdot", "\\frac{1}", "{", "3", "}"])
    assert handcalcs.handcalcs.swap_chained_fracs(  # Test for chained div followed by non-chained div
        deque(["d", "=", "a", "/", "b", "/", "3", "+", "c", "/", "e"])
    ) == deque(
        [
            "d",
            "=",
            "a",
            "/",
            "b",
            "\\cdot",
            "\\frac{1}",
            "{",
            "3",
            "}",
            "+",
            "c",
            "/",
            "e",
        ]
    )
    assert handcalcs.handcalcs.swap_chained_fracs(  # Test for nested chained divs
        deque(["d", "=", "a", "/", "b", "/", deque(["a", "/", "b", "/", "3"])])
    ) == deque(
        [
            "d",
            "=",
            "a",
            "/",
            "b",
            "\\cdot",
            "\\frac{1}",
            "{",
            deque(["a", "/", "b", "\\cdot", "\\frac{1}", "{", "3", "}"]),
            "}",
        ]
    )


def test_test_for_py_operator():
    assert handcalcs.handcalcs.test_for_py_operator("*") == True
    assert handcalcs.handcalcs.test_for_py_operator("+") == True
    assert handcalcs.handcalcs.test_for_py_operator("-") == True
    assert handcalcs.handcalcs.test_for_py_operator("*") == True
    assert handcalcs.handcalcs.test_for_py_operator("**") == True
    assert handcalcs.handcalcs.test_for_py_operator("%") == True
    assert handcalcs.handcalcs.test_for_py_operator("/") == False
    assert handcalcs.handcalcs.test_for_py_operator("//") == True
    assert handcalcs.handcalcs.test_for_py_operator(">") == True
    assert handcalcs.handcalcs.test_for_py_operator(">=") == True
    assert handcalcs.handcalcs.test_for_py_operator("==") == True
    assert handcalcs.handcalcs.test_for_py_operator("<") == True
    assert handcalcs.handcalcs.test_for_py_operator("<=") == True
    assert handcalcs.handcalcs.test_for_py_operator("!=") == True
    assert handcalcs.handcalcs.test_for_py_operator("sin") == False
    assert handcalcs.handcalcs.test_for_py_operator(12) == False
    assert handcalcs.handcalcs.test_for_py_operator(True) == False


def test_for_numeric_line():
    assert (
        handcalcs.handcalcs.test_for_numeric_line(deque(["=", "2", "*", "4"])) == True
    )
    assert (
        handcalcs.handcalcs.test_for_numeric_line(deque(["=", "2", "*", "b"])) == False
    )
    assert (
        handcalcs.handcalcs.test_for_numeric_line(
            deque(["=", "2", "*", deque(["2", "*", "4"])])
        )
        == True
    )
    assert (
        handcalcs.handcalcs.test_for_numeric_line(
            deque(["=", "2", "*", deque(["b", "*", "4"])])
        )
        == False
    )
    assert (
        handcalcs.handcalcs.test_for_numeric_line(
            deque(["=", "2", "*", deque(["sin", "4"])])
        )
        == True
    )
