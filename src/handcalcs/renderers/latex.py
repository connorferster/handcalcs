from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Any
from handcalcs.renderers.base import BaseRenderer, RenderContext, BaseRenderContext, ContextKeyError, ContextValueError


# Node type imports only used for typing
from handcalcs.parsing.nodes import (
    HcNode,
    Name,
    Constant,
    
)
from handcalcs.parsing.operator_nodes import (
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
from handcalcs.parsing.inline_nodes import (
    InlineComment,
    FunctionCall,
    Compare
)
from handcalcs.parsing.line_nodes import (
    CalcLine,
    ExprLine,
    Import
)
from handcalcs.parsing.block_nodes import (
    IfBlock,
    ElseBlock,
    ElifBlock
)



class LatexRenderer(BaseRenderer):
    name = 'latex'

    # def create_context(
    #     self, 
    #     **kwargs
    #     ):
    #     context = PlainTextRenderContext(**kwargs | {'mode': 'full'})
    #     return context

LR = LatexRenderer
BRC = BaseRenderContext

BRC.global_context.space = '\\ '
BRC.global_context.newline = '\\\n'
BRC.global_context.indent = '\hspace*{1em}'


## SWAP RULES

@LatexRenderer.register("name:sym")
def swap_greeks(renderer: LR, node: Name, base_context: BRC) -> HcNode:
    """
    Swaps out any greek substrings or unicode symbols in a Name's identifier.

    Registered as a 'sym' rule on the Name node: the identifier is only shown in
    symbolic mode (numeric mode renders the Name's value instead).
    """
    GREEK_LOWER = {
        "alpha": "\\alpha",
        "beta": "\\beta",
        "gamma": "\\gamma",
        "delta": "\\delta",
        "epsilon": "\\epsilon",
        "varepsilon": "\\varepsilon",
        "zeta": "\\zeta",
        "theta": "\\theta",
        "vartheta": "\\vartheta",
        "iota": "\\iota",
        "kappa": "\\kappa",
        "mu": "\\mu",
        "nu": "\\nu",
        "xi": "\\xi",
        "omicron": "\\omicron",
        "pi": "\\pi",
        "varpi": "\\varpi",
        "rho": "\\rho",
        "varrho": "\\varrho",
        "sigma": "\\sigma",
        "varsigma": "\\varsigma",
        "tau": "\\tau",
        "upsilon": "\\upsion",
        "phi": "\\phi",
        "varphi": "\\varphi",
        "chi": "\\chi",
        "omega": "\\omega",
        "eta": "\\eta",
        "psi": "\\psi",
        "lamb": "\\lambda",
    }

    GREEK_UPPER = {
        "Alpha": "\\Alpha",
        "Beta": "\\Beta",
        "Gamma": "\\Gamma",
        "Delta": "\\Delta",
        "Epsilon": "\\Epsilon",
        "Zeta": "\\Zeta",
        "Theta": "\\Theta",
        "Iota": "\\Iota",
        "Kappa": "\\Κappa",
        "Mu": "\\Mu",
        "Nu": "\\Nu",
        "Xi": "\\Xi",
        "Omicron": "\\Omicron",
        "Pi": "\\Pi",
        "Rho": "\\Rho",
        "Sigma": "\\Sigma",
        "Tau": "\\Tau",
        "Upsilon": "\\Upsilon",
        "Phi": "\\Phi",
        "Chi": "\\Chi",
        "Omega": "\\Omega",
        "Eta": "\\Eta",
        "Psi": "\\Psi",
        "Lamb": "\\Lambda",
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
    
    
@LatexRenderer.register("mult_op:pre")
@LatexRenderer.register("pow_op:pre")
@LatexRenderer.register("div_op:pre")
@LatexRenderer.register("floor_op:pre")
@LatexRenderer.register("add_op:pre")
@LatexRenderer.register("sub_op:pre")
@LatexRenderer.register("mod_op:pre")
def swap_py_operators(renderer: LR, node: HcBinOp, base_context: BRC) -> HcBinOp:
    """
    Rewrite a binary operator's display symbol/pre/post to the plain-text form.

    Registered as a 'pre' rule on each arithmetic operator node: the swap is
    mode-independent (the same symbol is shown in both the symbolic and numeric
    columns), so it must run before rendering regardless of mode. The mutation
    is idempotent, so re-running it on the second (numeric) pass is harmless.
    """
    context = base_context.current
    _ = context.space
    if node.type not in ('mult_op', 'pow_op', 'div_op', 'floor_op', 'add_op', 'sub_op'):
        return node
    elif node.type == 'mult_op':
        node.symbol = '\\cdot'
        node.pre = ''
        node.post = ''
        return node
    elif node.type == 'div_op':
        # Division always renders with its '/' symbol. Any parentheses around an
        # operand come from the infix precedence logic (lpar/rpar), not from
        # pre/post, so pre/post stay empty regardless of operand type.
        node.symbol = "}{"
        node.pre = "\\frac{"
        node.post = "}"
        return node
    elif node.type == 'floor_op':
        node.symbol = '}{'
        node.pre = '\\lfloor \\frac{'
        node.post = '} \\rfloor'
        return node
    elif node.type == 'add_op':
        node.symbol = '+'
        return node
    elif node.type == 'mod_op':
        node.symbol = '\\bmod'
    elif node.type == 'sub_op':
        node.symbol = '-'
        return node
    elif node.type == 'pow_op' and isinstance(node.right, Constant):
        node.symbol = '^{'
        node.post = '}'
        return node
    else:
        return node


@LatexRenderer.register("function_call:pre")
def swap_func_symbols(renderer: LR, node: FunctionCall, base_context: BRC) -> FunctionCall:
    """
    Swap function names for special function symbols in Latex. e.g. swap a ``sqrt(...)`` call's 
    function name for the '\\sqrt{}' symbol.

    Registered as a 'pre' rule on function_call: the function name is shown in
    both symbolic and numeric columns, so the swap must be mode-independent. The
    mutation is idempotent across the two render passes.
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
    }
    node.pre = '\\left('
    node.post = '\\right)'
    if node.function_name.identifier == 'sqrt':
        node.function_name.identifier = '\\sqrt'
        node.function_name.value = '\\sqrt'
        node.pre = '{'
        node.post = '}'
    elif node.function_name.identifier == 'floor':
        node.function_name.identifier = ''
        node.function_name.value = ''
        node.pre = '\\lfloor'
        node.post = '\\rfloor'
    elif node.function_name.identifier == 'ceil':
        node.function_name.identifier = ''
        node.function_name.value = ''
        node.pre = '\\lceil'
        node.post = '\\rceil'
    elif node.function_name.identifier in latex_math_funcs:
        func_identifier = node.function_name.identifier
        latex_func_name = latex_math_funcs.get(func_identifier)
        node.function.identifier = latex_func_name
        node.function.value = latex_func_name
    else:
        new_func_name = node.function_name.identifier
        wrapped_func_name = f"\\operatorname{{{new_func_name}}} "
        node.function.identifier = wrapped_func_name
        node.function.value = wrapped_func_name
    return node


            

