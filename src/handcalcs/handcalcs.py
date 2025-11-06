# #    Copyright 2020 Connor Ferster

# #    Licensed under the Apache License, Version 2.0 (the "License");
# #    you may not use this file except in compliance with the License.
# #    You may obtain a copy of the License at

# #        http://www.apache.org/licenses/LICENSE-2.0

# #    Unless required by applicable law or agreed to in writing, software
# #    distributed under the License is distributed on an "AS IS" BASIS,
# #    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# #    See the License for the specific language governing permissions and
# #    limitations under the License.

# from collections import deque
# from functools import singledispatch
# import itertools
# import math
# from typing import Any, Union
# import pyparsing as pp

# from handcalcs.constants import GREEK_UPPER, GREEK_LOWER
# from handcalcs import global_config
# from handcalcs.integrations import DimensionalityError
# from handcalcs.calcline import CalcLine, IntertextLine


# @singledispatch
# def add_result_values_to_line(line_object, calculated_results: dict):
#     raise TypeError(
#         f"Line object, {type(line_object)} is not recognized yet in add_result_values_to_line()"
#     )


# @add_result_values_to_line.register(CalcLine)
# def results_for_calcline(line_object, calculated_results):
#     parameter_name = line_object.line[0]
#     resulting_value = dict_get(calculated_results, parameter_name)
#     line_object.line.append(deque(["=", resulting_value]))
#     return line_object


# @add_result_values_to_line.register(IntertextLine)
# def results_for_intertext(line_object, calculated_results):
#     return line_object


# @singledispatch
# def convert_line(
#     line_object,
#     calculated_results: dict,
#     **config_options,
# ):
#     """
#     Returns 'line_object' with its .line attribute converted into a
#     deque with elements that have been converted to their appropriate
#     Latex counterparts.

#     convert_line() runs the deque through all of the conversion functions
#     as organized in `swap_calculation()`.
#     """
#     raise TypeError(
#         f"Cell object {type(line_object)} is not yet recognized in convert_line()"
#     )


# @convert_line.register(CalcLine)
# def convert_calc(line, calculated_results, **config_options):
#     (
#         *line_deque,
#         result,
#     ) = line.line  # Unpack deque of form [[calc_line, ...], ['=', 'result']]
#     symbolic_portion, numeric_portion = swap_calculation(
#         line_deque, calculated_results, **config_options
#     )
#     line.line = symbolic_portion + numeric_portion + result
#     return line


# @convert_line.register(IntertextLine)
# def convert_intertext(line, calculated_results, **config_options):
#     return line


# @singledispatch
# def format_cell(cell_object, **config_options):
#     raise TypeError(
#         f"Cell type {type(cell_object)} has not yet been implemented in format_cell()."
#     )


# @format_cell.register(ParameterCell)
# def format_parameters_cell(cell: ParameterCell, **config_options):
#     """
#     Returns the input parameters as an \\align environment with 'cols'
#     number of columns.
#     """
#     cols = config_options["param_columns"]
#     if cell.precision is None:
#         precision = config_options["display_precision"]
#     else:
#         precision = cell.precision
#     cell_notation = toggle_scientific_notation(
#         config_options["use_scientific_notation"], cell.scientific_notation
#     )
#     opener = config_options["latex_block_start"]
#     begin = f"\\begin{{{config_options['math_environment_start']}}}"
#     end = f"\\end{{{config_options['math_environment_end']}}}"
#     closer = config_options["latex_block_end"]
#     line_break = f"{config_options['line_break']}\n"
#     cycle_cols = itertools.cycle(range(1, cols + 1))
#     for line in cell.lines:
#         line = round_and_render_line_objects_to_latex(
#             line, precision, cell_notation, **config_options
#         )
#         line = format_lines(line, **config_options)
#         if isinstance(line, BlankLine):
#             continue
#         if isinstance(line, ConditionalLine):
#             outgoing = deque([])
#             for expr in line.true_expressions:
#                 current_col = next(cycle_cols)
#                 if current_col % cols == 0:
#                     outgoing.append("&" + expr + line_break)
#                 elif current_col % cols != 1:
#                     outgoing.append("&" + expr)
#                 else:
#                     outgoing.append(expr)
#             line.latex_expressions = " ".join(outgoing)
#             line.latex = line.latex_condition + line.latex_expressions
#         else:
#             latex_param = line.latex

#             current_col = next(cycle_cols)
#             if current_col % cols == 0:
#                 line.latex = "&" + latex_param + line_break
#             elif current_col % cols != 1:
#                 line.latex = "&" + latex_param
#             else:
#                 line.latex = latex_param

#     latex_block = " ".join(
#         [line.latex for line in cell.lines if not isinstance(line, BlankLine)]
#     ).rstrip()  # .rstrip(): Hack to solve another problem of empty lines in {aligned} environment
#     cell.latex_code = "\n".join([opener, begin, latex_block, end, closer])
#     return cell


# @format_cell.register(CalcCell)
# def format_calc_cell(cell: CalcCell, **config_options) -> str:
#     line_break = f"{config_options['line_break']}\n"
#     if cell.precision is None:
#         precision = config_options["display_precision"]
#     else:
#         precision = cell.precision
#     cell_notation = toggle_scientific_notation(
#         config_options["use_scientific_notation"], cell.scientific_notation
#     )
#     incoming = deque([])
#     for line in cell.lines:
#         line = round_and_render_line_objects_to_latex(
#             line, precision, cell_notation, **config_options
#         )
#         line = convert_applicable_long_lines(line)
#         line = format_lines(line, **config_options)
#         incoming.append(line)
#     cell.lines = incoming

#     latex_block = line_break.join([line.latex for line in cell.lines if line.latex])
#     opener = config_options["latex_block_start"]
#     begin = f"\\begin{{{config_options['math_environment_start']}}}"
#     end = f"\\end{{{config_options['math_environment_end']}}}"
#     closer = config_options["latex_block_end"]
#     cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
#         "\n" + end, end
#     )
#     return cell


# @format_cell.register(ShortCalcCell)
# def format_shortcalc_cell(cell: ShortCalcCell, **config_options) -> str:
#     incoming = deque([])
#     line_break = f"{config_options['line_break']}\n"
#     if cell.precision is None:
#         precision = config_options["display_precision"]
#     else:
#         precision = cell.precision
#     cell_notation = toggle_scientific_notation(
#         config_options["use_scientific_notation"], cell.scientific_notation
#     )
#     for line in cell.lines:
#         line = round_and_render_line_objects_to_latex(
#             line, precision, cell_notation, **config_options
#         )
#         line = format_lines(line, **config_options)
#         incoming.append(line)
#     cell.lines = incoming

#     latex_block = line_break.join([line.latex for line in cell.lines if line.latex])
#     opener = config_options["latex_block_start"]
#     begin = f"\\begin{{{config_options['math_environment_start']}}}"
#     end = f"\\end{{{config_options['math_environment_end']}}}"
#     closer = config_options["latex_block_end"]
#     cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
#         "\n" + end, end
#     )
#     return cell


# @format_cell.register(LongCalcCell)
# def format_longcalc_cell(cell: LongCalcCell, **config_options) -> str:
#     line_break = f"{config_options['line_break']}\n"
#     if cell.precision is None:
#         precision = config_options["display_precision"]
#     else:
#         precision = cell.precision
#     cell_notation = toggle_scientific_notation(
#         config_options["use_scientific_notation"], cell.scientific_notation
#     )
#     incoming = deque([])
#     for line in cell.lines:
#         line = round_and_render_line_objects_to_latex(
#             line, precision, cell_notation, **config_options
#         )
#         line = convert_applicable_long_lines(line)
#         line = format_lines(line, **config_options)
#         incoming.append(line)
#     cell.lines = incoming

#     latex_block = line_break.join([line.latex for line in cell.lines if line.latex])
#     opener = config_options["latex_block_start"]
#     begin = f"\\begin{{{config_options['math_environment_start']}}}"
#     end = f"\\end{{{config_options['math_environment_end']}}}"
#     closer = config_options["latex_block_end"]
#     cell.latex_code = "\n".join([opener, begin, latex_block, end, closer]).replace(
#         "\n" + end, end
#     )
#     return cell


# @singledispatch
# def round_and_render_line_objects_to_latex(
#     line: Union[CalcLine, IntertextLine],
#     cell_precision: int,
#     cell_notation: bool,
#     **config_options,
# ):  # Not called for symbolic lines; see format_symbolic_cell()
#     """
#     Returns 'line' with the elements of the deque in its .line attribute
#     converted into their final string form for rendering (thereby preserving
#     its intermediate step) and populates the
#     .latex attribute with the joined string from .line.

#     'precision' is the number of decimal places that each object should
#     be rounded to for display.
#     """
#     raise TypeError(
#         f"Line type {type(line)} not recognized yet in round_and_render_line_objects_to_latex()"
#     )


# @round_and_render_line_objects_to_latex.register(CalcLine)
# def round_and_render_calc(
#     line: CalcLine, cell_precision: int, cell_notation: bool, **config_options
# ) -> CalcLine:
#     idx_line = line.line
#     precision = cell_precision
#     use_scientific_notation = toggle_scientific_notation(
#         config_options["use_scientific_notation"], cell_notation
#     )
#     preferred_formatter = config_options["preferred_string_formatter"]
#     rendered_line = render_latex_str(
#         idx_line, use_scientific_notation, precision, preferred_formatter
#     )
#     rendered_line = swap_dec_sep(rendered_line, config_options["decimal_separator"])
#     line.line = rendered_line
#     line.latex = " ".join(rendered_line)
#     return line


# @round_and_render_line_objects_to_latex.register(LongCalcLine)
# def round_and_render_longcalc(
#     line: LongCalcLine, cell_precision: int, cell_notation: bool, **config_options
# ) -> LongCalcLine:
#     idx_line = line.line
#     precision = cell_precision
#     use_scientific_notation = toggle_scientific_notation(
#         config_options["use_scientific_notation"], cell_notation
#     )
#     preferred_formatter = config_options["preferred_string_formatter"]
#     rendered_line = render_latex_str(
#         idx_line, use_scientific_notation, precision, preferred_formatter
#     )
#     rendered_line = swap_dec_sep(rendered_line, config_options["decimal_separator"])
#     line.line = rendered_line
#     line.latex = " ".join(rendered_line)
#     return line


# @round_and_render_line_objects_to_latex.register(ConditionalLine)
# def round_and_render_conditional(
#     line: ConditionalLine, cell_precision: int, cell_notation: bool, **config_options
# ) -> ConditionalLine:
#     conditional_line_break = f"{config_options['line_break']}\n"
#     outgoing = deque([])
#     idx_line = line.true_condition
#     precision = cell_precision
#     use_scientific_notation = toggle_scientific_notation(
#         config_options["use_scientific_notation"], cell_notation
#     )
#     preferred_formatter = config_options["preferred_string_formatter"]
#     rendered_line = render_latex_str(
#         idx_line, use_scientific_notation, precision, preferred_formatter
#     )
#     rendered_line = swap_dec_sep(rendered_line, config_options["decimal_separator"])
#     line.line = rendered_line
#     line.latex = " ".join(rendered_line)
#     # return line
#     line.true_condition = rendered_line
#     for (
#         expr
#     ) in line.true_expressions:  # Each 'expr' item is a CalcLine or other line type
#         outgoing.append(
#             round_and_render_line_objects_to_latex(
#                 expr, cell_precision, cell_notation, **config_options
#             )
#         )
#     line.true_expressions = outgoing
#     line.latex = conditional_line_break.join(
#         [calc_line.latex for calc_line in outgoing]
#     )
#     return line


# @round_and_render_line_objects_to_latex.register(IntertextLine)
# def round_and_render_intertext(
#     line, cell_precision: int, cell_notation: bool, **config_options
# ):
#     return line


# def render_latex_str(
#     line_of_code: deque,
#     use_scientific_notation: bool,
#     precision: int,
#     preferred_formatter: str,
# ) -> deque:
#     """
#     Returns a rounded str based on the latex_repr of an object in
#     'line_of_code'
#     """
#     outgoing = deque([])
#     for item in line_of_code:
#         rendered_str = latex_repr(
#             item, use_scientific_notation, precision, preferred_formatter
#         )
#         outgoing.append(rendered_str)
#     return outgoing


# def latex_repr(
#     item: Any, use_scientific_notation: bool, precision: int, preferred_formatter: str
# ) -> str:
#     """
#     Return a str if the object, 'item', has a special repr method
#     for rendering itself in latex. If not, returns str(result).
#     """
#     # Check for arrays
#     if hasattr(item, "__len__") and not isinstance(item, (str, dict)):
#         comma_space = ",\\ "
#         try:
#             array = (
#                 "["
#                 + comma_space.join(
#                     [
#                         latex_repr(
#                             v, use_scientific_notation, precision, preferred_formatter
#                         )
#                         for v in item
#                     ]
#                 )
#                 + "]"
#             )
#             rendered_string = array
#             return rendered_string
#         except TypeError:
#             pass

#     # Check for sympy objects
#     if hasattr(item, "__sympy__"):
#         return render_sympy(round_sympy(item, precision, use_scientific_notation))

#     # Check for scientific notation strings
#     if isinstance(item, str) and test_for_scientific_float(item):
#         if "e-" in item:
#             rendered_string = swap_scientific_notation_str(item)
#         elif "e+" in item:
#             rendered_string = swap_scientific_notation_str(item)
#         elif "e" in item:
#             rendered_string = swap_scientific_notation_str(item.replace("e", "e+"))
#         return rendered_string

#     # Procedure for atomic data items
#     try:
#         if use_scientific_notation:
#             rendered_string = f"{item:.{precision}e{preferred_formatter}}"
#         else:
#             rendered_string = f"{item:.{precision}f{preferred_formatter}}"
#     except (ValueError, TypeError):
#         try:
#             if use_scientific_notation and isinstance(item, complex):
#                 rendered_real = f"{item.real:.{precision}e}"
#                 rendered_real = swap_scientific_notation_str(rendered_real)

#                 rendered_imag = f"{item.imag:.{precision}e}"
#                 rendered_imag = swap_scientific_notation_str(rendered_imag)

#                 rendered_string = (
#                     f"\\left( {rendered_real} + {rendered_imag} j \\right)"
#                 )
#             elif use_scientific_notation and not isinstance(item, int):
#                 rendered_string = f"{item:.{precision}e}"
#                 rendered_string = swap_scientific_notation_str(rendered_string)
#             elif not isinstance(item, int):
#                 rendered_string = f"{item:.{precision}f}"
#             else:
#                 rendered_string = str(item)
#         except (ValueError, TypeError):
#             try:
#                 rendered_string = item._repr_latex_()
#             except AttributeError:
#                 rendered_string = str(item)

#     return rendered_string.replace("$", "")


# def round_sympy(elem: Any, precision: int, use_scientific_notation: bool) -> Any:
#     """
#     Returns the Sympy expression 'elem' rounded to 'precision'
#     """
#     from sympy import Float

#     rule = {}
#     for n in elem.atoms(Float):
#         if use_scientific_notation:
#             rule[n] = round_for_scientific_notation(n, precision)
#         else:
#             rule[n] = round(n, precision)
#     rounded = elem.xreplace(rule)
#     if hasattr(elem, "units") and not hasattr(rounded, "units"):
#         # Add back pint units lost during rounding.
#         rounded = rounded * elem.units
#     return rounded


# def render_sympy(elem: Any) -> str:
#     """
#     Returns a string of the Latex representation of the sympy object, 'elem'.
#     """
#     from sympy import latex

#     return latex(elem)


# def round_for_scientific_notation(elem, precision):
#     """
#     Returns a float rounded so that the decimals behind the coefficient are rounded to 'precision'.
#     """
#     adjusted_precision = calculate_adjusted_precision(elem, precision)
#     rounded = round(elem, adjusted_precision)
#     return rounded


# def calculate_adjusted_precision(elem, precision):
#     """
#     Returns the number of decimal places 'elem' should be rounded to
#     to achieve a final 'precision' in scientific notation.
#     """
#     try:
#         power_of_ten = int(math.log10(abs(elem)))
#     except (DimensionalityError, TypeError):
#         elem_float = float(str(elem).split(" ")[0])
#         power_of_ten = int(math.log10(abs(elem_float)))
#     if power_of_ten < 1:
#         return precision - power_of_ten + 1
#     else:
#         return precision - power_of_ten


# @singledispatch
# def format_lines(line_object, **config_options):
#     """
#     format_lines adds small, context-dependent pieces of latex code in
#     amongst the latex string in the line_object.latex attribute. This involves
#     things like inserting "&" or linebreak characters for equation alignment,
#     formatting comments stored in the .comment attribute and putting them at
#     the end of the calculation, or the distinctive "Since, <condition> ..."
#     text that occurs when a conditional calculation is rendered.
#     """
#     raise TypeError(
#         f"Line type {type(line_object)} is not yet implemented in format_lines()."
#     )


# @format_lines.register(CalcLine)
# def format_calc_line(line: CalcLine, **config_options) -> CalcLine:
#     latex_code = line.latex

#     equals_signs = [idx for idx, char in enumerate(latex_code) if char == "="]
#     second_equals = equals_signs[1]  # Change to 1 for second equals
#     latex_code = latex_code.replace("=", "&=")  # Align with ampersands for '\align'
#     comment_space = ""
#     comment = ""
#     if line.comment:
#         comment_space = "\\;"
#         comment = format_strings(line.comment, comment=True)
#     line.latex = f"{latex_code[0:second_equals + 1]} {latex_code[second_equals + 2:]} {comment_space} {comment}\n"
#     return line


# @format_lines.register(ConditionalLine)
# def format_conditional_line(line: ConditionalLine, **config_options) -> ConditionalLine:
#     """
#     Returns the conditional line as a string of latex_code
#     """
#     if line.true_condition:
#         latex_condition = " ".join(line.true_condition)
#         a = "{"
#         b = "}"
#         comment_space = ""
#         comment = ""
#         if line.comment:
#             comment_space = "\\;"
#             comment = format_strings(line.comment, comment=True)

#         line_break = f"{config_options['line_break']}\n"
#         first_line = f"&\\text{a}Since, {b} {latex_condition} : {comment_space} {comment} {line_break}"
#         if line.condition_type == "else":
#             first_line = ""
#         line.latex_condition = first_line

#         outgoing = deque([])
#         for calc_line in line.true_expressions:
#             outgoing.append((format_lines(calc_line, **config_options)).latex)
#         line.true_expressions = outgoing
#         line.latex_expressions = line_break.join(line.true_expressions)
#         line.latex = line.latex_condition + line.latex_expressions
#         return line
#     else:
#         line.condition_latex = ""
#         line.true_expressions = deque([])
#         return line


# @format_lines.register(ParameterLine)
# def format_param_line(line: ParameterLine, **config_options) -> ParameterLine:
#     comment_space = "\\;"
#     line_break = "\n"
#     if "=" in line.latex:
#         replaced = line.latex.replace("=", "&=")
#         comment = format_strings(line.comment, comment=True)
#         line.latex = f"{replaced} {comment_space} {comment}{line_break}"
#     else:  # To handle sympy symbols displayed alone
#         replaced = line.latex.replace(" ", comment_space)
#         comment = format_strings(line.comment, comment=True)
#         line.latex = f"{replaced} {comment_space} {comment}{line_break}"
#     return line


# @format_lines.register(IntertextLine)
# def format_intertext_line(line: IntertextLine, **config_options) -> IntertextLine:
#     cleaned_line = line.line.replace("##", "")
#     line.latex = f"& \\textrm{{{cleaned_line}}}"
#     return line


# def format_strings(string: str, comment: bool, **config_options) -> deque:
#     """
#     Returns 'string' appropriately formatted to display in a latex
#     math environment.
#     """
#     if not string:
#         return ""
#     text_env = ""
#     end_env = ""
#     l_par = ""
#     r_par = ""
#     if comment:
#         l_par = "("
#         r_par = ")"
#         text_env = "\\;\\textrm{"
#         end_env = "}"
#     else:
#         l_par = ""
#         r_par = ""
#         text_env = "\\textrm{"
#         end_env = "}"

#     return "".join([text_env, l_par, string.strip().rstrip(), r_par, end_env])
