import copy
import importlib
import pathlib
import inspect
import math
import os
import subprocess
from collections import deque
from typing import Any, Union, Optional, Tuple, List

# WHERE YOU ARE AT:
# Find a way to deal with excessive brackets
# Find why rendering of units text only goes two deque levels deep (e.g. not in brackets in fractions)

import pyparsing as pp
import jinja2

from jinja2 import Template

latex_jinja_env = jinja2.Environment(
    block_start_string=r"\BLOCK{",
    block_end_string="}",
    variable_start_string=r"\VAR{",
    variable_end_string="}",
    comment_start_string=r"\#{",
    comment_end_string="}",
    line_statement_prefix="%%",
    line_comment_prefix="%#",
    trim_blocks=True,
    autoescape=False,
    loader=jinja2.FileSystemLoader(
        os.path.join(os.path.dirname(__file__), "templates")
    ),
)

class LatexRenderer:
    def __init__(self, python_code_str: str, results: dict):
        self.source = python_code_str
        self.results = results
        self.precision = 3
        self.parsed = {}
        #self.latex = {}
        self.vert_space = "jot2"
        self.normal_expr = "align"
        self.long_expr = "multline"
        self.text_env = "normalfont"

        self.char_threshold = 30  # TODO: This is hackey and inconsistent,
        # find better ways of testing for line breaks

    def set_precision(self, n=3):
        """Sets the precision (number of decimal places) in all
        latex printed values. Default = 3"""
        self.precision = n

    def set_latex_envs(self, normal_expr: str, long_expr: str, text_env: str):
        """Sets latex math section parameters. Defaults are:
        'normal_expr' = 'align'
        'long_expr' = 'multline'
        If you do not want numbered equations, remove the asterisk.
        (e.g. 'align', 'gather')
        """
        self.normal_expr = normal_expr
        self.long_expr = long_expr
        self.text_env = text_env

    def render(self):
        return latex(self.source, self.results, 130, self.char_threshold)

def latex(raw_python_source: str, calculated_results: dict, long_threshold: int, char_threshold: int, precision = 3, p_cols=3) -> str:
    """
    Returns the Python source as a string that has been converted into latex code.
    """
    calc_results = calculated_results
    source = raw_python_source
    if not test_for_parameter_cell(raw_python_source):
        parsed_code = parse_python_code(source, calc_results, long_threshold, char_threshold)
        converted_into_latex = python_to_latex_conversion(parsed_code, calc_results, char_threshold)
        #print(converted_into_latex)
        rendered_into_latex_strs = render_latex_reprs(converted_into_latex, precision)
        final_latex_deque = render_to_string(rendered_into_latex_strs, char_threshold)
        #print(final_latex_deque)
        joined_code = "\\\\[10pt]\n".join(final_latex_deque)
        beg_env = "\\begin{aligned}\n"
        end_env = "\\end{aligned}"
        latex_code = f"{beg_env}{joined_code}{end_env}"
    else:
        latex_code = parse_parameter_cell(source, calc_results, precision)
        
    return f"\\[\n{latex_code}\n\]"
        
    #latex_deque.appendleft(params)

    #template = latex_jinja_env.get_template(name="EngTemplate.tex")
    #latex = template.render(latex_code=latex_deque, project_info=project_info)



def parse_python_code(raw_python_source: str, calculated_results: dict, long_threshold: int, char_threshold: int) -> dict:
    """
    The methods read the source code from self.source and parse
    them into a dictionary of nested deques from which all other
    latex parsing will operate on.
    """
    source = raw_python_source
    calc_results = calculated_results
    separated_code = raw_python_to_separated_dict(source, calculated_results, long_threshold)
    parsed_with_results = add_result_values_to_lines(separated_code, calc_results)
    return parsed_with_results

def raw_python_to_separated_dict(raw_python_source: str, calculated_results: dict, long_threshold: int = 130) -> dict:
    """
    Returns a dict representing the parsed python code in self.source
    """
    separated_code = {}
    pycode_deque = deque(raw_python_source.split("\n"))
    for line_num, line in enumerate(pycode_deque):
        try:
            line, comment = line.split("#")
        except ValueError:
            comment = ""
        if test_for_parameter_line(line):
            separated_code.update({line_num: {"line": parse_parameter_line(line, calculated_results), "type": "parameter", "comment": comment}})
        elif ":" in line:
            # TODO: Put this conditional stuff into its own function
            condition, expressions = line.split(":")
            expr_deque = deque(expressions.split(";"))  # handle multiple lines in cond
            condition = condition.lstrip("else").lstrip("elif").lstrip("if")
            try:
                cond = expr_parser(condition.strip())
            except pp.ParseException:
                cond = [condition.strip()]

            expr_acc = deque([])
            for line in expr_deque:
                try:
                    expr = expr_parser(line.strip())
                except pp.ParseException:
                    expr = [line.strip()]
                expr_acc.append(expr)

            new_line = [cond] + [expr_acc]
            separated_code.update(
                {line_num: {"line": new_line, "type": "conditional", "comment": comment}} # Test for long conditionals later
            )

        elif "=" in line:
            if test_long_line_of_math(code_reader(line), calculated_results, long_threshold)[0]:
                separated_code.update(
                    {line_num: {"line": code_reader(line), 
                                "type": "long calc", "comment": comment}})
            else:
                separated_code.update(
                    {line_num: {"line": code_reader(line), 
                    "type": "normal calc", 
                    "comment": comment}}
                )
    return separated_code

def add_result_values_to_lines(parsed_results: dict, calculated_results: dict) -> None:
    calc_results = calculated_results
    for line_data in parsed_results.values():
        ltype = line_data["type"]
        if "calc" in ltype: # Capture both 'normal calc' and 'long calc'
            parameter_name = line_data["line"][0]
            resulting_value = calc_results.get(parameter_name, parameter_name)
            line_data["line"] = [line_data["line"], ["=", resulting_value]]
        elif ltype == "parameter":
            pass
        elif ltype == "conditional":
            _, exprs = line_data["line"]
            for idx, expr in enumerate(exprs):
                parameter_name = expr[0]
                resulting_value = calc_results.get(parameter_name, parameter_name)
                line_data["line"][1][idx] = [expr, ["=", resulting_value]]
    return parsed_results

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

    return deque(list(line)[first_equals:second_equals + 1])

# TODO: Ignore or deal with inline comments; deal with headings

def python_to_latex_conversion(parsed_results: dict, calculated_results: dict, char_threshold: int) -> dict:
    """
    Coordinates the conversion of the data in parsed_results into latex.
    Stores the output in self._latex after performing the conversion
    with module functions.
    """
    latex_results = {}
    calc_results = calculated_results
    for line_num, line_data in parsed_results.items():
        ltype = line_data["type"]  # str
        line = line_data["line"]  # str or deque
        comment = format_comments(line_data["comment"])

        if ltype == "heading":
            new_line = swap_headings(line)
        elif ltype == "note":
            new_line = line
        #TODO: Deal with parameter lines
        elif ltype == "parameter":
            new_line = line + comment
        elif ltype == "conditional":
            condition, expressions = line
            true_cond = swap_conditional(condition, calc_results)
            if true_cond:
                expr_acc = deque([])
                for expr in expressions:
                    calcd_result = expr[1]
                    expr = expr[0]  # break out of nested deque
                    substituted = swap_calculation(expr, calc_results, ltype, char_threshold, 2.5)
                    expr_acc.append([substituted, calcd_result])
                new_line = [true_cond, expr_acc] + comment
            else:
                new_line = deque([])

        elif ltype == "normal calc":
            expr, calcd_result = line
            calcd_result = deque(calcd_result)
            substituted = swap_calculation(expr, calc_results, ltype, char_threshold, 2.5)
            # May need to fine-tune what part of 'line' gets submitted to these functions
            #print(type(substituted), type(calcd_result), type(comment))
            new_line = substituted + calcd_result + comment

        elif ltype == "long calc":
            expr, calcd_result = line
            calcd_result = deque(calcd_result)
            substituted = swap_calculation(expr + calcd_result, calc_results, ltype, char_threshold, 4.3)
            #substituted_w_gather = insert_gathered_environment(substituted, char_threshold)
            #print("gathered: ", substituted_w_gather)           
            #gathered_w_linebreaks = break_long_equations(substituted_w_gather, char_threshold)
            #print("line breaks: ", gathered_w_linebreaks) 
            new_line = substituted
            #print(new_line)
        latex_results.update({line_num: {"line": new_line, "type": ltype}})
    return latex_results

def render_to_string(latex_results: dict, char_threshold: int) -> deque:
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
            threshold = char_threshold
            condition, expressions = line
            cond = format_conditional_lines(condition[0])
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

def test_long_line_of_math(line: deque, calculated_results: dict, long_threshold: int) -> Tuple[bool, int]:
    """
    Return a Tuple[bool, int] that indicates whether the substituted values of `line`
    will be over the character threshold. int represents the number of characters counted
    in the str representation of the substituted values. 
    """
    count = 0
    recurse_bool = False
    count_bool = False
    new_bool = False
    for component in line:
        if type(component) == deque:
            new_bool, new_count = test_long_line_of_math(component, calculated_results, long_threshold)
            count += new_count
            recurse_bool = recurse_bool or new_bool
        elif type(component) == (float, int):
            count += len(str(component))
        elif type(component) == str:

            substitution = calculated_results.get(component, component)
            count += len(str(substitution))
    if count > long_threshold:
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
        if type(component) == deque:
            count_deque.append(count_subbed_chars_in_equation(component, calculated_results))
        elif type(component) == (float, int):
            count += len(str(component))
        elif type(component) == str:
            substitution = calculated_results.get(component, component)
            count += len(str(substitution))
    count_deque.append(count)
    return count_deque

def break_long_equations(line: deque, char_threshold: int) -> deque:
    """
    Returns a deque that matches `line` except with a linebreak character inserted
    after the next mathematical operator after the character count of items within
    `line` exceeds the `char_threshold`.
    """
    #TODO: Create test for appropriate palcement of linebreaks
    line_break = "{}\\\\\n"
    str_lengths = count_str_len_in_deque(line, False)
    sum_of_lengths = 0
    acc = deque([])
    for idx, length in enumerate(str_lengths):
        if isinstance(length, deque):
            acc.append(break_long_equations(line[idx], char_threshold))
        elif "\\" in str(line[idx]):
            acc.append(line[idx])        
        else:
            acc.append(line[idx])
            sum_of_lengths += length
            if sum_of_lengths > char_threshold and line[idx] != line[-1]:# and\
                #("+" in line[idx+1] or "*" in line[idx+1] or "-" in line[idx+1]):
                acc.append(line_break)
                sum_of_lengths = 0
    return acc

def insert_gathered_environment(line: deque, char_threshold: int, mode: str) -> deque:
    """
    Returns `line` with a gathered environment inserted at the edges of the 

    """
    beg_gathered = "\\begin{gathered}\n"
    end_gathered = "\n\\end{gathered}\n"
    beg_aligned = "\[\n\\begin{aligned}\n"
    end_aligned = "\\end{aligned}\n\]\n"
    beg_multline = "\\begin{multline}\n"
    end_multline = "\n\\end{multline}\n"
    char_count = 0
    acc = deque([])
    if mode == "partial":
        #print("partial runs")
        equals = 0
        for component in line:
            if isinstance(component, deque):
                acc.append(insert_gathered_environment(component, char_threshold, mode))
            elif "=" in str(component) and equals == 0:
                acc.append("&=")
                equals += 1
            elif "=" in str(component) and equals == 1:
                acc.append("=")
                equals += 1
            elif "=" in str(component) and equals == 2:
                acc.append("&=")
            else:
                char_count += len(str(component))
                acc.append(component)
        if char_count > char_threshold:
            acc.appendleft(beg_gathered)
            acc.append(end_gathered)

    elif mode == "full":
        #print("full runs")
        equals = 0
        for component in line:
            #print(component)
            if "=" in str(component) and equals == 0:
                equals += 1
                acc.append("=")
            elif component == "=" and equals == 1:
                acc.append("\\\\=")
            else:
                acc.append(component)
        #print(acc)
        acc.appendleft(beg_multline)
        acc.appendleft(end_aligned)
        acc.append(end_multline)
        acc.append(beg_aligned)
    return acc

  
def count_str_len_in_deque(d: deque, omit_latex = True) -> deque:
    """
    Returns `l` with each item in `l` being replaced with an int that
    represents the length of each item in `l`.
    """
    acc = deque([])
    for component in d:
        if isinstance(component, (deque, list)):
            acc.append(count_str_len_in_deque(component))
        elif "\\" in str(component):
            if omit_latex:
                    pass
            else:
                acc.append(len(str(component)))
        else:
            acc.append(len(str(component)))
    return acc

def sum_str_len_in_deque(d: deque, omit_latex = True) -> int:
    """
    Returns the cumulative sum of len(str) nested deques in d.
    """
    counts = count_str_len_in_deque(d, omit_latex)
    cum_sum = 0
    for count in counts:
        if isinstance(count, deque):
            cum_sum += sum_str_len_in_deque(count, omit_latex)
        else:
            cum_sum += count
    return cum_sum



def test_for_parameter_line(line: str) -> bool:
    """
    Returns True if `line` appears to be a line to simply declare a
    parameter (e.g. "a = 34") instead of an actual calculation.
    """
    try:
        expr, comment = line.split("#")
    except ValueError:
        expr = line
    if not expr.strip():
        return False
    left_side, right_side = expr.split("=")
    right_side.replace(" ", "")
    expr_as_code = code_reader(expr)
    if right_side.find("(") == 0 and right_side.find(")") == (len(right_side) + 1):
        return True

    elif len(expr_as_code) == 3 and expr_as_code[1] == "=":
        return True
    #print(split_line, len(split_line), split_line[1])
    #if len(split_line) == 3:
    #    if split_line[1] == "=":
            #print("Passes")
    #        return True
    else:
        #print("Does not pass")
        return False

def test_for_parameter_cell(raw_python_source: str) -> bool:
    """
    Returns True if the text, "# Parameters" or "#Parameters" is the first
    element of `line`. False, otherwise.
    """
    first_element = raw_python_source.split("\n")[0]
    if "#" in first_element and "parameters" in first_element.lower():
        return True
    return False

def parse_parameter_line(python_line: str, calculated_results: dict) -> deque:
    """
    Returns a 'line' with any symbols for the parameter name swapped out
    """
    param = python_line.replace(" ","").split("=")[0]
    param_line = deque([param, "&=", calculated_results[param]])
    swapped_param_symbols = swap_symbolic_calcs(param_line)
    #print("Runs: ", swapped_param_symbols)
    return swapped_param_symbols


def parse_parameter_cell(
    raw_python_source: str, calculated_results: dict, precision: int, cols: int = 3
) -> dict:
    """
    Return a str representing the latex code conversion of `raw_python_code` which
    consists entirely of a "Parameters" cell; a Jupyter cell containing only 
    variable assignments that begins with a "# Parameters" comment.

    This is an alternate end point to the latex() function.
    """
    python_lines = deque(raw_python_source.split("\n"))
    parsed_params = {}
    python_lines.popleft() # Omit "# Parameters" line
    removed_blank_lines = [line for line in python_lines if line.strip() != ""]
    for line_num, line in enumerate(removed_blank_lines):
        param_line = parse_parameter_line(line, calculated_results)
        #param = line.split("=")[0].replace(" ","")
        #param_line = deque([param, "=", calculated_results[param]])
        #swapped_param_symbols = swap_symbolic_calcs(param_line)
        parsed_params.update({line_num: {"line": param_line, "ltype": "parameter"}})
    return format_parameters_cell(parsed_params, precision, cols)

def format_parameters_cell(
    parameters_dict: dict, precision: int, cols: int = 3
) -> str:
    """
    Returns the input parameters as an \align environment with 'cols'
    number of columns.
    """
    #section = r"\section*{Parameters}"
    begin = "\\begin{aligned}"
    end = "\\end{aligned}"
    align = "&"
    linebreak = "\\\\"
    param_acc = deque([])
    for idx, parameter in enumerate(parameters_dict.values()):
        line = parameter["line"]
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
        param_acc.append(" ".join([symbol, equals, value]))
    param_code = " ".join(param_acc)
    #return "\n".join([section, begin, param_code, end])
    return "\n".join([begin, param_code, end])

def format_comments(comment: str) -> deque:
    """
    Returns 'line' but with any inline comments 
    """
    text_env = "\;\\textit{"
    end_env = "}"
    l_par = ""
    r_par = ""
    if comment:
        l_par = "("
        r_par = ")"
    return deque([text_env, l_par, comment.strip(), r_par, end_env])

def render_latex_reprs(latex_dict: dict, precision: int) -> dict:
    """
    Returns the line-by-line latex code in latex_dict compiled into a
    str for rendering. Floats and other numerical objects are rounded
    and converted into appropriate strings for display.
    """
    latex_lines = {}
    for line_num, line_data in latex_dict.items():
        line = line_data["line"]
        ltype = line_data["type"]
        if not line:
            continue
        elif "calc" in ltype:
            latex_line = round_resulting_values(line, precision)
            latex_lines.update(
                {line_num: {"line": " ".join(latex_line), "type": ltype}}
            )

        elif ltype == "parameter":
            latex_line = round_resulting_values(line, precision)
            latex_lines.update(
                {line_num: {"line": " ".join(latex_line), "type": ltype}}
            )
        elif ltype == "conditional":
            #'line' structure for 'ltype' == "conditional":
            # [[condition],[[[expression_1 if true], [result of expression]],
            #             [[expression_2 if true], [result of expression]]]]
            condition = line[0]
            expressions = line[1]
            conditioned = round_resulting_values(condition, precision)
            expr_acc = deque([])
            for expression in expressions:
                expr, result = expression
                expr_rep = round_resulting_values(expr, precision)
                result_rep = round_resulting_values(result, precision)
                combined = expr_rep + result_rep
                expr_acc.append(combined)
            latex_lines.update(
                {
                    line_num: {
                        "line": [[" ".join(conditioned)], [expr_acc]],
                        "type": ltype,
                    }
                }
            )
        else:
            latex_lines.update({line_num: {"line": line, "type": ltype}})
    return latex_lines

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
        if isinstance(item, deque):
            return round_resulting_values(item, precision)  # Recursion!
        elif not isinstance(item, (str, int)):
            try:
                rounded = round(item, precision)
            except TypeError:
                rounded = None
            if rounded is not None:
                line_of_strs.append(latex_repr(rounded))
            else:
                line_of_strs.append(latex_repr(item))
        else:
            line_of_strs.append(str(item))

    return line_of_strs


def latex_repr(result: Any) -> str:
    """
    Return a str if the object in 'result' has a special repr method
    for rendering itself in latex.Returns str(result), otherwise.
    """
    if hasattr(result, "_repr_latex_"):
        return result._repr_latex_()
    elif hasattr(result, "latex"):
        try:
            return result.latex()
        except TypeError:
            return result.latex
        finally:
            return str(result)
    elif hasattr(result, "to_latex"):
        try:
            return result.to_latex()
        except TypeError:
            return result.to_latex
        finally:
            return str(result)
    else:
        return str(result)


def swap_headings(heading: str) -> str:
    """
    Returns a tex formatted heading for the raw string supplied in 'heading'.
    Possible values for the tex formatting are hard-coded into this function.
    """
    latex_emphasis = {
        1: r"\section*",
        2: r"\subsection*",
        3: r"\subsubsection*",
        4: r"\boldface",
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


def swap_conditional(conditional: deque, calc_results: dict) -> deque:
    """
    Returns the deque, 'conditional' if the conditional statement
    evaluates as True based on the data in calc_results.
    Returns an empty deque, otherwise.
    This to ensure that unnecessary conditional statements are not
    printed in the final results.
    """
    condition = "".join(conditional)
    result = eval_conditional(condition, **calc_results)
    if result == True:
        l_par = "\\left("
        r_par = "\\right)"
        symbolic_portion = swap_symbolic_calcs(conditional)
        numeric_portion = swap_numeric_calcs(conditional, calc_results)
        resulting_latex = (
            symbolic_portion + ["\\rightarrow"] + [l_par] + numeric_portion + [r_par]
        )
        return resulting_latex
    else:
        return deque([])


def swap_params(parameter: deque) -> deque:
    """
    Returns the python code elements in the 'parameter' deque converted
    into latex code elements in the deque. This primarily involves operating
    on the variable name.
    """
    return swap_symbolic_calcs(parameter)


def swap_calculation(calculation: deque, calc_results: dict, ltype: str, char_threshold: int, multiplier: float) -> deque:
    """Returns the python code elements in the deque converted into
    latex code elements in the deque"""
    #print(calculation)
    calc_drop_decl = deque(list(calculation)[1:])  # Drop the param declaration
    symbolic_portion = swap_symbolic_calcs(calculation)
    if ltype == "long calc":
        symbolic_portion.pop() # Remove the "Result" value of the calculation that is tagging along for the ride.
        symbolic_portion.pop() #...and its "=" sign
        numeric_portion = swap_numeric_calcs(calc_drop_decl, calc_results)
        if sum_str_len_in_deque(numeric_portion) + sum_str_len_in_deque(calc_drop_decl) < char_threshold * multiplier:
            gathered_numeric_partial = insert_gathered_environment(numeric_portion, char_threshold, "partial")
            with_line_breaks = break_long_equations(gathered_numeric_partial, char_threshold)
            return with_line_breaks

        if sum_str_len_in_deque(numeric_portion) + sum_str_len_in_deque(calc_drop_decl) >= char_threshold * multiplier:
            full_equation = symbolic_portion + numeric_portion
            gathered_numeric_full = insert_gathered_environment(full_equation, char_threshold, "full")
            return gathered_numeric_full
        
    else:
        numeric_portion = swap_numeric_calcs(calc_drop_decl, calc_results)
    resulting_latex = symbolic_portion + numeric_portion
    # print("Resulting latex: ", resulting_latex)
    return resulting_latex


def swap_symbolic_calcs(calculation: deque) -> deque:
    symbolic_expression = copy.copy(calculation)
    functions_on_symbolic_expressions = [
        swap_frac_divs,
        swap_math_funcs,
        swap_py_operators,
        swap_for_greek,
        extend_subscripts,
        swap_superscripts,
        flatten_pycode_as_deque,
    ]
    for function in functions_on_symbolic_expressions:
        symbolic_expression = function(symbolic_expression)
        # print("Function, result: ", function, symbolic_expression)
    return symbolic_expression


def swap_numeric_calcs(calculation: deque, calc_results: dict) -> deque:
    numeric_expression = copy.copy(calculation)
    functions_on_numeric_expressions = [
        swap_frac_divs,
        swap_math_funcs,
        swap_py_operators,
        swap_values,
        swap_superscripts,
        flatten_pycode_as_deque,
    ]
    for function in functions_on_numeric_expressions:
        if function is swap_values:
            numeric_expression = function(numeric_expression, calc_results)
        else:
            numeric_expression = function(numeric_expression)
        # print("Function, Numeric expression: ", f"{function} ", numeric_expression)
    return numeric_expression

# TODO: Add logic into flatten() or flatten_pycode...()
# to prevent the build-up of unnecessary brackets, such as
# in fractions
def flatten(pycode_as_deque: deque, parentheses=False) -> deque:
    """Returns elements from a deque and flattens elements from subdeques"""
    if isinstance(pycode_as_deque, deque) and not isinstance(
        pycode_as_deque, (str, bytes)
    ):
        if parentheses:
            yield "\\left("
        for item in pycode_as_deque:
            yield from flatten(item, True)  # recursion!
        if parentheses:
            yield "\\right)"
    else:
        yield pycode_as_deque


def flatten_pycode_as_deque(pycode_as_deque: deque) -> deque:
    """Returns pycode_as_deque flattened with parentheses on either side of the
    flattened deque item"""
    flattened_deque = deque([])
    for item in pycode_as_deque:
        if type(item) is deque:
            sub_deque_generator = flatten(item, True)
            for new_item in sub_deque_generator:
                flattened_deque.append(new_item)
        else:
            flattened_deque.append(item)
    return flattened_deque


def eval_conditional(conditional_str: str, **kwargs) -> bool:
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
    Returns deque (or nested deque) of the mathematical expression, 'exp_as_str', that represents
    the expression broken down into components of [<term>, <operator>, <term>, ...etc.]. If the expression
    contains parentheses, then a nested deque is started, with the expressions within the parentheses as the
    items within the nested deque. All deques are then converted to deques.
    """
    term = pp.Word(pp.srange("[A-Za-z0-9_.]"), pp.srange("[A-Za-z0-9_.]"))
    operator = pp.Word("+-*/^,%<>=~!")
    # eol = pp.Word(";")
    func = pp.Word(pp.srange("[A-Za-z0-9_]")) + pp.FollowedBy(
        pp.Word(pp.srange("[A-Za-z0-9_(),]"))
    )
    group = term ^ operator ^ func
    # parenth = pp.nestedExpr(content=group ^ eol)
    parenth = pp.nestedExpr(content=group)
    master = group ^ parenth
    expr = pp.OneOrMore(master)
    return list_to_deque(expr.parseString(expr_as_str).asList())


def get_latex_method(o: object):
    """Returns a bound method of the object, 'o', if 'o' has
    a method name containing the string, 'latex' (but not "_repr_latex_").
    This is a crap-shoot to test if an evaluated value is an object that
    has such a method that would convenient for display.
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
    for index, item in enumerate(pycode_as_deque):
        if isinstance(item, deque):
            new_item = extend_subscripts(item)  # recursion!
            swapped_deque.append(new_item)
        elif isinstance(item, str) and "_" in item:
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
    prev_idx = -1
    a = "{"
    b = "}"
    ops = r"\frac"
    close_bracket_token = False
    for index, item in enumerate(code):
        next_idx = min(index + 1, length - 1)
        next_next_idx = next_idx + 1
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
        prev_idx = index
        prev_item = item
    return swapped_deque


def swap_math_funcs(pycode_as_deque: deque) -> deque:
    """
    Swaps out math operator functions builtin to the math library for latex functions.
    e.g. python: sin(3*x), becomes: \sin(3*x)
    if the function name is not in the list of recognized Latex names, then a custom
    operator name is declared with r"\operatorname{", "}" appropriately appended.
    """
    latex_math_funcs = {
        "sin": r"\sin",
        "cos": r"\cos",
        "tan": r"\tan",
        "sqrt": r"\sqrt",
        "log": r"\log",
        "exp": r"\exp",
        "sinh": r"\sinh",
        "tanh": r"\tanh",
        "cosh": r"\cosh",
        "asin": r"\arcsin",
        "acos": r"\arccos",
        "atan": r"\arctan",
        "atan2": r"\arctan",
        "asinh": r"\arcsinh",
        "acosh": r"\arccosh",
        "atanh": r"\arctanh",
    }
    swapped_deque = deque([])
    length = len(pycode_as_deque)
    close_bracket_token = False
    a = "{"
    b = "}"
    for index, item in enumerate(pycode_as_deque):
        next_idx = min(index + 1, length - 1)
        prev_idx = max(0, index - 1)
        if type(item) is deque and not close_bracket_token:
            new_item = swap_math_funcs(item)  # recursion!
            swapped_deque.append(new_item)
        elif close_bracket_token:
            swapped_deque.append(item)
            new_item = f"{b}"
            close_bracket_token = False
            swapped_deque.append(new_item)
        elif isinstance(pycode_as_deque[next_idx], deque) and item in latex_math_funcs:
            new_item = f"{latex_math_funcs[item]}{a}"
            swapped_deque.append(new_item)
            close_bracket_token = True
        elif isinstance(pycode_as_deque[next_idx], deque) and item.isalpha():
            ops = r"\operatorname"
            new_item = f"{ops}{a}{item}{b}"
            swapped_deque.append(new_item)
        else:
            swapped_deque.append(item)
    return swapped_deque


def swap_py_operators(pycode_as_deque: deque) -> deque:
    """
    Swaps out Python mathematical operators that do not exist in Latex.
    Specifically, swaps "*", "**", and "%" for "\cdot", "^", and "\bmod".
    """
    swapped_deque = deque([])
    length = len(pycode_as_deque)
    for index, item in enumerate(pycode_as_deque):
        if type(item) is deque:
            new_item = swap_py_operators(item)  # recursion!
            swapped_deque.append(new_item)
        else:
            next_idx = min(index + 1, length - 1)  # Ensures idx in range
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
    for idx, item in enumerate(pycode_as_deque):
        next_idx = min(idx + 1, len(pycode_as_deque) - 1)
        next_item = pycode_as_deque[next_idx]
        if isinstance(item, deque) and not close_bracket_token:
            new_item = swap_superscripts(item)  # recursion!
            pycode_with_supers.append(new_item)
        elif next_item == "**":
            pycode_with_supers.append(l_par)
            pycode_with_supers.append(item)
            pycode_with_supers.append(r_par)
        elif item == "**":
            new_item = f"{ops}{a}"
            pycode_with_supers.append(new_item)
            close_bracket_token = True
        elif close_bracket_token and prev_item == "**":
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
    # note: using 'eta' is not allowed b/c it's a substring of beta, zeta, theta
    # same with 'psi'
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
            swapped_value = tex_results.get(item, item)
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


def format_calc_lines(latex_code: str) -> str:
    """
    Returns a line of 'latex_code' that has been formatted for the 'aligned' environment
    """
    a = "{"
    b = "}"
    equals_signs = [idx for idx, char in enumerate(latex_code) if char == "="]
    first_equals = equals_signs[1] # Change to 1 for second equals

    latex_code = latex_code.replace("=", "&=")  # Align with ampersands for '\align'
    remove_amp_from_first = (
        f"{latex_code[0:first_equals+1]}{latex_code[first_equals+2:]}"
    )
    normal_line = f"{remove_amp_from_first}\n"
    return normal_line


def format_conditional_lines(latex_code: str) -> str:
    """
    Returns a line of 'latex_code' that has been formatted for the 'aligned' environment
    """
    a = "{"
    b = "}"
    text = "\\text"
    #opening = f"\\begin{a}{environment}{b}\n"
    conditional = f"&{text}{a}Since, {b}{latex_code}:\n"
    #end = f"\\end{a}{environment}{b}\n"
    conditional_line = f"{conditional}"
    return conditional_line
