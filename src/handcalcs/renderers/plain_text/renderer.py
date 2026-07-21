from collections import deque
from dataclasses import dataclass, field
from typing import Optional
from handcalcs.renderers.base import BaseRenderer, RenderContext, ContextKeyError, ContextValueError


# Node type imports only used for typing
from handcalcs.parsing.nodes import (
    HcNode,
    Name,
    
)
from handcalcs.parsing.line_nodes import (
    CalcLine,
    ExprLine
)
from handcalcs.parsing.block_nodes import (
    IfBlock,
    ElseBlock,
    ElifBlock
)



INDENT = " " * 4

class PlainTextRenderContext(RenderContext):
    pass


class PlainTextRenderer(BaseRenderer):
    name = 'plain_text'

    def create_context(
        self, 
        **kwargs
        ):
        context = PlainTextRenderContext(**kwargs | {'mode': 'full'})
        return context

@PlainTextRenderer.register('name')
def render_name(renderer: PlainTextRenderer, node: Name, context: PlainTextRenderContext) -> str:
    if not hasattr(context, 'current_mode'):
        raise ContextKeyError(
            f"Attempting to render the Name node while context does not have a 'current_mode' key.\n"
            f"{context=}"
        )
    if context.current_mode == 'sym':
        if renderer.symbolic_rules is None:
            symbolic_rules = []
        else:
            symbolic_rules = renderer.symbolic_rules
        symbol = node.identifier
        for rule in symbolic_rules:
            symbol = rule(symbol, context)
        return symbol
    elif context.current_mode == 'num':
        if renderer.numeric_rules is None:
            numeric_rules = []
        else:
            numeric_rules = renderer.numeric_rules
        value = node.value
        for rule in numeric_rules:
            value = rule(value, context)
        return value
    else:
        raise ContextValueError(
            f"The context.current_mode has an unrecognized value: {context.current_mode}"
        )

@PlainTextRenderer.register('calc_line')
def render_calcline(renderer: PlainTextRenderer, node: CalcLine, context: PlainTextRenderContext) -> str:
    rendered = f"{INDENT * node.level}"
    if context.mode == 'full' or 'ass' in context.mode:
        context.current_mode = 'sym'
        print(f"{context=}")
        assign_nodes = deque([renderer.render(subnode, context) for subnode in node.assigns])
        assigns = ", ".join([name.identifier for name in assign_nodes])
        assign_portion = f"{assign}  =  "
        rendered += assign_portion
    if context.mode == 'full' or 'sym' in context.mode:
        context.current_mode = 'sym'
        symbolic = deque([])
        for subnode in node.expression_tree:
            symbolic.append(renderer.render(subnode, context))
        symbolic = "".join(symbolic)
        symbolic_portion = f"{symbolic}  =  "
        rendered += symbolic_portion
    if context.mode == "full" or "num" in context.mode:
        context.current_mode = "num"
        numeric = deque([])
        for subnode in node.expression_tree:
            numeric.append(renderer.render(subnode, context))
        numeric = "".join(numeric)
        numeric_portion = f"{numeric}  =  "
        rendered += numeric_portion
    if context.mode == "full" or "res" in context.mode:
        context.current_mode = "num"
        assign_nodes = deque([renderer.render(subnode) for subnode in node.assigns])
        results = deque([name.value for name in assign_nodes])
        for rule in renderer.numeric_rules:
            for idx, result in enumerate(results):
                results[idx] = rule(result, context)
        result_portion = f"{result}"
        rendered += result_portion
    if node.comment is not None:
        comment_portion = f"  ({node.comment.comment.lstrip("# ")})"
        rendered += comment_portion
    ready_for_next_line = f"{rendered}\n"
    return ready_for_next_line


@PlainTextRenderer.register('expr_line')
def render_exprline(renderer: PlainTextRenderer, node: CalcLine, context: PlainTextRenderContext) -> str:
    rendered = f"{INDENT * node.level}"
    if context.mode == 'full' or 'sym' in context.mode:
        context.current_mode = 'sym'
        symbolic = deque([])
        for subnode in node.expression_tree:
            symbolic.append(renderer.render(subnode, context))
        symbolic = "".join(symbolic)
        symbolic_portion = f"{symbolic}  =  "
        rendered += symbolic_portion
    if context.mode == "full" or "num" in context.mode:
        context.current_mode = "num"
        numeric = deque([])
        for subnode in node.expression_tree:
            numeric.append(renderer.render(subnode, context))
        numeric = "".join(numeric)
        numeric_portion = f"{numeric}  =  "
        rendered += numeric_portion
    # if context.mode == "full" or "res" in context.mode:
    #     context.current_mode = "num"
    #     result = node.assign.value
    #     for rule in renderer.numeric_rules:
    #         result = rule(result, context)
    #     result_portion = f"{result}"
    #     rendered += result_portion
    if node.comment is not None:
        comment_portion = f"  ({node.comment.comment.lstrip("# ")})"
        rendered += comment_portion
    ready_for_next_line = f"{rendered}\n"
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
        lines = "\n".join(lines_acc)
        block_header = f"{INDENT * node.level}{elif_block_header}"
        block_text = f"{block_header}\n{lines}"
        return block_text

                

        




            

