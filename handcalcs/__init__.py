import copy
import importlib
import pathlib
import inspect
import math
import os
import subprocess
import collections
from typing import Any, Union, Optional

# WHERE YOU ARE AT:
# Find a way to deal with excessive brackets
# Find why rendering of units text only goes two list levels deep (e.g. not in brackets in fractions)

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


class Calc:
    def __init__(self, module_name):
        """
        module_name is a string describing a module name in your calc folder
        """
        self.module = importlib.import_module(
            module_name, "{}.main".format(module_name)
        )
        self.name = self.module.__name__

        self._calc_function = self.module.main
        self._source = inspect.getsource(self._calc_function)
        self._parsed = {}
        self._latex = {}
        self._parameters = {}
        self._os = os.name
        self._rm = "rm"
        if self._os == "nt":
            self._rm = "del"

        self.results = {}
        self.inputs = inspect.signature(self._calc_function)
        self.precision = 3
        self.vert_space = "jot2"
        self.normal_expr = "align"
        self.long_expr = "multline"
        self.text_env = "normalfont"

        self.char_threshold = 130  # TODO: This is hackey and inconsistent,
        # find better ways of testing for line breaks

    def __call__(self, *args, **kwargs) -> dict:
        self.results = self._calc_function(*args, **kwargs)
        return self.results

    def precision(n=3):
        """Sets the precision (number of decimal places) in all
        latex printed values. Default = 3"""
        self.precision = n

    def latex_envs(normal_expr: str, long_expr: str):
        """Sets latex math section parameters. Defaults are:
        'normal_expr' = 'align*'
        'long_expr' = 'gather*'
        If you do not want numbered equations, remove the asterisk.
        (e.g. 'align', 'gather')
        """
        self.normal_expr = normal_expr
        self.long_expr = long_expr

    def latex(
        self, project_info: Optional[dict] = {}, parameters=True, p_cols=3
    ) -> str:
        """
        Returns the Python source as a string that has been converted into latex code.
        """
        # Collect params if parameters == True
        params = []
        if parameters:
            parsed_parameters = self._parse_parameters(
                self.results, self.inputs.parameters
            )
            params = compiled_latex_from_parameters(
                parsed_parameters, self.precision, p_cols
            )

        parsed_code = self._parse()
        parsed_into_latex = self._generate_latex_results(parsed_code)
        rendered_into_latex_strs = render_latex_reprs(parsed_into_latex, self.precision)
        final_latex = self._format_latex_to_environments(rendered_into_latex_strs)
        latex_deque = collections.deque(final_latex)
        latex_deque.appendleft(params)

        template = latex_jinja_env.get_template(name="EngTemplate.tex")
        latex = template.render(latex_code=latex_deque, project_info=project_info)
        return latex

    def print(
        self,
        project_info={},
        filename="",
        file_type="",
        path: Union[pathlib.Path, str] = "",
        parameters=True,
        p_cols=3,
    ) -> None:
        """
        Prints the rendered latex to a file
        'project_info' is a dict with the following keys:
            'project': the name of the project
            'job': the job number of the project
            'element_desc': a description of the element under consideration
            'designer': your name
        'path' is the absolute file path of where you want to save the file
        'filename' is the name of the file (both .tex and .pdf)
        """
        path = pathlib.Path(path)  # Ensure a Path object is created
        if not filename:
            filename = input("Please enter a filename (no extension): ")
        fullpath = path / (filename + ".tex")

        latex = self.latex(project_info, parameters)

        # print(latex)

        with open(fullpath, "w+") as fp:
            fp.write(latex)
        try:
            process = subprocess.run(["pdflatex", str(fullpath)])
            if process.returncode == 0:

                subprocess.run(
                    [self._rm, str(fullpath).replace(".tex", ".log")], shell=True
                )
                subprocess.run(
                    [self._rm, str(fullpath).replace(".tex", ".aux")], shell=True
                )
                if file_type == "pdf":
                    subprocess.run([self._rm, str(fullpath)], shell=True)
                print("handcalcs: Latex rendering complete.")
            else:
                print(
                    f"There was an error in printing; return code {process.returncode}"
                )

        except ValueError:
            raise ValueError(
                "Make sure you have pdflatex installed and is a registered command "
                "on your computer to to generate the PDF output."
            )

        def _render_subprocess(self):
            pass

    def _parse(self) -> dict:
        """
        The methods read the source code from self._source and parse
        them into a dictionary of nested lists from which all other
        latex parsing will operate on.
        """
        source = self._source
        calc_results = self.results
        parameters = self.inputs.parameters
        parsed_code = self._parse_code(source)
        parsed_with_results = self._append_result(calc_results, parsed_code)
        return parsed_with_results

    def _parse_code(self, source: str) -> dict:
        """
        Returns a dict representing the parsed python code in self._source
        """
        parsed_code = {}
        pycode_list = source.split("\n")
        pycode_list = [line.strip() for line in pycode_list][1:]  # omit signature
        line_counter = 0
        for line in pycode_list:
            if "#" in line:
                parsed_code.update({line_counter: {"line": line, "type": "heading"}})
                line_counter += 1
            elif ":" in line:
                condition, expressions = line.split(":")
                expr_list = expressions.split(";")  # handle multiple lines in cond
                condition = condition.lstrip("else").lstrip("elif").lstrip("if")
                try:
                    cond = expr_parser(condition.strip())
                except pp.ParseException:
                    cond = [condition.strip()]

                expr_acc = []
                for line in expr_list:
                    try:
                        expr = expr_parser(line.strip())
                    except pp.ParseException:
                        expr = [line.strip()]
                    expr_acc.append(expr)

                new_line = [cond] + [expr_acc]
                parsed_code.update(
                    {line_counter: {"line": new_line, "type": "conditional"}}
                )
                line_counter += 1
            elif '"' in line:
                parsed_code.update({line_counter: {"line": line, "type": "note"}})
                line_counter += 1
            elif "=" in line:
                parsed_code.update(
                    {line_counter: {"line": code_reader(line), "type": "normal"}}
                )
                line_counter += 1

        return parsed_code

    def _parse_parameters(self, calc_results: dict, params_dict: dict) -> list:
        parsed_params = {}
        for idx, param in enumerate(params_dict.keys()):
            param_list = [param, "=", calc_results[param]]
            swapped_params = swap_params(param_list)
            parsed_params.update({idx: {"line": swapped_params, "ltype": "parameter"}})
        return parsed_params

    def _append_result(self, calc_results: dict, parsed_results: dict) -> None:
        for line_num, line_data in parsed_results.items():
            ltype = line_data["type"]
            if ltype == "normal":
                parameter_name = line_data["line"][0]
                resulting_value = calc_results.get(parameter_name, parameter_name)
                line_data["line"] = [line_data["line"], ["=", resulting_value]]
            elif ltype == "conditional":
                cond, exprs = line_data["line"]
                for idx, expr in enumerate(exprs):
                    parameter_name = expr[0]
                    resulting_value = calc_results.get(parameter_name, parameter_name)
                    line_data["line"][1][idx] = [expr, ["=", resulting_value]]
        return parsed_results

    def _generate_latex_results(self, parsed_results: dict) -> dict:
        """
        Coordinates the conversion of the data in self._parsed into latex.
        Stores the output in self._latex after performing the conversion
        with module functions.
        """
        latex_results = {}
        calc_results = self.results
        for line_num, line_data in parsed_results.items():
            ltype = line_data["type"]  # str
            line = line_data["line"]  # str or list
            if ltype == "heading":
                new_line = swap_headings(line)
            elif ltype == "note":
                new_line = line
            elif ltype == "conditional":
                condition, expressions = line
                true_cond = swap_conditional(condition, calc_results)
                if true_cond:
                    expr_acc = []
                    for expr in expressions:
                        calcd_result = expr[1]
                        expr = expr[0]  # break out of nested list
                        substituted = swap_calculation(expr, calc_results)
                        expr_acc.append([substituted, calcd_result])
                    new_line = [true_cond, expr_acc]
                else:
                    new_line = []
            elif ltype == "normal":
                expr, calcd_result = line
                substituted = swap_calculation(expr, calc_results)
                new_line = substituted + calcd_result
            latex_results.update({line_num: {"line": new_line, "type": ltype}})
        return latex_results

    def _format_latex_to_environments(self, latex_results: dict) -> list:
        """
        Returns a list of rendered latex_lines that are ready for printing.
        """
        normal = self.normal_expr
        long = self.long_expr
        rendered_list = []
        for line_num, line_data in latex_results.items():
            line = line_data["line"]  # list
            ltype = line_data["type"]  # str
            if ltype == "heading":
                rendered_list.append(line)
            elif ltype == "note":
                formatted_note = format_notes(line, self.text_env)
                rendered_list.append(formatted_note)

            elif ltype == "normal":
                threshold = self.char_threshold
                if "return" in line:
                    return rendered_list
                if r"\frac{" in line:
                    threshold = self.char_threshold * 1.3  # More lenient on fractions
                if len(line) > threshold:
                    formatted_calc = format_long_lines(line, self.long_expr)
                else:
                    formatted_calc = format_normal_lines(line, self.normal_expr)
                rendered_list.append(formatted_calc)

            elif ltype == "conditional":
                threshold = self.char_threshold
                condition, expressions = line
                cond = format_conditional_lines(condition[0], self.normal_expr)
                formatted_acc = []
                for expression in expressions[0]:
                    expr = expression
                    if "return" in " ".join(expr):
                        formatted_conditional = f"{cond}{' '.join(formatted_acc)}"
                        rendered_list.append(formatted_conditional)
                        return rendered_list
                    if r"\frac{" in expr:
                        threshold = (
                            self.char_threshold * 1.5
                        )  # More lenient on fractions
                    if len(" ".join(expr)) > threshold:
                        formatted_calc = format_long_lines(
                            " ".join(expr), self.long_expr
                        )
                    else:
                        formatted_calc = format_normal_lines(
                            " ".join(expr), self.normal_expr
                        )
                    formatted_acc.append(formatted_calc)
                else:
                    formatted_conditional = f"{cond}{' '.join(formatted_acc)}"
                    rendered_list.append(formatted_conditional)
        return rendered_list


def compiled_latex_from_parameters(
    parameters_dict: dict, precision: int, cols: int = 3
) -> str:
    """
    Returns the input parameters as an \align environment with 'cols'
    number of columns.
    """
    section = r"\section*{Parameters}"
    begin = r"\begin{align*}"
    end = r"\end{align*}"
    align = "&"
    linebreak = r"\\"
    param_acc = []
    for idx, parameter in enumerate(parameters_dict.values()):
        line = parameter["line"]
        latex_line = latex_line_conversion(line, precision)
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
    return "\n".join([section, begin, param_code, end])


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
        elif ltype == "normal":
            latex_line = latex_line_conversion(line, precision)
            latex_lines.update(
                {line_num: {"line": " ".join(latex_line), "type": ltype}}
            )
        elif ltype == "conditional":
            #'line' structure for 'ltype' == "conditional":
            # [[condition],[[[expression_1 if true], [result of expression]],
            #             [[expression_2 if true], [result of expression]]]]
            condition = line[0]
            expressions = line[1]
            conditioned = latex_line_conversion(condition, precision)
            expr_acc = []
            for expression in expressions:
                expr, result = expression
                expr_rep = latex_line_conversion(expr, precision)
                result_rep = latex_line_conversion(result, precision)
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


def latex_line_conversion(line_of_code: list, precision: int) -> str:
    """
    Returns a rounded str based on the latex_repr of an object in
    'line_of_code'
    """
    line_of_strs = []
    for item in line_of_code:
        if isinstance(item, str):
            line_of_strs.append(item)
        elif isinstance(item, int):
            line_of_strs.append(str(item))
        else:
            try:
                rounded = round(item, precision)
            except TypeError:
                rounded = None
            if rounded is not None:
                line_of_strs.append(latex_repr(rounded))
            else:
                line_of_strs.append(latex_repr(item))
    return line_of_strs


def latex_repr(result: Any) -> str:
    """
    Returns a str if the object in 'result' has a special "latex repr"
    method. Returns str(result), otherwise.
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


def swap_conditional(conditional: list, calc_results: dict) -> list:
    """
    Returns the list, 'conditional' if the conditional statement
    evaluates as True based on the data in calc_results.
    Returns an empty list, otherwise.
    This to ensure that unnecessary conditional statements are not
    printed in the final results.
    """
    condition = "".join(conditional)
    result = eval_conditional(condition, **calc_results)
    if result == True:
        l_par = r"\left("
        r_par = r"\right)"
        symbolic_portion = swap_symbolic_calcs(conditional)
        numeric_portion = swap_numeric_calcs(conditional, calc_results)
        resulting_latex = (
            symbolic_portion + [r"\rightarrow"] + [l_par] + numeric_portion + [r_par]
        )
        return resulting_latex
    else:
        return []


def swap_params(parameter: list) -> list:
    """
    Returns the python code elements in the 'parameter' list converted
    into latex code elements in the list. This primarily involves operating
    on the variable name.
    """
    return swap_symbolic_calcs(parameter)


def swap_calculation(calculation: list, calc_results: dict) -> list:
    """Returns the python code elements in the list converted into
    latex code elements in the list"""
    calc_drop_decl = calculation[1:]  # Drop the param declaration
    symbolic_portion = swap_symbolic_calcs(calculation)
    numeric_portion = swap_numeric_calcs(calc_drop_decl, calc_results)
    resulting_latex = symbolic_portion + numeric_portion
    # print("Resulting latex: ", resulting_latex)
    return resulting_latex


def swap_symbolic_calcs(calculation: list) -> list:
    symbolic_expression = copy.copy(calculation)
    functions_on_symbolic_expressions = [
        swap_frac_divs,
        swap_math_funcs,
        swap_py_operators,
        swap_for_greek,
        extend_subscripts,
        swap_superscripts,
        flatten_pycode_as_list,
    ]
    for function in functions_on_symbolic_expressions:
        symbolic_expression = function(symbolic_expression)
        # print("Function, result: ", function, symbolic_expression)
    return symbolic_expression


def swap_numeric_calcs(calculation: list, calc_results: dict) -> list:
    numeric_expression = copy.copy(calculation)
    functions_on_numeric_expressions = [
        swap_frac_divs,
        swap_math_funcs,
        swap_py_operators,
        swap_values,
        swap_superscripts,
        flatten_pycode_as_list,
    ]
    for function in functions_on_numeric_expressions:
        if function is swap_values:
            numeric_expression = function(numeric_expression, calc_results)
        else:
            numeric_expression = function(numeric_expression)
        # print("Function, Numeric expression: ", f"{function} ", numeric_expression)
    return numeric_expression


def flatten(pycode_as_list: list, parentheses=False) -> list:
    """Returns elements from a list and flattens elements from sublists"""
    if isinstance(pycode_as_list, collections.Iterable) and not isinstance(
        pycode_as_list, (str, bytes)
    ):
        if parentheses:
            yield r"\left("
        for item in pycode_as_list:
            yield from flatten(item, True)  # recursion!
        if parentheses:
            yield r"\right)"
    else:
        yield pycode_as_list


def flatten_pycode_as_list(pycode_as_list: list) -> list:
    """Returns pycode_as_list flattened with parentheses on either side of the
    flattened list item"""
    flattened_list = []
    for item in pycode_as_list:
        if type(item) is list:
            sub_list_generator = flatten(item, True)
            for new_item in sub_list_generator:
                flattened_list.append(new_item)
        else:
            flattened_list.append(item)
    return flattened_list


def eval_conditional(conditional_str: str, **kw) -> bool:
    """
    Evals the python code statement, 'conditional_str', based on the variables passed in
    as an unpacked dict as kwargs. The first line allows the dict values to be added to
    locals that can be drawn upon to evaluate the conditional_str. Returns bool.
    """
    # From Thomas Holder on SO:
    # https://stackoverflow.com/questions/1897623/
    # unpacking-a-passed-dictionary-into-the-functions-name-space-in-python
    exec(",".join(kw) + ", = kw.values()")
    try:
        return eval(conditional_str)
    except SyntaxError:
        return conditional_str


def code_reader(pycode_as_str: str) -> list:
    """
    Returns full line of code parsed into list items
    """
    var_name, expression = pycode_as_str.split("=")
    var_name, expression = var_name.strip(), expression.strip()
    expression_as_list = expr_parser(expression)
    return [var_name] + list("=") + expression_as_list


def expr_parser(expr_as_str: str) -> list:
    """
    Returns list (or nested list) of the mathematical expression, 'exp_as_str', that represents
    the expression broken down into components of [<term>, <operator>, <term>, ...etc.]. If the expression
    contains parentheses, then a nested list is started, with the expressions within the parentheses as the
    items within the nested list.
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
    return expr.parseString(expr_as_str).asList()


def get_latex_method(o: object):
    """Returns a bound method of the object, 'o', if 'o' has
    a method name containing the string, 'latex' (but not "_repr_latex_").
    This is a crap-shoot to test if an evaluated value is an object that
    has such a method that would convenient for display.
    Returns None otherwise."""
    for method in dir(o):
        if "latex" in method:
            return getattr(o, method)


def extend_subscripts(pycode_as_list: list) -> list:
    """
    For variables named with a subscript, e.g. V_c, this function ensures that any
    more than one subscript, e.g. s_ze, is included in the latex subscript notation.
    For any item in 'pycode_as_list' that has more than one character in the subscript,
    e.g. s_ze, then it will be converted to s_{ze}. Also handles nested subscripts.
    """
    swapped_list = []
    for index, item in enumerate(pycode_as_list):
        if isinstance(item, list):
            new_item = extend_subscripts(item)  # recursion!
            swapped_list.append(new_item)
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
            swapped_list.append(new_item)
        else:
            swapped_list.append(item)
    return swapped_list


def swap_frac_divs(code: list) -> list:
    """
    Swaps out the division symbol, "/", with a Latex fraction.
    The numerator is the symbol before the "/" and the denominator follows.
    If either is a string, then that item alone is in the fraction.
    If either is a list, then all the items in the list are in that part of the fraction.
    Returns a list.
    """
    swapped_list = []
    length = len(code)
    prev_idx = -1
    a = "{"
    b = "}"
    ops = r"\frac"
    close_bracket_token = False
    for index, item in enumerate(code):
        next_idx = min(index + 1, length - 1)
        next_next_idx = next_idx + 1
        if code[next_idx] is "/" and isinstance(item, list):
            new_item = f"{ops}{a}"
            swapped_list.append(new_item)
            swapped_list.append(swap_frac_divs(item))  # recursion!
        elif code[next_idx] is "/" and not isinstance(item, list):
            new_item = f"{ops}{a}"
            swapped_list.append(new_item)
            swapped_list.append(item)
        elif item is "/":
            swapped_list.append(f"{b}{a}")
            close_bracket_token = True
        elif close_bracket_token:
            close_bracket_token = False
            swapped_list.append(item)
            new_item = f"{b}"
            swapped_list.append(new_item)
        elif isinstance(item, list):
            new_item = swap_frac_divs(item)  # recursion!
            swapped_list.append(new_item)
        else:
            swapped_list.append(item)
        prev_idx = index
        prev_item = item
    return swapped_list


def swap_math_funcs(pycode_as_list: list) -> list:
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
    swapped_list = []
    length = len(pycode_as_list)
    close_bracket_token = False
    a = "{"
    b = "}"
    for index, item in enumerate(pycode_as_list):
        next_idx = min(index + 1, length - 1)
        prev_idx = max(0, index - 1)
        if type(item) is list and not close_bracket_token:
            new_item = swap_math_funcs(item)  # recursion!
            swapped_list.append(new_item)
        elif close_bracket_token:
            swapped_list.append(item)
            new_item = f"{b}"
            close_bracket_token = False
            swapped_list.append(new_item)
        elif isinstance(pycode_as_list[next_idx], list) and item in latex_math_funcs:
            new_item = f"{latex_math_funcs[item]}{a}"
            swapped_list.append(new_item)
            close_bracket_token = True
        elif isinstance(pycode_as_list[next_idx], list) and item.isalpha():
            ops = r"\operatorname"
            new_item = f"{ops}{a}{item}{b}"
            swapped_list.append(new_item)
        else:
            swapped_list.append(item)
    return swapped_list


def swap_py_operators(pycode_as_list: list) -> list:
    """
    Swaps out Python mathematical operators that do not exist in Latex.
    Specifically, swaps "*", "**", and "%" for "\cdot", "^", and "\bmod".
    """
    swapped_list = []
    length = len(pycode_as_list)
    for index, item in enumerate(pycode_as_list):
        if type(item) is list:
            new_item = swap_py_operators(item)  # recursion!
            swapped_list.append(new_item)
        else:
            next_idx = min(index + 1, length - 1)  # Ensures idx in range
            if item is "*":
                swapped_list.append(r"\cdot")
            elif item is "%":
                swapped_list.append(r"\bmod")
            else:
                swapped_list.append(item)
    return swapped_list


def swap_superscripts(pycode_as_list: list) -> list:
    """
    Returns the python code list with any exponentials swapped
    out for latex superscripts.
    """
    pycode_with_supers = []
    close_bracket_token = False
    ops = "^"
    a = "{"
    b = "}"
    l_par = r"\left("
    r_par = r"\right)"
    for idx, item in enumerate(pycode_as_list):
        next_idx = min(idx + 1, len(pycode_as_list) - 1)
        next_item = pycode_as_list[next_idx]
        if isinstance(item, list) and not close_bracket_token:
            new_item = swap_superscripts(item)  # recursion!
            pycode_with_supers.append(new_item)
        elif next_item == "**":
            new_item = f"{l_par}{item}{r_par}"
            pycode_with_supers.append(new_item)
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


def swap_for_greek(pycode_as_list: list) -> list:
    """
    Returns full line of code as list with any Greek terms swapped in for words describing
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
    pycode_with_greek = []
    for item in pycode_as_list:
        if isinstance(item, list):
            new_item = swap_for_greek(item)  # recursion!
            pycode_with_greek.append(new_item)
        elif isinstance(item, str):
            for letter in greeks:
                if letter in item.lower():
                    new_item = "\\" + item
                    pycode_with_greek.append(new_item)
                    break
            else:
                pycode_with_greek.append(item)
        else:
            pycode_with_greek.append(item)
    return pycode_with_greek


def swap_values(pycode_as_list: list, tex_results: dict) -> list:
    """
    Returns a the 'pycode_as_list' with any symbolic terms swapped out for their corresponding
    values.
    """
    swapped_values = []
    for item in pycode_as_list:
        swapped_value = ""
        if isinstance(item, list):
            swapped_values.append(swap_values(item, tex_results))
        else:
            swapped_value = tex_results.get(item, item)
            swapped_values.append(swapped_value)
    return swapped_values


def format_long_lines(latex_code: str, environment: str) -> str:
    """
    Returns a line of latex code that has been broken up into a \multiline with line
    breaks at each '=' sign.
    """
    a = "{"
    b = "}"

    # Align with '\\' for '\multline'
    latex_code = latex_code.replace("=", r"\\=")
    latex_code = latex_code.replace(r"\\=", "=", 1)
    long_line = f"\\begin{a}{environment}{b}\n{latex_code}\n\\end{a}{environment}{b}\n"
    return long_line


def format_normal_lines(latex_code: str, environment: str) -> str:
    """
    Returns a line of 'latex_code' that has been formatted within the math environment,
    'environment'.
    """
    a = "{"
    b = "}"
    equals_signs = [idx for idx, char in enumerate(latex_code) if char == "="]
    second_equals = equals_signs[1]

    latex_code = latex_code.replace("=", "&=")  # Align with ampersands for '\align'
    remove_amp_from_second = (
        f"{latex_code[0:second_equals+1]}{latex_code[second_equals+2:]}"
    )
    normal_line = f"\\begin{a}{environment}{b}\n{remove_amp_from_second}\n\\end{a}{environment}{b}\n"
    return normal_line


def format_conditional_lines(latex_code: str, environment: str) -> str:
    """
    Returns a line of 'latex_code' that has been formatted within the math environment,
    'environment'.
    """
    a = "{"
    b = "}"
    text = r"\text"
    opening = f"\\begin{a}{environment}{b}\n"
    conditional = f"&{text}{a}Since, {b}{latex_code}:\n"
    end = f"\\end{a}{environment}{b}\n"
    conditional_line = f"{opening}{conditional}{end}"
    return conditional_line


if __name__ == "__main__":
    from forallpeople import *

    environment("structural")
    from forallpeople import *
    import handcalcs.handcalcs as hc

    moi = hc.Calc("calcs.timber.clt.EIx")
    moi(
        layers=9,
        t_strong=35 * mm,
        t_weak=25 * mm,
        E_strong=12.8 * GPa,
        E_weak=9.7 * GPa / 30,
    )
    moi.print2file()
