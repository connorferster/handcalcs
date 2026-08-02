from collections import deque, ChainMap
from dataclasses import dataclass, field
from typing import ClassVar, Callable, Optional, Any
from handcalcs.parsing.nodes import HcNode
from handcalcs.parsing.sequence import HcSequence

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
    Compare,
    InlineCommand
)
from handcalcs.parsing.line_nodes import (
    CalcLine,
    ExprLine,
    Import,
    CommentCommand
)
from handcalcs.parsing.block_nodes import (
    IfBlock,
    ElseBlock,
    ElifBlock
)

RenderHandler = Callable

class ContextValueError(Exception):
    pass

class ContextKeyError(Exception):
    pass

class RenderContext:
    def __init__(
        self, 
        space: str = ' ', 
        newline: str = '\n', 
        indent: int = "    ",
        mode: str = 'full',
        **kwargs
    ):
        self.space = space
        self.newline = newline
        self.indent = indent
        self.mode = mode

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        attrs = [f"{k}={v}" for k, v in self.__dict__.items() if not k.startswith("_") and k.islower()]
        repr_attrs = ", ".join(attrs)
        return f"{__class__.__name__}({repr_attrs})"

    def __or__(self, other):
        if not isinstance(other, self.__class__):
            raise ValueError(f"Can only union between two RenderContexts, not {type(other)}.")
        else:
            return RenderContext(self.__dict__ | other.__dict__)


class BaseRenderContext:
    def __init__(self, global_context: RenderContext, line_context: RenderContext):

        self.global_context = global_context
        self.line_context = line_context

    
    @property
    def current(self):
        return RenderContext(**ChainMap(self.line_context.__dict__, self.global_context.__dict__))


class BaseRenderer:
    name: ClassVar[str] = 'base'
    node_handlers: ClassVar[dict[str, Callable]] = {}
    symbolic_rules: ClassVar[dict[str, Callable]] = {}
    numeric_rules: ClassVar[dict[str, Callable]] = {}
    root_pre_renderers: ClassVar[dict[str, Callable]] = {}
    root_post_renderers: ClassVar[dict[str, Callable]] = {}

    def __init__(self) -> None:
        self._handlers: dict[str, Callable] = dict(self.node_handlers)
        self._symbolic_rules: dict[str, Callable] = dict(self.symbolic_rules)
        self._numeric_rules: dict[str, Callable] = dict(self.numeric_rules)
        self._root_pre_renderers: dict[str, Callable] = dict(self.root_pre_renderers)
        self._root_post_renderers: dict[str, Callable] = dict(self.root_post_renderers)


    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.node_handlers = dict(cls.node_handlers)
        cls.symbolic_rules = dict(cls.symbolic_rules)
        cls.numeric_rules = dict(cls.numeric_rules)
        cls.root_pre_renderers = dict(cls.root_pre_renderers)
        cls.root_post_renderers = dict(cls.root_post_renderers)

    def create_context(self, **kwargs) -> RenderContext:
        return BaseRenderContext(RenderContext(**kwargs), RenderContext())


    def render(self, node: HcNode, base_context: Optional[BaseRenderContext] = None) -> str:
        """
        Render a node.

        If 'context' is None, a new context is created.
        """
        if base_context is None:
            base_context = self.create_context()
        if node.type == 'root':
            return self.render_root(node, base_context)
        return self.render_node(node, base_context)


    def render_root(self, root: HcSequence, base_context: BaseRenderContext) -> str:
        """
        Render an HcSequence (root node) with the registered pre/post render callables.
        """
        parts = [pre(self, root, base_context) for pre in self._root_pre_renderers]
        for node in root.sequence:
            parts.append(self.render(node, base_context))
        parts.extend(
            [post(self, root, base_context) for post in self._root_post_renderers]
        )
        return parts

    def render_node(self, node: HcNode, base_context: BaseRenderContext) -> str:
        """
        Render one node with an existing context.
        """
        for rule in self.symbolic_rules.values():
            node = rule(node, base_context)
        for rule in self.numeric_rules.values():
            node = rule(node, base_context)
        handler = self._handlers.get(node.type)
        if handler is None:
            return self.render_unknown(node, base_context)
        return handler(self, node, base_context)

    @classmethod
    def register(cls, node_classifier: str) -> Callable[[Callable], Callable]:
        """
        Register a render handler for a given node classifier.
        """
        def decorator(handler: Callable) -> Callable:
            if ":" in node_classifier and node_classifier.count(":") == 1:
                node_name, callable_identifier = node_classifier.split(":")

                if node_name == "pre":
                    cls.root_pre_renderers.update({callable_identifier: handler})
                elif node_name == "post":
                    cls.root_post_renderers.update({callable_identifier: handler})
                elif node_name == "sym":
                    cls.symbolic_rules.update({callable_identifier: handler})
                elif node_name == "num": 
                    cls.numeric_rules.update({callable_identifier: handler})
                else:
                    raise NotImplementedError(
                        f"Cannot register a method for {node_classifier}.\n"
                        "Node classifiers must be either in the form of {prefix}:{unique_identifier} "
                        "where {prefix} is one of: 'pre', 'post', 'sym', 'num'\n-or-\n"
                        "the node classifier must be the name of a recognized HcNode (in snake_case)."
                    )
            else:
                cls.node_handlers.update({node_classifier: handler})
            return handler
        return decorator

    def register_handler(self, node_classifier: str, handler: RenderHandler) -> None:
    
        if ":" in node_classifier and node_classifier.count(":") == 1:
            node_name, callable_identifier = node_classifier.split(":")
            if node_name == "pre":
                self._root_pre_renderers.update({callable_identifier: handler})
            elif node_name == "post":
                self._root_post_renderers.update({callable_identifier: handler})
            elif node_name == "sym":
                self._symbolic_rules.update({callable_identifier: handler})
            elif node_name == "num": 
                self._numeric_rules.update({callable_identifier: handler})
            else:
                raise NotImplementedError(
                    f"Cannot register a method for {node_classifier}.\n"
                    "Node classifiers must be either in the form of {prefix}:{unique_identifier} "
                    "where {prefix} is one of: 'pre', 'post', 'sym', 'num'\n-or-\n"
                    "the node classifier must be the name of a recognized HcNode (in snake_case)."
                )
        else:
            self._handlers.update({node_classifier: handler})


    def render_unknown(self, node: HcNode, base_context: BaseRenderContext) -> str:
        return str(node)


## Register BaseRenderer basic node implementations

BR = BaseRenderer
BRC = RenderContext


@BaseRenderer.register('constant')
def render_constant(renderer: BaseRenderer, node: Constant, base_context: BaseRenderContext) -> Any:
    return f"{node.value}"

@BaseRenderer.register('inline_comment')
def render_inline_comment(renderer: BaseRenderer, node: InlineComment, base_context: BaseRenderContext) -> str:
    context = base_context.current
    _ = context.space
    return f"{_}({node.content})"

@BaseRenderer.register('name')
def render_name(renderer: BaseRenderer, node: Name, base_context: BaseRenderContext) -> str:
    context = base_context.current
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

@BaseRenderer.register('add_op')
def render_add_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    return f"{node.pre}{renderer.render(node.left, base_context)}{node.symbol}{renderer.render(node.right, base_context)}{node.post}"


@BaseRenderer.register('sub_op')
def render_sub_op(renderer: BR, node: SubOp, base_context: BaseRenderContext) -> str:
    return f"{node.pre}{renderer.render(node.left, base_context)}{node.symbol}{renderer.render(node.right, base_context)}{node.post}"


@BaseRenderer.register('mult_op')
def render_mult_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    return f"{node.pre}{renderer.render(node.left, base_context)}{node.symbol}{renderer.render(node.right, base_context)}{node.post}"


@BaseRenderer.register('div_op')
def render_div_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    return f"{node.pre}{renderer.render(node.left, base_context)}{node.symbol}{renderer.render(node.right, base_context)}{node.post}"


@BaseRenderer.register('pow_op')
def render_pow_op(renderer: BR, node: AddOp, base_context: BaseRenderContext) -> str:
    return f"{node.pre}{renderer.render(node.left, base_context)}{node.symbol}{renderer.render(node.right, base_context)}{node.post}"

@BaseRenderer.register('gt_op')
def render_gt_op(renderer: BR, node: GtOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('gte_op')
def render_gte_op(renderer: BR, node: GtEOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('lt_op')
def render_lt_op(renderer: BR, node: LtOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('lte_op')
def render_lte_op(renderer: BR, node: LtEOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('eq_op')
def render_eq_op(renderer: BR, node: EqOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('neq_op')
def render_neq_op(renderer: BR, node: NeqOp, base_context: BaseRenderContext) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('compare')
def render_compare(renderer: BR, node: Compare, base_context: BaseRenderContext) -> str:
    acc = [renderer.render(node, base_context) for node in node.comparison]
    return f"".join(acc)

@BaseRenderer.register('function_call')
def render_function_call(renderer: BR, node: FunctionCall, base_context: BaseRenderContext) -> str:
    context = base_context.current
    function_name = renderer.render(node.function_name, base_context)
    namespace = renderer.render(node.namespace, base_context)
    args = [renderer.render(arg, base_context) for arg in node.args]
    arg_str = f",{context.space}".join(args)
    if namespace == '__main__':
        namespace = ''
    if namespace:
        rendered = f"{context.space}{namespace}.{function_name}({arg_str}){context.space}"
    else:
        rendered = f"{context.space}{function_name}({arg_str}){context.space}"
    return rendered


@BaseRenderer.register('comment_command')
def render_comment_command(renderer: BR, node: CommentCommand, base_context: BaseRenderContext) -> str:
    base_context.global_context = base_context.global_context | RenderContext(**node.commands)
    return ''


@BaseRenderer.register('inline_command')
def render_inline_command(renderer: BR, node: InlineCommand, base_context: BaseRenderContext) -> str:
    base_context.line_context =  RenderContext(**node.commands)
    return ''


@BaseRenderer.register('import')
def render_import(renderer: BR, node: Import, base_context: BaseRenderContext) -> str:
    context = base_context.current
    _ = context.space
    nl = context.newline
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
        

@BaseRenderer.register('calc_line')
def render_calcline(renderer: BaseRenderer, node: CalcLine, base_context: BaseRenderContext) -> str:
    context = base_context.current
    comment_render = None
    # TODO: Remove param_line from base implementation and move to PTRC
    #   - Break out rendering code into subroutines
    #   - Make sure you no longer need to maintain retrieving context before parsing other nodes
    # Retrieve param_line immediately before the next .render method is called because it will change
    # the state of the current context to the context of the next node.
    param_line = getattr(context, 'param_line', False)
    comment_render = None
    if node.comment is not None:
        comment_render = renderer.render(node.comment, base_context)
    # Update the context from teh comment render
    context = base_context.current
    rendered = f"{context.indent * node.level}"
    if context.mode == 'full' or 'ass' in context.mode:
        base_context.line_context.current_mode = 'sym'
        assign_nodes = deque([renderer.render(subnode, base_context) for subnode in node.assigns])
        assigns = ", ".join([name for name in assign_nodes])
        assign_portion = f"{assigns}{context.space}={context.space}"
        rendered += assign_portion
    if not param_line:
        if context.mode == 'full' or 'sym' in context.mode:
            base_context.line_context.current_mode = 'sym'
            symbolic = deque([])
            for subnode in node.expression_tree:
                symbolic.append(renderer.render(subnode, base_context))
            symbolic = "".join(symbolic)
            symbolic_portion = f"{symbolic}{context.space}={context.space}"
            rendered += symbolic_portion
        if context.mode == "full" or "num" in context.mode:
            base_context.line_context.current_mode = "num"
            numeric = deque([])
            for subnode in node.expression_tree:
                numeric.append(renderer.render(subnode, base_context))
            numeric = "".join(numeric)
            numeric_portion = f"{numeric}{context.space}={context.space}"
            rendered += numeric_portion
    if context.mode == "full" or "res" in context.mode:
        base_context.line_context.current_mode = "num"
        assign_nodes = deque([renderer.render(subnode, base_context) for subnode in node.assigns])
        results = deque([val for val in assign_nodes])
        for rule in renderer.numeric_rules:
            for idx, result in enumerate(results):
                results[idx] = rule(result, base_context)
        result_portion = f',{context.space}'.join(results)
        rendered += result_portion
    if comment_render is not None:
        rendered += comment_render
    ready_for_next_line = f"{rendered}{context.newline}"
    context.line_context = RenderContext() # Clear any line-specific context
    return ready_for_next_line


@BaseRenderer.register('expr_line')
def render_exprline(renderer: BaseRenderer, node: ExprLine, base_context: BaseRenderContext) -> str:
    context = base_context.current
    rendered = f"{context.indent * node.level}"
    if context.mode == 'full' or 'sym' in context.mode:
        context.current_mode = 'sym'
        symbolic = deque([])
        for subnode in node.expression_tree:
            symbolic.append(renderer.render(subnode, base_context))
        symbolic = "".join(symbolic)
        symbolic_portion = f"{symbolic}{context.space}={context.space}"
        rendered += symbolic_portion
    if context.mode == "full" or "num" in context.mode:
        context.current_mode = "num"
        numeric = deque([])
        for subnode in node.expression_tree:
            numeric.append(renderer.render(subnode, base_context))
        numeric = "".join(numeric)
        numeric_portion = f"{numeric}{context.space}={context.space}"
        rendered += numeric_portion
    # if context.mode == "full" or "res" in context.mode:
    #     context.current_mode = "num"
    #     result = node.assign.value
    #     for rule in renderer.numeric_rules:
    #         result = rule(result, base_context)
    #     result_portion = f"{result}"
    #     rendered += result_portion
    if node.comment is not None:
        comment_portion = renderer.render(node.comment, base_context)
        rendered += comment_portion
    ready_for_next_line = f"{rendered}{context.newline}"
    return rendered
    

@BaseRenderer.register('elif_block')
def render_elifblock(renderer: BaseRenderer, node: ElifBlock, base_context: BaseRenderContext) -> str:
    clauses: deque = node.lines
    try:
        true_clause: IfBlock = next(ib for ib in clauses if ib.is_true)
    except StopIteration:
        if len(clauses) >= 1 and isinstance(clauses[-1], ElseBlock):
            true_clause: ElseBlock = clauses[-1]
        else:
            true_clause = None

    if true_clause is None:
        return "No conditions were satisfied within the if-elif block"
    else:
        block_text = renderer.render(true_clause, base_context)
        return block_text

@BaseRenderer.register('if_block')
def render_if_block(renderer: BaseRenderer, node: IfBlock, base_context: BaseRenderContext) -> str:
    context = base_context.current
    _ = context.space
    condition: deque = node.test.comparison
    sym_acc = []
    context.current_mode = 'sym'
    for elem in condition:
        sym_acc.append(renderer.render(elem, base_context))
    sym_expr = "".join(sym_acc)

    context.current_mode = 'num'
    num_acc = []
    for elem in condition:
        num_acc.append(renderer.render(elem, base_context))
    num_expr = "".join(num_acc)
    if_block_header = f"Since{_}({sym_expr}){_}->{_}({num_expr}){_}is{_}True:"

    context.current_mode = None
    lines_acc = []
    for line in node.lines:
        lines_acc.append(renderer.render(line, base_context))
    lines = f"{context.newline}".join(lines_acc)
    block_header = f"{context.indent * node.level}{if_block_header}"
    block_text = f"{block_header}\n{lines}"
    return block_text

