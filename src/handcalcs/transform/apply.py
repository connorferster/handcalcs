from collections import deque
from typing import Callable, Union, Any
from ..parsing.blocks import (
    IfBlock,
    ForBlock,
    FunctionBlock,
    ComprehensionBlock,
    Comprehension,
    HandCalcsBlock
)
from ..parsing.linetypes import(
    CalcLine,
    ExprLine,
    HandCalcsObj,
    List,
    Tuple,
    Set,
    Dictionary,
    Attribute,

)
from ..parsing.linetypes import HandCalcsObj
from ..parsing.renderables import HandCalcsRenderable

from functools import singledispatch

@singledispatch
def apply_hc_func(elem: Any, func: Callable, apply_numeric: bool = False, level: int = 0):
    return func(elem)


@apply_hc_func.register
def apply_hc_func_list(hc_tree: list, func: Callable, apply_numeric: bool = False, level: int = 0):
    hc_tree_acc = []
    for elem in hc_tree:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        hc_tree_acc.append(transformed)
    return hc_tree_acc
    # raise NotImplemented


@apply_hc_func.register
def apply_hc_func_calc_line(cl: CalcLine, func: Callable, apply_numeric: bool = False, level: int = 0):
    assigns_acc = deque()
    for elem in cl.assigns:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        assigns_acc.append(transformed)
    cl.assigns = assigns_acc

    expr_tree_acc = deque()
    for elem in cl.expression_tree:
        transformed = apply_hc_func(elem, func, apply_numeric, level + 1)
        expr_tree_acc.append(transformed)

    if apply_numeric:
        cl._numeric = expr_tree_acc
    else:
        cl.expression_tree = expr_tree_acc

    return cl


@apply_hc_func.register
def apply_hc_func_expr_line(el: ExprLine, func: Callable, apply_numeric: bool = False, level: int = 0):
    expr_tree_acc = deque()
    for elem in el.expression_tree:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        expr_tree_acc.append(transformed)

    if apply_numeric:
        el._numeric = expr_tree_acc
    else:
        el.expression_tree = expr_tree_acc

    return el


@apply_hc_func.register
def apply_hc_func_funcblock(fb: FunctionBlock, func: Callable, apply_numeric: bool = False, level: int = 0):
    lines_acc = deque()
    for elem in fb.lines:
        transformed = apply_hc_func(elem, func, apply_numeric, level+1)
        lines_acc.append(transformed)
    fb.lines = lines_acc

    namespace_acc = deque()
    for elem in fb.namespace:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        namespace_acc.append(transformed)
    fb.namespace = namespace_acc

    function_name_acc = deque()
    for elem in fb.function_name:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        function_name_acc.append(transformed)
    fb.function_name = function_name_acc

    args_acc = deque()
    for elem in fb.args:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        args_acc.append(transformed)
    fb.args = args_acc

    params_acc = deque()
    for elem in fb.params:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        params_acc.append(transformed)
    fb.params = params_acc

    return fb


@apply_hc_func.register
def apply_hc_func_forblock(fb: ForBlock, func: Callable, apply_numeric: bool = False, level: int = 0):
    lines_acc = deque()
    for elem in fb.lines:
        transformed = apply_hc_func(elem, func, apply_numeric, level + 1)
        lines_acc.append(transformed)
    fb.lines = lines_acc

    assigns_acc = deque()
    for elem in fb.assigns:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        assigns_acc.append(transformed)
    fb.assigns = assigns_acc

    iterator_acc = deque()
    for elem in fb.iterator:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        iterator_acc.append(transformed)
    fb.iterator = iterator_acc

    return fb


@apply_hc_func.register
def apply_hc_func_ifblock(ib: IfBlock, func: Callable, apply_numeric: bool = False, level: int = 0):
    lines_acc = deque()
    for elem in ib.lines:
        transformed = apply_hc_func(elem, func, apply_numeric, level + 1)
        lines_acc.append(transformed)
    ib.lines = lines_acc

    test_acc = deque()
    for elem in ib.test:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        test_acc.append(transformed)
    ib.test = test_acc

    orelse_acc = deque()
    for elem in ib.orelse:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        orelse_acc.append(transformed)
    ib.orelse = orelse_acc
    return ib


@apply_hc_func.register
def apply_hc_func_compblock(cb: ComprehensionBlock, func: Callable, apply_numeric: bool = False, level: int = 0):
    assign_acc = deque()
    for elem in cb.assign:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        assign_acc.append(transformed)
    cb.assign = assign_acc

    key_acc = deque()
    for elem in cb.key:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        key_acc.append(transformed)
    cb.key = key_acc

    value_acc = deque()
    for elem in cb.value:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        value_acc.append(transformed)
    cb.value = value_acc

    comprehensions_acc = deque()
    for elem in cb.comprehensions:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        comprehensions_acc.append(transformed)
    cb.comprehensions = comprehensions_acc
    return cb


@apply_hc_func.register
def apply_hc_func_comp(comp: ForBlock, func: Callable, apply_numeric: bool = False, level: int = 0):
    assigns_acc = deque()
    for elem in comp.assigns:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        assigns_acc.append(transformed)
    comp.assigns = assigns_acc

    iterator_acc = deque()
    for elem in comp.iterator:
        transformed = apply_hc_func(elem, func, apply_numeric, level)
        iterator_acc.append(transformed)
    comp.iterator = iterator_acc
    return comp

@apply_hc_func.register
def apply_hc_func_list_obj(list_obj: List, func: Callable, apply_numeric: bool = False, level: int = 0):
    elems = list_obj.elems
    acc = deque()
    for elem in elems:
        transformed = func(elem, apply_numeric)
        acc.append(transformed)
    list_obj.elems = acc
    return list_obj


@apply_hc_func.register
def apply_hc_func_tuple(tuple_obj: Tuple, func: Callable, apply_numeric: bool = False, level: int = 0):
    elems = tuple_obj.elems
    acc = deque()
    for elem in elems:
        transformed = func(elem, apply_numeric)
        acc.append(transformed)
    tuple_obj.elems = acc
    return tuple_obj


@apply_hc_func.register
def apply_hc_func_set(set_obj: Set, func: Callable, apply_numeric: bool = False, level: int = 0):
    elems = set_obj.elems
    acc = deque()
    for elem in elems:
        transformed = func(elem, apply_numeric)
        acc.append(transformed)
    set_obj.elems = acc
    return set_obj


@apply_hc_func.register
def apply_hc_func_dict(dict_obj: Dictionary, func: Callable, apply_numeric: bool = False, level: int = 0):
    elems = zip(dict_obj.keys, dict_obj.values)
    acc = deque()
    for k, v in elems:
        transformed_k = func(k, apply_numeric)
        transformed_v = func(v, apply_numeric)
        acc.append((transformed_k, transformed_v))
    keys, values = zip(*acc)
    dict_obj.keys, dict_obj.values = deque(keys), deque(values)
    return dict_obj


@apply_hc_func.register
def apply_hc_func_deque(elems: deque, func: Callable, apply_numeric: bool = False, level: int = 0):
    elems_acc = deque()
    for elem in elems:
        transformed = func(elem, apply_numeric)
        elems_acc.append(transformed)
    return elems_acc