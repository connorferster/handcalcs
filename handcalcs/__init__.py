from collections import deque
import copy
from dataclasses import dataclass
from functools import singledispatch
import importlib
import inspect
import math
import os
import pathlib
from typing import Any, Union, Optional, Tuple, List

import pyparsing as pp

# import jinja2
# from jinja2 import Template

# TODO: Add support for conditional expressions with ConditionalLine
# TODO: Do something with inequality checks

# Four basic line types
@dataclass
class CalcLine:
    line: deque
    comment: str


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


@dataclass
class ParameterLine:
    line: deque
    comment: str


@dataclass
class LongCalcLine:
    def __init__(self, calcline: CalcLine):
        self.line = calcline.line
        self.comment = calcline.comment


# Three types of cell
@dataclass
class CalcCell:
    source: str
    calculated_results: dict
    precision: int
    incoming_lines: deque
    outgoing_lines: deque
    latex_code: str

    def __repr__(self):
        return str(
            "CalcCell(\n"
            + f"source=\n{self.source}\n"
            + f"incoming_lines=\n{self.incoming_lines}\n"
            + f"outgoing_lines={self.outgoing_lines}"
        )


@dataclass
class OutputCell:
    source: str
    calculated_results: dict
    incoming_lines: deque
    outgoing_lines: deque
    precision: int
    cols: int
    latex_code: str

    def __repr__(self):
        return str(
            "OutputCell(\n"
            + f"source=\n{self.source}\n"
            + f"incoming_lines=\n{self.incoming_lines}\n"
            + f"outgoing_lines=\n{self.outgoing_lines}"
        )


@dataclass
class ParameterCell:
    source: str
    calculated_results: dict
    incoming_lines: deque
    outgoing_lines: deque
    precision: int
    cols: int
    latex_code: str

    def __repr__(self):
        return str(
            "ParametersCell(\n"
            + f"source=\n{self.source}\n"
            + f"incoming_lines=\n{self.incoming_lines}\n"
            + f"outgoing_lines=\n{self.outgoing_lines}"
        )


# The renderer class ("output" class)
class LatexRenderer:
    def __init__(self, python_code_str: str, results: dict):
        self.source = python_code_str
        self.results = results
        self.precision = 3

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
    return cell


    # parsed_calc_cell = parse_python_code(cell)
    # cell.lines = python_to_latex_conversion(cell.lines, cell.calculated_results)
    # # print(converted_into_latex)
    # cell.lines = render_latex_reprs(cell.lines, cell.precision)
    # cell.latex_code = render_to_string(cell.lines)
    # # print(final_latex_deque)
    # cell.latex_code = "\\\\[10pt]\n".join(cell.latex_code)
    # beg_env = "\\begin{aligned}\n"
    # end_env = "\\end{aligned}"
    # cell.latex_code = f"{beg_env}{cell.latex_code}{end_env}"

    # cell.latex_code = f"\\[\n{cell.latex_code}\n\\]"


def categorize_raw_cell(
    raw_source: str, calculated_results: dict, precision: int = 3
) -> Union[ParameterCell, OutputCell, CalcCell]:
    """
    Return a "Cell" type depending on the source of the cell.
    """
    if test_for_parameter_cell(raw_source):
        cell = ParameterCell(
            source=raw_source,
            calculated_results=calculated_results,
            incoming_lines=deque([]),
            outgoing_lines=deque([]),
            precision=precision,
            cols=3,
            latex_code="",
        )

    elif test_for_output_cell(raw_source):
        cell = OutputCell(
            source=raw_source,
            calculated_results=calculated_results,
            incoming_lines=deque([]),
            outgoing_lines=deque([]),
            precision=precision,
            cols=3,
            latex_code="",
        )
    else:
        cell = CalcCell(
            source=raw_source,
            calculated_results=calculated_results,
            precision=precision,
            incoming_lines=deque([]),
            outgoing_lines=deque([]),
            latex_code="",
        )
    return cell


def categorize_line(
    line: str, calculated_results: dict
) -> Union[CalcLine, ParameterLine, ConditionalLine]:
    """
    Return 'line' as either a CalcLine, ParameterLine, or ConditionalLine if 'line'
    fits the appropriate criteria. Raise ValueError, otherwise.
    """
    try:
        line, comment = line.split("#")
    except ValueError:
        comment = ""

    if test_for_parameter_line(line):
        categorized_line = ParameterLine(
            split_parameter_line(line, calculated_results), comment
        )

    elif ":" in line and ("if" in line or "else" in line):
        (
            condition,
            condition_type,
            expression,
            raw_condition,
            raw_expression,
        ) = split_conditional(line)
        categorized_line = ConditionalLine(
            condition=condition,
            condition_type=condition_type,
            expressions=expression,
            raw_condition=raw_condition,
            raw_expression=raw_expression.strip(),
            true_condition=deque([]),
            true_expressions=deque([]),
            comment=comment,
        )

    elif "=" in line:
        categorized_line = CalcLine(code_reader(line), comment)

    elif len(line) == 1:
        categorized_line = ParameterLine(split_parameter_line(line, calculated_results), comment)        

    else:
        if line == "":
            pass
        else:
            raise ValueError(
                f"Line: {line} is not recognized for rendering.\n"
                "Lines must include either 'if/else' or '='."
                "Did you intend to create an '# Output' cell?"
            )
    return categorized_line


def categorize_lines(cell: Union[CalcCell, ParameterCell, OutputCell]) -> Union[CalcCell, ParameterCell, OutputCell]:
    """
    Return 'cell' with the line data contained in cell_object.source categorized
    into one of four types:
    * CalcLine
    * ParameterLine
    * ConditionalLine

    categorize_lines(calc_cell) is considered the default behaviour for the 
    singledispatch categorize_lines function.
    """
    source = cell.source
    outgoing = source.split("\n")
    incoming = deque([])
    calculated_results = cell.calculated_results
    for line in outgoing:
        categorized = categorize_line(line, calculated_results)
        categorized_w_result_appended = add_result_values_to_line(categorized, calculated_results)
        incoming.append(categorized_w_result_appended)
    cell.incoming_lines = incoming
    return cell


@singledispatch
def add_result_values_to_line(line_object, calculated_results: dict):
    raise ValueError(f"Line object, {type(line_object)} not fully implemented yet.")


@add_result_values_to_line.register(CalcLine)
def results_for_calcline(line_object, calculated_results):
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
        parameter_name = expr[0]
        resulting_value = calculated_results.get(parameter_name, parameter_name)
        expr.append(deque(["=", resulting_value]))
    return line_object

@singledispatch
def convert_cell(cell_object):
    raise ValueError(f"Cell object {type(cell_object)} not recognized, yet.")

@convert_cell.register(CalcCell)
def convert_calc_cell(cell: CalcCell) -> CalcCell:
    outgoing = cell.incoming_lines
    calculated_results = cell.calculated_results
    incoming = deque([])
    for line in outgoing:
        incoming.append(convert_line(line, calculated_results))
    cell.incoming_lines = incoming
    return cell

@convert_cell.register(ParameterCell)
def convert_parameter_cell(cell: ParameterCell) -> ParameterCell:
    outgoing = cell.incoming_lines
    incoming = deque([])
    for line in outgoing:
        conversion_line = line.line
        line.line = swap_symbolic_calcs(conversion_line)
        incoming.append(line)
    cell.incoming_lines = incoming
    return cell

@convert_cell.register(OutputCell)
def convert_parameter_cell(cell: OutputCell) -> OutputCell:
    outgoing = cell.incoming_lines
    incoming = deque([])
    for line in outgoing:
        conversion_line = line.line
        line.line = swap_symbolic_calcs(conversion_line)
        incoming.append(line)
    cell.incoming_lines = incoming
    return cell

@singledispatch
def convert_line(line_object: Union[CalcLine, ConditionalLine, ParameterLine], calculated_results: dict) -> Union[CalcLine, ConditionalLine, ParameterLine]:
    raise ValueError(f"Cell object {type(line_object)} not recognized, yet.")

@convert_line.register(CalcLine)
def convert_calc(line, calculated_results):
    *line_deque, result = line.line
    symbolic_portion, numeric_portion = swap_calculation(line_deque, calculated_results)
    try:
        line.line = symbolic_portion + numeric_portion + result
    except:
        breakpoint()
    return line

@convert_line.register(ConditionalLine)
def convert_conditional(line, calculated_results):
    condition, condition_type, expressions, raw_condition = (line.condition, line.condition_type, line.expressions, line.raw_condition)
    swap_conditional = ConditionalEvaluator() # Callable helper class
    true_condition_deque = swap_conditional(condition, condition_type, raw_condition, calculated_results)
    if true_condition_deque:
        line.true_condition = true_condition_deque
        for expression in expressions:
            *expr, result = expression # Unpack deque of form [[expr, ...], ['=', 'result']]
            symbolic_portion, numeric_portion = swap_calculation(expr, calculated_results)
            line.true_expressions.append(symbolic_portion + numeric_portion + result)
    return line

@convert_line.register(ParameterLine)
def convert_parameter(line, calculated_results):
    conversion_line = line.line
    converted_line = swap_symbolic_calcs(conversion_line)
    line.line = converted_line
    return line

#TODO: Get clear on which functions return what in the last steps
# Road map: render_objects_in_deque_to_str('round resulting values', consumes line object) -> format_cell: format_lines(returns Line object) -> render_cell_to_str


def render_lines_to_latex(cell_object: Union[CalcCell, ParameterCell, OutputCell]) -> Union[CalcCell, ParameterCell, OutputCell]:
    """
    At this point, the .line deques still have various objects in them (e.g. float, int, other)
    This function renders those objects into strings. They are rounded to the appropriate
    precision. If they are non-native Python objects, then an attempt is made to call
    their _repr_latex_ function to render them as a latex string.
    """
    precision = cell_object.precision
    for line in cell_object.incoming_lines:
        line = round_resulting_values(line, precision)
    cell_object.latex_code = " ".join(cell_object.incoming_lines)
    return cell_object

    #cell.latex_code = " ".join(cell.incoming_lines)
    #return format_calc_cell(cell) -> Write this function


@singledispatch
def format_cell(cell_object: Union[OutputCell, ParametersCell, CalcCell]):
    raise ValueError(f'Cell type {type(cell_object)} has not been implemented, yet.')

# Check this one out. Does it need to do so much in one function or can it follow
# the unified process?
@format_cell.register
def parameters_cell(cell: ParameterCell):
    """
    Returns the input parameters as an \\align environment with 'cols'
    number of columns.
    """
    outgoing = cell.incoming_lines
    precision = cell.precision
    cols = cell.cols
    begin = "\\begin{aligned}"
    end = "\\end{aligned}"
    linebreak = "\\\\"
    incoming = deque([])
    for idx, line in enumerate(outgoing):
        latex_line = round_resulting_values(line, precision)
        symbol, equals, value = latex_line
        if idx % cols == 0:
            equals = "&="
        elif idx % cols == cols - 1:
            symbol = f"&{symbol}"
            equals = "&="
            value = f"{value} {linebreak} "
        else:
            symbol = f"&{symbol}"
            equals = "&="
        incoming.append(" ".join([symbol, equals, value]))
    cell.incoming = incoming
    latex_code = " ".join(cell.incoming)
    cell.latex_code = "\n".join([begin, latex_code, end])
    return cell

@format_cell.register
def format_calc_cell(cell: CalcCell) -> str:
    for line in cell.latex_code:
        line = format_calc_lines(line)
    joined_latex = "\\\\[10pt]\n".join(cell.latex_code)
    beg_env = "\\begin{aligned}\n"
    end_env = "\\end{aligned}"
    return f"{beg_env}{joined_latex}{end_env}\n\\"

@format_cell.register
def format_output_cell(cell: OutputCell) -> str:
    for line in cell.latex_code:
        line = format_calc_lines(line)
    joined_latex = "\\\\[10pt]\n".join(cell.latex_code)
    beg_env = "\\begin{aligned}\n"
    end_env = "\\end{aligned}"
    return f"{beg_env}{joined_latex}{end_env}\n\\"

@singledispatch
def format_lines(line_object):
    raise ValueError(f"Line type {type(line_object)} is not implemented, yet.")

@format_lines.register
def format_calc_lines(line: CalcLine) -> CalcLine:
    latex_code = line.line
    equals_signs = [idx for idx, char in enumerate(latex_code) if char == "="]
    second_equals = equals_signs[1]  # Change to 1 for second equals
    latex_code = latex_code.replace("=", "&=")  # Align with ampersands for '\align'
    return f"{latex_code[0:second_equals + 1]}{latex_code[second_equals + 2:]}\n"


class ConditionalLine:
    condition: deque
    condition_type: str
    expressions: deque
    raw_condition: str
    raw_expression: str
    true_condition: deque
    true_expressions: deque
    comment: str


# def format_conditional_lines(latex_code: str) -> str:
#     """
#     Returns a line of 'latex_code' that has been formatted for the 'aligned' environment
#     """
#     a = "{"
#     b = "}"
#     text = "\\textrm"
#     # opening = f"\\begin{a}{environment}{b}\n"
#     conditional = f"&{text}{a}Since, {b}{latex_code}:\\\\\n"
#     # end = f"\\end{a}{environment}{b}\n"
#     conditional_line = f"{conditional}"
#     return conditional_line


@format_lines.register
def format_conditional_lines(line: ConditionalLine) -> ConditionalLine:
    """
    Returns the conditional line as a string of latex_code
    """
    # THIS IS NOT DONE YET. Need to figure out if expression_lines are fully processed and ready to be joined with "\\\\\n" or if further formatting is required.
    latex_condition = " ".join(line.true_condition) # This needs to be coming in as a line of joined latex; or made into one here
    a = "{"
    b = "}"
    text = "\\text"
    # opening = f"\\begin{a}{environment}{b}\n"
    first_line = f"&\\text{a}Since, {b}{latex_condition}:\\\\\n"
    transition_line = "\\text{Therefore} \\; \\rightarrow \\;"
    expression_lines = deque([" ".join(expression) for expression in line.true_expressions]) # Maybe format_calc_line for every expression?
    remaining_lines = "\\\\\n".join(expression_lines)
    return rendered_deque

def render_to_string(latex_results: dict) -> deque:
    """
    Returns a deque of rendered latex_lines that are ready for printing.
    """
    rendered_deque = deque([])
    for line_num, line_data in latex_results.items():
        line = line_data["line"]  # deque
        ltype = line_data["type"]  # str
        if ltype == "heading":
            rendered_deque.append(line)
        #         elif ltype == "note":
        #             formatted_note = format_notes(line, text_env)
        #             rendered_deque.append(formatted_note)
        elif ltype == "normal calc":
            if "return" in line:
                return rendered_deque
            else:
                formatted_calc = format_calc_lines(line)
            rendered_deque.append(formatted_calc)
        elif ltype == "long calc":
            rendered_deque.append(line)
        elif ltype == "parameter":
            rendered_deque.append(line)
        elif ltype == "conditional":
            condition, expressions = line
            if condition[0]:
                cond = format_conditional_lines(condition[0])
            else:
                cond = "\\text{Therefore} \\; \\rightarrow \\;"
            formatted_acc = deque([])
            for expression in expressions[0]:
                expr = expression
                if "return" in " ".join(expr):
                    formatted_conditional = f"{cond}{' '.join(formatted_acc)}"
                    rendered_deque.append(formatted_conditional)
                    return rendered_deque
                else:
                    formatted_calc = format_calc_lines(" ".join(expr))
                formatted_acc.append(formatted_calc)
            else:
                formatted_conditional = f"{cond}{' '.join(formatted_acc)}"
                rendered_deque.append(formatted_conditional)
    return rendered_deque



def format_calc_lines(latex_code: str) -> str:
    """
    Returns a line of 'latex_code' that has been formatted for the 'aligned' environment
    """
    equals_signs = [idx for idx, char in enumerate(latex_code) if char == "="]
    second_equals = equals_signs[1]  # Change to 1 for second equals

    latex_code = latex_code.replace("=", "&=")  # Align with ampersands for '\align'
    remove_amp_from_second = (
        f"{latex_code[0:second_equals + 1]}{latex_code[second_equals + 2:]}"
    )
    normal_line = f"{remove_amp_from_second}\n"
    return normal_line


def format_conditional_lines(latex_code: str) -> str:
    """
    Returns a line of 'latex_code' that has been formatted for the 'aligned' environment
    """
    a = "{"
    b = "}"
    text = "\\textrm"
    # opening = f"\\begin{a}{environment}{b}\n"
    conditional = f"&{text}{a}Since, {b}{latex_code}:\\\\\n"
    # end = f"\\end{a}{environment}{b}\n"
    conditional_line = f"{conditional}"
    return conditional_line


    
    # cell.lines = render_latex_reprs(cell.lines, cell.precision)
    # cell.latex_code = render_to_string(cell.lines)

# def render_latex_reprs(latex_dict: dict, precision: int) -> dict:
#     """
#     Returns the line-by-line latex code in latex_dict compiled into a
#     str for rendering. Floats and other numerical objects are rounded
#     and converted into appropriate strings for display.
#     """
#     latex_lines = {}
#     for line_num, line_data in latex_dict.items():
#         line = line_data["line"]
#         ltype = line_data["type"]
#         if not line:
#             continue
#         elif "calc" in ltype:
#             latex_line = round_resulting_values(line, precision)
#             latex_lines.update(
#                 {line_num: {"line": " ".join(latex_line), "type": ltype}}
#             )

#         elif ltype == "parameter":
#             latex_line = round_resulting_values(line, precision)
#             latex_lines.update(
#                 {line_num: {"line": " ".join(latex_line), "type": ltype}}
#             )
#         elif ltype == "conditional":
#             # 'line' structure for 'ltype' == "conditional":
#             # [[condition],[[[expression_1 if true], [result of expression]],
#             #             [[expression_2 if true], [result of expression]]]]
#             condition = line[0]
#             expressions = line[1]
#             conditioned = round_resulting_values(condition, precision)
#             expr_acc = deque([])
#             for expression in expressions:
#                 expr, result = expression
#                 expr_rep = round_resulting_values(expr, precision)
#                 result_rep = round_resulting_values(result, precision)
#                 combined = expr_rep + result_rep
#                 expr_acc.append(combined)
#             latex_lines.update(
#                 {
#                     line_num: {
#                         "line": [[" ".join(conditioned)], [expr_acc]],
#                         "type": ltype,
#                     }
#                 }
#             )
#         else:
#             latex_lines.update({line_num: {"line": line, "type": ltype}})
#     return latex_lines



def split_conditional(line: str):
    raw_conditional, raw_expressions = line.split(":")
    expr_deque = deque(raw_expressions.split(";"))  # handle multiple lines in cond
    cond_type, condition = raw_conditional.split(" ", 1)
    cond_type = cond_type.strip().lstrip()
    condition = condition.strip().lstrip()
    try:
        cond = expr_parser(condition)
    except pp.ParseException:
        cond = deque([condition])

    expr_acc = deque([])
    for line in expr_deque:
        try:
            expr = expr_parser(line.strip())
        except pp.ParseException:
            expr = [line.strip()]
        expr_acc.append(expr)

    return (
        cond,
        cond_type,
        expr_acc,
        condition,
        raw_expressions,
    )

def split_expressions(d: deque) -> deque:
    """
    Return d with symbolics and numerics swapped for the list of 
    calculations/expressions within d
    """
    pass

def subbed_results_indexes(line: deque) -> Tuple[int]:
    """
    Returns a 2-tuple of ints that represent the index location of the 
    two "=" within line.
    """
    acc = []
    for idx, component in enumerate(line):
        if component == "=":
            acc.append(idx)
    return tuple(acc)


def subbed_results_line(line: deque) -> deque:
    """
    Returns a deque that contains only the portion of the `line` that
    contains the substituted results, between the two "=" signs.
    """
    first_equals, second_equals = subbed_results_indexes(line)

    return deque(list(line)[first_equals : second_equals + 1])


# TODO: Ignore or deal with inline comments; deal with headings


def python_to_latex_conversion(parsed_results: dict, calculated_results: dict) -> dict:
    """
    Coordinates the conversion of the data in parsed_results into latex.
    Stores the output in self._latex after performing the conversion
    with module functions.
    """
    latex_results = {}
    calc_results = calculated_results
    swap_conditional = ConditionalEvaluator()  # Helper class as stateful function
    for line_num, line_data in parsed_results.items():
        ltype = line_data["type"]  # str
        line = line_data["line"]  # deque
        comment = line_data["comment"]
        if comment:
            comment = format_strings(comment, comment=True)
        else:
            comment = deque([])
        if ltype == "heading":
            new_line = swap_headings(line)
        elif ltype == "note":
            new_line = line
        # TODO: Deal with parameter lines
        elif ltype == "parameter":
            # print(line, comment)
            new_line = line + comment
        elif ltype == "conditional":
            condition, expressions = line
            true_cond = swap_conditional(
                condition, line_data["raw conditional"], calc_results
            )
            if true_cond:
                expr_acc = deque([])
                for expr in expressions:
                    calcd_result = expr[1]
                    expr = expr[0]  # break out of nested deque
                    symbolic_portion, numeric_portion = swap_calculation(
                        expr, calc_results
                    )
                    expr_acc.append([symbolic_portion + numeric_portion, calcd_result])
                new_line = deque([true_cond, expr_acc]) + comment
            else:
                new_line = deque([])

        elif ltype == "normal calc":
            expr, calcd_result = line
            calcd_result = deque(calcd_result)
            symbolic_portion, numeric_portion = swap_calculation(expr, calc_results)
            # May need to fine-tune what part of 'line' gets submitted to these functions
            new_line = symbolic_portion + numeric_portion + calcd_result + comment

        elif ltype == "long calc":
            expr, calcd_result = line
            calcd_result = deque(calcd_result)
            symbolic_portion, numeric_portion = swap_calculation(expr, calc_results)
            new_line = format_long_calc_lines(
                symbolic_portion, numeric_portion, calcd_result
            )
        latex_results.update({line_num: {"line": new_line, "type": ltype}})
    return latex_results

def test_long_line_of_math(line: deque, calculated_results: dict) -> Tuple[bool, int]:
    """
    Return a Tuple[bool, int] that indicates whether the substituted values of `line`
    will be over the character threshold. int represents the number of characters counted
    in the str representation of the substituted values. 
    """
    # discount_fraction_chars(line, calculated_results)
    count = 0
    recurse_bool = False
    count_bool = False
    new_bool = False
    for component in line:
        if isinstance(component, deque):
            new_bool, new_count = test_long_line_of_math(component, calculated_results)
            count += new_count
            recurse_bool = recurse_bool or new_bool
        elif isinstance(component, (float, int)):
            count += len(str(component))
        elif isinstance(component, str):
            substitution = calculated_results.get(component, component)
            count += len(str(substitution))
    if count > 65:
        count_bool = True
    if count_bool or recurse_bool:
        return (True, count)
    else:
        return (False, count)


def count_subbed_chars_in_equation(line: deque, calculated_results: dict) -> deque:
    """
    Returns a deque of int representing the length of the substituted values in
    `line`. Each int represents the total length of the strs within one 
    set of nested parentheses, deeper parentheses first.
    e.g.
    count_subbed_chars_in_equation(
        ['234', '+', '958', '+', ['1234', '+', '2345', '+', '0942']]
        )
    returns [14, 8]
    """
    count = 0
    count_deque = deque([])
    for component in line:
        if isinstance(component, deque):
            count_deque.append(
                count_subbed_chars_in_equation(component, calculated_results)
            )
        elif isinstance(component, (float, int)):
            count += len(str(component))
        elif isinstance(component, str):
            substitution = calculated_results.get(component, component)
            count += len(str(substitution))
    count_deque.append(count)
    return count_deque


def format_long_calc_lines(
    symbolic_portion: deque, numeric_portion: deque, result_value: deque
):
    full_equation = symbolic_portion + numeric_portion + result_value
    equation_in_multline_env = insert_multline_environment(full_equation)
    with_gathered_envs = insert_gathered_environments(equation_in_multline_env)
    with_line_breaks = break_long_equations(with_gathered_envs)
    return with_line_breaks  # + result_value




def break_long_equations(flattened_deque: deque) -> deque:
    """
    Returns a deque that matches `line` except with a linebreak character inserted
    after the next mathematical operator after the character count of items within
    `line` exceeds the threshold
    """
    # TODO: Create test for appropriate palcement of linebreaks
    line_break = "{}\\\\\n"
    str_lengths = count_str_len_in_deque(flattened_deque, omit_latex=True, dive=False)
    sum_of_lengths = 0
    acc = deque([])
    exclusions = ("\\right)", "\\cdot", "}")
    insert_next = False
    discount = discount_fraction_chars(flattened_deque)
    for idx, length in enumerate(str_lengths):
        component = flattened_deque[idx]
        next_idx = min(idx + 1, len(flattened_deque) - 1)
        next_component = flattened_deque[next_idx]
        if "\\" in str(component):
            acc.append(component)
        elif (
            str(component) == "+" or str(component) == "-" or str(component) == "\\cdot"
        ):
            if insert_next:
                acc.append(component)
                acc.append(line_break)
                insert_next = False
            else:
                acc.append(component)
        else:
            acc.append(component)
            sum_of_lengths += length
            if (
                sum_of_lengths > 60
                and (
                    str(component) not in exclusions
                    or str(next_component) not in exclusions
                )
                and (str(next_component) == "+" or str(next_component) == "-")
            ):  # Hard-coded value
                insert_next = True
                sum_of_lengths = 0
    return acc


def insert_gathered_environments(line: deque) -> deque:
    """
    Returns 'line' with "\\begin{gathered}" environments inserted at the beginning
    of nested deques within 'line' and at the end of nested deques within 'line'.

    @param line:
    @return:
    """
    beg_gathered = "\\begin{gathered}"
    end_gathered = "\\end{gathered}"
    acc = []
    left_trigger = "\\left("
    sqrt_trigger = "\\sqrt{"
    right_trigger = "\\right)"
    brace_trigger = "}"
    sqrt_stack = deque([])
    equals = 0
    for component in line:
        if str(component) == "=" or str(component) == "&=":
            equals += 1
        if 1 <= equals <= 2:
            if (
                (
                    "{" in str(component)
                    or (
                        str(component) == left_trigger or str(component) == sqrt_trigger
                    )
                )
                and "_" not in component
                and component != "}{"
            ):
                if str(component) == left_trigger:
                    sqrt_stack.append(0)
                    acc.append(component)
                    acc.append(beg_gathered)
                elif str(component) == sqrt_trigger:
                    sqrt_stack.append(1)
                    acc.append(component)
                    acc.append(beg_gathered)
                else:
                    sqrt_stack.append(0)
                    acc.append(component)
            elif str(component) in (brace_trigger, right_trigger):
                sqrt_close_trigger = sqrt_stack.pop()
                if sqrt_close_trigger and str(component) == brace_trigger:
                    acc.append(end_gathered)
                    acc.append(component)
                elif str(component) == right_trigger:
                    acc.append(end_gathered)
                    acc.append(component)
                else:
                    acc.append(component)
            else:
                acc.append(component)
        else:
            acc.append(component)
    return acc


def insert_multline_environment(line: deque) -> deque:
    """
    Returns `line` with a gathered environment inserted at the edges of the 

    """
    beg_gathered = "\\begin{gathered}\n"
    end_gathered = "\n\\end{gathered}\n"
    beg_aligned = "\\[\n\\begin{aligned}\n"
    end_aligned = "\\end{aligned}\n\\]\n"
    beg_multline = "\\begin{multline}\n"
    end_multline = "\n\\end{multline}\n"
    char_count = 0
    acc = deque([])
    # print("full runs")
    equals = 0
    for component in line:
        # print(component)
        if str(component) == "=" or str(component) == "&=" and equals == 0:
            equals += 1
            acc.append("=")
        elif str(component) == "=" or str(component) == "&=" and equals == 1:
            acc.append("\\\\=")
        else:
            acc.append(component)
    # print(acc)

    acc.appendleft(beg_multline)
    acc.appendleft(end_aligned)
    acc.append(end_multline)
    acc.append(beg_aligned)
    return acc


def count_str_len_in_deque(d: deque, omit_latex=True, dive=True) -> deque:
    """
    Returns `l` with each item in `l` being replaced with an int that
    represents the length of each item in `l`.
    If 'omit_latex' is True, then any components with latex symbols
    will not be counted.
    If 'dive' is True, then the function will recursively count strs
    in nested deques.
    """
    acc = deque([])
    for component in d:
        if isinstance(component, (deque, list)) and dive:
            acc.append(count_str_len_in_deque(component, omit_latex, dive))
        elif isinstance(component, (deque, list)) and not dive:
            acc.append([])
        elif str(component).startswith("\\"):
            if omit_latex:
                acc.append(0)
            else:
                acc.append(len(str(component).replace("_", "")))
        else:
            acc.append(len(str(component).replace("_", "")))
    return acc


def count_fraction_chars(flattened_deque: deque) -> deque:
    """
    Returns a deque representing the character counts in 'd' that belong
    within a fraction.
    """
    frac_stack = deque([])
    count_stack = deque([])
    equals = 0
    for idx, component in enumerate(flattened_deque):
        component = str(component)
        if "=" in str(component):
            equals += 1
            continue
        if 1 <= equals <= 2:
            if "{" in component and "_" not in component and "}" not in component:
                if component == "\\frac{":
                    frac_stack.append(1)
                    count_stack.append("Numerator")
                else:
                    frac_stack.append(0)
            elif component == "}{":
                count_stack.append("End")
                count_stack.append("Denominator")
            elif "}" in component and "{" not in component:
                frac_end_trigger = frac_stack.pop()
                if frac_end_trigger:
                    count_stack.append("End")
            else:
                if "_" in component:
                    if "\\" not in component:
                        split_subs = (
                            component.replace("{", "").replace("}", "").split("_")
                        )
                        count_stack.append(len("".join(split_subs)))
                    else:
                        split_subs = (
                            component.replace("{", "").replace("}", "").split("_")
                        )
                        count_stack.append(len("".join(split_subs[1:])) + 1)
                elif "\\" in component:
                    if component == "\\cdot":
                        count_stack.append(1)
                    elif component == "\\pi":
                        count_stack.append(1)
                    elif "operatorname" in component:
                        func_name = component.replace("\\operatorname{", "").replace(
                            "}", ""
                        )
                        count_stack.append(len(func_name))
                else:
                    count_stack.append(len(component))
    return count_stack


def discount_fraction_chars(flattened_deque: deque) -> int:
    """
    Returns an int representing the number of chars

    @param d:
    @return:
    """
    frac_counts = count_fraction_chars(flattened_deque)
    tally = 0
    num_count = 0
    denom_count = 0
    in_num = False
    in_denom = False
    for item in frac_counts:
        if item == "Numerator":
            in_num = True
            if num_count > denom_count:
                tally += num_count - denom_count
            elif num_count < denom_count:
                tally += denom_count - num_count
            else:
                tally += num_count
            num_count = 0
        elif item == "Denominator":
            denom_count = 0
        elif item == "End":
            if in_num:
                in_num = False
            elif in_denom:
                in_denom = False
            continue
        else:
            if in_num:
                num_count += item
            elif in_denom:
                denom_count += item
    return tally


def sum_str_len_in_deque(d: deque, omit_latex=True, dive=True) -> int:
    """
    Returns the cumulative sum of len(str) nested deques in d.
    """
    counts = count_str_len_in_deque(d, omit_latex)
    cum_sum = 0
    for count in counts:
        if isinstance(count, deque) and dive:
            cum_sum += sum_str_len_in_deque(count, omit_latex, dive)
        elif isinstance(count, deque) and not dive:
            pass
        else:
            cum_sum += count
    return cum_sum


def test_for_parameter_line(line: str) -> bool:
    """
    Returns True if `line` appears to be a line to simply declare a
    parameter (e.g. "a = 34") instead of an actual calculation.
    """
    if not line.strip():
        return False
    elif "=" not in line or "if" in line:
        return False
    else:
        _, right_side = line.split("=")
        right_side.replace(" ", "")
        if right_side.find("(") == 0 and right_side.find(")") == (len(right_side) + 1):
            return True
        try:
            expr_as_code = code_reader(line)
            if len(expr_as_code) == 3 and expr_as_code[1] == "=":
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


def test_for_output_cell(raw_python_source: str) -> bool:
    """
    Returs True if the text "# Out" is in the first line of 
    'raw_python_source'. False otherwise.
    """
    first_element = raw_python_source.split("\n")[0]
    if "#" in first_element and "out" in first_element.lower():
        return True
    return False


def split_parameter_line(line: str, calculated_results: dict) -> deque:
    """
    Return 'line' as a deque that represents the line as: 
        deque([<parameter>, "&=", <value>])
    """
    param = line.replace(" ", "").split("=")[0]
    param_line = deque([param, "&=", calculated_results[param]])
    return param_line

def parse_parameter_line(line: str, calculated_results: dict) -> deque:
    """
    Returns a 'line' with any symbols for the parameter name swapped out
    """
    return swap_symbolic_calcs(line)
    # print("Runs: ", swapped_param_symbols)


def parse_output_line(python_line: str, calculated_results: dict) -> deque:
    """
    Returns a 'line' with any symbols for the parameter name swapped out
    """
    param = python_line.replace(" ", "")
    param_line = deque([param, "&=", calculated_results[param]])
    swapped_param_symbols = swap_symbolic_calcs(param_line)
    # print("Runs: ", swapped_param_symbols)
    return swapped_param_symbols


def parse_parameter_cell(param_cell: ParameterCell) -> ParameterCell:
    """
    Return a str representing the latex code conversion of `raw_python_code` which
    consists entirely of a "Parameters" cell; a Jupyter cell containing only 
    variable assignments that begins with a "# Parameters" comment.

    This is an alternate end point to the latex() function.
    """
    param_cell.outgoing_lines = deque(param_cell.source.split("\n"))
    param_lines = param_cell.outgoing_lines
    param_lines.popleft()  # Omit "# Parameters" line
    removed_blank_lines = [line for line in param_lines if line.strip() != ""]
    incoming = deque([])
    for line in removed_blank_lines:
        param_line = parse_parameter_line(line, param_cell.calculated_results)
        incoming.append(param_line)
    param_cell.incoming_lines = incoming
    return param_cell


def parse_output_cell(out_cell: OutputCell) -> OutputCell:

    # raw_python_source: str, calculated_results: dict, precision: int, cols: int = 3
    # ) -> str:
    """
    Return a str representing the latex code conversion of `raw_python_code` which
    consists entirely of a "Parameters" cell; a Jupyter cell containing only 
    variable assignments that begins with a "# Parameters" comment.

    This is an alternate end point to the latex() function.
    """
    source = out_cell.source
    precision = out_cell.precision
    calculated_results = out_cell.calculated_results
    out_cell.outgoing_lines = deque(source.split("\n"))
    out_cell.outgoing_lines.popleft()  # Omit "# Output" line
    removed_blank_lines = [
        line for line in out_cell.outgoing_lines if line.strip() != ""
    ]
    incoming = deque([])
    for line_num, line in enumerate(removed_blank_lines):
        param_line = parse_output_line(line, calculated_results)
        incoming.append(param_line)
    out_cell.incoming_lines = incoming
    return out_cell






def format_strings(string: str, comment: bool) -> deque:
    """
    Returns 'string' appropriately formatted to display in a latex
    math environment.
    """
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

    return deque([text_env, l_par, string.strip().rstrip(), r_par, end_env])





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


def round_resulting_values(line_of_code: deque, precision: int) -> deque:
    """
    Returns a rounded str based on the latex_repr of an object in
    'line_of_code'
    """
    line_of_strs = deque([])
    for item in line_of_code:
        #if isinstance(item, deque):
        #    return round_resulting_values(item, precision)  # Recursion!
        if not isinstance(item, (str, int)):
            try:
                rounded = round(item, precision)
            except:
                rounded = item
            line_of_strs.append(latex_repr(rounded))
        else:
            line_of_strs.append(str(item))
    return line_of_strs


def latex_repr(result: Any) -> str:
    """
    Return a str if the object in 'result' has a special repr method
    for rendering itself in latex. If not, returns str(result).
    """
    if hasattr(result, "hc_latex"):
        try:
            return result.hc_latex()
        except TypeError:
            return str(result)

    elif hasattr(result, "_repr_latex_"):
        return result._repr_latex_()

    elif hasattr(result, "latex"):
        try:
            return result.latex()
        except TypeError:
            str(result)

    elif hasattr(result, "to_latex"):
        try:
            return result.to_latex()
        except TypeError:
            str(result)

    else:
        return str(result)


def swap_headings(heading: str) -> str:
    """
    Returns a tex formatted heading for the raw string supplied in 'heading'.
    Possible values for the tex formatting are hard-coded into this function.
    """
    latex_emphasis = {
        1: "\\section*",
        2: "\\subsection*",
        3: "\\subsubsection*",
        4: "\\boldface",
    }
    emphasis = heading.count("#")
    comment = heading.lstrip().replace("#", "")
    return "{}{}{}{}".format(latex_emphasis[emphasis], "{", comment, "}")


def format_notes(note: str, environment: str) -> str:
    """
    Returns a tex formatted note from the raw string supplied in 'note'.
    """
    backs = "\\"
    a = "{"
    b = "}"
    note = note.replace('"', "")
    formatted = f"{backs}{environment}{a}{note}{b}"
    return formatted


# def swap_conditional(conditional: deque, raw_conditional: str, calc_results: dict) -> deque:
#     """
#     Returns the deque, 'conditional' if the conditional statement
#     evaluates as True based on the data in calc_results.
#     Returns an empty deque, otherwise.
#     This to ensure that unnecessary conditional statements are not
#     printed in the final results.
#     """
#     # print(raw_conditional)
#     result = eval_conditional(raw_conditional, **calc_results)
#     if result == True:
#         l_par = "\\left("
#         r_par = "\\right)"
#         symbolic_portion = swap_symbolic_calcs(conditional)
#         numeric_portion = swap_numeric_calcs(conditional, calc_results)
#         resulting_latex = deque([
#             symbolic_portion + deque(["\\rightarrow"]) + deque([l_par]) + numeric_portion + deque([r_par])
#         ])
#         return resulting_latex
#     else:
#         return deque([])


class ConditionalEvaluator:
    def __init__(self):
        self.prev_cond_type = ""
        self.prev_result = False

    def __call__(
        self, conditional: deque, conditional_type: str, raw_conditional: str, calc_results: dict
    ) -> deque:
        if conditional_type != "else":
            result = eval_conditional(raw_conditional, **calc_results)
        else:
            result = True
        # print(f"cond_type: {cond_type}, condition: {condition}, prev_cond_type: {self.prev_cond_type}, prev_result: {self.prev_result}, result: {result}, check_cond_type: {self.check_prev_cond_type(cond_type)}")
        if (
            result == True
            and self.check_prev_cond_type(conditional_type)
            and not self.prev_result
        ) or (self.prev_result == True and not self.check_prev_cond_type(conditional_type)):
            l_par = "\\left("
            r_par = "\\right)"
            if conditional_type != "else":
                symbolic_portion = swap_symbolic_calcs(conditional)
                numeric_portion = swap_numeric_calcs(conditional, calc_results)
                resulting_latex = deque(
                    [
                        symbolic_portion
                        + deque(["\\rightarrow"])
                        + deque([l_par])
                        + numeric_portion
                        + deque([r_par])
                    ]
                )
            else:
                numeric_portion = swap_numeric_calcs(conditional, calc_results)
                resulting_latex = numeric_portion
            self.prev_cond_type = conditional_type
            self.prev_result = result
            return resulting_latex
        else:
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


def swap_arrays():
    pass


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
                # print(item)
                # print(next_item)
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
                # print(function_source)
                source_deque = expr_parser(function_source)
                a = next_item[2]
                b = next_item[4]
                # print(a, b)
                l_br = "{"
                r_br = "}"
                integral = f"\\int_{l_br}{a}{r_br}^{l_br}{b}{r_br}"
                # print(integral)
                # print(source_deque)
                swapped_deque.append(integral)
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
        """Returns elements from a deque and flattens elements from sub-deques"""
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
    # eol = pp.Word(";")
    func = pp.Word(pp.srange("[A-Za-z0-9_.]")) + pp.FollowedBy(
        pp.Word(pp.srange("[A-Za-z0-9_()]"))
    )
    string = pp.Word(pp.srange("[A-Za-z0-9'\"]"))
    group = term ^ operator ^ func ^ string
    # parenth = pp.nestedExpr(content=group ^ eol)
    parenth = pp.nestedExpr(content=group)
    master = group ^ parenth
    expr = pp.OneOrMore(master)
    return list_to_deque(expr.parseString(expr_as_str).asList())


def get_latex_method(o: object):
    """Returns a bound method of the object, 'o', if 'o' has
    a method name containing the string, 'latex'.
    This is a crap-shoot to test if an evaluated value is an object that
    has such a method that would be convenient for display.
    Returns None otherwise."""
    for method in dir(o):
        if "latex" in method:
            return getattr(o, method)


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
        prev_idx = max(0, index - 1)
        next_item = pycode_as_deque[next_idx]
        if type(item) is deque:
            new_item = swap_math_funcs(item)  # recursion!
            swapped_deque.append(new_item)
            if close_bracket_token:
                swapped_deque.append(b)
                close_bracket_token = False
        elif close_bracket_token:
            swapped_deque.append(latex_math_funcs.get(item, item))
            new_item = f"{b}"
            close_bracket_token = False
            swapped_deque.append(new_item)
        elif (
            isinstance(next_item, deque)
            and item.isalpha()
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
    length = len(pycode_as_deque)
    for index, item in enumerate(pycode_as_deque):
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
        # print(item == "**", "**" in str(item))
        # if item != "**" and "**" in str(item):
        #     print(str(item))
        if isinstance(item, deque) and not close_bracket_token:
            new_item = swap_superscripts(item)  # recursion!
            pycode_with_supers.append(new_item)
        elif not isinstance(next_item, deque) and "**" in str(
            next_item
        ):  # next_item == "**":#"**" in str(next_item):
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
        ):  # prev_item == "**":
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
    # "eta" and "psi" need to be last on the list b/c they are substrings of "theta" and "epsilon"
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
        "eta",
        "psi",
    ]
    pycode_with_greek = deque([])
    for item in pycode_as_deque:
        if isinstance(item, deque):
            new_item = swap_for_greek(item)  # recursion!
            pycode_with_greek.append(new_item)
        elif isinstance(item, str):
            for letter in greeks:
                if letter in item.lower():
                    new_item = "\\" + item.replace("amb", "ambda")
                    pycode_with_greek.append(new_item)
                    break
            else:
                pycode_with_greek.append(item)
        else:
            pycode_with_greek.append(item)
    return pycode_with_greek


def swap_values(pycode_as_deque: deque, tex_results: dict) -> deque:
    """
    Returns a the 'pycode_as_deque' with any symbolic terms swapped out for their corresponding
    values.
    """
    swapped_values = deque([])
    for item in pycode_as_deque:
        swapped_value = ""
        if isinstance(item, deque):
            swapped_values.append(swap_values(item, tex_results))
        else:

            try:
                swapped_value = tex_results.get(item, item)
            except:
                breakpoint()
            if isinstance(swapped_value, str) and swapped_value != item:
                swapped_value = format_strings(swapped_value, comment=False)
            swapped_values.append(swapped_value)
    return swapped_values


#  def format_full_multline(latex_code: str, environment: str) -> str:
#      """
#      Returns a line of latex code that has been broken up into a \multiline with line
#      breaks at each '=' sign.
#      """
#      a = "{"
#      b = "}"

#      # Align with '\\' for '\multline'
#      latex_code = latex_code.replace("=", r"\\=")
#      latex_code = latex_code.replace(r"\\=", "=", 1)
#      long_line = f"\\begin{a}{environment}{b}\n{latex_code}\n\\end{a}{environment}{b}\n"
#      return long_line



