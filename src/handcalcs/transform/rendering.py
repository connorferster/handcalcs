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
def hc_render(elem: Any, config_options: dict):
    raise NotImplementedError


@hc_render.register
def hc_render_list(hc_tree: list[Any], config_options: dict[str, str]):
    hc_tree_acc = []
    for elem in hc_tree:
        transformed = hc_render(elem, config_options)
        hc_tree_acc.append(transformed)
    return hc_tree_acc
    # raise NotImplemented


@hc_render.register
def hc_render_calc_line(cl: CalcLine, config_options: dict):
    opts = config_options
    assign_elems = opts.get('assign_sep', '').join(cl.assigns)
    assigns = f"{opts.get('pre_assign', '')}{assign_elems}{opts.get('post_assign', '')}"
    assign_eq = opts.get('eq_op', '')
    assigns = f"{assigns}{assign_eq}"

    expr_tree_acc = deque()
    for elem in cl.expression_tree:
        transformed = hc_render(elem, config_options)
        expr_tree_acc.append(transformed)

    # if apply_numeric:
        cl._numeric = expr_tree_acc
    # else:
        cl.expression_tree = expr_tree_acc

    return cl