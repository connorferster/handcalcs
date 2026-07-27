from dataclasses import dataclass, field
from typing import ClassVar, Callable, Optional
from handcalcs.parsing.nodes import HcNode
from handcalcs.parsing.sequence import HcSequence

RenderHandler = Callable

class ContextValueError(Exception):
    pass

class ContextKeyError(Exception):
    pass

@dataclass
class RenderContext:
    
    def __init__(
        self, 
        single_space_char: str = ' ', 
        newline_char: str = '\n', 
        indent_size: int = 4,
        mode: str = 'full',
        **kwargs
    ):
        self.single_space_char = single_space_char
        self.newline_char = newline_char
        self.indent_size = indent_size
        self.mode = mode

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        attrs = [f"{k}={v}" for k, v in self.__dict__.items() if not k.startswith("_") and k.islower()]
        repr_attrs = ", ".join(attrs)
        return f"{__class__.__name__}({repr_attrs})"


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
        return RenderContext(**kwargs)

    def render(self, node: HcNode, context: Optional[RenderContext] = None) -> str:
        """
        Render a node.

        If 'context' is None, a new context is created.
        """
        if context is None:
            context = self.create_context()
        if node.type == 'root':
            return self.render_root(node, context)
        return self.render_node(node, context)


    def render_root(self, root: HcSequence, context: RenderContext) -> str:
        """
        Render an HcSequence (root node) with the registered pre/post render callables.
        """
        parts = [pre(self, root, context) for pre in self._root_pre_renderers]
        for node in root.sequence:
            parts.append(self.render(node, context))
        parts.extend(
            [post(self, root, context) for post in self._root_post_renderers]
        )
        return parts

    def render_node(self, node: HcNode, context: RenderContext) -> str:
        """
        Render one node with an existing context.
        """
        for rule in self.symbolic_rules.values():
            node = rule(node, context)
        for rule in self.numeric_rules.values():
            node = rule(node, context)
        handler = self._handlers.get(node.type)
        if handler is None:
            return self.render_unknown(node, context)
        return handler(self, node, context)

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


    def render_unknown(self, node: HcNode, context: RenderContext) -> str:
        return str(node)


## Register BaseRenderer basic node implementations

BR = BaseRenderer
BRC = BaseRendererContext


@BaseRenderer.register('constant')
def render_constant(renderer: BaseRenderer, node: Constant, context: RenderContext) -> Any:
    return f"{node.value}"

@BaseRenderer.register('inline_comment')
def render_inline_comment(renderer: BaseRenderer, node: InlineComment, context: RenderContext) -> str:
    _ = context.single_space_char
    return f"{_}({node.comment.lstrip("# ")})"

@BaseRenderer.register('name')
def render_name(renderer: BaseRenderer, node: Name, context: RenderContext) -> str:
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
def render_add_op(renderer: BR, node: AddOp, context: BRC) -> str:
    return f"{node.pre}{renderer.render(node.left, context)}{node.symbol}{renderer.render(node.right, context)}{node.post}"


@BaseRenderer.register('sub_op')
def render_sub_op(renderer: BR, node: SubOp, context: BRC) -> str:
    return f"{node.pre}{renderer.render(node.left, context)}{node.symbol}{renderer.render(node.right, context)}{node.post}"


@BaseRenderer.register('mult_op')
def render_mult_op(renderer: BR, node: AddOp, context: BRC) -> str:
    return f"{node.pre}{renderer.render(node.left, context)}{node.symbol}{renderer.render(node.right, context)}{node.post}"


@BaseRenderer.register('div_op')
def render_div_op(renderer: BR, node: AddOp, context: BRC) -> str:
    return f"{node.pre}{renderer.render(node.left, context)}{node.symbol}{renderer.render(node.right, context)}{node.post}"


@BaseRenderer.register('pow_op')
def render_pow_op(renderer: BR, node: AddOp, context: BRC) -> str:
    return f"{node.pre}{renderer.render(node.left, context)}{node.symbol}{renderer.render(node.right, context)}{node.post}"

@BaseRenderer.register('gt_op')
def render_gt_op(renderer: BR, node: GtOp, context: BRC) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('gte_op')
def render_gte_op(renderer: BR, node: GtEOp, context: BRC) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('lt_op')
def render_lt_op(renderer: BR, node: LtOp, context: BRC) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('lte_op')
def render_lte_op(renderer: BR, node: LtEOp, context: BRC) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('eq_op')
def render_eq_op(renderer: BR, node: EqOp, context: BRC) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('neq_op')
def render_neq_op(renderer: BR, node: NeqOp, context: BRC) -> str:
    return f"{node.symbol}"

@BaseRenderer.register('compare')
def render_compare(renderer: BR, node: Compare, context: BRC) -> str:
    acc = [renderer.render(node, context) for node in node.comparison]
    return f"".join(acc)

@BaseRenderer.register('function_call')
def render_function_call(renderer: BR, node: FunctionCall, context: BRC) -> str:
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

@BaseRenderer.register('import')
def render_import(renderer: BR, node: Import, context: BRC) -> str:
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
        

@BaseRenderer.register('calc_line')
def render_calcline(renderer: BaseRenderer, node: CalcLine, context: RenderContext) -> str:
    rendered = f"{context.indent * node.level}"
    # Retrieve param_line immediately before the next .render method is called because it will change
    # the state of the current context to the context of the next node.
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


@BaseRenderer.register('expr_line')
def render_exprline(renderer: BaseRenderer, node: ExprLine, context: RenderContext) -> str:
    rendered = f"{context.indent * node.level}"
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
    

@BaseRenderer.register('elif_block')
def render_elifblock(renderer: BaseRenderer, node: ElifBlock, context: RenderContext) -> str:
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
        block_text = renderer.render(true_clause, context)
        return block_text

@BaseRenderer.register('if_block')
def render_if_block(renderer: BaseRenderer, node: IfBlock, context: BRC) -> str:
    _ = context.single_space_char
    condition: deque = node.test.comparison
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
    if_block_header = f"Since{_}({sym_expr}){_}->{_}({num_expr}){_}is{_}True:"

    context.current_mode = None
    lines_acc = []
    for line in node.lines:
        lines_acc.append(renderer.render(line, context))
    lines = f"{context.newline_char}".join(lines_acc)
    block_header = f"{context.indent * node.level}{if_block_header}"
    block_text = f"{block_header}\n{lines}"
    return block_text

