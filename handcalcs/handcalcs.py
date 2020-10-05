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

from collections import deque, ChainMap
import copy
from dataclasses import dataclass
from functools import singledispatch
import importlib
import inspect
import itertools
import more_itertools
import math
import os
import pathlib
import re
from typing import Any, Union, Optional, Tuple, List
import pyparsing as pp

# TODO:
# Test for sci. notation str X
# Convert str sci. notation to latex sci. notation X
# Convert small rendered floats to latex sci. notation X
# Convert comparison operators X
# Change greeks detection to a regex for exact substitution X
# Multi-character var names to text X
# PRE_INSERT APPROPRIATE PARENTH and Simplify FLatten function

GREEK_LOWER = {
    "alpha": "\\alpha",
    "beta": "\\beta",
    "gamma": "\\gamma",
    "delta": "\\delta",
    "epsilon": "\\epsilon",
    "zeta": "\\zeta",
    "theta": "\\theta",
    "iota": "\\iota",
    "kappa": "\\kappa",
    "mu": "\\mu",
    "nu": "\\nu",
    "xi": "\\xi",
    "omicron": "\\omicron",
    "pi": "\\pi",
    "rho": "\\rho",
    "sigma": "\\sigma",
    "tau": "\\tau",
    "upsilon": "\\upsilon",
    "phi": "\\phi",
    "chi": "\\chi",
    "omega": "\\omega",
    "eta": "\\eta",
    "psi": "\\psi",
    "lamb": "\\lambda",
}

GREEK_UPPER = {
    "Alpha": "\\Alpha",
    "Beta": "\\Beta",
    "Gamma": "\\Gamma",
    "Delta": "\\Delta",
    "Epsilon": "\\Epsilon",
    "Zeta": "\\Zeta",
    "Theta": "\\Theta",
    "Iota": "\\Iota",
    "Kappa": "\\Kappa",
    "Mu": "\\Mu",
    "Nu": "\\Nu",
    "Xi": "\\Xi",
    "Omicron": "\\Omicron",
    "Pi": "\\Pi",
    "Rho": "\\Rho",
    "Sigma": "\\Sigma",
    "Tau": "\\Tau",
    "Upsilon": "\\Upsilon",
    "Phi": "\\Phi",
    "Chi": "\\Chi",
    "Omega": "\\Omega",
    "Eta": "\\Eta",
    "Psi": "\\Psi",
    "Lamb": "\\Lambda",
}

# Six basic line types
@dataclass
class CalcLine:
    line: deque
    comment: str
    latex: str


@dataclass
class SymbolicLine:
    line: deque
    comment: str
    latex: str


@dataclass
class ConditionalLine:
    condition: deque
    condition_type: str
    expressions: deque
    raw_condition: str
    raw_expression: str
    true_condition: deque
    true_expressions: deque
    comment: str
    latex_condition: str
    latex_expressions: str
    latex: str


@dataclass
class ParameterLine:
    line: deque
    comment: str
    latex: str


@dataclass
class LongCalcLine:
    line: deque
    comment: str
    latex: str


@dataclass
class BlankLine:  # Attributes not used on BlankLine but still req'd
    line: deque
    comment: str
    latex: str


# Five types of cell
@dataclass
class CalcCell:
    source: str
    calculated_results: dict
    precision: int
    lines: deque
    latex_code: str


@dataclass
class ShortCalcCell:
    source: str
    calculated_results: dict
    precision: int
    lines: deque
    latex_code: str


@dataclass
class SymbolicCell:
    source: str
    calculated_results: dict
    precision: int
    lines: deque
    latex_code: str


@dataclass
class ParameterCell:
    source: str
    calculated_results: dict
    lines: deque
    precision: int
    cols: int
    latex_code: str


@dataclass
class LongCalcCell:
    source: str
    calculated_results: dict
    lines: deque
    precision: int
    latex_code: str


def is_number(s: str) -> bool:
    """
    A basic helper function because Python str methods do not
    have this ability...
    """
    try:
        float(s)
        return True
    except:
        return False


def dict_get(d: dict, item: Any) -> Any:
    """
    Return the item from the dict, 'd'.
    """
    try:
        return d.get(item, item)
    except TypeError:
        return item


# The renderer class ("output" class)
class LatexRenderer:
    dec_sep = "."

    def __init__(self, python_code_str: str, results: dict, line_args: dict):
        self.source = python_code_str
        self.results = results
        self.precision = line_args["precision"] or 3
        self.override = line_args["override"]

    def render(self):
        return latex(
            self.source,
            self.results,
            self.override,
            self.precision,
            LatexRenderer.dec_sep,
        )


# Pure functions that do all the work
def latex(
    raw_python_source: str,
    calculated_results: dict,
    override: str,
    precision: int = 3,
    dec_sep: str = ".",
) -> str:
    """
    Returns the Python source as a string that has been converted into latex code.
    """
    source = raw_python_source
    cell = categorize_raw_cell(source, calculated_results, override, precision)
    cell = categorize_lines(cell)
    cell = convert_cell(cell)
    cell = format_cell(cell, dec_sep)
    return cell.latex_code


def create_param_cell(
    raw_source: str, calculated_result: dict, precision: int
) -> ParameterCell:
    """
    Returns a ParameterCell.
    """
    comment_tag_removed = strip_cell_code(raw_source)
    cell = ParameterCell(
        source=comment_tag_removed,
        calculated_results=calculated_result,
        lines=deque([]),
        precision=precision,
        cols=3,
        latex_code="",
    )
    return cell


def create_long_cell(
    raw_source: str, calculated_result: dict, precision: int
) -> LongCalcCell:
    """
    Returns a LongCalcCell.
    """
    comment_tag_removed = strip_cell_code(raw_source)
    cell = LongCalcCell(
        source=comment_tag_removed,
        calculated_results=calculated_result,
        lines=deque([]),
        precision=precision,
        latex_code="",
    )
    return cell


def create_short_cell(
    raw_source: str, calculated_result: dict, precision: int
) -> ShortCalcCell:
    """
    Returns a ShortCell
    """
    comment_tag_removed = strip_cell_code(raw_source)
    cell = ShortCalcCell(
        source=comment_tag_removed,
        calculated_results=calculated_result,
        lines=deque([]),
        precision=precision,
        latex_code="",
    )
    return cell


def create_symbolic_cell(
    raw_source: str, calculated_result: dict, precision: int
) -> SymbolicCell:
    """
    Returns a SymbolicCell
    """
    comment_tag_removed = strip_cell_code(raw_source)
    cell = SymbolicCell(
        source=comment_tag_removed,
        calculated_results=calculated_result,
        lines=deque([]),
        precision=precision,
        latex_code="",
    )
    return cell


def create_calc_cell(
    raw_source: str, calculated_result: dict, precision: int
) -> CalcCell:
    """
    Returns a CalcCell
    """
    cell = CalcCell(
        source=raw_source,
        calculated_results=calculated_result,
        precision=precision,
        lines=deque([]),
        latex_code="",
    )
    return cell


def create_conditional_line(
    line: str, calculated_results: dict, override: str, comment: str
):
    (
        condition,
        condition_type,
        expression,
        raw_condition,
        raw_expression,
    ) = split_conditional(line, calculated_results, override)
    categorized_line = ConditionalLine(
        condition=condition,
        condition_type=condition_type,
        expressions=expression,
        raw_condition=raw_condition,
        raw_expression=raw_expression.strip(),
        true_condition=deque([]),
        true_expressions=deque([]),
        comment=comment,
        latex_condition="",
        latex_expressions="",
        latex="",
    )
    return categorized_line


def categorize_raw_cell(
    raw_source: str, calculated_results: dict, override: str, precision: int = 3
) -> Union[ParameterCell, CalcCell]:
    """
    Return a "Cell" type depending on the source of the cell.
    """
    if override:
        if override == "params":
            return create_param_cell(raw_source, calculated_results, precision)
        elif override == "long":
            return create_long_cell(raw_source, calculated_results, precision)
        elif override == "short":
            return create_short_cell(raw_source, calculated_results, precision)
        elif override == "symbolic":
            return create_symbolic_cell(raw_source, calculated_results, precision)

    if test_for_parameter_cell(raw_source):
        return create_param_cell(raw_source, calculated_results, precision)
    elif test_for_long_cell(raw_source):
        return create_long_cell(raw_source, calculated_results, precision)
    elif test_for_short_cell(raw_source):
        return create_short_cell(raw_source, calculated_results, precision)
    elif test_for_symbolic_cell(raw_source):
        return create_symbolic_cell(raw_source, calculated_results, precision)
    else:
        return create_calc_cell(raw_source, calculated_results, precision)


def strip_cell_code(raw_source: str) -> str:
    """
    Return 'raw_source' with the "cell code" removed.
    A "cell code" is a first-line comment in the cell for the
    purpose of categorizing an IPython cell as something other
    than a CalcCell.
    """
    split_lines = deque(raw_source.split("\n"))
    if split_lines[0].startswith("#"):
        split_lines.popleft()
        return "\n".join(split_lines)
    return raw_source


def categorize_lines(
    cell: Union[CalcCell, ParameterCell]
) -> Union[CalcCell, ParameterCell]:
    """
    Return 'cell' with the line data contained in cell_object.source categorized
    into one of four types:
    * CalcLine
    * ParameterLine
    * ConditionalLine

    categorize_lines(calc_cell) is considered the default behaviour for the 
    singledispatch categorize_lines function.
    """
    outgoing = cell.source.rstrip().split("\n")
    incoming = deque([])
    calculated_results = cell.calculated_results
    override = ""
    for line in outgoing:
        if isinstance(cell, ParameterCell):
            override = "parameter"
        elif isinstance(cell, LongCalcCell):
            override = "long"
        elif isinstance(cell, SymbolicCell):
            override = "symbolic"
        categorized = categorize_line(line, calculated_results, override)
        categorized_w_result_appended = add_result_values_to_line(
            categorized, calculated_results
        )
        incoming.append(categorized_w_result_appended)
    cell.lines = incoming
    return cell


def categorize_line(
    line: str, calculated_results: dict, override: str = ""
) -> Union[CalcLine, ParameterLine, ConditionalLine]:
    """
    Return 'line' as either a CalcLine, ParameterLine, or ConditionalLine if 'line'
    fits the appropriate criteria. Raise ValueError, otherwise.

    'override' is a str used to short-cut the tests in categorize_line(). e.g.
    if the cell that the lines belong to is a ParameterCell,
    we do not need to run the test_for_parameter_line() function on the line
    because, in a ParameterCell, all lines will default to a ParameterLine
    because of the cell it's in and how that cell is supposed to behave.

    'override' is passed from the categorize_lines() function because that
    function has the information of the cell type and can pass along any
    desired behavior to categorize_line().
    """
    try:
        line, comment = line.split("#")
    except ValueError:
        comment = ""
    categorized_line = None

    # Override behaviour
    if not test_for_blank_line(line):  # True is a blank line
        if override == "parameter":
            if test_for_conditional_line(line):
                categorized_line = create_conditional_line(
                    line, calculated_results, override, comment
                )
            else:
                categorized_line = ParameterLine(
                    split_parameter_line(line, calculated_results), comment, ""
                )
            return categorized_line

        elif override == "long":
            if test_for_parameter_line(
                line
            ):  # A parameter can exist in a long cell, too
                categorized_line = ParameterLine(
                    split_parameter_line(line, calculated_results), comment, ""
                )
            elif test_for_conditional_line(
                line
            ):  # A conditional line can exist in a long cell, too
                categorized_line = create_conditional_line(
                    line, calculated_results, override, comment
                )
            else:
                categorized_line = LongCalcLine(
                    expr_parser(line), comment, ""
                )  # code_reader
            return categorized_line
        elif override == "symbolic":
            if test_for_conditional_line(
                line
            ):  # A conditional line can exist in a symbolic cell, too
                categorized_line = create_conditional_line(
                    line, calculated_results, override, comment
                )
            else:
                categorized_line = SymbolicLine(
                    expr_parser(line), comment, ""
                )  # code_reader
            return categorized_line
        elif override == "short":
            categorized_line = CalcLine(expr_parser(line), comment, "")  # code_reader
            return categorized_line
        elif True:
            pass  # Future override conditions to match new cell types can be put here

    # Standard behaviour
    if line == "\n" or line == "":
        categorized_line = BlankLine(line, "", "")

    elif test_for_parameter_line(line):

        categorized_line = ParameterLine(
            split_parameter_line(line, calculated_results), comment, ""
        )

    elif test_for_conditional_line(line):
        categorized_line = create_conditional_line(
            line, calculated_results, override, comment
        )

    elif "=" in line:
        categorized_line = CalcLine(expr_parser(line), comment, "")  # code_reader

    elif len(expr_parser(line)) == 1:
        categorized_line = ParameterLine(
            split_parameter_line(line, calculated_results), comment, ""
        )

    else:
        raise ValueError(
            f"Line: {line} is not recognized for rendering.\n"
            "Lines must either:\n"
            "\t * Be the name of a previously assigned single variable\n"
            "\t * Be an arithmetic variable assignment (i.e. calculation that uses '=' in the line)\n"
            "\t * Be a conditional arithmetic assignment (i.e. uses 'if', 'elif', or 'else', each on a single line)"
        )
    return categorized_line


@singledispatch
def add_result_values_to_line(line_object, calculated_results: dict):
    raise TypeError(
        f"Line object, {type(line_object)} is not recognized yet in add_result_values_to_line()"
    )


@add_result_values_to_line.register(CalcLine)
def results_for_calcline(line_object, calculated_results):
    parameter_name = line_object.line[0]
    resulting_value = dict_get(calculated_results, parameter_name)
    line_object.line.append(deque(["=", resulting_value]))
    return line_object


@add_result_values_to_line.register(LongCalcLine)
def results_for_longcalcline(line_object, calculated_results):
    parameter_name = line_object.line[0]
    resulting_value = dict_get(calculated_results, parameter_name)
    line_object.line.append(deque(["=", resulting_value]))
    return line_object


@add_result_values_to_line.register(ParameterLine)
def results_for_paramline(line_object, calculated_results):
    return line_object


@add_result_values_to_line.register(ConditionalLine)
def results_for_conditionline(line_object, calculated_results: dict):
    expressions = line_object.expressions
    for expr in expressions:
        add_result_values_to_line(expr, calculated_results)
    return line_object


@add_result_values_to_line.register(SymbolicLine)
def results_for_symbolicline(line_object, calculated_results):
    return line_object


@add_result_values_to_line.register(BlankLine)
def results_for_blank(line_object, calculated_results):
    return line_object


@singledispatch
def convert_cell(cell_object):
    """
    Return the cell_object with all of its lines run through the function, 
    'convert_lines()', effectively converting each python element in the parsed
    deque in the equivalent element in latex. 

    The result remains stored in cell.lines
    """
    raise TypeError(
        f"Cell object {type(cell_object)} is not yet recognized in convert_cell()"
    )


@convert_cell.register(CalcCell)
def convert_calc_cell(cell: CalcCell) -> CalcCell:
    outgoing = cell.lines
    calculated_results = cell.calculated_results
    incoming = deque([])
    for line in outgoing:
        incoming.append(convert_line(line, calculated_results))
    cell.lines = incoming
    return cell


@convert_cell.register(ShortCalcCell)
def convert_calc_cell(cell: ShortCalcCell) -> ShortCalcCell:
    outgoing = cell.lines
    calculated_results = cell.calculated_results
    incoming = deque([])
    for line in outgoing:
        incoming.append(convert_line(line, calculated_results))
    cell.lines = incoming
    return cell


@convert_cell.register(LongCalcCell)
def convert_longcalc_cell(cell: LongCalcCell) -> LongCalcCell:
    outgoing = cell.lines
    calculated_results = cell.calculated_results
    incoming = deque([])
    for line in outgoing:
        incoming.append(convert_line(line, calculated_results))
    cell.lines = incoming
    return cell


@convert_cell.register(ParameterCell)
def convert_parameter_cell(cell: ParameterCell) -> ParameterCell:
    outgoing = cell.lines
    calculated_results = cell.calculated_results
    incoming = deque([])
    for line in outgoing:
        incoming.append(convert_line(line, calculated_results))
    cell.lines = incoming
    return cell


@convert_cell.register(SymbolicCell)
def convert_symbolic_cell(cell: SymbolicCell) -> SymbolicCell:
    outgoing = cell.lines
    calculated_results = cell.calculated_results
    incoming = deque([])
    for line in outgoing:
        incoming.append(convert_line(line, calculated_results))
    cell.lines = incoming
    return cell


@singledispatch
def convert_line(
    line_object: Union[
        CalcLine, ConditionalLine, ParameterLine, SymbolicLine, BlankLine
    ],
    calculated_results: dict,
) -> Union[CalcLine, ConditionalLine, ParameterLine, SymbolicLine, BlankLine]:
    """
    Returns 'line_object' with its .line attribute converted into a 
    deque with elements that have been converted to their appropriate
    Latex counterparts.

    convert_line() runs the deque through all of the conversion functions
    as organized in `swap_calculation()`.
    """
    raise TypeError(
        f"Cell object {type(line_object)} is not yet recognized in convert_line()"
    )


@convert_line.register(CalcLine)
def convert_calc(line, calculated_results):
    (
        *line_deque,
        result,
    ) = line.line  # Unpack deque of form [[calc_line, ...], ['=', 'result']]
    symbolic_portion, numeric_portion = swap_calculation(line_deque, calculated_results)
    line.line = symbolic_portion + numeric_portion + result
    return line


@convert_line.register(LongCalcLine)
def convert_longcalc(line, calculated_results):
    (
        *line_deque,
        result,
    ) = line.line  # Unpack deque of form [[calc_line, ...], ['=', 'result']]
    symbolic_portion, numeric_portion = swap_calculation(line_deque, calculated_results)
    line.line = symbolic_portion + numeric_portion + result
    return line


@convert_line.register(ConditionalLine)
def convert_conditional(line, calculated_results):
    condition, condition_type, expressions, raw_condition = (
        line.condition,
        line.condition_type,
        line.expressions,
        line.raw_condition,
    )
    true_condition_deque = swap_conditional(
        condition, condition_type, raw_condition, calculated_results
    )
    if true_condition_deque:
        line.true_condition = true_condition_deque
        for expression in expressions:
            line.true_expressions.append(convert_line(expression, calculated_results))
    return line


@convert_line.register(ParameterLine)
def convert_parameter(line, calculated_results):
    line.line = swap_symbolic_calcs(line.line, calculated_results)
    return line


@convert_line.register(SymbolicLine)
def convert_symbolic_line(line, calculated_results):
    line.line = swap_symbolic_calcs(line.line, calculated_results)
    return line


@convert_line.register(BlankLine)
def convert_blank(line, calculated_results):
    return line


@singledispatch
def format_cell(
    cell_object: Union[ParameterCell, LongCalcCell, CalcCell, SymbolicCell],
    dec_sep: str,
) -> Union[ParameterCell, LongCalcCell, CalcCell, SymbolicCell]:
    raise TypeError(
        f"Cell type {type(cell_object)} has not yet been implemented in format_cell()."
    )


@format_cell.register(ParameterCell)
def format_parameters_cell(cell: ParameterCell, dec_sep: str):
    """
    Returns the input parameters as an \\align environment with 'cols'
    number of columns.
    """
    cols = cell.cols
    precision = cell.precision
    opener = "\\["
    begin = "\\begin{aligned}"
    end = "\\end{aligned}"
    closer = "\\]"
    line_break = "\\\\[10pt]\n"
    cycle_cols = itertools.cycle(range(1, cols + 1))
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision, dec_sep)
        line = format_lines(line)
        if isinstance(line, ConditionalLine):
            outgoing = deque([])
            for expr in line.true_expressions:
                current_col = next(cycle_cols)
                if current_col % (cols - 1) == 0:
                    outgoing.append("&" + expr)
                elif current_col % cols == 0:
                    outgoing.append("&" + expr + line_break)
                else:
                    outgoing.append(expr)
            line.latex_expressions = " ".join(outgoing)
            line.latex = line.latex_condition + line.latex_expressions
        else:
            latex_param = line.latex

            current_col = next(cycle_cols)
            if current_col % (cols - 1) == 0:
                line.latex = "&" + latex_param
            elif current_col % cols == 0:
                line.latex = "&" + latex_param + line_break
            else:
                line.latex = latex_param

    latex_block = " ".join(
        [line.latex for line in cell.lines if not isinstance(line, BlankLine)]
    ).rstrip()  # .rstrip(): Hack to solve another problem of empty lines in {aligned} environment
    cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
        "\n" + end, end
    )
    return cell


@format_cell.register(CalcCell)
def format_calc_cell(cell: CalcCell, dec_sep: str) -> str:
    line_break = "\\\\[10pt]\n"
    precision = cell.precision
    incoming = deque([])
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision, dec_sep)
        line = convert_applicable_long_lines(line)
        line = format_lines(line)
        incoming.append(line)
    cell.lines = incoming

    latex_block = line_break.join([line.latex for line in cell.lines if line.latex])
    opener = "\\["
    begin = "\\begin{aligned}"
    end = "\\end{aligned}"
    closer = "\\]"
    cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
        "\n" + end, end
    )
    return cell


@format_cell.register(ShortCalcCell)
def format_shortcalc_cell(cell: ShortCalcCell, dec_sep: str) -> str:
    line_break = "\\\\[10pt]\n"
    precision = cell.precision
    incoming = deque([])
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision, dec_sep)
        line = format_lines(line)
        incoming.append(line)
    cell.lines = incoming

    latex_block = line_break.join([line.latex for line in cell.lines if line.latex])
    opener = "\\["
    begin = "\\begin{aligned}"
    end = "\\end{aligned}"
    closer = "\\]"
    cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
        "\n" + end, end
    )
    return cell


@format_cell.register(LongCalcCell)
def format_longcalc_cell(cell: LongCalcCell, dec_sep: str) -> str:
    line_break = "\\\\[10pt]\n"
    precision = cell.precision
    incoming = deque([])
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision, dec_sep)
        line = convert_applicable_long_lines(line)
        line = format_lines(line)
        incoming.append(line)
    cell.lines = incoming

    latex_block = line_break.join([line.latex for line in cell.lines if line.latex])
    opener = "\\["
    begin = "\\begin{aligned}"
    end = "\\end{aligned}"
    closer = "\\]"
    cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
        "\n" + end, end
    )
    return cell


@format_cell.register(SymbolicCell)
def format_symbolic_cell(cell: SymbolicCell, dec_sep: str) -> str:
    line_break = "\\\\[10pt]\n"
    precision = cell.precision
    incoming = deque([])
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision, dec_sep)
        line = format_lines(line)
        incoming.append(line)
    cell.lines = incoming

    latex_block = line_break.join([line.latex for line in cell.lines if line.latex])
    opener = "\\["
    begin = "\\begin{aligned}"
    end = "\\end{aligned}"
    closer = "\\]"
    cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
        "\n" + end, end
    )
    return cell


@singledispatch
def round_and_render_line_objects_to_latex(
    line: Union[CalcLine, ConditionalLine, ParameterLine], precision: int, dec_sep: str
):  # Not called for symbolic lines; see format_symbolic_cell()
    """
    Returns 'line' with the elements of the deque in its .line attribute
    converted into their final string form for rendering (thereby preserving
    its intermediate step) and populates the 
    .latex attribute with the joined string from .line.

    'precision' is the number of decimal places that each object should
    be rounded to for display.
    """
    raise TypeError(
        f"Line type {type(line)} not recognized yet in round_and_render_line_objects_to_latex()"
    )


@round_and_render_line_objects_to_latex.register(CalcLine)
def round_and_render_calc(line: CalcLine, precision: int, dec_sep: str) -> CalcLine:
    idx_line = line.line
    idx_line = swap_scientific_notation_float(idx_line, precision)
    idx_line = swap_scientific_notation_str(idx_line)
    idx_line = swap_scientific_notation_complex(idx_line, precision)
    rounded_line = round_and_render(idx_line, precision)
    rounded_line = swap_dec_sep(rounded_line, dec_sep)
    line.line = rounded_line
    line.latex = " ".join(rounded_line)
    return line


@round_and_render_line_objects_to_latex.register(LongCalcLine)
def round_and_render_longcalc(
    line: LongCalcLine, precision: int, dec_sep: str
) -> LongCalcLine:
    idx_line = line.line
    idx_line = swap_scientific_notation_float(idx_line, precision)
    idx_line = swap_scientific_notation_str(idx_line)
    idx_line = swap_scientific_notation_complex(idx_line, precision)
    rounded_line = round_and_render(idx_line, precision)
    rounded_line = swap_dec_sep(rounded_line, dec_sep)
    line.line = rounded_line
    line.latex = " ".join(rounded_line)
    return line


@round_and_render_line_objects_to_latex.register(ParameterLine)
def round_and_render_parameter(
    line: ParameterLine, precision: int, dec_sep: str
) -> ParameterLine:
    idx_line = line.line
    idx_line = swap_scientific_notation_float(idx_line, precision)
    idx_line = swap_scientific_notation_str(idx_line)
    idx_line = swap_scientific_notation_complex(idx_line, precision)
    rounded_line = round_and_render(idx_line, precision)
    rounded_line = swap_dec_sep(rounded_line, dec_sep)
    line.line = rounded_line
    line.latex = " ".join(rounded_line)
    return line


@round_and_render_line_objects_to_latex.register(ConditionalLine)
def round_and_render_conditional(
    line: ConditionalLine, precision: int, dec_sep: str
) -> ConditionalLine:
    line_break = "\\\\\n"
    outgoing = deque([])
    idx_line = line.true_condition
    idx_line = swap_scientific_notation_float(idx_line, precision)
    idx_line = swap_scientific_notation_str(idx_line)
    idx_line = swap_scientific_notation_complex(idx_line, precision)
    rounded_line = round_and_render(idx_line, precision)
    rounded_line = swap_dec_sep(rounded_line, dec_sep)
    line.true_condition = rounded_line
    for (
        expr
    ) in line.true_expressions:  # Each 'expr' item is a CalcLine or other line type
        expr.line = swap_scientific_notation_float(expr.line, precision)
        expr.line = swap_scientific_notation_str(expr.line)
        expr.line = swap_scientific_notation_complex(expr.line, precision)
        outgoing.append(
            round_and_render_line_objects_to_latex(expr, precision, dec_sep)
        )
    line.true_expressions = outgoing
    line.latex = line_break.join([calc_line.latex for calc_line in outgoing])
    return line


@round_and_render_line_objects_to_latex.register(SymbolicLine)
def round_and_render_symbolic(
    line: SymbolicLine, precision: int, dec_sep: str
) -> SymbolicLine:
    expr = line.line
    expr = swap_scientific_notation_float(expr, precision)
    expr = swap_scientific_notation_str(expr)
    expr = swap_scientific_notation_complex(expr, precision)
    rounded_line = round_and_render(expr, precision)
    rounded_line = swap_dec_sep(rounded_line, dec_sep)
    line.line = rounded_line
    line.latex = " ".join(rounded_line)
    return line


@round_and_render_line_objects_to_latex.register(BlankLine)
def round_and_render_blank(line, precision, dec_sep):
    return line


@singledispatch
def convert_applicable_long_lines(
    line: Union[ConditionalLine, CalcLine]
):  # Not called for symbolic lines; see format_symbolic_cell()
    raise TypeError(
        f"Line type {type(line)} not yet implemented in convert_applicable_long_lines()."
    )


@convert_applicable_long_lines.register(CalcLine)
def convert_calc_to_long(line: CalcLine):
    if test_for_long_lines(line):

        return convert_calc_line_to_long(line)
    return line


@convert_applicable_long_lines.register(LongCalcLine)
def convert_longcalc_to_long(line: LongCalcLine):
    return line


@convert_applicable_long_lines.register(ConditionalLine)
def convert_expressions_to_long(line: ConditionalLine):
    for idx, expr in enumerate(line.true_expressions):
        if test_for_long_lines(expr):
            line.true_expressions[idx] = convert_calc_line_to_long(expr)
    return line


@convert_applicable_long_lines.register(ParameterLine)
def convert_param_to_long(line: ParameterLine):
    return line


@convert_applicable_long_lines.register(BlankLine)
def convert_blank_to_long(line: BlankLine):
    return line


@singledispatch
def test_for_long_lines(line: Union[CalcLine, ConditionalLine]) -> bool:
    raise TypeError(
        f"Line type of {type(line)} not yet implemented in test_for_long_lines()."
    )


@test_for_long_lines.register(ParameterLine)
def test_for_long_param_lines(line: ParameterLine) -> bool:
    return False


@test_for_long_lines.register(BlankLine)
def test_for_long_blank(line: BlankLine) -> bool:
    return False


@test_for_long_lines.register(LongCalcLine)
def test_for_long_longcalcline(line: LongCalcLine) -> bool:
    # No need to return True since it's already a LongCalcLine
    return False


@test_for_long_lines.register(CalcLine)
def test_for_long_calc_lines(line: CalcLine) -> bool:
    """
    Return True if 'calc_line' passes the criteria to be considered, 
    as a "LongCalcLine". False otherwise.

    Function goes through all of the code in the CalcLine and maintains
    several (imperfect) tallies of characters to determine if the 
    calculation is too long to exist on a single line.

    This is attempted by counting actual characters that will appear
    in the resulting equation and that are not part of
    the actual latex code (e.g. anything with a "\\" in front of it, etc.),
    and by also "discounting" characters that are in a fraction, since
    the overall length of the fraction (on the page) is determined by
    whichever is longer, the numerator or denominator. As such, characters
    in a fraction (single level of fraction, only) are counted and 
    discounted from the total tally.

    This is an imperfect work-in-progress.
    """
    threshold = 130  # This is an arbitrary value that can be adjusted manually, if reqd
    item_length = 0
    fraction_discount = 0
    stack = 0
    stack_location = 0
    fraction_flag = False
    fraction_count = 0
    total_length = 0
    for item in line.line:
        if "_" in item or "^" in item:  # Check for subscripts and superscripts first
            item = (
                item.replace("_", "").replace("^", "").replace("{", "").replace("}", "")
            )
            item_length = len(item)

        elif "\\" not in item or "{" not in item:
            item_length = len(item)

        elif "{" in item:  # Check for other latex operators that use { }
            stack += 1

        else:  # Assume the latex command adds at least one character, e.g. \left( or \cdot
            total_length += 1
            continue

        if item == "\\frac{" or item == "}{":  # If entering into a fraction
            fraction_discount = (
                fraction_count
                if fraction_count > fraction_discount
                else fraction_discount
            )
            fraction_count = 0
            fraction_flag = True
            if item == "\\frac{":
                stack_location = stack  # Mark where the fraction is in relation to the other "{" operators
                stack += 1

        elif (  # Check for closing of misc latex operators, which may include a fraction
            item == "}"
        ):
            stack -= 1
            if stack == stack_location:
                fraction_flag == False
                fraction_discount = (
                    fraction_count
                    if fraction_count > fraction_discount
                    else fraction_discount
                )

        if fraction_flag == True:
            fraction_count += item_length

        total_length += item_length

    stat = total_length - fraction_discount
    return stat >= threshold


def convert_calc_line_to_long(calc_line: CalcLine) -> LongCalcLine:
    """
    Return a LongCalcLine based on a calc_line
    """
    return LongCalcLine(
        line=calc_line.line, comment=calc_line.comment, latex=calc_line.latex
    )


@singledispatch
def format_lines(line_object):
    """
    format_lines adds small, context-dependent pieces of latex code in
    amongst the latex string in the line_object.latex attribute. This involves
    things like inserting "&" or linebreak characters for equation alignment, 
    formatting comments stored in the .comment attribute and putting them at 
    the end of the calculation, or the distinctive "Since, <condition> ..."
    text that occurs when a conditional calculation is rendered.
    """
    raise TypeError(
        f"Line type {type(line_object)} is not yet implemented in format_lines()."
    )


@format_lines.register(CalcLine)
def format_calc_line(line: CalcLine) -> CalcLine:
    latex_code = line.latex
    equals_signs = [idx for idx, char in enumerate(latex_code) if char == "="]
    second_equals = equals_signs[1]  # Change to 1 for second equals
    latex_code = latex_code.replace("=", "&=")  # Align with ampersands for '\align'
    comment_space = ""
    comment = ""
    if line.comment:
        comment_space = "\\;"
        comment = format_strings(line.comment, comment=True)
    line.latex = f"{latex_code[0:second_equals + 1]}{latex_code[second_equals + 2:]}{comment_space}{comment}\n"
    return line


@format_lines.register(ConditionalLine)
def format_conditional_line(line: ConditionalLine) -> ConditionalLine:
    """
    Returns the conditional line as a string of latex_code
    """

    if line.true_condition:
        latex_condition = " ".join(line.true_condition)
        a = "{"
        b = "}"
        comment_space = ""
        comment = ""
        if line.comment:
            comment_space = "\\;"
            comment = format_strings(line.comment, comment=True)
        new_math_env = "\n\\end{aligned}\n\\]\n\\[\n\\begin{aligned}\n"
        first_line = f"&\\text{a}Since, {b}{latex_condition}:{comment_space}{comment}{new_math_env}"
        if line.condition_type == "else":
            first_line = ""
        line_break = "\\\\[10pt]\n"
        line.latex_condition = first_line

        outgoing = deque([])
        for calc_line in line.true_expressions:
            outgoing.append((format_lines(calc_line)).latex)
        line.true_expressions = outgoing
        line.latex_expressions = line_break.join(line.true_expressions)
        line.latex = line.latex_condition + line.latex_expressions
        return line
    else:
        line.condition_latex = ""
        line.true_expressions = deque([])
        return line


@format_lines.register(LongCalcLine)
def format_long_calc_line(line: LongCalcLine) -> LongCalcLine:
    """
    Return line with .latex attribute formatted with line breaks suitable
    for positioning within the "\aligned" latex environment.
    """
    latex_code = line.latex
    long_latex = latex_code.replace("=", "\\\\&=")  # Change all...
    long_latex = long_latex.replace("\\\\&=", "&=", 1)  # ...except the first one
    line_break = "\\\\\n"
    comment_space = ""
    comment = ""
    if line.comment:
        comment_space = "\\;"
        comment = format_strings(line.comment, comment=True)
    line.latex = f"{long_latex}{comment_space}{comment}{line_break}"
    return line


@format_lines.register(ParameterLine)
def format_param_line(line: ParameterLine) -> ParameterLine:
    comment_space = "\\;"
    line_break = "\n"
    if "=" in line.latex:
        replaced = line.latex.replace("=", "&=")
        comment = format_strings(line.comment, comment=True)
        line.latex = f"{replaced}{comment_space}{comment}{line_break}"
    else:  # To handle sympy symbols displayed alone
        replaced = line.latex.replace(" ", comment_space)
        comment = format_strings(line.comment, comment=True)
        line.latex = f"{replaced}{comment_space}{comment}{line_break}"
    return line


@format_lines.register(SymbolicLine)
def format_symbolic_line(line: SymbolicLine) -> SymbolicLine:
    replaced = line.latex.replace("=", "&=")
    comment_space = "\\;"
    comment = format_strings(line.comment, comment=True)
    line.latex = f"{replaced}{comment_space}{comment}\n"
    return line


@format_lines.register(BlankLine)
def format_blank_line(line: BlankLine) -> BlankLine:
    line.latex = ""
    return line


def split_conditional(line: str, calculated_results: dict, override: str):
    raw_conditional, raw_expressions = line.split(":")
    expr_deque = deque(raw_expressions.split(";"))  # handle multiple lines in cond
    try:
        cond_type, condition = raw_conditional.strip().split(" ", 1)
    except:
        cond_type = "else"
        condition = ""
    cond_type = cond_type.strip().lstrip()
    condition = condition.strip().lstrip()
    try:
        cond = expr_parser(condition)
    except pp.ParseException:
        cond = deque([condition])

    expr_acc = deque([])
    for line in expr_deque:
        categorized = categorize_line(line, calculated_results, override=override)
        expr_acc.append(categorized)

    return (
        cond,
        cond_type,
        expr_acc,
        condition,
        raw_expressions,
    )


def test_for_parameter_line(line: str) -> bool:
    """
    Returns True if `line` appears to be a line to simply declare a
    parameter (e.g. "a = 34") instead of an actual calculation.
    """
    # Fast Tests
    if not line.strip():  # Blank lines
        return False
    elif len(line.strip().split()) == 1:  # Outputing variable names
        return True
    elif "=" not in line or "if " in line or ":" in line:  # conditional lines
        return False

    # Exploratory Tests
    _, right_side = line.split("=", 1)
    right_side = right_side.replace(" ", "")

    if (right_side.find("(") == 0) and (
        right_side.find(")") == len(right_side)
    ):  # Blocked by parentheses
        return True

    try:
        right_side_deque = expr_parser(right_side)
    except pp.ParseException:
        right_side_deque = deque([right_side])

    if len(right_side_deque) == 1:
        return True
    elif test_for_unary(right_side_deque):
        return True
    else:
        return False


def test_for_parameter_cell(raw_python_source: str) -> bool:
    """
    Returns True if the text, "# Parameters" or "#Parameters" is the line
    of 'row_python_source'. False, otherwise.
    """
    first_element = raw_python_source.split("\n")[0]
    if "#" in first_element and "parameter" in first_element.lower():
        return True
    return False


def test_for_long_cell(raw_python_source: str) -> bool:
    """
    Returns True if the text "# Long" is in the first line of
    `raw_python_source`. False otherwise.
    """
    first_element = raw_python_source.split("\n")[0]
    if "#" in first_element and "long" in first_element.lower():
        return True
    return False


def test_for_short_cell(raw_python_source: str) -> bool:
    """
    Returns True if the text "# Long" is in the first line of
    `raw_python_source`. False otherwise.
    """
    first_element = raw_python_source.split("\n")[0]
    if "#" in first_element and "short" in first_element.lower():
        return True
    return False


def test_for_symbolic_cell(raw_python_source: str) -> bool:
    """
    Returns True if the text "# Long" is in the first line of
    `raw_python_source`. False otherwise.
    """
    first_element = raw_python_source.split("\n")[0]
    if "#" in first_element and "symbolic" in first_element.lower():
        return True
    return False


def test_for_blank_line(source: str) -> bool:
    """
    Returns True if 'source' is effectively a blank line, 
    either "\n", " ", or "", or any combination thereof.
    Returns False, otherwise.
    """
    return not bool(source.strip())


def test_for_conditional_line(source: str) -> bool:
    """
    Returns True if 'source' appears to be conditional expression.
    """
    return ":" in source and ("if" in source or "else" in source)


def test_for_single_dict(source: str, calc_results: dict) -> bool:
    """
    Returns True if 'source' is a str representing a variable name
    within 'calc_results' whose value itself is a single-level 
    dictionary of keyword values.
    """
    gotten = calc_results.get(source, "")
    return isinstance(gotten, dict)


def test_for_scientific_notation_str(elem: str) -> bool:
    """
    Returns True if 'elem' represents a python float in scientific
    "e notation".
    e.g. 1.23e-3, 0.09e5
    Returns False otherwise
    """
    test_for_float = False
    try:
        float(elem)
        test_for_float = True
    except:
        pass

    if "e" in str(elem).lower() and test_for_float:
        return True
    return False


def round_complex(elem: complex, precision: int) -> complex:
    """
    Returns the complex 'elem' rounded to 'precision'
    """
    return complex(round(elem.real, precision), round(elem.imag, precision))


def test_for_small_complex(elem: Any, precision: int) -> bool:
    """
    Returns True if 'elem' is a complex whose rounded str representation
    has fewer significant figures than the number in 'precision'.
    Returns False otherwise.
    """
    if isinstance(elem, complex):
        test = [
            test_for_small_float(elem.real, precision),
            test_for_small_float(elem.imag, precision),
        ]
        return any(test)


def test_for_small_float(elem: Any, precision: int) -> bool:
    """
    Returns True if 'elem' is a float whose rounded str representation
    has fewer significant figures than the numer in 'precision'. 
    Return False otherwise.
    """

    if not isinstance(elem, (float)):
        return False
    elem_as_str = str(round(abs(elem), precision))
    if "e" in str(elem):
        return True
    if "." in elem_as_str:
        left, *_right = elem_as_str.split(".")
        if left != "0":
            return False
    if (
        round(elem, precision) != round(elem, precision + 1)
        or str(abs(round(elem, precision))).replace("0", "").replace(".", "")
        == str(abs(round(elem, precision + 1))).replace("0", "").replace(".", "")
        == ""
    ):
        return True
    else:
        return False


def split_parameter_line(line: str, calculated_results: dict) -> deque:
    """
    Return 'line' as a deque that represents the line as: 
        deque([<parameter>, "&=", <value>])
    """
    param = line.replace(" ", "").split("=", 1)[0]
    param_line = deque([param, "=", calculated_results[param]])
    return param_line


def format_strings(string: str, comment: bool) -> deque:
    """
    Returns 'string' appropriately formatted to display in a latex
    math environment.
    """
    if not string:
        return ""
    text_env = ""
    end_env = ""
    l_par = ""
    r_par = ""
    if comment:
        l_par = "("
        r_par = ")"
        text_env = "\\;\\textrm{"
        end_env = "}"
    else:
        l_par = ""
        r_par = ""
        text_env = "\\textrm{"
        end_env = "}"

    return "".join([text_env, l_par, string.strip().rstrip(), r_par, end_env])


def round_and_render(line_of_code: deque, precision: int) -> deque:
    """
    Returns a rounded str based on the latex_repr of an object in
    'line_of_code'
    """
    outgoing = deque([])
    for item in line_of_code:
        if hasattr(item, "__len__") and not isinstance(item, (str, dict)):
            try:
                rounded = [round(v, precision) for v in item]
                outgoing.append(latex_repr(rounded))
            except:
                rounded = item
        elif isinstance(item, complex):
            rounded = round_complex(item, precision)
            outgoing.append(latex_repr(rounded))
        elif not isinstance(item, (str, int)):
            try:
                rounded = round(item, precision)  # Rounding
            except:
                rounded = item
            outgoing.append(latex_repr(rounded))  # Rendering
        else:
            outgoing.append(latex_repr(item))
    return outgoing


def latex_repr(item: Any) -> str:
    """
    Return a str if the object, 'item', has a special repr method
    for rendering itself in latex. If not, returns str(result).
    """
    if hasattr(item, "_repr_latex_"):
        return item._repr_latex_().replace("$", "")

    elif hasattr(item, "latex"):
        try:
            return item.latex().replace("$", "")
        except TypeError:
            return str(item)

    elif hasattr(item, "to_latex"):
        try:
            return item.to_latex().replace("$", "")
        except TypeError:
            return str(item)

    elif hasattr(item, "__len__") and not isinstance(item, (str, dict, tuple)):
        comma_space = ",\\ "
        try:
            array = "[" + comma_space.join([str(v) for v in item]) + "]"
            return array
        except TypeError:
            return str(item)

    else:
        return str(item)


class ConditionalEvaluator:
    def __init__(self):
        self.prev_cond_type = ""
        self.prev_result = False

    def __call__(
        self,
        conditional: deque,
        conditional_type: str,
        raw_conditional: str,
        calc_results: dict,
    ) -> deque:
        if conditional_type == "if":  # Reset
            self.prev_cond_type = ""
            self.prev_result = False
        if conditional_type != "else":
            result = eval_conditional(raw_conditional, **calc_results)
        else:
            result = True
        if (
            result == True
            and self.check_prev_cond_type(conditional_type)
            and not self.prev_result
        ):
            l_par = "\\left("
            r_par = "\\right)"
            if conditional_type != "else":
                symbolic_portion = swap_symbolic_calcs(conditional, calc_results)
                numeric_portion = swap_numeric_calcs(conditional, calc_results)
                resulting_latex = (
                    symbolic_portion
                    + deque(["\\rightarrow"])
                    + deque([l_par])
                    + numeric_portion
                    + deque([r_par])
                )
            else:
                numeric_portion = swap_numeric_calcs(conditional, calc_results)
                resulting_latex = numeric_portion
            self.prev_cond_type = conditional_type
            self.prev_result = result
            return resulting_latex
        else:
            self.prev_cond_type = conditional_type
            self.prev_result = result
            return deque([])

    def check_prev_cond_type(self, cond_type: str) -> bool:
        """
        Returns True if cond_type is a legal conditional type to 
        follow self.prev_cond_type. Returns False otherwise.
        e.g. cond_type = "elif", self.prev_cond_type = "if" -> True
        e.g. cond_type = "if", self.prev_cond_type = "elif" -> False
        """
        prev = self.prev_cond_type
        current = cond_type
        if prev == "else":
            return False
        elif prev == "elif" and current == "if":
            return False
        return True


swap_conditional = (
    ConditionalEvaluator()
)  # Instantiate the callable helper class at "Cell" level scope


# def swap_params(parameter: deque) -> deque:
#     """
#     Returns the python code elements in the 'parameter' deque converted
#     into latex code elements in the deque. This primarily involves operating
#     on the variable name.
#     """
#     return swap_symbolic_calcs(parameter)


def swap_calculation(calculation: deque, calc_results: dict) -> tuple:
    """Returns the python code elements in the deque converted into
    latex code elements in the deque"""
    # calc_w_integrals_preswapped = swap_integrals(calculation, calc_results)
    symbolic_portion = swap_symbolic_calcs(calculation, calc_results)
    calc_drop_decl = deque(list(calculation)[1:])  # Drop the variable declaration
    numeric_portion = swap_numeric_calcs(calc_drop_decl, calc_results)
    return (symbolic_portion, numeric_portion)


def swap_symbolic_calcs(calculation: deque, calc_results: dict) -> deque:
    # remove calc_results function parameter
    symbolic_expression = copy.copy(calculation)
    functions_on_symbolic_expressions = [
        insert_parentheses,
        swap_math_funcs,
        swap_superscripts,
        swap_frac_divs,
        swap_py_operators,
        swap_comparison_ops,
        swap_for_greek,
        swap_prime_notation,  # Fix problem here
        swap_long_var_strs,
        extend_subscripts,
        swap_superscripts,
        flatten_deque,
    ]
    for function in functions_on_symbolic_expressions:
        # breakpoint()
        if function is swap_math_funcs:
            symbolic_expression = function(symbolic_expression, calc_results)
        else:
            symbolic_expression = function(symbolic_expression)
    return symbolic_expression


def swap_numeric_calcs(calculation: deque, calc_results: dict) -> deque:
    numeric_expression = copy.copy(calculation)
    functions_on_numeric_expressions = [
        insert_parentheses,
        swap_math_funcs,
        swap_frac_divs,
        swap_py_operators,
        swap_comparison_ops,
        swap_values,
        swap_superscripts,
        extend_subscripts,
        flatten_deque,
    ]
    for function in functions_on_numeric_expressions:
        if function is swap_values or function is swap_math_funcs:
            numeric_expression = function(numeric_expression, calc_results)
        else:
            numeric_expression = function(numeric_expression)
    return numeric_expression


def swap_integrals(d: deque, calc_results: dict) -> deque:
    """
    Returns 'calculation' with any function named "quad" or "integrate"
    rendered as an integral.
    """
    swapped_deque = deque([])
    if "integrate" == d[0] or "quad" == d[0]:
        args_deque = d[1]
        function_name = args_deque[0]
        function = dict_get(calc_results, function_name)
        function_source = (
            inspect.getsource(function).split("\n")[1].replace("return", "")
        )
        d_var = (
            str(inspect.signature(function))
            .replace("(", "")
            .replace(")", "")
            .replace(" ", "")
            .split(":")[0]
        )
        source_deque = expr_parser(function_source)
        a = args_deque[2]
        b = args_deque[4]
        swapped_deque += deque(["\\int_{", a, "}", "^", "{", b, "}"])
        swapped_deque.append(source_deque)
        swapped_deque.append(f"\\; d{d_var}")
        return swapped_deque
    else:
        return d


def swap_log_func(d: deque, calc_results: dict) -> deque:
    """
    Returns a new deque representing 'd' but with any log functions swapped 
    out for the appropriate Latex equivalent.
    """
    swapped_deque = deque([])
    base = ""
    if isinstance(d[2], deque) or hasattr(d[2], "__len__"):
        if "," in d[2]:
            try:
                base = d[2][-1]
                operand = swap_math_funcs(deque(list(d[2])[:-2]), calc_results)
            except IndexError:
                base = ""
                operand = swap_math_funcs(d[2], calc_results)
        elif d[0] in ["log10", "log2"]:
            base = d[0].replace("log", "")
            operand = swap_math_funcs(d[2], calc_results)
        else:
            operand = swap_math_funcs(d[2], calc_results)
    elif len(d) == 2:
        operand = d[2]
    if base == "e":
        base = ""

    base = dict_get(calc_results, base)

    if base:
        log_func = "\\log_"
    else:
        log_func = "\\ln"

    swapped_deque.append(log_func + str(base))
    swapped_deque.append(d[1])
    swapped_deque.append(operand)
    swapped_deque.append(d[3])
    return swapped_deque


def swap_floor_ceil(d: deque, func_name: str, calc_results: dict) -> deque:
    """
    Return a deque representing 'd' but with the functions floor(...)
    and ceil(...) swapped out for floor and ceiling Latex brackets. 
    """
    swapped_deque = deque([])
    for item in d:
        if isinstance(item, deque):
            new_item = swap_math_funcs(item, calc_results)
            swapped_deque.append(new_item)
        elif item == func_name:
            continue
        elif item == "\\left(":
            swapped_deque.append(f"\\left \\l{func_name}")
        elif item == "\\right)":
            swapped_deque.append(f"\\right \\r{func_name}")
        else:
            swapped_deque.append(item)
    return swapped_deque


def flatten_deque(d: deque) -> deque:
    new_deque = deque([])
    for item in flatten(d):
        new_deque.append(item)
    return new_deque


def flatten(items: Any, omit_parentheses: bool = False) -> deque:
    """Returns elements from a deque and flattens elements from sub-deques.
    Inserts latex parentheses ( '\\left(' and '\\right)' ) where sub-deques
    used to exists, except if the reason for the sub-deque was to encapsulate
    either a fraction or an integral (then no parentheses).
    """
    if isinstance(items, deque):
        for item in items:
            yield from flatten(item)  # recursion!
    else:
        yield items


def eval_conditional(conditional_str: str, **kwargs) -> str:
    """
    Evals the python code statement, 'conditional_str', based on the variables passed in
    as an unpacked dict as kwargs. The first line allows the dict values to be added to
    locals that can be drawn upon to evaluate the conditional_str. Returns bool.
    """
    # From Thomas Holder on SO:
    # https://stackoverflow.com/questions/1897623/
    # unpacking-a-passed-dictionary-into-the-functions-name-space-in-python
    exec(",".join(kwargs) + ", = kwargs.values()")
    try:
        # It would be good to sanitize the code coming in on 'conditional_str'
        # Should this code be forced into using only boolean operators?
        # Do not need to cross this bridge, yet.
        return eval(conditional_str)
    except SyntaxError:
        return conditional_str


# def code_reader(pycode_as_str: str) -> deque:
#     """
#     Returns full line of code parsed into deque items
#     """
#     breakpoint()
#     var_name, expression = pycode_as_str.split("=", 1)
#     var_name, expression = var_name.strip(), expression.strip()
#     expression_as_deque = expr_parser(expression)
#     return deque([var_name]) + deque(["=",]) + expression_as_deque


def expr_parser(line: str) -> list:
    import sys

    sys.setrecursionlimit(3000)
    pp.ParserElement.enablePackrat()

    variable = pp.Word(pp.alphanums + "_")
    numbers = pp.pyparsing_common.fnumber.setParseAction("".join)
    imag = pp.Literal("j")
    plusminus = pp.oneOf("+ -")
    imag_num = pp.Combine(numbers + imag)
    comp_num = pp.Combine(numbers + plusminus + numbers + imag)
    complex_number = comp_num | imag_num
    all_nums = complex_number | numbers

    lpar = pp.Literal("(").suppress()
    rpar = pp.Literal(")").suppress()
    functor = variable + pp.ZeroOrMore(".")

    expr = pp.Forward()
    func = pp.Group(functor + lpar + pp.Optional(pp.delimitedList(expr)) + rpar)
    # operand = func | numbers | variable .
    operand = func | all_nums | variable

    expop = pp.Literal("**")
    signop = pp.oneOf("+ - ~")
    arithop = pp.oneOf("= + - * / // % , < > >= <= == !=")

    expr <<= pp.infixNotation(
        operand,
        [
            (expop, 2, pp.opAssoc.RIGHT),
            (signop, 1, pp.opAssoc.RIGHT),
            (arithop, 2, pp.opAssoc.LEFT),
        ],
    )

    return list_to_deque(
        more_itertools.collapse(expr.parseString(line).asList(), levels=1)
    )


def list_to_deque(los: List[str]) -> deque:
    """
    Return `los` converted into a deque.
    """
    acc = deque([])
    for s in los:
        if isinstance(s, list):
            acc.append(list_to_deque(s))
        else:
            acc.append(s)
    return deque(acc)


def extend_subscripts(pycode_as_deque: deque) -> deque:
    """
    For variables named with a subscript, e.g. V_c, this function ensures that any
    more than one subscript, e.g. s_ze, is included in the latex subscript notation.
    For any item in 'pycode_as_deque' that has more than one character in the subscript,
    e.g. s_ze, then it will be converted to s_{ze}. Also handles nested subscripts.
    """
    swapped_deque = deque([])
    for item in pycode_as_deque:
        discount = 0  # hack to prevent excess braces from swap_long_var_str
        if isinstance(item, deque):
            new_item = extend_subscripts(item)  # recursion!
            swapped_deque.append(new_item)
        elif isinstance(item, str) and "_" in item and not "\\int" in item:
            if "\\mathrm{" in item:
                discount = 1
            new_item = ""
            for char in item:
                if char == "_":
                    new_item += char
                    new_item += "{"
                else:
                    new_item += char
            num_braces = new_item.count("{") - discount

            new_item += "}" * num_braces
            swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_frac_divs(code: deque) -> deque:
    """
    Swaps out the division symbol, "/", with a Latex fraction.
    The numerator is the symbol before the "/" and the denominator follows.
    If either is a string, then that item alone is in the fraction.
    If either is a deque, then all the items in the deque are in that part of the fraction.
    Returns a deque.
    """
    swapped_deque = deque([])
    length = len(code)
    a = "{"
    b = "}"
    ops = "\\frac"
    close_bracket_token = 0
    for index, item in enumerate(code):
        next_idx = min(index + 1, length - 1)
        if code[next_idx] == "/" and isinstance(item, deque):
            new_item = f"{ops}{a}"
            swapped_deque.append(new_item)
            swapped_deque.append(swap_frac_divs(item))  # recursion!
        elif code[next_idx] == "/" and not isinstance(item, deque):
            new_item = f"{ops}{a}"
            swapped_deque.append(new_item)
            swapped_deque.append(item)
        elif item == "/":
            swapped_deque.append(f"{b}{a}")
            close_bracket_token += 1
        elif close_bracket_token:
            if isinstance(item, deque):
                swapped_deque.append(swap_frac_divs(item))
            else:
                swapped_deque.append(item)
            new_item = f"{b}" * close_bracket_token
            close_bracket_token = 0
            swapped_deque.append(new_item)
        elif isinstance(item, deque):
            new_item = swap_frac_divs(item)  # recursion!
            swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_math_funcs(pycode_as_deque: deque, calc_results: dict) -> deque:
    """
    Returns a deque representing 'pycode_as_deque' but with appropriate
    parentheses inserted.
    """
    a = "{"
    b = "}"
    swapped_deque = deque([])
    for item in pycode_as_deque:
        if isinstance(item, deque):
            # possible_func = not test_for_typ_arithmetic(item)
            poss_func_name = get_function_name(item)
            func_name_match = get_func_latex(poss_func_name)
            if poss_func_name != func_name_match:
                item = swap_func_name(item, poss_func_name)
                item = insert_func_braces(item)
                new_item = swap_math_funcs(item, calc_results)
                swapped_deque.append(new_item)
            elif poss_func_name == func_name_match:
                # Begin checking for specialized function names
                if poss_func_name == "quad":
                    new_item = swap_integrals(item, calc_results)
                    # new_item = swap_math_funcs(item, calc_results)
                    swapped_deque.append(new_item)
                elif "log" in poss_func_name:
                    new_item = swap_log_func(item, calc_results)
                    swapped_deque.append(new_item)
                elif poss_func_name == "ceil" or poss_func_name == "floor":
                    new_item = swap_floor_ceil(item, poss_func_name, calc_results)
                    swapped_deque.append(new_item)
                else:
                    ops = "\\operatorname"
                    new_func = f"{ops}{a}{poss_func_name}{b}"
                    item = swap_func_name(item, poss_func_name, new_func)
                    if not test_for_typ_arithmetic:
                        item = insert_func_braces(item)
                    new_item = swap_math_funcs(item, calc_results)
                    swapped_deque.append(new_item)
            else:
                swapped_deque.append(item)
        else:
            swapped_deque.append(item)
    return swapped_deque


def get_func_latex(func: str) -> str:
    """
    Returns the Latex equivalent of the function name, 'func'.
    If a match is not found then 'func' is returned.
    """
    latex_math_funcs = {
        "sin": "\\sin",
        "cos": "\\cos",
        "tan": "\\tan",
        "sqrt": "\\sqrt",
        "exp": "\\exp",
        "sinh": "\\sinh",
        "tanh": "\\tanh",
        "cosh": "\\cosh",
        "asin": "\\arcsin",
        "acos": "\\arccos",
        "atan": "\\arctan",
        "atan2": "\\arctan",
        "asinh": "\\arcsinh",
        "acosh": "\\arccosh",
        "atanh": "\\arctanh",
        "sum": "\\Sigma",
    }
    return dict_get(latex_math_funcs, func)


def insert_func_braces(d: deque) -> deque:
    """
    Returns a deque representing 'd' with appropriate latex function
    braces inserted.
    'd' represents a deque representing a function and its parameters
    having already been tested by 'get_function_name(...)'
    """
    a = "{"
    b = "}"
    swapped_deque = deque([])
    d_len = len(d)
    last_idx = d_len - 1
    for idx, elem in enumerate(d):
        if last_idx == 1:  # Special case, func is sqrt or other non-parenth func
            swapped_deque.append(d[0])
            swapped_deque.append(a)
            swapped_deque.append(d[1])
            swapped_deque.append(b)
            return swapped_deque
        elif idx == 1:  # func name is 0, brace at 1
            swapped_deque.append(a)
            swapped_deque.append(elem)
        elif idx == last_idx:  # brace at end
            swapped_deque.append(elem)
            swapped_deque.append(b)
        else:
            swapped_deque.append(elem)
    return swapped_deque


def swap_func_name(d: deque, old: str, new: str = "") -> deque:
    """
    Returns 'd' with the function name swapped out
    """
    swapped_deque = deque([])
    for elem in d:
        if elem == old:
            if new:
                swapped_deque.append(new)
            else:
                swapped_func = get_func_latex(elem)
                swapped_deque.append(swapped_func)
        else:
            swapped_deque.append(elem)
    return swapped_deque


def swap_py_operators(pycode_as_deque: deque) -> deque:
    """
    Swaps out Python mathematical operators that do not exist in Latex.
    Specifically, swaps "*", "**", and "%" for "\\cdot", "^", and "\\bmod",
    respectively.
    """
    swapped_deque = deque([])
    for item in pycode_as_deque:
        if type(item) is deque:
            new_item = swap_py_operators(item)  # recursion!
            swapped_deque.append(new_item)
        else:
            if item == "*":
                swapped_deque.append("\\cdot")
            elif item == "%":
                swapped_deque.append("\\bmod")
            elif item == ",":
                swapped_deque.append(",\\ ")
            else:
                swapped_deque.append(item)
    return swapped_deque


def swap_scientific_notation_str(pycode_as_deque: deque) -> deque:
    """
    Returns a deque representing 'line' with any python 
    float elements in the deque
    that are in scientific notation "e" format converted into a Latex 
    scientific notation.
    """
    b = "}"
    swapped_deque = deque([])
    for item in pycode_as_deque:
        if isinstance(item, deque):
            new_item = swap_scientific_notation_str(item)
            swapped_deque.append(new_item)
        elif test_for_scientific_notation_str(item):
            new_item = item.replace("e", " \\times 10 ^ {")
            swapped_deque.append(new_item)
            swapped_deque.append(b)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_scientific_notation_float(line: deque, precision: int) -> deque:
    """
    Returns a deque representing 'pycode_as_deque' with any python floats that
    will get "cut-off" by the 'precision' arg when they are rounded as being 
    rendered as strings in python's "e format" scientific notation.

    A float is "cut-off" by 'precision' when it's number of significant digits will
    be less than those required by precision. 

    e.g. elem = 0.001353 with precision=3 will round to 0.001, with only one
    significant digit (1 < 3). Therefore this float is "cut off" and will be 
    formatted instead as "1.353e-3"

    elem = 0.1353 with precision=3 will round to 0.135 with three significant digits
    (3 == 3). Therefore this float will not be formatted.
    """
    swapped_deque = deque([])
    for item in line:
        if test_for_small_float(item, precision):
            new_item = (
                "{:.{precision}e}".format(item, precision=precision)
                .replace("e-0", "e-")
                .replace("e+0", "e+")
            )
            swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)

    return swapped_deque


def swap_scientific_notation_complex(line: deque, precision: int) -> deque:
    swapped_deque = deque([])
    for item in line:
        if isinstance(item, complex) and test_for_small_complex(item, precision):
            new_complex = swap_scientific_notation_float(
                [item.real, item.imag], precision
            )
            new_complex = list(swap_scientific_notation_str(new_complex))
            ops = "" if item.imag < 0 else "+"
            new_complex_str = (
                f"({new_complex[0]} {new_complex[1]} {ops} {new_complex[-1]}j)"
            )
            swapped_deque.append(new_complex_str)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_comparison_ops(pycode_as_deque: deque) -> deque:
    """
    Returns a deque representing 'pycode_as_deque' with any python 
    comparison operators, eg. ">", ">=", "!=", "==" swapped with 
    their latex equivalent.
    """
    py_ops = {
        "<": "\\lt",
        ">": "\\gt",
        "<=": "\\leq",
        ">=": "\\geq",
        "==": "=",
        "!=": "\\neq",
    }
    swapped_deque = deque([])
    for item in pycode_as_deque:
        if type(item) is deque:
            new_item = swap_comparison_ops(item)
            swapped_deque.append(new_item)
        else:
            new_item = dict_get(py_ops, item)
            swapped_deque.append(new_item)
    return swapped_deque


def swap_superscripts(pycode_as_deque: deque) -> deque:
    """
    Returns the python code deque with any exponentials swapped
    out for latex superscripts.
    """
    pycode_with_supers = deque([])
    close_bracket_token = False
    ops = "^"
    a = "{"
    b = "}"
    l_par = "\\left("
    r_par = "\\right)"
    prev_item = ""
    for idx, item in enumerate(pycode_as_deque):
        next_idx = min(idx + 1, len(pycode_as_deque) - 1)
        next_item = pycode_as_deque[next_idx]
        if isinstance(item, deque) and not close_bracket_token:
            if "**" == str(next_item):
                pycode_with_supers.append(l_par)
                new_item = swap_superscripts(item)
                pycode_with_supers.append(new_item)
                pycode_with_supers.append(r_par)
            else:
                new_item = swap_superscripts(item)  # recursion!
                pycode_with_supers.append(new_item)

        else:
            if "**" == str(next_item):
                pycode_with_supers.append(l_par)
                pycode_with_supers.append(item)
                pycode_with_supers.append(r_par)
            elif str(item) == "**":
                new_item = f"{ops}{a}"
                pycode_with_supers.append(new_item)
                close_bracket_token = True
            elif close_bracket_token:
                pycode_with_supers.append(item)
                new_item = f"{b}"
                pycode_with_supers.append(new_item)
                close_bracket_token = False
            else:
                pycode_with_supers.append(item)
                prev_item = item

    return pycode_with_supers


def swap_for_greek(pycode_as_deque: deque) -> deque:
    """
    Returns full line of code as deque with any Greek terms swapped in for words describing
    Greek terms, e.g. 'beta' -> 'β'
    """
    swapped_deque = deque([])
    greek_chainmap = ChainMap(GREEK_LOWER, GREEK_UPPER)
    for item in pycode_as_deque:
        if isinstance(item, deque):
            new_item = swap_for_greek(item)
            swapped_deque.append(new_item)
        elif "_" in str(item):
            components = str(item).split("_")
            swapped_components = [
                dict_get(greek_chainmap, component) for component in components
            ]
            new_item = "_".join(swapped_components)
            swapped_deque.append(new_item)
        else:
            new_item = dict_get(greek_chainmap, item)
            swapped_deque.append(new_item)
    return swapped_deque


def test_for_long_var_strs(elem: Any) -> bool:
    """
    Returns True if 'elem' is a variable string that has more than one character
    in it's "top-level" name (as opposed to it's subscript).
    False, otherwise.

    e.g. elem = "Rate_annual" -> True
         elem = "x_rake_red" -> False
         elem = "AB_x_y" -> True
         elem = "category_x" -> True
         elem = "x" -> False
         elem = "xy" -> True
    """
    if not isinstance(elem, str):
        return False
    if "\\" in elem or "{" in elem or "}" in elem:
        return False
    components = elem.replace("'", "").split("_")
    if len(components) != 1:
        top_level, *_remainders = components
        if len(top_level) == 1:
            return False
        else:
            return True
    if len(components[0]) == 1:
        return False
    return True


def swap_long_var_strs(pycode_as_deque: deque) -> deque:
    """
    Returns a new deque that represents 'pycode_as_deque' but
    with all long variable names "escaped" so that they do not 
    render as italic variables but rather upright text. 

    ***Must be just before swap_subscripts in stack.***
    """
    swapped_deque = deque([])
    begin = "\\mathrm{"
    end = "}"
    for item in pycode_as_deque:
        if isinstance(item, deque):
            new_item = swap_long_var_strs(item)
            swapped_deque.append(new_item)
        elif test_for_long_var_strs(item) and not is_number(str(item)):
            try:
                top_level, remainder = str(item).split("_", 1)
                new_item = begin + top_level + end + "_" + remainder
                swapped_deque.append(new_item)
            except:
                new_item = begin + item + end
                swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_prime_notation(d: deque) -> deque:
    """
    Returns a deque representing 'd' with all elements
    with  "_prime" substrings replaced with "'".
    """
    swapped_deque = deque([])
    for item in d:
        if isinstance(item, deque):
            new_item = swap_prime_notation(item)
            swapped_deque.append(new_item)
        elif isinstance(item, str):
            new_item = item.replace("_prime", "'")
            swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_values(pycode_as_deque: deque, tex_results: dict) -> deque:
    """
    Returns a the 'pycode_as_deque' with any symbolic terms swapped out for their corresponding
    values.
    """
    outgoing = deque([])
    for item in pycode_as_deque:
        swapped_value = ""
        if isinstance(item, deque):
            outgoing.append(swap_values(item, tex_results))
        else:
            swapped_value = dict_get(tex_results, item)
            if isinstance(swapped_value, str) and swapped_value != item:
                swapped_value = format_strings(swapped_value, comment=False)
            outgoing.append(swapped_value)
    return outgoing


def test_for_function_special_case(d: deque) -> bool:
    """
    Returns True if 'd' qualifies for a typical function that should have 
    some form of function brackets around it.
    """
    if (
        len(d) == 2
        and (isinstance(d[0], str) and re.match(r"^[A-Za-z0-9_]+$", d[0]))
        and (isinstance(d[1], str) and re.match(r"^[A-Za-z0-9_]+$", d[1]))
    ):
        return True
    elif (isinstance(d[0], str) and re.match(r"^[A-Za-z0-9_]+$", d[0])) and isinstance(
        d[1], deque
    ):
        return True
    else:
        return False


def test_for_unary(d: deque) -> bool:
    """
    Returns True if 'd' represents a unary expression, e.g. -1.
    False otherwise.
    """
    ops = "+ -".split()
    if len(d) == 2 and d[0] in ops:
        return True
    return False


def test_for_typ_arithmetic(d: deque) -> bool:
    """
    Returns True if 'd' represents a deque created to store lower-precedent
    arithmetic. Returns False otherwise.
    """
    operators = "+ - * ** / // % , < > >= <= == !=".split()
    any_op = any(elem for elem in d if elem in operators)
    return any_op and not test_for_unary(d)


def get_function_name(d: deque) -> str:
    """
    Returns the function name if 'd' represents a deque containing a function
    name (both typical case and special case).
    """
    if test_for_function_special_case(d):
        return d[0]
    elif (isinstance(d[0], str) and d[0].isidentifier()) and (
        isinstance(d[1], deque) or d[1] == "\\left("
    ):
        return d[0]
    else:
        return ""


def insert_unary_parentheses(d: deque) -> deque:
    """
    Returns a deque representing 'd' with parentheses inserted
    appropriately for unary brackets
    """
    lpar = "\\left("
    rpar = "\\right)"
    swapped_deque = deque([])
    swapped_deque.append(lpar)
    for elem in d:
        swapped_deque.append(elem)
    swapped_deque.append(rpar)
    return swapped_deque


def test_for_fraction_exception(item: Any, next_item: Any) -> bool:
    """
    Returns True if a combination 'item' and 'next_item' appear to indicate
    a fraction in the symbolic deque. False otherwise.
    
    e.g. item=deque([...]), next_item="/" -> True
         item="/", next_item=deque -> True
         False otherwise
    """
    if isinstance(item, deque) and next_item == "/":
        return True
    elif item == "/" and isinstance(next_item, deque):
        return True
    return False


def insert_function_parentheses(d: deque) -> deque:
    """
    Returns a deque representing 'd' with parentheses inserted
    appropriately for functions.
    """
    lpar = "\\left("
    rpar = "\\right)"
    swapped_deque = deque([])
    last = len(d) - 1
    exclude = ["sqrt", "log", "ceil", "floor"]
    for idx, item in enumerate(d):
        if idx == last == 1:
            swapped_deque.append(lpar)
            swapped_deque.append(item)
            swapped_deque.append(rpar)
        elif idx == 1:
            swapped_deque.append(lpar)
            swapped_deque.append(item)
        elif idx == last:
            swapped_deque.append(item)
            swapped_deque.append(rpar)
        else:
            swapped_deque.append(item)
    return swapped_deque


def insert_arithmetic_parentheses(d: deque) -> deque:
    """
    Returns a deque representing 'd' with parentheses inserted
    appropriately for arithmetical brackets.
    """
    lpar = "\\left("
    rpar = "\\right)"
    swapped_deque = deque([])
    last = len(d) - 1
    exp_check = False
    if last > 1:
        exp_check = d[1] == "**"  # Don't double up parenth on exponents
    for idx, item in enumerate(d):
        if idx == 0 and not exp_check:
            swapped_deque.append(lpar)
            swapped_deque.append(item)
        elif idx == last and not exp_check:
            swapped_deque.append(item)
            swapped_deque.append(rpar)
        else:
            swapped_deque.append(item)
    return swapped_deque


def insert_parentheses(pycode_as_deque: deque) -> deque:
    """
    Returns a deque representing 'pycode_as_deque' but with appropriate
    parentheses inserted.
    """
    swapped_deque = deque([])
    peekable_deque = more_itertools.peekable(pycode_as_deque)
    lpar = "\\left("
    prev_item = None
    func_exclude = ["sqrt", "quad", "integrate"]
    skip_fraction_token = False
    for item in peekable_deque:
        # breakpoint()
        next_item = peekable_deque.peek(False)
        if isinstance(item, deque):
            poss_func_name = get_function_name(item)
            typ_arithmetic = test_for_typ_arithmetic(item)
            if poss_func_name:
                if test_for_fraction_exception(item, next_item):
                    skip_fraction_token = True
                if not poss_func_name in func_exclude:
                    item = insert_function_parentheses(item)
                new_item = insert_parentheses(item)
                swapped_deque.append(new_item)

            elif typ_arithmetic and not prev_item == lpar and not skip_fraction_token:
                if test_for_fraction_exception(item, next_item):
                    skip_fraction_token = True
                    new_item = insert_parentheses(item)
                    swapped_deque.append(new_item)
                else:
                    if (
                        prev_item not in func_exclude
                        and not test_for_nested_deque(item)
                        and next_item != "**"
                    ):  # Allow swap_superscript to handle its parenths
                        item = insert_arithmetic_parentheses(item)

                    new_item = insert_parentheses(item)
                    swapped_deque.append(new_item)

            elif test_for_unary(item):
                item = insert_unary_parentheses(item)
                new_item = insert_parentheses(item)
                swapped_deque.append(new_item)
            else:
                if skip_fraction_token and prev_item == "/":
                    skip_fraction_token = False
                new_item = insert_parentheses(item)
                swapped_deque.append(new_item)
        else:
            if item == "/":
                skip_fraction_token = True
            elif skip_fraction_token and prev_item == "/":
                skip_fraction_token = False
            swapped_deque.append(item)
        prev_item = item
    return swapped_deque


def test_for_nested_deque(d: deque) -> bool:
    """
    Returns true if 'd' has a deque as its first item.
    False otherwise
    """
    return next(isinstance(i, deque) for i in d)


def swap_dec_sep(d: deque, dec_sep: str) -> deque:
    """
    Returns 'd' with numerical elements with the "." decimal separator,
    replaced with 'dec_sep'.
    """
    swapped_deque = deque([])
    for item in d:
        # if is_number(item):
        item = item.replace(".", dec_sep)
        swapped_deque.append(item)

        # else:
        #     swapped_deque.append(item)
    return swapped_deque
