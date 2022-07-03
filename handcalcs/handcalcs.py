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

from handcalcs.constants import GREEK_UPPER, GREEK_LOWER
from handcalcs import global_config
from handcalcs.integrations import DimensionalityError

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
class NumericCalcLine:
    line: deque
    comment: str
    latex: str


@dataclass
class IntertextLine:
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
    precision: Optional[int]
    scientific_notation: Optional[bool]
    lines: deque
    latex_code: str


@dataclass
class ShortCalcCell:
    source: str
    calculated_results: dict
    precision: Optional[int]
    scientific_notation: Optional[bool]
    lines: deque
    latex_code: str


@dataclass
class SymbolicCell:
    source: str
    calculated_results: dict
    precision: Optional[int]
    scientific_notation: Optional[bool]
    lines: deque
    latex_code: str


@dataclass
class ParameterCell:
    source: str
    calculated_results: dict
    lines: deque
    precision: Optional[int]
    scientific_notation: Optional[bool]
    # cols: int
    latex_code: str


@dataclass
class LongCalcCell:
    source: str
    calculated_results: dict
    lines: deque
    precision: Optional[int]
    scientific_notation: Optional[bool]
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
    # dec_sep = "."

    def __init__(self, python_code_str: str, results: dict, line_args: dict):
        self.source = python_code_str
        self.results = results
        self.override_precision = line_args["precision"]
        self.override_scientific_notation = line_args['sci_not']
        self.override_commands = line_args["override"]

    def render(self, config_options: dict = global_config._config):
        return latex(
            raw_python_source=self.source,
            calculated_results=self.results,
            override_commands=self.override_commands,
            config_options=config_options,
            cell_precision=self.override_precision,
            cell_notation=self.override_scientific_notation,
        )


# Pure functions that do all the work
def latex(
    raw_python_source: str,
    calculated_results: dict,
    override_commands: str,
    config_options: dict,
    cell_precision: Optional[int] = None,
    cell_notation: Optional[bool] = None,
) -> str:
    """
    Returns the Python source as a string that has been converted into latex code.
    """
    # decimal_separator = config_options.get("decimal_separator")
    # latex_block_start = config_options.get("latex_block_start")
    # latex_block_end = config_options.get("latex_block_end")
    # latex_math_environment = config_options.get("latex_math_environment")
    # use_sci_notation = config_options.get("use_sci_notation")
    # display_precision = config_options.get("display_precision")
    # underscore_subscripts = config_options.get("underscore_subscripts")
    # zero_tolerance = config_options.get("zero_tolerance")
    # greek_exclusions = config_options.get("greek_exclusions")
    # param_columns = config_options.get("param_columns")

    source = raw_python_source

    cell = categorize_raw_cell(
        source, 
        calculated_results, 
        override_commands,
        cell_precision,
        cell_notation,
    )
    cell = categorize_lines(cell)
    cell = convert_cell(
        cell,
        **config_options,
        )
    cell = format_cell(
        cell,
        **config_options,
        # dec_sep
    )
    return cell.latex_code


def categorize_raw_cell(
    raw_source: str, 
    calculated_results: dict, 
    override_commands: str,
    cell_precision: Optional[int] = None,
    cell_notation: Optional[bool] = None,
) -> Union[ParameterCell, CalcCell]:
    """
    Return a "Cell" type depending on the source code of the cell.
    """
    if override_commands:
        if override_commands == "params":
            return create_param_cell(raw_source, calculated_results, cell_precision, cell_notation)
        elif override_commands == "long":
            return create_long_cell(raw_source, calculated_results, cell_precision, cell_notation)
        elif override_commands == "short":
            return create_short_cell(raw_source, calculated_results, cell_precision, cell_notation)
        elif override_commands == "symbolic":
            return create_symbolic_cell(raw_source, calculated_results, cell_precision, cell_notation)

    if test_for_parameter_cell(raw_source):
        return create_param_cell(raw_source, calculated_results, cell_precision, cell_notation)
    elif test_for_long_cell(raw_source):
        return create_long_cell(raw_source, calculated_results, cell_precision, cell_notation)
    elif test_for_short_cell(raw_source):
        return create_short_cell(raw_source, calculated_results, cell_precision, cell_notation)
    elif test_for_symbolic_cell(raw_source):
        return create_symbolic_cell(raw_source, calculated_results, cell_precision, cell_notation)
    else:
        return create_calc_cell(raw_source, calculated_results, cell_precision, cell_notation)


def strip_cell_code(raw_source: str) -> str:
    """
    Return 'raw_source' with the "cell code" removed.
    A "cell code" is a first-line comment in the cell for the
    purpose of categorizing an IPython cell as something other
    than a CalcCell.
    """
    split_lines = deque(raw_source.split("\n"))
    first_line = split_lines[0]
    if first_line.startswith("#") and not first_line.startswith(
        "##"
    ):  ## for intertext line
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
    incoming = cell.source.rstrip().split("\n")
    outgoing = deque([])
    calculated_results = cell.calculated_results
    cell_override = ""
    for line in incoming:
        if isinstance(cell, ParameterCell):
            cell_override = "parameter"
        elif isinstance(cell, LongCalcCell):
            cell_override = "long"
        elif isinstance(cell, SymbolicCell):
            cell_override = "symbolic"
        categorized = categorize_line(line, calculated_results, cell_override)
        categorized_w_result_appended = add_result_values_to_line(
            categorized, calculated_results
        )
        outgoing.append(categorized_w_result_appended)
    cell.lines = outgoing
    return cell


def categorize_line(
    line: str, calculated_results: dict, cell_override: str = ""
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
    if test_for_blank_line(line):
        return BlankLine(line, "", "")

    if test_for_intertext_line(line):
        return IntertextLine(line, "", "")

    if line.startswith("#"):
        return BlankLine(line, "", "")

    try:
        line, comment = line.split("#", 1)
    except ValueError:
        comment = ""

    # Override behaviour
    categorized_line = None
    if cell_override == "parameter":
        if test_for_conditional_line(line):
            categorized_line = create_conditional_line(
                line, calculated_results, cell_override, comment
            )
        else:
            categorized_line = ParameterLine(
                split_parameter_line(line, calculated_results), comment, ""
            )
        return categorized_line

    elif cell_override == "long":
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
                line, calculated_results, cell_override, comment
            )
        elif test_for_numeric_line(
            deque(
                list(expr_parser(line))[1:]
            )  # Leave off the declared variable, e.g. _x_ = ...
        ):
            categorized_line = NumericCalcLine(expr_parser(line), comment, "")

        else:
            categorized_line = LongCalcLine(
                expr_parser(line), comment, ""
            )  # code_reader
        return categorized_line

    elif cell_override == "symbolic":
        if test_for_conditional_line(
            line
        ):  # A conditional line can exist in a symbolic cell, too
            categorized_line = create_conditional_line(
                line, calculated_results, cell_override, comment
            )
        else:
            categorized_line = SymbolicLine(
                expr_parser(line), comment, ""
            )  # code_reader
        return categorized_line

    elif cell_override == "short":        
        if test_for_numeric_line(
            deque(list(line)[1:])  # Leave off the declared variable
        ):
            categorized_line = NumericCalcLine(expr_parser(line), comment, "")
        else:
            categorized_line = CalcLine(
                expr_parser(line), comment, ""
            )  # code_reader

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
            line, calculated_results, cell_override, comment
        )

    elif test_for_numeric_line(
        deque(list(expr_parser(line))[1:])  # Leave off the declared variable
    ):
        categorized_line = NumericCalcLine(expr_parser(line), comment, "")

    elif "=" in line:
        categorized_line = CalcLine(expr_parser(line), comment, "")  # code_reader

    elif len(expr_parser(line)) == 1:
        categorized_line = ParameterLine(
            split_parameter_line(line, calculated_results), comment, ""
        )

    else:
        # TODO: Raise this error in a test
        raise ValueError(
            f"Line: {line} is not recognized for rendering.\n"
            "Lines must either:\n"
            "\t * Be the name of a previously assigned single variable\n"
            "\t * Be an arithmetic variable assignment (i.e. calculation that uses '=' in the line)\n"
            "\t * Be a conditional arithmetic assignment (i.e. uses 'if', 'elif', or 'else', each on a single line)"
        )
    return categorized_line


def create_param_cell(
    raw_source: str, calculated_result: dict, cell_precision: Optional[int] = None, cell_notation: Optional[bool] = None
) -> ParameterCell:
    """
    Returns a ParameterCell.
    """
    comment_tag_removed = strip_cell_code(raw_source)
    cell = ParameterCell(
        source=comment_tag_removed,
        calculated_results=calculated_result,
        precision=cell_precision,
        scientific_notation=cell_notation,
        lines=deque([]),
        latex_code="",
    )
    return cell


def create_long_cell(
    raw_source: str, calculated_result: dict,  cell_precision: Optional[int] = None, cell_notation: Optional[bool] = None
) -> LongCalcCell:
    """
    Returns a LongCalcCell.
    """
    comment_tag_removed = strip_cell_code(raw_source)
    cell = LongCalcCell(
        source=comment_tag_removed,
        calculated_results=calculated_result,
        precision=cell_precision,
        scientific_notation=cell_notation,
        lines=deque([]),
        latex_code="",
    )
    return cell


def create_short_cell(
    raw_source: str, calculated_result: dict,  cell_precision: Optional[int] = None, cell_notation: Optional[bool] = None
) -> ShortCalcCell:
    """
    Returns a ShortCell
    """
    comment_tag_removed = strip_cell_code(raw_source)
    cell = ShortCalcCell(
        source=comment_tag_removed,
        calculated_results=calculated_result,
        precision=cell_precision,
        scientific_notation=cell_notation,
        lines=deque([]),
        latex_code="",
    )
    return cell


def create_symbolic_cell(
    raw_source: str, calculated_result: dict,  cell_precision: Optional[int] = None, cell_notation: Optional[bool] = None,
) -> SymbolicCell:
    """
    Returns a SymbolicCell
    """
    comment_tag_removed = strip_cell_code(raw_source)
    cell = SymbolicCell(
        source=comment_tag_removed,
        calculated_results=calculated_result,
        precision=cell_precision,
        scientific_notation=cell_notation,
        lines=deque([]),
        latex_code="",
    )
    return cell


def create_calc_cell(
    raw_source: str, calculated_result: dict,  cell_precision: Optional[int] = None, cell_notation: Optional[bool] = None
) -> CalcCell:
    """
    Returns a CalcCell
    """
    cell = CalcCell(
        source=raw_source,
        calculated_results=calculated_result,
        precision=cell_precision,
        scientific_notation=cell_notation,
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


@add_result_values_to_line.register(NumericCalcLine)
def results_for_numericcalcline(line_object, calculated_results):
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


@add_result_values_to_line.register(IntertextLine)
def results_for_intertext(line_object, calculated_results):
    return line_object


@singledispatch
def convert_cell(
    cell_object,
    **config_options,
    ):
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
def convert_calc_cell(
    cell: CalcCell,
    **config_options,
    ) -> CalcCell:
    outgoing = cell.lines
    calculated_results = cell.calculated_results
    incoming = deque([])
    for line in outgoing:
        incoming.append(
            convert_line(
                line, 
                calculated_results,
                **config_options,
            )
        )
    cell.lines = incoming
    return cell


@convert_cell.register(ShortCalcCell)
def convert_calc_cell(cell: ShortCalcCell, **config_options) -> ShortCalcCell:
    outgoing = cell.lines
    calculated_results = cell.calculated_results
    incoming = deque([])
    for line in outgoing:
        incoming.append(
            convert_line(
            line,
         calculated_results,
         **config_options
        )
        )
    cell.lines = incoming
    return cell


@convert_cell.register(LongCalcCell)
def convert_longcalc_cell(cell: LongCalcCell, **config_options) -> LongCalcCell:
    outgoing = cell.lines
    calculated_results = cell.calculated_results
    incoming = deque([])
    for line in outgoing:
        incoming.append(
            convert_line(
            line,
            calculated_results,
            **config_options
        )
        )
    cell.lines = incoming
    return cell


@convert_cell.register(ParameterCell)
def convert_parameter_cell(cell: ParameterCell, **config_options) -> ParameterCell:
    outgoing = cell.lines
    calculated_results = cell.calculated_results
    incoming = deque([])
    for line in outgoing:
        incoming.append(
            convert_line(
            line, 
        calculated_results,
        **config_options
        )
        )
    cell.lines = incoming
    return cell


@convert_cell.register(SymbolicCell)
def convert_symbolic_cell(cell: SymbolicCell, **config_options) -> SymbolicCell:
    outgoing = cell.lines
    calculated_results = cell.calculated_results
    incoming = deque([])
    for line in outgoing:
        incoming.append(
            convert_line(
            line, 
        calculated_results,
        **config_options
        )
        )
    cell.lines = incoming
    return cell


@singledispatch
def convert_line(
    line_object, 
    calculated_results: dict,
    **config_options,

):
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
def convert_calc(
    line, 
    calculated_results,
    **config_options
):
    (
        *line_deque,
        result,
    ) = line.line  # Unpack deque of form [[calc_line, ...], ['=', 'result']]
    symbolic_portion, numeric_portion = swap_calculation(line_deque, calculated_results, **config_options)
    line.line = symbolic_portion + numeric_portion + result
    return line


@convert_line.register(NumericCalcLine)
def convert_numericcalc(
    line, 
calculated_results,
**config_options
):
    (
        *line_deque,
        result,
    ) = line.line  # Unpack deque of form [[calc_line, ...], ['=', 'result']]
    symbolic_portion, _ = swap_calculation(line_deque, calculated_results, **config_options)
    line.line = symbolic_portion + result
    return line


@convert_line.register(LongCalcLine)
def convert_longcalc(
    line, 
calculated_results,
**config_options
):
    (
        *line_deque,
        result,
    ) = line.line  # Unpack deque of form [[calc_line, ...], ['=', 'result']]
    symbolic_portion, numeric_portion = swap_calculation(line_deque, calculated_results, **config_options)
    line.line = symbolic_portion + numeric_portion + result
    return line


@convert_line.register(ConditionalLine)
def convert_conditional(
    line, 
calculated_results,
**config_options
):
    condition, condition_type, expressions, raw_condition = (
        line.condition,
        line.condition_type,
        line.expressions,
        line.raw_condition,
    )
    true_condition_deque = swap_conditional(
        condition, condition_type, raw_condition, calculated_results, **config_options
    )
    if true_condition_deque:
        line.true_condition = true_condition_deque
        for expression in expressions:
            line.true_expressions.append(convert_line(expression, calculated_results, **config_options))
    return line


@convert_line.register(ParameterLine)
def convert_parameter(
    line, 
calculated_results,
**config_options
):
    line.line = swap_symbolic_calcs(line.line, calculated_results, **config_options)
    return line


@convert_line.register(SymbolicLine)
def convert_symbolic_line(
    line, 
calculated_results,
**config_options
):
    line.line = swap_symbolic_calcs(line.line, calculated_results, **config_options)
    return line


@convert_line.register(IntertextLine)
def convert_intertext(
    line, 
calculated_results,
**config_options
):
    return line


@convert_line.register(BlankLine)
def convert_blank(
    line, 
calculated_results,
**config_options
):
    return line


@singledispatch
def format_cell(
    cell_object,
    **config_options
):
    raise TypeError(
        f"Cell type {type(cell_object)} has not yet been implemented in format_cell()."
    )


@format_cell.register(ParameterCell)
def format_parameters_cell(cell: ParameterCell, **config_options):
    """
    Returns the input parameters as an \\align environment with 'cols'
    number of columns.
    """
    cols = config_options['param_columns']
    precision = cell.precision or config_options["display_precision"]
    cell_notation = toggle_scientific_notation(config_options['use_scientific_notation'], cell.scientific_notation)
    opener = config_options['latex_block_start']
    begin = f"\\begin{{{config_options['math_environment_start']}}}"
    end = f"\\end{{{config_options['math_environment_end']}}}"
    closer = config_options['latex_block_end']
    line_break = f"{config_options['line_break']}\n"
    cycle_cols = itertools.cycle(range(1, cols + 1))
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision, cell_notation, **config_options)
        line = format_lines(line, **config_options)
        if isinstance(line, BlankLine):
            continue
        if isinstance(line, ConditionalLine):
            outgoing = deque([])
            for expr in line.true_expressions:
                current_col = next(cycle_cols)
                if current_col % cols == 0:
                    outgoing.append("&" + expr + line_break)
                elif current_col % cols != 1:
                    outgoing.append("&" + expr)
                else:
                    outgoing.append(expr)
            line.latex_expressions = " ".join(outgoing)
            line.latex = line.latex_condition + line.latex_expressions
        else:
            latex_param = line.latex

            current_col = next(cycle_cols)
            if current_col % cols == 0:
                line.latex = "&" + latex_param + line_break
            elif current_col % cols != 1:
                line.latex = "&" + latex_param
            else:
                line.latex = latex_param

    latex_block = " ".join(
        [line.latex for line in cell.lines if not isinstance(line, BlankLine)]
    ).rstrip()  # .rstrip(): Hack to solve another problem of empty lines in {aligned} environment
    cell.latex_code = "\n".join([opener, begin, latex_block, end, closer])
    return cell


@format_cell.register(CalcCell)
def format_calc_cell(cell: CalcCell, **config_options) -> str:
    line_break = f"{config_options['line_break']}\n"
    precision = cell.precision or config_options["display_precision"]
    cell_notation = toggle_scientific_notation(config_options['use_scientific_notation'], cell.scientific_notation)
    incoming = deque([])
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision, cell_notation, **config_options)
        line = convert_applicable_long_lines(line)
        line = format_lines(line, **config_options)
        incoming.append(line)
    cell.lines = incoming

    latex_block = line_break.join([line.latex for line in cell.lines if line.latex])
    opener = config_options['latex_block_start']
    begin = f"\\begin{{{config_options['math_environment_start']}}}"
    end = f"\\end{{{config_options['math_environment_end']}}}"
    closer = config_options['latex_block_end']
    cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
        "\n" + end, end
    )
    return cell


@format_cell.register(ShortCalcCell)
def format_shortcalc_cell(cell: ShortCalcCell, **config_options) -> str:
    incoming = deque([])
    line_break = f"{config_options['line_break']}\n"
    precision = cell.precision or config_options["display_precision"]
    cell_notation = toggle_scientific_notation(config_options['use_scientific_notation'], cell.scientific_notation)
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision, cell_notation, **config_options)
        line = format_lines(line, **config_options)
        incoming.append(line)
    cell.lines = incoming

    latex_block = line_break.join([line.latex for line in cell.lines if line.latex])
    opener = config_options['latex_block_start']
    begin = f"\\begin{{{config_options['math_environment_start']}}}"
    end = f"\\end{{{config_options['math_environment_end']}}}"
    closer = config_options['latex_block_end']
    cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
        "\n" + end, end
    )
    return cell


@format_cell.register(LongCalcCell)
def format_longcalc_cell(cell: LongCalcCell, **config_options) -> str:
    line_break = f"{config_options['line_break']}\n"
    precision = cell.precision or config_options["display_precision"]
    cell_notation = toggle_scientific_notation(config_options['use_scientific_notation'], cell.scientific_notation)
    incoming = deque([])
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision, cell_notation, **config_options)
        line = convert_applicable_long_lines(line)
        line = format_lines(line, **config_options)
        incoming.append(line)
    cell.lines = incoming

    latex_block = line_break.join([line.latex for line in cell.lines if line.latex])
    opener = config_options['latex_block_start']
    begin = f"\\begin{{{config_options['math_environment_start']}}}"
    end = f"\\end{{{config_options['math_environment_end']}}}"
    closer = config_options['latex_block_end']
    cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
        "\n" + end, end
    )
    return cell


@format_cell.register(SymbolicCell)
def format_symbolic_cell(cell: SymbolicCell, **config_options) -> str:
    line_break = f"{config_options['line_break']}\n"
    precision = cell.precision or config_options["display_precision"]
    cell_notation = toggle_scientific_notation(config_options['use_scientific_notation'], cell.scientific_notation)
    incoming = deque([])
    for line in cell.lines:
        line = round_and_render_line_objects_to_latex(line, precision, cell_notation, **config_options)
        line = format_lines(line, **config_options)
        incoming.append(line)
    cell.lines = incoming

    latex_block = line_break.join([line.latex for line in cell.lines if line.latex])
    opener = config_options['latex_block_start']
    begin = f"\\begin{{{config_options['math_environment_start']}}}"
    end = f"\\end{{{config_options['math_environment_end']}}}"
    closer = config_options['latex_block_end']
    cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
        "\n" + end, end
    )
    return cell


@singledispatch
def round_and_render_line_objects_to_latex(
    line: Union[CalcLine, ConditionalLine, ParameterLine], cell_precision: int, cell_notation: bool, **config_options
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
def round_and_render_calc(line: CalcLine, cell_precision: int, cell_notation: bool, **config_options) -> CalcLine:
    idx_line = line.line
    precision = cell_precision or config_options['display_precision']
    use_scientific_notation = toggle_scientific_notation(config_options['use_scientific_notation'], cell_notation)
    preferred_formatter = config_options['preferred_string_formatter']
    rendered_line = render_latex_str(idx_line, use_scientific_notation, precision, preferred_formatter)
    rendered_line = swap_dec_sep(rendered_line, config_options["decimal_separator"])
    line.line = rendered_line
    line.latex = " ".join(rendered_line)
    return line


@round_and_render_line_objects_to_latex.register(NumericCalcLine)
def round_and_render_numericcalc(
    line: NumericCalcLine,  cell_precision: int, cell_notation: bool, **config_options
) -> NumericCalcLine:
    idx_line = line.line
    precision = cell_precision or config_options['display_precision']
    use_scientific_notation = toggle_scientific_notation(config_options['use_scientific_notation'], cell_notation)
    preferred_formatter = config_options['preferred_string_formatter']
    rendered_line = render_latex_str(idx_line, use_scientific_notation, precision, preferred_formatter)
    rendered_line = swap_dec_sep(rendered_line, config_options["decimal_separator"])
    line.line = rendered_line
    line.latex = " ".join(rendered_line)
    return line


@round_and_render_line_objects_to_latex.register(LongCalcLine)
def round_and_render_longcalc(
    line: LongCalcLine, cell_precision: int, cell_notation: bool, **config_options
) -> LongCalcLine:
    idx_line = line.line
    precision = cell_precision or config_options['display_precision']
    use_scientific_notation = toggle_scientific_notation(config_options['use_scientific_notation'], cell_notation)
    preferred_formatter = config_options['preferred_string_formatter']
    rendered_line = render_latex_str(idx_line, use_scientific_notation, precision, preferred_formatter)
    rendered_line = swap_dec_sep(rendered_line, config_options["decimal_separator"])
    line.line = rendered_line
    line.latex = " ".join(rendered_line)
    return line


@round_and_render_line_objects_to_latex.register(ParameterLine)
def round_and_render_parameter(
    line: ParameterLine, cell_precision: int, cell_notation: bool, **config_options
) -> ParameterLine:
    idx_line = line.line
    precision = cell_precision or config_options['display_precision']
    use_scientific_notation = toggle_scientific_notation(config_options['use_scientific_notation'], cell_notation)
    preferred_formatter = config_options['preferred_string_formatter']
    rendered_line = render_latex_str(idx_line, use_scientific_notation, precision, preferred_formatter)
    rendered_line = swap_dec_sep(rendered_line, config_options["decimal_separator"])
    line.line = rendered_line
    line.latex = " ".join(rendered_line)
    return line


@round_and_render_line_objects_to_latex.register(ConditionalLine)
def round_and_render_conditional(
    line: ConditionalLine, cell_precision: int, cell_notation: bool, **config_options
) -> ConditionalLine:
    conditional_line_break = f"{config_options['line_break']}\n"
    outgoing = deque([])
    idx_line = line.true_condition
    precision = cell_precision or config_options['display_precision']
    use_scientific_notation = toggle_scientific_notation(config_options['use_scientific_notation'], cell_notation)
    preferred_formatter = config_options['preferred_string_formatter']
    rendered_line = render_latex_str(idx_line, use_scientific_notation, precision, preferred_formatter)
    rendered_line = swap_dec_sep(rendered_line, config_options["decimal_separator"])
    line.line = rendered_line
    line.latex = " ".join(rendered_line)
    # return line
    line.true_condition = rendered_line
    for (
        expr
    ) in line.true_expressions:  # Each 'expr' item is a CalcLine or other line type
        outgoing.append(
            round_and_render_line_objects_to_latex(expr, cell_precision, cell_notation, **config_options)
        )
    line.true_expressions = outgoing
    line.latex = conditional_line_break.join([calc_line.latex for calc_line in outgoing])
    return line


@round_and_render_line_objects_to_latex.register(SymbolicLine)
def round_and_render_symbolic(
    line: SymbolicLine, cell_precision: int, cell_notation: bool, **config_options
) -> SymbolicLine:
    idx_line = line.line
    precision = cell_precision or config_options['display_precision']
    use_scientific_notation = toggle_scientific_notation(config_options['use_scientific_notation'], cell_notation)
    preferred_formatter = config_options['preferred_string_formatter']
    rendered_line = render_latex_str(idx_line, use_scientific_notation, precision, preferred_formatter)
    rendered_line = swap_dec_sep(rendered_line, config_options["decimal_separator"])
    line.line = rendered_line
    line.latex = " ".join(rendered_line)
    return line


@round_and_render_line_objects_to_latex.register(BlankLine)
def round_and_render_blank(line,  cell_precision: int, cell_notation: bool, **config_options):
    return line


@round_and_render_line_objects_to_latex.register(IntertextLine)
def round_and_render_intertext(line,  cell_precision: int, cell_notation: bool, **config_options):
    return line


def round_elements(line_of_code: deque, cell_precision: Optional[int] = None,  cell_notation: bool = False) -> deque:
    """
    Returns a rounded float
    """
    outgoing = deque([])
    for item in line_of_code:
        rounded = round_(item, precision=cell_precision, use_scientific_notation=cell_notation)
        outgoing.append(rounded)
    return outgoing


def round_(item: Any, precision: int, depth: int = 0, use_scientific_notation: bool = False) -> Any:
    """
    Recursively round an object and its elements to a given precision.
    """
    round_notation = use_scientific_notation
    if depth > 3:
        # Limit maximum recursion depth.
        return item

    if hasattr(item, "__sympy__"):
        return round_sympy(item, precision, use_scientific_notation)

    if hasattr(item, "__len__") and not isinstance(item, (str, dict, tuple)):
        try: # For catching arrays
            return [round_(v, precision=precision, depth=depth + 1, use_scientific_notation=use_scientific_notation) for v in item]
        except (ValueError, TypeError):
            # Objects like Quantity (from pint) have a __len__ wrapper
            # even if the wrapped magnitude object is not iterable.
            return round_float(item, precision, use_scientific_notation)

    if isinstance(item, complex):
        return round_complex(item, precision, use_scientific_notation)
    if not isinstance(item, (str, int)):
        try:
            return round_float(item, precision, use_scientific_notation)
        except (ValueError, TypeError):
            pass
    return item


def round_float(elem: Any, precision: int, use_scientific_notation: bool) -> Any:
    """
    Returns 'elem', presumed to be float-like, to 'precision', where 'precision' varies
    depending on whether 'use_scientific_notation' is True or not.
    """
    if use_scientific_notation:
        return round_for_scientific_notation(elem, precision)
    else:
        return round(elem, precision)


def round_complex(elem: complex, precision: int, use_scientific_notation: bool) -> complex:
    """
    Returns the complex 'elem' rounded to 'precision'
    """
    return complex(
        round_float(elem.real, precision, use_scientific_notation), 
        round_float(elem.imag, precision, use_scientific_notation)
    )


def round_sympy(elem: Any, precision: int, use_scientific_notation: bool) -> Any:
    """
    Returns the Sympy expression 'elem' rounded to 'precision'
    """
    from sympy import Float
    rule = {}
    for n in elem.atoms(Float):
            rule[n] = round_for_scientific_notation(n, precision)
    rounded = elem.xreplace(rule)
    if hasattr(elem, "units") and not hasattr(rounded, "units"):
        # Add back pint units lost during rounding.
        rounded = rounded * elem.units
    return rounded


def round_for_scientific_notation(elem, precision):
    """
    Returns a float rounded so that the decimals behind the coefficient are rounded to 'precision'.
    """
    adjusted_precision = calculate_adjusted_precision(elem, precision)
    rounded = round(elem, adjusted_precision)
    return rounded


def calculate_adjusted_precision(elem, precision):
    """
    Returns the number of decimal places 'elem' should be rounded to
    to achieve a final 'precision' in scientific notation.
    """
    try:
        power_of_ten = int(math.log10(abs(elem)))
    except (DimensionalityError, TypeError):
        elem_float = float(str(elem).split(" ")[0])
        power_of_ten = int(math.log10(abs(elem_float)))
    if power_of_ten < 1:
        return precision - power_of_ten + 1
    else:
        return precision - power_of_ten


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


@convert_applicable_long_lines.register(NumericCalcLine)
def convert_calc_to_long(line: NumericCalcLine):
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


@convert_applicable_long_lines.register(IntertextLine)
def convert_intertext_to_long(line: IntertextLine):
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


@test_for_long_lines.register(IntertextLine)
def test_for_long_intertext(line: IntertextLine) -> bool:
    return False


@test_for_long_lines.register(LongCalcLine)
def test_for_long_longcalcline(line: LongCalcLine) -> bool:
    return True


@test_for_long_lines.register(NumericCalcLine)
def test_for_long_numericcalcline(line: NumericCalcLine) -> bool:
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

    This is a (very) imperfect work-in-progress.
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
def format_lines(line_object, **config_options):
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
def format_calc_line(line: CalcLine, **config_options) -> CalcLine:
    latex_code = line.latex

    equals_signs = [idx for idx, char in enumerate(latex_code) if char == "="]
    second_equals = equals_signs[1]  # Change to 1 for second equals
    latex_code = latex_code.replace("=", "&=")  # Align with ampersands for '\align'
    comment_space = ""
    comment = ""
    if line.comment:
        comment_space = "\\;"
        comment = format_strings(line.comment, comment=True)
    line.latex = f"{latex_code[0:second_equals + 1]} {latex_code[second_equals + 2:]} {comment_space} {comment}\n"
    return line


@format_lines.register(NumericCalcLine)
def format_calc_line(line: NumericCalcLine, **config_options) -> NumericCalcLine:
    latex_code = line.latex
    latex_code = latex_code.replace("=", "&=")  # Align with ampersands for '\align'
    comment_space = ""
    comment = ""
    if line.comment:
        comment_space = "\\;"
        comment = format_strings(line.comment, comment=True)
    line.latex = f"{latex_code} {comment_space} {comment}\n"
    return line


@format_lines.register(ConditionalLine)
def format_conditional_line(line: ConditionalLine, **config_options) -> ConditionalLine:
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
        
        new_math_env = (
            f"\n\\end{{{config_options['math_environment_start']}}}\n"
            f"{config_options['latex_block_end']}\n"
            f"{config_options['latex_block_start']}\n"
            f"\\begin{{{config_options['math_environment_end']}}}\n"
        )
        first_line = f"&\\text{a}Since, {b} {latex_condition} : {comment_space} {comment} {new_math_env}"
        if line.condition_type == "else":
            first_line = ""
        line_break = f"{config_options['line_break']}\n"
        line.latex_condition = first_line

        outgoing = deque([])
        for calc_line in line.true_expressions:
            outgoing.append((format_lines(calc_line, **config_options)).latex)
        line.true_expressions = outgoing
        line.latex_expressions = line_break.join(line.true_expressions)
        line.latex = line.latex_condition + line.latex_expressions
        return line
    else:
        line.condition_latex = ""
        line.true_expressions = deque([])
        return line


@format_lines.register(LongCalcLine)
def format_long_calc_line(line: LongCalcLine, **config_options) -> LongCalcLine:
    """
    Return line with .latex attribute formatted with line breaks suitable
    for positioning within the "\aligned" latex environment.
    """
    latex_code = line.latex
    long_latex = latex_code.replace("=", "\\\\&=")  # Change all...
    long_latex = long_latex.replace("\\\\&=", "&=", 1)  # ...except the first one
    line_break = f"{config_options['line_break']}\n"
    comment_space = ""
    comment = ""
    if line.comment:
        comment_space = "\\;"
        comment = format_strings(line.comment, comment=True)
    line.latex = f"{long_latex} {comment_space} {comment}{line_break}"
    return line


@format_lines.register(ParameterLine)
def format_param_line(line: ParameterLine, **config_options) -> ParameterLine:
    comment_space = "\\;"
    line_break = "\n"
    if "=" in line.latex:
        replaced = line.latex.replace("=", "&=")
        comment = format_strings(line.comment, comment=True)
        line.latex = f"{replaced} {comment_space} {comment}{line_break}"
    else:  # To handle sympy symbols displayed alone
        replaced = line.latex.replace(" ", comment_space)
        comment = format_strings(line.comment, comment=True)
        line.latex = f"{replaced} {comment_space} {comment}{line_break}"
    return line


@format_lines.register(SymbolicLine)
def format_symbolic_line(line: SymbolicLine, **config_options) -> SymbolicLine:
    replaced = line.latex.replace("=", "&=")
    comment_space = "\\;"
    comment = format_strings(line.comment, comment=True)
    line.latex = f"{replaced} {comment_space} {comment}\n"
    return line


@format_lines.register(IntertextLine)
def format_intertext_line(line: IntertextLine, **config_options) -> IntertextLine:
    cleaned_line = line.line.replace("##", "")
    line.latex = f"& \\textrm{{{cleaned_line}}}"
    return line


@format_lines.register(BlankLine)
def format_blank_line(line: BlankLine, **config_options) -> BlankLine:
    line.latex = ""
    return line


def split_conditional(line: str, calculated_results: dict, cell_override: str):
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
        categorized = categorize_line(line, calculated_results, cell_override=cell_override)
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
        right_side.find(")") == len(right_side) - 1
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


def test_for_intertext_line(source: str) -> bool:
    """
    Returns True if 'source' appears to be an intertext line
    """
    return source.startswith("##")


def test_for_numeric_line(
    d: deque,
    # func_deque: bool = False
) -> bool:
    """
    Returns True if 'd' appears to be a calculation in
    consisting entirely of numerals, operators, and functions.
    In other words, the calculation has no "variables" in it,
    whatsoever.
    """
    bool_acc = []
    func_flag = False
    if get_function_name(d):
        func_flag = True
        # bool_acc.append((item, True))
    for item in d:
        # if func_deque:
        if func_flag:
            func_flag = False
            bool_acc.append(True)
            continue
        if is_number(item):
            bool_acc.append(True)
        elif test_for_py_operator(item):
            bool_acc.append(True)
        elif (
            item == "/" or item == "//"
        ):  # Not tested in test_for_py_operator, for reasons
            bool_acc.append(True)
        elif item == ",":  # Numbers separated with commas: ok
            bool_acc.append(True)
        elif isinstance(item, deque):
            if get_function_name(item):
                bool_acc.append(True)
                bool_acc.append(
                    test_for_numeric_line(
                        d=item,
                        # func_deque=True
                    )
                )
            else:
                bool_acc.append(test_for_numeric_line(d=item))
        else:
            bool_acc.append(False)
    return all(bool_acc)


def toggle_scientific_notation(use_scientific_notation: bool, cell_notation: Optional[bool]) -> bool:
    """
    Returns a bool representing whether or not scientific notation should be used or not
    based on whether it has been turned on in global_config and whether it has been
    toggled in the cell overides.
    
    In general, the cell overide toggles the reverse of the global_config.
    """
    if not cell_notation:
        return use_scientific_notation
    else:
        return not use_scientific_notation


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
    if "e-" in str(elem).lower():
        return True
    elif "e+" in str(elem).lower():
        return True
    return False


def test_for_small_complex(elem: Any, precision: int) -> bool:
    """
    Returns True if 'elem' is a complex whose rounded str representation
    has fewer significant figures than the number in 'precision'.
    Returns False otherwise.
    """
    if isinstance(elem, complex):
        test = [
            test_for_float(elem.real, precision),
            test_for_float(elem.imag, precision),
        ]
        return any(test)


def test_for_float(elem: Any, precision: int) -> bool:
    """
    Returns True if 'elem' is a float whose rounded str representation
    has fewer significant figures than the numer in 'precision'.
    Return False otherwise.
    """
    if isinstance(elem, float):
        return True
    elif not test_for_int(elem) and not isinstance(elem, str):
        try:
            float(elem)
            return True
        except (TypeError, DimensionalityError, ValueError):
            return False
    else:
        return False



def test_for_int(elem: Any) -> bool:
    """
    Returns True if 'elem' can be expressed as an integer. 
    Returns False otherwise.
    """
    if isinstance(elem, int):
        return True
    if isinstance(elem, str) and elem.replace("-","").isnumeric():
        return True
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


def render_latex_str(line_of_code: deque, use_scientific_notation: bool, precision: int, preferred_formatter: str) -> deque:
    """
    Returns a rounded str based on the latex_repr of an object in
    'line_of_code'
    """
    outgoing = deque([])
    for item in line_of_code:
        rendered_str = latex_repr(item, use_scientific_notation, precision, preferred_formatter)
        outgoing.append(rendered_str)
    return outgoing


def latex_repr(item: Any, use_scientific_notation: bool, precision: int, preferred_formatter: str) -> str:
    """
    Return a str if the object, 'item', has a special repr method
    for rendering itself in latex. If not, returns str(result).
    """    
    # Check for arrays
    if hasattr(item, "__len__") and not isinstance(item, (str, dict)):
        comma_space = ",\\ "
        try:
            array = (
                "[" + comma_space.join(
                    [latex_repr(v, use_scientific_notation, precision, preferred_formatter) for v in item]) 
                + "]"
            )
            rendered_string = array
        except TypeError:
            pass

    # Procedure for atomic data items
    try:
        if use_scientific_notation:
            rendered_string = f"{item:.{precision}e{preferred_formatter}}"
        else:
            rendered_string = f"{item:.{precision}f{preferred_formatter}}"
    except (ValueError):
        try:
            if use_scientific_notation:
                rendered_string = f"{item:.{precision}e}"
                rendered_string = swap_scientific_notation_str(rendered_string)
            else:
                rendered_string = f"{item:.{precision}f}"
        except (ValueError):
            try:
                rendered_string = item._repr_latex_()
            except AttributeError:
                rendered_string = str(item)
    
    return rendered_string.replace("$", "")




    if hasattr(item, preferred_latex_method):
        method = getattr(item, preferred_latex_method)
        rendered_string = method()

    elif hasattr(item, "_repr_latex_"):
        rendered_string = item._repr_latex_()

    elif hasattr(item, "latex"):
        try:
            rendered_string = item.latex()
        except TypeError:
            rendered_string = str(item)

    elif hasattr(item, "to_latex"):
        try:
            rendered_string = item.to_latex()
        except TypeError:
            rendered_string = str(item)

    elif hasattr(item, "__len__") and not isinstance(item, (str, dict)):
        comma_space = ",\\ "
        try:
            array = "[" + comma_space.join([str(v) for v in item]) + "]"
            rendered_string = array
        except TypeError:
            rendered_string = str(item)

    else:
        rendered_string = str(item)

    return rendered_string.replace("$", "")


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
        **config_options
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
                symbolic_portion = swap_symbolic_calcs(conditional, calc_results, **config_options)
                numeric_portion = swap_numeric_calcs(conditional, calc_results, **config_options)
                resulting_latex = (
                    symbolic_portion
                    + deque(["\\rightarrow"])
                    + deque([l_par])
                    + numeric_portion
                    + deque([r_par])
                )
            else:
                numeric_portion = swap_numeric_calcs(conditional, calc_results, **config_options)
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


def swap_calculation(calculation: deque, calc_results: dict, **config_options) -> tuple:
    """Returns the python code elements in the deque converted into
    latex code elements in the deque"""
    symbolic_portion = swap_symbolic_calcs(calculation, calc_results, **config_options)
    calc_drop_decl = deque(list(calculation)[1:])  # Drop the variable declaration
    numeric_portion = swap_numeric_calcs(calc_drop_decl, calc_results, **config_options)
    return (symbolic_portion, numeric_portion)


def swap_symbolic_calcs(calculation: deque, calc_results: dict, **config_options) -> deque:
    # remove calc_results function parameter
    symbolic_expression = copy.copy(calculation)
    functions_on_symbolic_expressions = [
        insert_parentheses,
        swap_math_funcs,
        swap_superscripts,
        swap_chained_fracs,
        swap_frac_divs,
        swap_py_operators,
        swap_comparison_ops,
        swap_for_greek,
        swap_prime_notation,
        swap_long_var_strs,
        extend_subscripts,
        swap_superscripts,
        flatten_deque,
    ]
    for function in functions_on_symbolic_expressions:
        # breakpoint()
        if function is swap_math_funcs:
            symbolic_expression = function(symbolic_expression, calc_results)
        elif function is extend_subscripts and not config_options["underscore_subscripts"]:
            symbolic_expression = replace_underscores(symbolic_expression, **config_options)
        else:
            symbolic_expression = function(symbolic_expression, **config_options)
    return symbolic_expression


def swap_numeric_calcs(calculation: deque, calc_results: dict, **config_options) -> deque:
    numeric_expression = copy.copy(calculation)
    functions_on_numeric_expressions = [
        insert_parentheses,
        swap_math_funcs,
        swap_chained_fracs,
        swap_frac_divs,
        swap_py_operators,
        swap_comparison_ops,
        swap_values,
        swap_for_greek,
        swap_prime_notation,
        swap_superscripts,
        extend_subscripts,
        flatten_deque,
    ]
    for function in functions_on_numeric_expressions:
        if function is swap_values or function is swap_math_funcs:
            numeric_expression = function(numeric_expression, calc_results, **config_options)
        elif function is extend_subscripts and not config_options["underscore_subscripts"]:
            numeric_expression = replace_underscores(numeric_expression, **config_options)
        else:
            numeric_expression = function(numeric_expression, **config_options)
    return numeric_expression


def swap_integrals(d: deque, calc_results: dict, **config_options) -> deque:
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


def swap_log_func(d: deque, calc_results: dict, **config_options) -> deque:
    """
    Returns a new deque representing 'd' but with any log functions swapped
    out for the appropriate Latex equivalent.
    """
    # Checks to figure out where things are and where they go
    swapped_deque = deque([])
    base = ""
    has_deque = isinstance(d[1], deque)
    has_nested_deque = len(d) > 2 and isinstance(d[2], deque) and d[0] == "\\left("
    log_func = d[0] if d[0] != "\\left(" else d[1]
    base = ""
    has_nested_lpar = d[0] == "\\left("
    has_rpar = d[-1] == "\\right)"
    has_single_lpar = d[1] == "\\left("

    # For specialized functions
    if log_func in ["log10", "log2"]:
        base = log_func.replace("log", "")

    if has_deque:  # Arithmetic expression as argument in sub-deque
        sub_deque = d[1]
    elif has_nested_deque:  # Nested function in sub-deque
        sub_deque = d[2]

    if has_deque or has_nested_deque:
        if "," in sub_deque:  # Log base argument provided
            base = sub_deque[-2]  # Last arg in d before "\\right)"
            operand = swap_math_funcs(
                deque(list(sub_deque)[:-3] + ["\\right)"]), calc_results
            )  # Operand is everything before the base argument
        else:
            # No Log base argument, recurse everything in the sub-deque
            operand = swap_math_funcs(deque([sub_deque]), calc_results)
    else:
        operand = d[2]  # swap_math_funcs(d, calc_results)

    if base == "e":
        base = ""
    if isinstance(base, deque):
        raise ValueError(
            "Cannot use an expression as the log base in handcalcs."
            " Try assigning the base to a variable first."
        )
    base = dict_get(calc_results, base)
    if base:
        log_func = "\\log_"
    else:
        log_func = "\\ln"

    swapped_deque.append(log_func + str(base))
    if has_single_lpar:
        swapped_deque.append("\\left(")
    swapped_deque.append(operand)

    if has_nested_lpar:
        swapped_deque.appendleft("\\left(")
    if has_rpar:
        swapped_deque.append("\\right)")

    return swapped_deque


def swap_floor_ceil(d: deque, func_name: str, calc_results: dict, **config_options) -> deque:
    """
    Return a deque representing 'd' but with the functions floor(...)
    and ceil(...) swapped out for floor and ceiling Latex brackets.
    """
    lpar = f"\\left \\l{func_name}"
    rpar = f"\\right \\r{func_name}"
    swapped_deque = deque([])
    peekable_deque = more_itertools.peekable(d)
    for item in peekable_deque:
        next_item = peekable_deque.peek(False)
        if isinstance(item, deque):
            new_item = swap_math_funcs(item, calc_results)
            swapped_deque.append(new_item)
        elif item == func_name and isinstance(next_item, deque):
            next_item.popleft()
            next_item.appendleft(lpar)
            next_item.pop()
            next_item.append(rpar)
        else:
            swapped_deque.append(item)
    return swapped_deque


def flatten_deque(d: deque, **config_options) -> deque:
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


def expr_parser(line: str) -> list:
    import sys

    sys.setrecursionlimit(3000)
    pp.ParserElement.enablePackrat()

    variable = pp.Word(pp.alphanums + "_.")
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
    return acc


def extend_subscripts(pycode_as_deque: deque, **config_options) -> deque:
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


def replace_underscores(pycode_as_deque: deque, **config_options) -> deque:
    """
    Returns 'pycode_as_deque' with underscores replaced with spaces.
    Used when global_config['underscore_subscripts'] == False
    """
    swapped_deque = deque([])
    for item in pycode_as_deque:
        if isinstance(item, deque):
            new_item = replace_underscores(item)
            swapped_deque.append(new_item)
        elif isinstance(item, str):
            new_item = item.replace("_", "\\ ")
            swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_chained_fracs(d: deque, **config_options) -> deque:
    """
    Swaps out the division symbol, "/", with a Latex fraction.
    The numerator is the symbol before the "/" and the denominator follows.
    If either is a string, then that item alone is in the fraction.
    If either is a deque, then all the items in the deque are in that part of the fraction.

    If a "chained division" is encountered, e.g. 4 / 2 / 2, these are rendered as
    fractions that retain the original order of operations meaning.

    Returns a deque.
    """
    a = "{"
    b = "}"
    swapped_deque = deque([])
    ops = "\\frac{1}"
    cdot = "\\cdot"
    past_first_frac = False
    close_bracket_token = False
    for item in d:
        if isinstance(item, deque):
            swapped_deque.append(swap_chained_fracs(item))  # recursion!

        elif item == "/" and not past_first_frac:
            past_first_frac = True
            swapped_deque.append(item)
            continue

        elif item == "/" and past_first_frac:
            swapped_deque.append(cdot)
            swapped_deque.append(ops)
            swapped_deque.append(a)
            close_bracket_token = True
            continue

        elif test_for_py_operator(item) and past_first_frac:
            past_first_frac = False
            swapped_deque.append(item)

        else:
            swapped_deque.append(item)

        if close_bracket_token:
            swapped_deque.append(b)
            close_bracket_token = False

    return swapped_deque


def test_for_py_operator(item: str):
    """
    Returns True if `item` represents a str that can be used as
    a Python arithmetic or binary operator. Return False otherwise.

    Python arithmetic operators:
    +, -, *, %, **
    (note `/`, and `//` is not considered b/c they will be
    swapped out as fractions)

    Python binary operators:
    >, <, =
    """
    py_ops = ["+", "-", "*", "%", "//", "**"]
    for op in py_ops:
        if op == str(item):
            return True

    bin_ops = "<>="
    for op in bin_ops:
        if op in str(item):
            return True

    return False


def swap_frac_divs(code: deque, **config_options) -> deque:
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
            swapped_deque.append(swap_frac_divs(item, **config_options))  # recursion!
        elif code[next_idx] == "/" and not isinstance(item, deque):
            new_item = f"{ops}{a}"
            swapped_deque.append(new_item)
            swapped_deque.append(item)
        elif item == "/":
            swapped_deque.append(f"{b}{a}")
            close_bracket_token += 1
        elif close_bracket_token:
            if isinstance(item, deque):
                swapped_deque.append(swap_frac_divs(item, **config_options)) # recursion!
            else:
                swapped_deque.append(item)
            new_item = f"{b}" * close_bracket_token
            close_bracket_token = 0
            swapped_deque.append(new_item)
        elif isinstance(item, deque):
            new_item = swap_frac_divs(item, **config_options)  # recursion!
            swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_math_funcs(pycode_as_deque: deque, calc_results: dict, **config_options) -> deque:
    """
    Returns a deque representing 'pycode_as_deque' but with appropriate
    parentheses inserted.
    """
    a = "{"
    b = "}"
    swapped_deque = deque([])
    for item in pycode_as_deque:
        if isinstance(item, deque):
            possible_func = not test_for_typ_arithmetic(item)
            poss_func_name = get_function_name(item)
            func_name_match = get_func_latex(poss_func_name)
            if poss_func_name != func_name_match:
                item = swap_func_name(item, poss_func_name)
                if poss_func_name == "sqrt":
                    item = insert_func_braces(item)
                new_item = swap_math_funcs(item, calc_results)
                swapped_deque.append(new_item)
            elif poss_func_name == func_name_match:
                # Begin checking for specialized function names
                if poss_func_name == "quad":
                    new_item = swap_integrals(item, calc_results)
                    swapped_deque.append(new_item)
                elif "log" in poss_func_name:
                    new_item = swap_log_func(item, calc_results)
                    swapped_deque.append(new_item)
                elif poss_func_name == "ceil" or poss_func_name == "floor":
                    new_item = swap_floor_ceil(item, poss_func_name, calc_results)
                    swapped_deque.append(new_item)
                #
                #  elif possible_func and poss_func_name:
                # elif possible_func:
                elif possible_func:
                    ops = "\\operatorname"
                    new_func = f"{ops}{a}{poss_func_name}{b}"
                    item = swap_func_name(item, poss_func_name, new_func)
                    if possible_func:
                        item = insert_func_braces(item)
                    new_item = swap_math_funcs(item, calc_results)
                    swapped_deque.append(new_item)

                else:
                    swapped_deque.append(swap_math_funcs(item, calc_results))
        else:
            swapped_deque.append(item)
    return swapped_deque


def get_func_latex(func: str, **config_options) -> str:
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


def insert_func_braces(d: deque, **config_options) -> deque:
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
    if last_idx == 1:  # Special case, func is sqrt or other non-parenth func
        swapped_deque.append(d[0])
        swapped_deque.append(a)
        swapped_deque.append(d[1])
        swapped_deque.append(b)
    elif (
        last_idx == 3 and d[0] == "\\left(" and d[last_idx] == "\\right)"
    ):  # Special case, func is inside another func with parenth
        swapped_deque.append(a)
        swapped_deque += d
        swapped_deque.append(b)
    else:
        for idx, elem in enumerate(d):
            if idx == 1:  # func name is 0, brace at 1
                swapped_deque.append(a)
                swapped_deque.append(elem)
            elif idx == last_idx:  # brace at end
                swapped_deque.append(elem)
                swapped_deque.append(b)
            else:
                swapped_deque.append(elem)
    return swapped_deque


def swap_func_name(d: deque, old: str, new: str = "", **config_options) -> deque:
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


def swap_py_operators(pycode_as_deque: deque, **config_options) -> deque:
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


def swap_scientific_notation_str(item: str) -> str:
    """
    Returns a deque representing 'line' with any python
    float elements in the deque
    that are in scientific notation "e" format converted into a Latex
    scientific notation.
    """
    b = "}"
    components = []
    for component in item.split(" "):
        if "e+" in component:
            new_component = component.replace("e+", " \\times 10 ^ {")
            components.append(new_component)
            components.append(b)
        elif "e-" in component:
            new_component = component.replace("e-", " \\times 10 ^ {")
            components.append(new_component)
            components.append(b)
        else:
            components.append(component)
    new_item = "\\ ".join(components)
    return new_item


def swap_scientific_notation_float(line: deque, precision: int, **config_options) -> deque:
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
        if test_for_float(item, precision):
            new_item = (
                "{:.{precision}e}".format(item, precision=precision)
                .replace("e-0", "e-")
                .replace("e+0", "e+")
            )
            swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)

    return swapped_deque


def swap_scientific_notation_complex(line: deque, precision: int, **config_options) -> deque:
    swapped_deque = deque([])
    for item in line:
        if isinstance(item, complex) and test_for_small_complex(item, precision):
            real = swap_scientific_notation_float([item.real], precision)
            imag = swap_scientific_notation_float([item.imag], precision)
            swapped_real = list(swap_scientific_notation_str(real, precision=precision))
            swapped_imag = list(swap_scientific_notation_str(imag, precision=precision))

            ops = "" if item.imag < 0 else "+"
            real_str = (
                f"{swapped_real[0]}"
                if len(swapped_real) == 1
                else " ".join(swapped_real)
            )
            imag_str = (
                f"{swapped_imag[0]}"
                if len(swapped_imag) == 1
                else " ".join(swapped_imag)
            )
            new_complex_str = f"( {real_str} {ops} {imag_str}j )"
            swapped_deque.append(new_complex_str)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_comparison_ops(pycode_as_deque: deque, **config_options) -> deque:
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


def swap_superscripts(pycode_as_deque: deque, **config_options) -> deque:
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
    for idx, item in enumerate(pycode_as_deque):
        next_idx = min(idx + 1, len(pycode_as_deque) - 1)
        next_item = pycode_as_deque[next_idx]
        if isinstance(item, deque):  # and not close_bracket_token:
            if "**" == str(next_item):
                pycode_with_supers.append(l_par)
                new_item = swap_superscripts(item)
                pycode_with_supers.append(new_item)
                pycode_with_supers.append(r_par)
            else:
                new_item = swap_superscripts(item)  # recursion!
                pycode_with_supers.append(new_item)
            if close_bracket_token:
                pycode_with_supers.append(b)
                close_bracket_token = False

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
                pycode_with_supers.append(b)
                close_bracket_token = False
            else:
                pycode_with_supers.append(item)
                prev_item = item

    return pycode_with_supers


def swap_for_greek(pycode_as_deque: deque, **config_options) -> deque:
    """
    Returns full line of code as deque with any Greek terms swapped in for words describing
    Greek terms, e.g. 'beta' -> 'β'
    """
    greeks_to_exclude = config_options['greek_exclusions']
    swapped_deque = deque([])
    greek_chainmap = ChainMap(GREEK_LOWER, GREEK_UPPER)
    for item in pycode_as_deque:
        if isinstance(item, deque):
            new_item = swap_for_greek(item, **config_options)
            swapped_deque.append(new_item)
        elif "_" in str(item):
            components = str(item).split("_")
            swapped_components = [
                dict_get(greek_chainmap, component) if component not in greeks_to_exclude else component 
                for component in components
            ]
            new_item = "_".join(swapped_components)
            swapped_deque.append(new_item)
        elif item not in greeks_to_exclude:
            new_item = dict_get(greek_chainmap, item)
            swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)
    return swapped_deque


def test_for_long_var_strs(elem: Any, **config_options) -> bool:
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
        if not config_options['underscore_subscripts']:
            if len(top_level) + len(_remainders) == 1:
                return False
            else:
                return True
        else:
            if len(top_level) > 1:
                return True
            else:
                return False
    if len(components[0]) == 1:
        return False
    return True


def swap_long_var_strs(pycode_as_deque: deque, **config_options) -> deque:
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
            new_item = swap_long_var_strs(item, **config_options)
            swapped_deque.append(new_item)
        elif test_for_long_var_strs(item, **config_options) and not is_number(str(item)):
            try:
                top_level, remainder = str(item).split("_", 1)
                if config_options["underscore_subscripts"]:
                    new_item = begin + top_level + end + "_" + remainder
                else:
                    new_item = begin + top_level + "_" + remainder + end
                swapped_deque.append(new_item)
            except:
                new_item = begin + item + end
                swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_prime_notation(d: deque, **config_options) -> deque:
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


def swap_values(pycode_as_deque: deque, tex_results: dict, **config_options) -> deque:
    """
    Returns a the 'pycode_as_deque' with any symbolic terms swapped out for their corresponding
    values.
    """
    outgoing = deque([])
    for item in pycode_as_deque:
        swapped_value = ""
        if isinstance(item, deque):
            outgoing.append(swap_values(item, tex_results, **config_options)) # recursion!
        else:
            swapped_value = dict_get(tex_results, item)
            if isinstance(swapped_value, str) and swapped_value != item:
                swapped_value = format_strings(swapped_value, comment=False, **config_options)
            outgoing.append(swapped_value)
    return outgoing


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
    dummy_deque = copy.deepcopy(d)
    dummy_deque.popleft()
    if test_for_function_name(d):
        return d[0]
    elif test_for_function_name(dummy_deque):
        return dummy_deque[0]
    # elif (isinstance(d[0], str) and re.match(r"^[A-Za-z0-9_]+$", d[0])
    #     and isinstance(d[1], deque)# and d[1][0] == "\\left("
    # ):
    #     return d[0]
    # elif (
    #     d[0] == "\\left("
    #     and (isinstance(d[1], str) and re.match(r"^[A-Za-z0-9_]+$", d[1])
    #     )
    # ):
    #     return d[1]
    else:
        return ""


def test_for_function_name(d: deque) -> bool:
    """
    Returns True if 'd' qualifies for a typical function that should have
    some form of function brackets around it.
    """
    if (
        (len(d) == 2 or len(d) == 4 or len(d) == 3)
        and (isinstance(d[0], str) and re.match(r"^[A-Za-z0-9_]+$", d[0]))
        and (
            isinstance(d[1], str)
            and (re.match(r"^[A-Za-z0-9_]+$", d[1]) or is_number(d[1]))
            or d[1] == "\\left("
            or d[-1] == "\\right)"
        )
    ):
        return True
    elif (
        len(d) > 1
        and isinstance(d[0], str)
        and re.match(r"^[A-Za-z0-9_]+$", d[0])
        and isinstance(d[1], deque)
    ):
        return True
    else:
        return False


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
    for idx, item in enumerate(d):
        if idx == last == 1 and not isinstance(item, deque):
            swapped_deque.append(lpar)
            swapped_deque.append(item)
            swapped_deque.append(rpar)
        elif idx == 1 and isinstance(item, deque):
            new_item = copy.deepcopy(item)
            new_item.appendleft(lpar)
            new_item.append(rpar)
            swapped_deque.append(new_item)
        elif idx == 2 and isinstance(item, deque) and d[0] == "\\left(":
            new_item = copy.deepcopy(item)
            new_item.appendleft(lpar)
            new_item.append(rpar)
            swapped_deque.append(new_item)
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
        if idx == 0 and not exp_check and d[idx] != lpar:
            swapped_deque.append(lpar)
            swapped_deque.append(item)
        elif idx == last and not exp_check and d[idx] != rpar:
            swapped_deque.append(item)
            swapped_deque.append(rpar)
        else:
            swapped_deque.append(item)
    return swapped_deque


def insert_parentheses(pycode_as_deque: deque, **config_options) -> deque:
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
        next_item = peekable_deque.peek(False)
        if isinstance(item, deque):
            poss_func_name = get_function_name(item)
            typ_arithmetic = test_for_typ_arithmetic(item)
            if poss_func_name:
                if test_for_fraction_exception(item, next_item):
                    skip_fraction_token = True
                if poss_func_name not in func_exclude:
                    item = insert_function_parentheses(item)
                new_item = insert_parentheses(item)
                swapped_deque.append(new_item)

            elif (
                typ_arithmetic
                # and not prev_item == lpar
                and not skip_fraction_token
            ):

                if test_for_fraction_exception(item, next_item):

                    skip_fraction_token = True
                    new_item = insert_parentheses(item)
                    swapped_deque.append(new_item)
                else:
                    if (
                        prev_item not in func_exclude
                        # and not test_for_nested_deque(item)
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
    nested_deque_bool = next(isinstance(i, deque) for i in d)
    try:
        not_exponent = (
            d[0][1] != "**"
        )  # Nested deques are permitted if first item is raised to power
    except IndexError:
        not_exponent = True
    return nested_deque_bool and not_exponent


def swap_dec_sep(d: deque, dec_sep: str) -> deque:
    """
    Returns 'd' with numerical elements with the "." decimal separator,
    replaced with 'dec_sep'.
    """
    swapped_deque = deque([])
    a = "{"
    b = "}"
    if dec_sep == ".":
        return d
    for item in d:
        if is_number(item):
            item = item.replace(".", f"{a}{dec_sep}{b}")
            swapped_deque.append(item)
        elif is_number(item.replace("\\", "")):
            item = item.replace(".", f"{a}{dec_sep}{b}")
            swapped_deque.append(item)
        elif " " in item:
            components = deque(item.split())
            swapped_components = swap_dec_sep(components, dec_sep)
            swapped_deque.append(" ".join(swapped_components))
        else:
            swapped_deque.append(item)
    return swapped_deque
