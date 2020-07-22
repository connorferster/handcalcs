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

from collections import deque
import copy
from dataclasses import dataclass
from functools import singledispatch
import importlib
import inspect
import itertools
import math
import os
import pathlib
import re
from typing import Any, Union, Optional, Tuple, List
import pyparsing as pp

# TODO: Provide better formatting for inequality checks and bools

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

    # Test
    def __repr__(self):
        return str(
            "CalcCell(\n" + f"source=\n{self.source}\n" + f"lines=\n{self.lines}\n"
        )


@dataclass
class ShortCalcCell:
    source: str
    calculated_results: dict
    precision: int
    lines: deque
    latex_code: str

    # Test
    def __repr__(self):
        return str(
            "ShortCalcCell(\n" + f"source=\n{self.source}\n" + f"lines=\n{self.lines}\n"
        )


@dataclass
class SymbolicCell:
    source: str
    calculated_results: dict
    precision: int
    lines: deque
    latex_code: str

    # Test
    def __repr__(self):
        return str(
            "CalcCell(\n" + f"source=\n{self.source}\n" + f"lines=\n{self.lines}\n"
        )


@dataclass
class ParameterCell:
    source: str
    calculated_results: dict
    lines: deque
    precision: int
    cols: int
    latex_code: str
    # Test
    def __repr__(self):
        return str(
            "ParametersCell(\n"
            + f"source=\n{self.source}\n"
            + f"lines=\n{self.lines}\n"
        )


@dataclass
class LongCalcCell:
    source: str
    calculated_results: dict
    lines: deque
    precision: int
    latex_code: str
    # Test
    def __repr__(self):
        return str(
            "LongCalcCell(\n" + f"source=\n{self.source}\n" + f"lines=\n{self.lines}\n"
        )


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


# The renderer class ("output" class)
class LatexRenderer:
    def __init__(self, python_code_str: str, results: dict):
        self.source = python_code_str
        self.results = results
        self.precision = 3

    # Test
    def set_precision(self, n=3):
        """Sets the precision (number of decimal places) in all
        latex printed values. Default = 3"""
        self.precision = n

    def render(self):
        return latex(self.source, self.results, self.precision)


# Pure functions that do all the work
def latex(raw_python_source: str, calculated_results: dict, precision: int = 3) -> str:
    """
    Returns the Python source as a string that has been converted into latex code.
    """
    source = raw_python_source
    cell = categorize_raw_cell(source, calculated_results)
    cell = categorize_lines(cell)
    cell = convert_cell(cell)
    cell = format_cell(cell)
    return cell.latex_code


def categorize_raw_cell(
    raw_source: str, calculated_results: dict, precision: int = 3
) -> Union[ParameterCell, CalcCell]:
    """
    Return a "Cell" type depending on the source of the cell.
    """
    raw_source = raw_source.strip()
    if test_for_parameter_cell(raw_source):
        comment_tag_removed = strip_cell_code(raw_source)
        cell = ParameterCell(
            source=comment_tag_removed,
            calculated_results=calculated_results,
            lines=deque([]),
            precision=precision,
            cols=3,
            latex_code="",
        )

    elif test_for_long_cell(raw_source):
        comment_tag_removed = strip_cell_code(raw_source)
        cell = LongCalcCell(
            source=comment_tag_removed,
            calculated_results=calculated_results,
            lines=deque([]),
            precision=precision,
            latex_code="",
        )

    elif test_for_short_cell(raw_source):
        comment_tag_removed = strip_cell_code(raw_source)
        cell = ShortCalcCell(
            source=comment_tag_removed,
            calculated_results=calculated_results,
            lines=deque([]),
            precision=precision,
            latex_code="",
        )

    # Test: a symbolic calc
    elif test_for_symbolic_cell(raw_source):
        comment_tag_removed = strip_cell_code(raw_source)
        cell = SymbolicCell(
            source=comment_tag_removed,
            calculated_results=calculated_results,
            lines=deque([]),
            precision=precision,
            latex_code="",
        )

    else:
        cell = CalcCell(
            source=raw_source,
            calculated_results=calculated_results,
            precision=precision,
            lines=deque([]),
            latex_code="",
        )
    return cell


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
            else:
                categorized_line = LongCalcLine(code_reader(line), comment, "")
            return categorized_line
        elif override == "symbolic":
            categorized_line = SymbolicLine(code_reader(line), comment, "")
            return categorized_line
        elif override == "short":
            categorized_line = CalcLine(code_reader(line), comment, "")
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

    elif ":" in line and ("if" in line or "else" in line):
        (
            condition,
            condition_type,
            expression,
            raw_condition,
            raw_expression,
        ) = split_conditional(line, calculated_results)
        categorized_line = ConditionalLine(
            condition=condition,
            condition_type=condition_type,
            expressions=expression,
            raw_condition=raw_condition,
            raw_expression=raw_expression.strip(),
            true_condition=deque([]),
            true_expressions=deque([]),
            comment=comment,
            latex="",
        )

    elif "=" in line:
        categorized_line = CalcLine(code_reader(line), comment, "")

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
    resulting_value = calculated_results.get(parameter_name, parameter_name)
    line_object.line.append(deque(["=", resulting_value]))
    return line_object


@add_result_values_to_line.register(LongCalcLine)
def results_for_longcalcline(line_object, calculated_results):
    parameter_name = line_object.line[0]
    resulting_value = calculated_results.get(parameter_name, parameter_name)
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
    line.line = swap_symbolic_calcs(line.line)
    return line


@convert_line.register(SymbolicLine)
def convert_symbolic_line(line, calculated_results):
    line.line = swap_symbolic_calcs(line.line)
    return line


@convert_line.register(BlankLine)
def convert_blank(line, calculated_results):
    return line


@singledispatch
def format_cell(
    cell_object: Union[ParameterCell, LongCalcCell, CalcCell, SymbolicCell]
) -> Union[ParameterCell, LongCalcCell, CalcCell, SymbolicCell]:
    raise TypeError(
        f"Cell type {type(cell_object)} has not yet been implemented in format_cell()."
    )


@format_cell.register(ParameterCell)
def parameters_cell(cell: ParameterCell):
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
    line_break = "\\\\\n"
    cycle_cols = itertools.cycle(range(1, cols + 1))
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision)
        latex_param = line.latex
        if isinstance(line, BlankLine):
            continue
        current_col = next(cycle_cols)
        if current_col % (cols - 1) == 0:
            line.latex = "&" + latex_param.replace("=", "&=")
        elif current_col % cols == 0:
            line.latex = "&" + latex_param.replace("=", "&=") + line_break
        else:
            line.latex = latex_param.replace("=", "&=")

    latex_block = " ".join(
        [line.latex for line in cell.lines if not isinstance(line, BlankLine)]
    ).rstrip()  # .rstrip(): Hack to solve another problem of empty lines in {aligned} environment
    cell.latex_code = "\n".join([opener, begin, latex_block, end, closer])
    return cell


@format_cell.register(CalcCell)
def format_calc_cell(cell: CalcCell) -> str:
    line_break = "\\\\[10pt]\n"
    precision = cell.precision
    incoming = deque([])
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision)
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
def format_shortcalc_cell(cell: ShortCalcCell) -> str:
    line_break = "\\\\[10pt]\n"
    precision = cell.precision
    incoming = deque([])
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision)
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
def format_longcalc_cell(cell: LongCalcCell) -> str:
    line_break = "\\\\[10pt]\n"
    precision = cell.precision
    incoming = deque([])
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision)
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
def format_symbolic_cell(cell: SymbolicCell) -> str:
    line_break = "\\\\[10pt]\n"
    precision = cell.precision
    incoming = deque([])
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision)
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
    line: Union[CalcLine, ConditionalLine, ParameterLine], precision: int
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
def round_and_render_calc(line: CalcLine, precision: int) -> CalcLine:
    rounded_line = round_and_render(line.line, precision)
    line.line = rounded_line
    line.latex = " ".join(rounded_line)
    return line


@round_and_render_line_objects_to_latex.register(LongCalcLine)
def round_and_render_calc(line: LongCalcLine, precision: int) -> LongCalcLine:
    rounded_line = round_and_render(line.line, precision)
    line.line = rounded_line
    line.latex = " ".join(rounded_line)
    return line


@round_and_render_line_objects_to_latex.register(ParameterLine)
def round_and_render_parameter(line: ParameterLine, precision: int) -> ParameterLine:
    rounded_line = round_and_render(line.line, precision)
    line.line = rounded_line
    line.latex = " ".join(rounded_line)
    return line


@round_and_render_line_objects_to_latex.register(ConditionalLine)
def round_and_render_conditional(
    line: ConditionalLine, precision: int
) -> ConditionalLine:
    line_break = "\\\\\n"
    outgoing = deque([])
    line.true_condition = round_and_render(line.true_condition, precision)
    for (
        expr
    ) in line.true_expressions:  # Each 'expr' item is a CalcLine or other line type
        outgoing.append(round_and_render_line_objects_to_latex(expr, precision))
    line.true_expressions = outgoing
    line.latex = line_break.join([calc_line.latex for calc_line in outgoing])
    return line


@round_and_render_line_objects_to_latex.register(SymbolicLine)
def round_and_render_symbolic(line: SymbolicLine, precision: int) -> SymbolicLine:
    rounded_line = round_and_render(line.line, precision)
    line.line = rounded_line
    line.latex = " ".join(rounded_line)
    return line


@round_and_render_line_objects_to_latex.register(BlankLine)
def round_and_render_blank(line, precision):
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
        line_break = "\\\\\n"

        outgoing = deque([])
        for calc_line in line.true_expressions:
            outgoing.append((format_lines(calc_line)).latex)
        latex_exprs = line_break.join(outgoing)
        line.latex = first_line + latex_exprs
        return line
    else:
        line.latex = ""
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
    replaced = line.latex.replace("=", "&=")
    comment_space = "\\;"
    comment = format_strings(line.comment, comment=True)
    line.latex = f"{replaced}{comment_space}{comment}\n"
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


def split_conditional(line: str, calculated_results):
    raw_conditional, raw_expressions = line.split(":")
    expr_deque = deque(raw_expressions.split(";"))  # handle multiple lines in cond
    try:
        cond_type, condition = raw_conditional.split(" ", 1)
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
        categorized = categorize_line(line, calculated_results)
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
    if not line.strip():
        return False
    elif "=" not in line or "if " in line or ":" in line:
        return False
    else:
        _, right_side = line.split("=")
        right_side.replace(" ", "")
        if right_side.find("(") == 0 and right_side.find(")") == (len(right_side) + 1):
            return True
        try:
            expr_as_code = code_reader(line)
            if len(expr_as_code) == 3 and expr_as_code[1] == "=":  # Param = value
                return True
            elif (  # Special check required for -ve nums
                len(expr_as_code) == 4
                and expr_as_code[1] == "="
                and expr_as_code[2] == "-"
            ):  # Param = -value
                return True
            else:
                return False
        except ValueError:
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


def split_parameter_line(line: str, calculated_results: dict) -> deque:
    """
    Return 'line' as a deque that represents the line as: 
        deque([<parameter>, "&=", <value>])
    """
    param = line.replace(" ", "").split("=")[0]
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
            except:
                rounded = item
        if not isinstance(item, (str, int)):
            try:
                rounded = round(item, precision)  # Rounding
            except:
                rounded = item
            outgoing.append(latex_repr(rounded))  # Rendering
        else:
            outgoing.append(str(item))
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
                symbolic_portion = swap_symbolic_calcs(conditional)
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


def swap_params(parameter: deque) -> deque:
    """
    Returns the python code elements in the 'parameter' deque converted
    into latex code elements in the deque. This primarily involves operating
    on the variable name.
    """
    return swap_symbolic_calcs(parameter)


def swap_calculation(calculation: deque, calc_results: dict) -> tuple:
    """Returns the python code elements in the deque converted into
    latex code elements in the deque"""
    calc_w_integrals_preswapped = swap_integrals(calculation, calc_results)
    symbolic_portion = swap_symbolic_calcs(calc_w_integrals_preswapped)
    calc_drop_decl = deque(
        list(calc_w_integrals_preswapped)[1:]
    )  # Drop the variable declaration
    numeric_portion = swap_numeric_calcs(calc_drop_decl, calc_results)
    return (symbolic_portion, numeric_portion)


def swap_symbolic_calcs(calculation: deque) -> deque:
    # remove calc_results function parameter
    symbolic_expression = copy.copy(calculation)
    flatten_deque = Flattener()
    functions_on_symbolic_expressions = [
        swap_frac_divs,
        swap_math_funcs,
        swap_py_operators,
        swap_for_greek,
        extend_subscripts,
        swap_superscripts,
        flatten_deque,
    ]
    for function in functions_on_symbolic_expressions:
        symbolic_expression = function(symbolic_expression)
    return symbolic_expression


def swap_numeric_calcs(calculation: deque, calc_results: dict) -> deque:
    numeric_expression = copy.copy(calculation)
    flatten_deque = Flattener()
    functions_on_numeric_expressions = [
        swap_frac_divs,
        swap_math_funcs,
        swap_py_operators,
        swap_values,
        swap_superscripts,
        flatten_deque,
    ]
    for function in functions_on_numeric_expressions:
        if function is swap_values:
            numeric_expression = function(numeric_expression, calc_results)
        else:
            numeric_expression = function(numeric_expression)
    return numeric_expression


def swap_integrals(calculation: deque, calc_results: dict) -> deque:
    """
    Returns 'calculation' with any function named 
    """
    swapped_deque = deque([])
    length = len(calculation)
    skip_next = False
    for index, item in enumerate(calculation):
        next_item = calculation[min(index + 1, length - 1)]
        if skip_next == True:
            skip_next = False
            continue
        if isinstance(item, deque):
            new_item = swap_integrals(item, calc_results)  # recursion!
            swapped_deque.append(new_item)
        else:
            if (
                "integrate" in str(item)
                or "quad" in str(item)
                and isinstance(next_item, deque)
            ):
                skip_next = True
                function_name = next_item[0]
                function = calc_results[function_name]
                function_source = (
                    inspect.getsource(function).split("\n")[1].replace("return", "")
                )
                variable = (
                    str(inspect.signature(function))
                    .replace("(", "")
                    .replace(")", "")
                    .replace(" ", "")
                    .split(":")[0]
                )
                source_deque = expr_parser(function_source)
                a = next_item[2]
                b = next_item[4]
                swapped_deque += deque(["\\int_{", a, "}", "^", "{", b, "}"])
                swapped_deque.append(source_deque)
                swapped_deque.append(f"\\; d{variable}")
            else:
                swapped_deque.append(item)
    return swapped_deque


class Flattener:  # Helper class
    def __init__(self):
        self.fraction = False

    def __call__(self, nested: deque):
        flattened_deque = deque([])
        for item in nested:
            if isinstance(item, str) and (
                "frac" in item or "}{" in item or "\\int" in item
            ):
                self.fraction = True
            if isinstance(item, deque):
                if self.fraction:
                    sub_deque_generator = self.flatten(item)
                    for new_item in sub_deque_generator:
                        flattened_deque.append(new_item)
                    self.fraction = False
                else:
                    sub_deque_generator = self.flatten(item)
                    for new_item in sub_deque_generator:
                        flattened_deque.append(new_item)
            else:
                sub_deque_generator = self.flatten(item)
                for new_item in sub_deque_generator:
                    flattened_deque.append(new_item)
        return flattened_deque

    def flatten(self, items: Any, omit_parentheses: bool = False) -> deque:
        """Returns elements from a deque and flattens elements from sub-deques.
        Inserts latex parentheses ( '\\left(' and '\\right)' ) where sub-deques
        used to exists, except if the reason for the sub-deque was to encapsulate
        either a fraction or an integral (then no parentheses).
        """
        if isinstance(items, str) and (
            "frac" in items or "}{" in items or "\\int" in items
        ):
            self.fraction = True
        omit_parentheses = self.fraction
        if isinstance(items, deque):
            self.fraction = False
            if not omit_parentheses:
                yield "\\left("
            for item in items:
                yield from self.flatten(item, omit_parentheses)  # recursion!
            if not omit_parentheses:
                yield "\\right)"
                self.fraction = False

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


def code_reader(pycode_as_str: str) -> deque:
    """
    Returns full line of code parsed into deque items
    """
    var_name, expression = pycode_as_str.split("=")
    var_name, expression = var_name.strip(), expression.strip()
    expression_as_deque = expr_parser(expression)
    return deque([var_name]) + deque(["=",]) + expression_as_deque


def expr_parser(expr_as_str: str) -> deque:
    """
    Returns deque (or nested deque) of the mathematical expression, 'expr_as_str', that represents
    the expression broken down into components of [<term>, <operator>, <term>, ...etc.]. If the expression
    contains parentheses, then a nested deque is started, with the expressions within the parentheses as the
    items within the nested deque.
    """
    term = pp.Word(pp.srange("[A-Za-z0-9_'\".]"), pp.srange("[A-Za-z0-9_'\".]"))
    operator = pp.Word("+-*/^%<>=~!,")
    func = pp.Word(pp.srange("[A-Za-z0-9_.]")) + pp.FollowedBy(
        pp.Word(pp.srange("[A-Za-z0-9_()]"))
    )
    string = pp.Word(pp.srange("[A-Za-z0-9'\"]"))
    group = term ^ operator ^ func ^ string
    parenth = pp.nestedExpr(content=group)
    master = group ^ parenth
    expr = pp.OneOrMore(master)
    return list_to_deque(expr.parseString(expr_as_str).asList())


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
        if isinstance(item, deque):
            new_item = extend_subscripts(item)  # recursion!
            swapped_deque.append(new_item)
        elif isinstance(item, str) and "_" in item and not "\\int" in item:
            new_item = ""
            for char in item:
                if char == "_":
                    new_item += char
                    new_item += "{"
                else:
                    new_item += char
            num_braces = new_item.count("{")
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
    ops = r"\frac"
    close_bracket_token = False
    for index, item in enumerate(code):
        next_idx = min(index + 1, length - 1)
        if code[next_idx] is "/" and isinstance(item, deque):
            new_item = f"{ops}{a}"
            swapped_deque.append(new_item)
            swapped_deque.append(swap_frac_divs(item))  # recursion!
        elif code[next_idx] is "/" and not isinstance(item, deque):
            new_item = f"{ops}{a}"
            swapped_deque.append(new_item)
            swapped_deque.append(item)
        elif item is "/":
            swapped_deque.append(f"{b}{a}")
            close_bracket_token = True
        elif close_bracket_token:
            close_bracket_token = False
            if isinstance(item, deque):
                swapped_deque.append(swap_frac_divs(item))
            else:
                swapped_deque.append(item)
            new_item = f"{b}"
            swapped_deque.append(new_item)
        elif isinstance(item, deque):
            new_item = swap_frac_divs(item)  # recursion!
            swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_math_funcs(pycode_as_deque: deque) -> deque:
    """
    Swaps out math operator functions builtin to the math library for latex functions.
    e.g. python: sin(3*x), becomes: \\sin(3*x)
    if the function name is not in the list of recognized Latex names, then a custom
    operator name is declared with "\\operatorname{", "}" appropriately appended.
    """
    latex_math_funcs = {
        "sin": "\\sin{",
        "cos": "\\cos{",
        "tan": "\\tan{",
        "sqrt": "\\sqrt{",
        "log": "\\log{",
        "exp": "\\exp{",
        "sinh": "\\sinh{",
        "tanh": "\\tanh{",
        "cosh": "\\cosh{",
        "asin": "\\arcsin{",
        "acos": "\\arccos{",
        "atan": "\\arctan{",
        "atan2": "\\arctan{",
        "asinh": "\\arcsinh{",
        "acosh": "\\arccosh{",
        "atanh": "\\arctanh{",
    }
    swapped_deque = deque([])
    length = len(pycode_as_deque)
    close_bracket_token = False
    a = "{"
    b = "}"
    for index, item in enumerate(pycode_as_deque):
        next_idx = min(index + 1, length - 1)
        next_item = pycode_as_deque[next_idx]
        if isinstance(item, deque):
            new_item = swap_math_funcs(item)  # recursion!
            swapped_deque.append(new_item)
            if close_bracket_token:
                swapped_deque.append(b)
                close_bracket_token = False
        elif (
            isinstance(next_item, deque)
            and isinstance(item, str)
            and re.match(r"^[A-Za-z_]+$", item)
            and item not in latex_math_funcs
        ):
            ops = "\\operatorname"
            new_item = f"{ops}{a}{item}{b}"
            swapped_deque.append(new_item)
        elif isinstance(next_item, deque) and item in latex_math_funcs:
            swapped_deque.append(latex_math_funcs.get(item, item))
            close_bracket_token = True

        else:
            swapped_deque.append(item)
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
            if item is "*":
                swapped_deque.append("\\cdot")
            elif item is "%":
                swapped_deque.append("\\bmod")
            else:
                swapped_deque.append(item)
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
            new_item = swap_superscripts(item)  # recursion!
            pycode_with_supers.append(new_item)
        elif not isinstance(next_item, deque) and "**" in str(next_item):
            pycode_with_supers.append(l_par)
            pycode_with_supers.append(item)
            pycode_with_supers.append(r_par)
        elif not isinstance(item, deque) and "**" in str(item):
            new_item = f"{ops}{a}"
            pycode_with_supers.append(new_item)
            close_bracket_token = True
        elif (
            close_bracket_token
            and not isinstance(prev_item, deque)
            and "**" in str(prev_item)
        ):
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
    # "eta" and "psi" need to be last on the list b/c they are substrings
    # of "theta" and "epsilon"
    greeks = [
        "alpha",
        "beta",
        "gamma",
        "delta",
        "epsilon",
        "zeta",
        "theta",
        "iota",
        "kappa",
        "lamb",
        "mu",
        "nu",
        "xi",
        "omicron",
        "pi",
        "rho",
        "sigma",
        "tau",
        "upsilon",
        "phi",
        "chi",
        "omega",
    ]
    greek_exceptions = ["eta", "psi"]
    pycode_with_greek = deque([])
    for item in pycode_as_deque:
        if isinstance(item, deque):
            new_item = swap_for_greek(item)  # recursion!
            pycode_with_greek.append(new_item)
        elif isinstance(item, str):
            # This code is intended to swap out the greeks but to also swap
            # out greeks in subscripts or sub-sub-scripts, etc.
            for greek in greeks:
                if (greek in item or greek.capitalize() in item) and (
                    greek not in greek_exceptions
                ):
                    item = item.replace(greek, "\\" + greek)
                    item = item.replace(greek.capitalize(), "\\" + greek.capitalize())
                    item = item.replace("lamb", "lambda")
                    item = item.replace("Lamb", "Lambda")
            for greek in greek_exceptions:
                greek_match = greek in item or greek.capitalize() in item
                greek_startswith = item.startswith(greek) or item.startswith(
                    greek.capitalize()
                )
                greek_submatch = ("_" + greek) in item or (
                    "_" + greek.capitalize()
                ) in item
                if greek_match and greek_startswith:
                    item = item.replace(greek, "\\" + greek, 1)
                    item = item.replace(
                        greek.capitalize(), "\\" + greek.capitalize(), 1
                    )
                if greek_match and greek_submatch:
                    item = item.replace("_" + greek, "_" + "\\" + greek)
                    item = item.replace(
                        "_" + greek.capitalize(), "_" + "\\" + greek.capitalize()
                    )

            pycode_with_greek.append(item)
        else:
            pycode_with_greek.append(item)
    return pycode_with_greek


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
            swapped_value = tex_results.get(item, item)
            if isinstance(swapped_value, str) and swapped_value != item:
                swapped_value = format_strings(swapped_value, comment=False)
            outgoing.append(swapped_value)
    return outgoing


## Basic Usage 2: Decorator


# def handcalc(left: str = "", right: str = "", jupyter_display: bool = False):
#     # @wraps(func)
#     def handcalc_decorator(func):
#         def wrapper(*args, **kwargs):
#             func_source = inspect.getsource(func)
#             cell_source = func_source_to_cell(func_source)
#             calculated_results = func(*args, **kwargs)  # Func must use `return locals()`
#             if not isinstance(calculated_results, dict):
#                 raise ValueError(
#                     f"Return value of decorated function should be locals(),",
#                     " not {calculated_results}",
#                 )
#             renderer = LatexRenderer(cell_source, calculated_results)
#             latex_code = renderer.render()
#             if jupyter_display:
#                 try:
#                     from IPython.display import Latex, display
#                 except ModuleNotFoundError:
#                     ModuleNotFoundError("jupyter_display option requires IPython.display to be installed.")
#                 display(Latex(latex_code))
#                 return calculated_results
#             latex_code = latex_code.replace("\\[", "", 1).replace("\\]", "")
#             return (left + latex_code + right, calculated_results)
#         return wrapper
#     return handcalc_decorator


# def func_source_to_cell(source: str):
#     """
#     Returns a string that represents `source` but with no signature, doc string,
#     or return statement.

#     `source` is a string representing a function's complete source code.
#     """
#     source_lines = source.split("\n")
#     acc = []
#     for line in source_lines:
#         doc_string = False
#         if not doc_string and '"""' in line:
#             doc_string = True
#             continue
#         elif doc_string and '"""' in line:
#             doc_string = False
#             continue
#         if (
#             "def" not in line
#             and not doc_string
#             and "return" not in line
#             and "@" not in line
#         ):
#             acc.append(line)
#     return "\n".join(acc)
