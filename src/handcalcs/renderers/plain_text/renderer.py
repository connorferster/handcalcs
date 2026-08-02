from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Any
from ..base import BaseRenderer, RenderContext, BaseRenderContext, ContextKeyError, ContextValueError


# Node type imports only used for typing
from ...parsing.nodes import (
    HcNode,
    Name,
    Constant,
    
)
from ...parsing.operator_nodes import (
    AddOp,
    MultOp,
    SubOp,
    DivOp,
    ModuloOp,
    FloorOp,
    PowOp,
    HcBinOp,
    EqOp,
    GtOp,
    GtEOp,
    LtOp,
    LtEOp,
    NeqOp,
    HcCompOp
)
from ...parsing.inline_nodes import (
    InlineComment,
    FunctionCall,
    Compare
)
from ...parsing.line_nodes import (
    CalcLine,
    ExprLine,
    Import
)
from ...parsing.block_nodes import (
    IfBlock,
    ElseBlock,
    ElifBlock
)



class PlainTextRenderer(BaseRenderer):
    name = 'plain_text'

    # def create_context(
    #     self, 
    #     **kwargs
    #     ):
    #     context = PlainTextRenderContext(**kwargs | {'mode': 'full'})
    #     return context

PTR = PlainTextRenderer
BRC = BaseRenderContext


## SWAP RULES

@PlainTextRenderer.register("sym:swap_greeks")
def swap_greeks(node: Name, base_base_context:BRC) -> HcNode:
    """
    Swaps out any greek substrings or unicode symbols
    """

    if not isinstance(node, Name): return node
    GREEK_LOWER = {
        "alpha": "α",
        "beta": "β",
        "gamma": "γ",
        "delta": "δ",
        "epsilon": "ε",
        "varepsilon": "ϵ",
        "zeta": "ζ",
        "theta": "θ",
        "vartheta": "ϑ",
        "iota": "ι",
        "kappa": "κ",
        "mu": "μ",
        "nu": "ν",
        "xi": "ξ",
        "omicron": "ο",
        "pi": "π",
        "varpi": "ϖ",
        "rho": "ρ",
        "varrho": "ϱ",
        "sigma": "σ",
        "varsigma": "ς",
        "tau": "τ",
        "upsilon": "υ",
        "phi": "φ",
        "varphi": "ϕ",
        "chi": "χ",
        "omega": "ω",
        "eta": "η",
        "psi": "ψ",
        "lamb": "λ",
    }

    GREEK_UPPER = {
        "Alpha": "Α",
        "Beta": "Β",
        "Gamma": "Γ",
        "Delta": "Δ",
        "Epsilon": "Ε",
        "Zeta": "Ζ",
        "Theta": "Θ",
        "Iota": "Ι",
        "Kappa": "Κ",
        "Mu": "Μ",
        "Nu": "Ν",
        "Xi": "Ξ",
        "Omicron": "Ο",
        "Pi": "Π",
        "Rho": "Ρ",
        "Sigma": "Σ",
        "Tau": "Τ",
        "Upsilon": "Υ",
        "Phi": "Φ",
        "Chi": "Χ",
        "Omega": "Ω",
        "Eta": "Η",
        "Psi": "Ψ",
        "Lamb": "Λ",
    }

    for name, unicode in (GREEK_LOWER | GREEK_UPPER).items():
        id_components = node.identifier.split("_")
        swapped_components = []
        for comp in id_components:
            if comp == name:
                comp = unicode
            swapped_components.append(comp)
        swapped_id = "_".join(swapped_components)
        node.identifier = swapped_id
    return node
    
    
@PlainTextRenderer.register("sym:swap_py_operators")
def swap_py_operators(node: HcBinOp, base_context:BRC) -> HcBinOp:
    context = base_context.current
    _ = context.space
    if node.type not in ('mult_op', 'pow_op', 'div_op', 'floor_op', 'add_op', 'sub_op'):
        return node
    elif node.type == 'mult_op':
        node.symbol = ')('
        node.pre = '('
        node.post = ')'
        return node
    elif node.type == 'div_op':
        symbol = f"){_}/{_}("
        pre = "("
        post = ")"
        # If it is a simple denominator, trim the parenths
        if isinstance(node.right, Constant):
            symbol = symbol[:-1]
            post = ""
        # And if it is also a simple numerator, trim the parenths
        if isinstance(node.left, Constant):
            symbol = symbol[1:]
            pre = ""
        node.symbol = symbol
        node.pre = pre
        node.post = post
        return node
    elif node.type == 'floor_op':
        node.symbol = ') / ('
        node.pre = 'floor[('
        node.post = ')]'
        return node
    elif node.type == 'add_op':
        node.symbol = ' + '
        return node
    elif node.type == 'sub_op':
        node.symbol = ' - '
        return node
    elif node.type == 'pow_op' and isinstance(node.right, Constant):
        exp_str = str(node.right.value)
        node.symbol = ''
        superscript_integers = {
            "1": "¹",
            "2": "²",
            "3": "³",
            "4": "⁴",
            "5": "⁵",
            "6": "⁶",
            "7": "⁷",
            "8": "⁸",
            "9": "⁹",
            "0": "⁰",
            ".": "'"
        }
        acc = []
        for char in exp_str:
            acc.append(superscript_integers.get(char,char))
        
        node.right = Constant(value="".join(acc))
        return node
    else:
        return node
        

@PlainTextRenderer.register("sym:toggle_param_line")
def toggle_param_line(node: CalcLine, base_context:BRC) -> CalcLine:
    context = base_context.current
    if node.type not in ('calc_line',):
        base_context.line_context.param_line = False
    else:
        if (
            len(node.expression_tree) == 1
            and isinstance(node.expression_tree[0], Constant)
        ):
            base_context.line_context.param_line = True
        else:
            base_context.line_context.param_line = False
    return node


@PlainTextRenderer.register("sym:swap_sqrt_symbol")
def swap_sqrt_symbol(node: FunctionCall, base_context:BRC) -> FunctionCall:
    if node.type not in ('function_call',): return node
    if node.function_name.identifier == 'sqrt':
        node.function_name.identifier = '√'
        node.function_name.value = '√'
    return node


            

