from collections import deque
from dataclasses import dataclass, field
from typing import Optional
from handcalcs.renders.base import BaseRenderer, RenderContext, ContextKeyError, ContextValueError

# Node type imports only used for typing
from handcalcs.parsing.nodes import (
    HcNode,
    Name,
    
)

class PlainTextRenderContext(RenderContext):
    pass


class PlainTextRenderer(BaseRenderer):
    name = 'plain_text'

    def create_context(
        self, 
        **kwargs
        ):
        context = PlainTextRenderContext(mode, commands)
        return context

@PlainTextRenderer.register('name')
def render_name(renderer: PlainTextRenderer, node: Name, context: PlainTextRenderContext) -> str:
    if not hasattr(context, 'current_mode'):
        raise ContextKeyError(
            f"Attempting to render the Name node while context does not have a 'current_mode' key.\n"
            f"{context=}"
        )
    if context.current_mode == 'sym':
        if self.symbolic_rules is None:
            symbolic_rules = []
        else:
            symbolic_rules = self.symbolic_rules
        symbol = node.identifier
        for rule in symbolic_rules:
            symbol = rule(symbol, context)
        return symbol
    elif context.current_mode == 'num':
        if self.numeric_rules is None:
            numeric_rules = []
        else:
            numeric_rules = self.numeric_rules
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
    rendered = ""
    if context.mode == 'full' or 'ass' in context.mode:
        context.current_mode = 'sym'
        assign = self.render(node.assign, context)
        assign_portion = f"{assign}  =  "
        rendered += assign_portion
    if context.mode == 'full' or 'sym' in context.mode:
        context.current_mode = 'sym'
        symbolic = deque([])
        for subnode in node.expression_tree:
            symbolic.append(self.render(subnode, context))
        symbolic = "".join(symbolic)
        symbolic_portion = f"{symbolic}  =  "
        rendered += symbolic_portion
    if context.mode == "full" or "num" in context.mode:
        context.current_mode = "num"
        numeric = deque([])
        for subnode in node.expression_tree:
            numeric.append(self.render(subnode, context))
        numeric = "".join(numeric)
        numeric_portion = f"{numeric}  =  "
        rendered += numeric_portion
    if context.mode == "full" or "res" in context.mode:
        context.current_mode = "num"
        result = node.assign.value
        for rule in self.numeric_rules:
            result = rule(result, context)
        result_portion = f"{result}"
        rendered += result_portion
    if node.comment is not None:
        comment_portion = f"  ({node.comment.comment.lstrip("# ")})"
        rendered += comment_portion
    return rendered


@PlainTextRenderer.register('expr_line')
def render_exprline(renderer: PlainTextRenderer, node: CalcLine, context: PlainTextRenderContext) -> str:
    rendered = ""
    if context.mode == 'full' or 'sym' in context.mode:
        context.current_mode = 'sym'
        symbolic = deque([])
        for subnode in node.expression_tree:
            symbolic.append(self.render(subnode, context))
        symbolic = "".join(symbolic)
        symbolic_portion = f"{symbolic}  =  "
        rendered += symbolic_portion
    if context.mode == "full" or "num" in context.mode:
        context.current_mode = "num"
        numeric = deque([])
        for subnode in node.expression_tree:
            numeric.append(self.render(subnode, context))
        numeric = "".join(numeric)
        numeric_portion = f"{numeric}  =  "
        rendered += numeric_portion
    if context.mode == "full" or "res" in context.mode:
        context.current_mode = "num"
        result = node.assign.value
        for rule in self.numeric_rules:
            result = rule(result, context)
        result_portion = f"{result}"
        rendered += result_portion
    if node.comment is not None:
        comment_portion = f"  ({node.comment.comment.lstrip("# ")})"
        rendered += comment_portion
    return rendered
    
@PlainTextRenderer.register('elif_block')
def render_elifblock(renderer: PlainTextRenderer, node: ElifBlock, context: PlainTextRenderContext) -> str:
    pass

        




            

