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



class HTMLRenderer(BaseRenderer):
    name = 'html'

    # def create_context(
    #     self, 
    #     **kwargs
    #     ):
    #     context = PlainTextRenderContext(**kwargs | {'mode': 'full'})
    #     return context

HTMLR = HTMLRenderer
BRC = BaseRenderContext


## SWAP RULES

@HTMLR.register("name:sym")
def swap_greeks(renderer: HTMLR, node: Name, base_context: BRC) -> HcNode:
    """
    Swaps out any greek substrings or unicode symbols in a Name's identifier.

    Registered as a 'sym' rule on the Name node: the identifier is only shown in
    symbolic mode (numeric mode renders the Name's value instead).
    """
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

@HTMLR.register("name:sym")
def swap_special_symbols(renderer: HTMLR, node: Name, base_context: BRC) -> Name:
    """
    Swaps '_prime', '_star', '_bar' and '_hat' symbols
    """
    identifier = node.identifier
    identifier = identifier.replace("_hat_", "\u0302_")
    identifier = identifier.replace("_prime_", f"\u2032_")
    identifier = identifier.replace("_star_", "<sup>*</sup>_")
    identifier = identifier.replace("_bar_", "\u0305_")
    node.identifier = identifier
    return node

@HTMLR.register("name:sym")
def swap_subscripts(renderer: HTMLR, node: Name, base_context: BRC) -> Name:
    """
    Interprets single underscores as subscripts, double underscores as spaces,
    triple underscores as literal underscores
    """
    context = base_context.current
    _ = context.space
    identifier = node.identifier
    # Replace all extra underscores with non-identifier characters for later
    identifier = identifier.replace('___', '|')
    identifier = identifier.replace("__", "^")
    under_count = identifier.count("_")
    identifier = identifier.replace("_", "<sub>")
    closers = "</sub>" * under_count
    identifier = f"{identifier}{closers}"
    identifier = identifier.replace("^", _)
    identifier = identifier.replace("|", "_")
    node.identifier = identifier
    return node
    
@HTMLR.register("mult_op:pre")
@HTMLR.register("pow_op:pre")
@HTMLR.register("div_op:pre")
@HTMLR.register("floor_op:pre")
@HTMLR.register("add_op:pre")
@HTMLR.register("sub_op:pre")
def swap_py_operators(renderer: HTMLR, node: HcBinOp, base_context: BRC) -> HcBinOp:
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
        node.symbol = '·'
        node.pre = ''
        node.post = ''
        return node
    elif node.type == 'div_op':
        # Division always renders with its '/' symbol. Any parentheses around an
        # operand come from the infix precedence logic (lpar/rpar), not from
        # pre/post, so pre/post stay empty regardless of operand type.
        node.symbol = "/"
        node.pre = ""
        node.post = ""
        return node
    elif node.type == 'floor_op':
        node.symbol = '//'
        node.pre = ''
        node.post = ''
        return node
    elif node.type == 'add_op':
        node.symbol = '+'
        return node
    elif node.type == 'sub_op':
        node.symbol = '-'
        return node
    elif node.type == 'pow_op' and isinstance(node.right, Constant):
        exp_str = str(node.right.value)
        node.symbol = ''
        supered = f"<sup>{exp_str}</sup>"
        node.right = Constant(value=supered)
        return node
    else:
        return node


@PlainTextRenderer.register("function_call:pre")
def swap_sqrt_symbol(renderer: HTMLR, node: FunctionCall, base_context: BRC) -> FunctionCall:
    """
    Swap a ``sqrt(...)`` call's function name for the '√' symbol.

    Registered as a 'pre' rule on function_call: the function name is shown in
    both symbolic and numeric columns, so the swap must be mode-independent. The
    mutation is idempotent across the two render passes.
    """
    if node.function_name.identifier == 'sqrt':
        node.function_name.identifier = '√'
        node.function_name.value = '√'
    return node


            

