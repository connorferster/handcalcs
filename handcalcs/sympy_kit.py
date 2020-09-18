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

from typing import List, Any

def sympy_cell_line_lists(cell: str) -> List[List[str]]:
    """
    Converts sympy cell to list of lists of str
    """
    raw_lines = cell.split("\n")
    raw_line_components = [[elem.strip() for elem in line.split("=")] for line in raw_lines]
    return raw_line_components

def test_sympy_parents(sympy_cls: str, parents: tuple) -> bool:
    """
    Returns True if 'sympy_cls' is in 'bases'.
    False, otherwise.
    """
    return any([sympy_cls in str(parent) for parent in parents])


def test_for_sympy_expr(obj_str: str, var_dict: dict) -> bool:
    """
    Return True if 'obj_str' is in 'var_dict' and 'obj_str' represents
    a sympy object.
    """
    if obj_str not in var_dict: False
    else:
        obj = var_dict[obj_str]
        obj_type = type(obj)
        parents = obj_type.__mro__
        return test_sympy_parents("sympy.core.basic.Basic", parents)
    return False

def test_for_sympy_eqn(obj_str: str, var_dict: dict) -> bool:
    """
    Return True if 'obj_str' is in 'var_dict' and 'obj_str' represents
    a sympy object.
    """
    if obj_str not in var_dict: False
    else:
        obj = var_dict[obj_str]
        obj_type = type(obj)
        parents = obj_type.__mro__
        return test_sympy_parents("sympy.core.relational.Equality", parents)
    return False

def convert_sympy_obj_to_py_str(obj_str: str, var_dict: dict) -> str:
    """
    Returns the sympy obj represented by the dict key 'obj_str', retrieved from
    'var_dict' as a python code string.
    """
    return str(var_dict['obj_str'])

def get_sympy_obj(obj_str: str, var_dict: dict) -> Any:
    """
    Returns the object represented by 'obj_str' from 'var_dict'
    """
    return var_dict[obj_str]

def convert_sympy_cell_to_py_cell(cell: str, var_dict: dict) -> str:
    """
    Returns 'cell' converted from a multiline string representing a bunch 
    of sympy expressions and equality objects to a multiline string of 
    equivalent, representative python code for rendering by handcalcs.
    """
    acc = []
    lines = cell.split("\n")
    for line in lines:
        #try:
        if "=" in line: 
            lhs, rhs = line.split("=", 1)
            obj_str = rhs.strip()
            if test_for_sympy_eqn(obj_str, var_dict):
                sym_obj = get_sympy_obj(obj_str, var_dict)
                lhs = sym_obj.lhs
                rhs = sym_obj.rhs
                acc.append(str(lhs) + "=" + str(rhs))
            elif test_for_sympy_expr(obj_str, var_dict):
                sym_obj = get_sympy_obj(obj_str, var_dict)
                acc.append(lhs + "=" + str(sym_obj))
            else:
                acc.append(line)
        else:
            obj_str = line.strip()
            if test_for_sympy_eqn(obj_str, var_dict):
                sym_obj = get_sympy_obj(obj_str, var_dict)
                lhs = sym_obj.lhs
                rhs = sym_obj.rhs
                acc.append(str(lhs) + "=" + str(rhs))
            elif test_for_sympy_expr(obj_str, var_dict):
                raise ValueError(f"The result of a sympy expr must be assigned to a new variable, e.g. x = {line}")
            else:
                acc.append(line)
        #except:
        #    raise ValueError(f"%%render sympy: Should only be used for a cell filled with sympy objects, not: {line}")
    return "\n".join(acc) 
    
