from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Any
from handcalcs.renderers.base import BaseRenderer, RenderContext, ContextKeyError, ContextValueError


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
    HcBinOp
)
from handcalcs.parsing.inline_nodes import (
    InlineComment,
    FunctionCall
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

class PlainTextRenderContext(RenderContext):
    def __init__(self, **kwargs):
        super().__init__()


class PlainTextRenderer(BaseRenderer):
    name = 'plain_text'

    def create_context(
        self, 
        **kwargs
        ):
        context = PlainTextRenderContext(**kwargs | {'mode': 'full'})
        return context

PTR = PlainTextRenderer
PTRC = PlainTextRenderContext

@PlainTextRenderer.register('constant')
def render_constant(renderer: PlainTextRenderer, node: Constant, context: PlainTextRenderContext) -> Any:
    return f"{node.value}"

@PlainTextRenderer.register('inline_comment')
def render_inline_comment(renderer: PlainTextRenderer, node: InlineComment, context: PlainTextRenderContext) -> str:
    return f"  ({node.comment.lstrip("# ")})"

@PlainTextRenderer.register('name')
def render_name(renderer: PlainTextRenderer, node: Name, context: PlainTextRenderContext) -> str:
    if not hasattr(context, 'current_mode'):
        raise ContextKeyError(
            f"Attempting to render the Name node while context does not have a 'current_mode' key.\n"
            f"{context=}"
        )
    if context.current_mode == 'sym':
        return node.identifier
    elif context.current_mode == 'num':
        return f"{node.value}"
    else:
        raise ContextValueError(
            f"The context.current_mode has an unrecognized value: {context.current_mode}"
        )

@PlainTextRenderer.register('add_op')
def render_add_op(renderer: PTR, node: AddOp, context: PTRC) -> str:
    return f"{node.pre}{renderer.render(node.left, context)}{node.symbol}{renderer.render(node.right, context)}{node.post}"


@PlainTextRenderer.register('sub_op')
def render_sub_op(renderer: PTR, node: SubOp, context: PTRC) -> str:
    return f"{node.pre}{renderer.render(node.left, context)}{node.symbol}{renderer.render(node.right, context)}{node.post}"


@PlainTextRenderer.register('mult_op')
def render_mult_op(renderer: PTR, node: AddOp, context: PTRC) -> str:
    return f"{node.pre}{renderer.render(node.left, context)}{node.symbol}{renderer.render(node.right, context)}{node.post}"


@PlainTextRenderer.register('div_op')
def render_div_op(renderer: PTR, node: AddOp, context: PTRC) -> str:
    return f"{node.pre}{renderer.render(node.left, context)}{node.symbol}{renderer.render(node.right, context)}{node.post}"


@PlainTextRenderer.register('pow_op')
def render_pow_op(renderer: PTR, node: AddOp, context: PTRC) -> str:
    return f"{node.pre}{renderer.render(node.left, context)}{node.symbol}{renderer.render(node.right, context)}{node.post}"


@PlainTextRenderer.register('function_call')
def render_function_call(renderer: PTR, node: FunctionCall, context: PTRC) -> str:
    function_name = renderer.render(node.function_name, context)
    namespace = renderer.render(node.namespace, context)
    args = [renderer.render(arg, context) for arg in node.args]
    arg_str = f",{context.single_space_char}".join(args)
    if namespace == '__main__':
        namespace = ''
    if namespace:
        rendered = f"{context.single_space_char}{namespace}.{function_name}({arg_str}){context.single_space_char}"
    else:
        rendered = f"{context.single_space_char}{function_name}({arg_str}){context.single_space_char}"
    return rendered

@PlainTextRenderer.register('import')
def render_import(renderer: PTR, node: Import, context: PTRC) -> str:
    _ = context.single_space_char
    nl = context.newline_char
    names = [
        f"{name.identifier}{_}as{_}{name.value}" if name.value is not None
        else f"{name.identifier}"
        for name in node.names
    ]
    rendered_names = f",{_}".join(names)
    if node.import_from:
        module = node.import_from_module
        level = node.import_from_level
        dots = "." * level
        if module is not None:
            rendered = f"[Python{_}import]:{_}from{_}{dots}{module}{_}import{_}{rendered_names}"
        else:
            rendered = f"[Python{_}import]:{_}from{_}{dots}{_}import{_}{rendered_names}"
    else:
        rendered = f"[Python{_}import]:{_}import{_}{rendered_names}"
    rendered = rendered + f"{nl}{nl}"
    return rendered
        

@PlainTextRenderer.register('calc_line')
def render_calcline(renderer: PlainTextRenderer, node: CalcLine, context: PlainTextRenderContext) -> str:
    rendered = f"{context.single_space_char * context.indent_size * node.level}"
    # Retrieve param_line immediately before the next .render method is called because it will change
    # the state of the context to that of the next node.
    param_line = getattr(context, 'param_line', False)
    if context.mode == 'full' or 'ass' in context.mode:
        context.current_mode = 'sym'
        assign_nodes = deque([renderer.render(subnode, context) for subnode in node.assigns])
        assigns = ", ".join([name for name in assign_nodes])
        assign_portion = f"{assigns}{context.single_space_char}={context.single_space_char}"
        rendered += assign_portion
    if not param_line:
        if context.mode == 'full' or 'sym' in context.mode:
            context.current_mode = 'sym'
            symbolic = deque([])
            for subnode in node.expression_tree:
                symbolic.append(renderer.render(subnode, context))
            symbolic = "".join(symbolic)
            symbolic_portion = f"{symbolic}{context.single_space_char}={context.single_space_char}"
            rendered += symbolic_portion
        if context.mode == "full" or "num" in context.mode:
            context.current_mode = "num"
            numeric = deque([])
            for subnode in node.expression_tree:
                numeric.append(renderer.render(subnode, context))
            numeric = "".join(numeric)
            numeric_portion = f"{numeric}{context.single_space_char}={context.single_space_char}"
            rendered += numeric_portion
    if context.mode == "full" or "res" in context.mode:
        context.current_mode = "num"
        assign_nodes = deque([renderer.render(subnode, context) for subnode in node.assigns])
        results = deque([val for val in assign_nodes])
        for rule in renderer.numeric_rules:
            for idx, result in enumerate(results):
                results[idx] = rule(result, context)
        result_portion = f',{context.single_space_char}'.join(results)
        rendered += result_portion
    if node.comment is not None:
        comment_portion = renderer.render(node.comment, context)
        rendered += comment_portion
    ready_for_next_line = f"{rendered}{context.newline_char}"
    return ready_for_next_line


@PlainTextRenderer.register('expr_line')
def render_exprline(renderer: PlainTextRenderer, node: ExprLine, context: PlainTextRenderContext) -> str:
    rendered = f"{context.single_space_char * context.indent_size * node.level}"
    if context.mode == 'full' or 'sym' in context.mode:
        context.current_mode = 'sym'
        symbolic = deque([])
        for subnode in node.expression_tree:
            symbolic.append(renderer.render(subnode, context))
        symbolic = "".join(symbolic)
        symbolic_portion = f"{symbolic}{context.single_space_char}={context.single_space_char}"
        rendered += symbolic_portion
    if context.mode == "full" or "num" in context.mode:
        context.current_mode = "num"
        numeric = deque([])
        for subnode in node.expression_tree:
            numeric.append(renderer.render(subnode, context))
        numeric = "".join(numeric)
        numeric_portion = f"{numeric}{context.single_space_char}={context.single_space_char}"
        rendered += numeric_portion
    # if context.mode == "full" or "res" in context.mode:
    #     context.current_mode = "num"
    #     result = node.assign.value
    #     for rule in renderer.numeric_rules:
    #         result = rule(result, context)
    #     result_portion = f"{result}"
    #     rendered += result_portion
    if node.comment is not None:
        comment_portion = renderer.render(node.comment, context)
        rendered += comment_portion
    ready_for_next_line = f"{rendered}{context.newline_char}"
    return rendered
    

@PlainTextRenderer.register('elif_block')
def render_elifblock(renderer: PlainTextRenderer, node: ElifBlock, context: PlainTextRenderContext) -> str:
    clauses: deque = node.lines
    try:
        true_clause: IfBlock = next(ib for ib in clauses if ib.is_true)
    except StopIteration:
        if isinstance(clauses[-1], ElseBlock):
            true_clause: ElseBlock = clauses[-1]
        else:
            true_clause = None

    if true_clause is None:
        return "No conditions were satisfied within the if-elif block"
    else:
        condition: deque = true_clause.test
        sym_acc = []
        context.current_mode = 'sym'
        for elem in condition:
            sym_acc.append(renderer.render(elem, context))
        sym_expr = "".join(sym_acc)

        context.current_mode = 'num'
        num_acc = []
        for elem in condition:
            num_acc.append(renderer.render(elem, context))
        num_expr = "".join(num_acc)
        elif_block_header = f"Since ({sym_expr}) -> ({num_expr}) is True:"

        context.current_mode = None
        lines_acc = []
        for line in true_clause.lines:
            lines_acc.append(renderer.render(elem, context))
        lines = f"{context.newline_char}".join(lines_acc)
        block_header = f"{context.single_space_char * context.indent_size * node.level}{elif_block_header}"
        block_text = f"{block_header}\n{lines}"
        return block_text

        
## SWAP RULES

@PlainTextRenderer.register("sym:swap_greeks")
def swap_greeks(node: Name, context: PTRC) -> HcNode:
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
def swap_py_operators(node: HcBinOp, context: PTRC) -> HcBinOp:
    _ = context.single_space_char
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
def toggle_param_line(node: CalcLine, context: PTRC) -> CalcLine:
    if node.type not in ('calc_line',):
        context.param_line = False
    else:
        if (
            len(node.expression_tree) == 1
            and isinstance(node.expression_tree[0], Constant)
        ):
            context.param_line = True
        else:
            context.param_line = False
    return node


@PlainTextRenderer.register("sym:swap_sqrt_symbol")
def swap_sqrt_symbol(node: FunctionCall, context: PTRC) -> FunctionCall:
    if node.type not in ('function_call',): return node
    if node.function_name.identifier == 'sqrt':
        node.function_name.identifier = '√'
        node.function_name.value = '√'
    return node
        


            

