from collections import deque, ChainMap
import copy


def swap_calculation(calculation: deque, calc_results: dict, **config_options) -> tuple:
    """Returns the python code elements in the deque converted into
    latex code elements in the deque"""
    symbolic_portion = swap_symbolic_calcs(calculation, calc_results, **config_options)
    calc_drop_decl = deque(list(calculation)[1:])  # Drop the variable declaration
    numeric_portion = swap_numeric_calcs(calc_drop_decl, calc_results, **config_options)
    return (symbolic_portion, numeric_portion)


def swap_symbolic_calcs(
    calculation: deque, calc_results: dict, **config_options
) -> deque:
    # remove calc_results function parameter
    symbolic_expression = copy.copy(calculation)
    functions_on_symbolic_expressions = [
        insert_parentheses,
        swap_custom_symbols,
        swap_math_funcs,
        swap_superscripts,
        swap_chained_fracs,
        swap_frac_divs,
        swap_py_operators,
        swap_comparison_ops,
        swap_for_greek,
        swap_prime_notation,
        swap_long_var_strs,
        swap_double_subscripts,
        extend_subscripts,
        swap_superscripts,
        flatten_deque,
    ]
    for function in functions_on_symbolic_expressions:
        # breakpoint()
        if function is swap_math_funcs:
            symbolic_expression = function(symbolic_expression, calc_results)
        elif (
            function is extend_subscripts
            and not config_options["underscore_subscripts"]
        ):
            symbolic_expression = replace_underscores(
                symbolic_expression, **config_options
            )
        else:
            symbolic_expression = function(symbolic_expression, **config_options)
    return symbolic_expression


def swap_numeric_calcs(
    calculation: deque, calc_results: dict, **config_options
) -> deque:
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
        swap_double_subscripts,
        extend_subscripts,
        flatten_deque,
    ]
    for function in functions_on_numeric_expressions:
        if function in (swap_values, swap_math_funcs):
            numeric_expression = function(
                numeric_expression, calc_results, **config_options
            )
        elif (
            function is extend_subscripts
            and not config_options["underscore_subscripts"]
        ):
            numeric_expression = replace_underscores(
                numeric_expression, **config_options
            )
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


def swap_custom_symbols(d: deque, **config_options) -> deque:
    """
    Swaps the custom symbols from the 'config_options'.
    """
    swapped_items = deque([])
    for item in d:
        if isinstance(item, deque):
            new_item = swap_custom_symbols(item, **config_options)
            swapped_items.append(new_item)
        elif isinstance(item, str):
            custom_symbols = config_options.get("custom_symbols", {})
            new_item = item
            for symbol, latex_symbol in custom_symbols.items():
                if symbol in item:
                    new_item = item.replace(symbol, latex_symbol)
                    break
            swapped_items.append(new_item)
        else:
            swapped_items.append(item)
    return swapped_items


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


def swap_floor_ceil(
    d: deque, func_name: str, calc_results: dict, **config_options
) -> deque:
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
    import sys

    # From Thomas Holder on SO:
    # https://stackoverflow.com/questions/1897623/
    # unpacking-a-passed-dictionary-into-the-functions-name-space-in-python
    exec_str = ",".join(kwargs) + " = kwargs.values()"
    if int(sys.version.split(".")[1]) >= 13:
        exec(exec_str, locals=sys._getframe(0).f_locals)
    else:
        exec(exec_str)
    try:
        # It would be good to sanitize the code coming in on 'conditional_str'
        # Should this code be forced into using only boolean operators?
        # Do not need to cross this bridge, yet.
        return eval(conditional_str)
    except SyntaxError:
        return conditional_str



def swap_double_subscripts(pycode_as_deque: deque, **config_options) -> deque:
    """
    For variables or function names that contain a double subscript '__',
    the double subscript will be replaced with LaTeX space: "\\ "
    """
    swapped_deque = deque([])
    for item in pycode_as_deque:
        if isinstance(item, deque):
            new_item = swap_double_subscripts(item)
        elif isinstance(item, str) and "__" in item:
            new_item = item.replace("__", "\\ ")
        else:
            new_item = item
        swapped_deque.append(new_item)
    return swapped_deque


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
            if "\\mathrm{" in item or "\\operatorname{" in item:
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
                swapped_deque.append(
                    swap_frac_divs(item, **config_options)
                )  # recursion!
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


def swap_math_funcs(
    pycode_as_deque: deque, calc_results: dict, **config_options
) -> deque:
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
                elif possible_func:
                    ops = "\\operatorname"
                    new_func = f"{ops}{a}{poss_func_name}{b}"
                    item = swap_func_name(item, poss_func_name, new_func)
                    # if possible_func:
                    #     item = insert_func_braces(item)
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
            new_component = component.replace("e+0", "e+").replace(
                "e+", " \\times 10 ^ {"
            )
            components.append(new_component + b)
        elif "e-" in component:
            new_component = component.replace("e-0", "e-").replace(
                "e-", " \\times 10 ^ {-"
            )
            components.append(new_component + b)
        else:
            components.append(component)
    new_item = "\\ ".join(components)
    return new_item


def swap_scientific_notation_float(
    line: deque, precision: int, **config_options
) -> deque:
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
        if is_number(item):
            new_item = (
                "{:.{precision}e}".format(item, precision=precision)
                .replace("e-0", "e-")
                .replace("e+0", "e+")
            )
            swapped_deque.append(new_item)
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
    greeks_to_exclude = config_options["greek_exclusions"]
    swapped_deque = deque([])
    greek_chainmap = ChainMap(GREEK_LOWER, GREEK_UPPER)
    for item in pycode_as_deque:
        if isinstance(item, deque):
            new_item = swap_for_greek(item, **config_options)
            swapped_deque.append(new_item)
        elif "_" in str(item):
            components = str(item).split("_")
            swapped_components = [
                (
                    dict_get(greek_chainmap, component)
                    if component not in greeks_to_exclude
                    else component
                )
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
        if not config_options["underscore_subscripts"]:
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
        elif test_for_long_var_strs(item, **config_options) and not is_number(
            str(item)
        ):
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
            outgoing.append(
                swap_values(item, tex_results, **config_options)
            )  # recursion!
        else:
            swapped_value = dict_get(tex_results, item)
            if isinstance(swapped_value, str) and swapped_value != item:
                swapped_value = format_strings(
                    swapped_value, comment=False, **config_options
                )
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

