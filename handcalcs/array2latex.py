#!/usr/bin/env python

"""
Arraytolatex: As from the name, the purpose of this tool is to convery numpy's array into a valid latex code. 
"""
import os
import csv
import re
import sys
from typing import Any

__version__ = "0.1"


def get_type(data):
    return type(data)


def access_numpy_module(array):
    return sys.modules[type(array).__module__]


def latex_repr(result: Any) -> str:
    """
    Return a str if the object in 'result' has a special repr method
    for rendering itself in latex.Returns str(result), otherwise.
    """
    if hasattr(result, "_repr_latex_"):
        try:
            return result._repr_latex_()
        except:
            return str(result)

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


def to_latex(array):
    """
    This function converts numpy ndarray into a valid latex table.
    """
    print("To latex: runs")
    numpy_module = access_numpy_module(array)
    string_array = numpy_module.array2string(array,formatter = {'all': latex_repr})[2:][
        :-2
    ]  # I use this for tables items

    regex_space_bracket = r"\s+?\]"
    regex_1 = r"\]\n "
    regex_2 = r"\[|\]"
    regex_3 = r"(-?\d*\.?\d+)\s+"
    repl_1 = r"\\\\\n"
    repl_2 = r""
    repl_3 = r"\1 & "
    repl_space_bracket = r"\]"

    #a_string = re.sub(
        #regex_1, repl_1, string_array
    #)  # I use this to compute the largest number length
    #string_table_items = a_string.replace("\n", "").split(" ")
    #length_table_items = max(len(str(i)) for i in string_table_items)

    template = "\\begin{bmatrix}"
    for regex_repl in zip(
        (regex_space_bracket, regex_1, regex_2, regex_3),
        (repl_space_bracket, repl_1, repl_2, repl_3),
    ):
        string_array = re.sub(regex_repl[0], regex_repl[1], string_array.rstrip())

    print(template + string_array + "\\end{bmatrix}")
    return template + string_array + "\\end{bmatrix}"
