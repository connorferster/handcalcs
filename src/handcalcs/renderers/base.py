from dataclasses import dataclass, field
from typing import ClassVar, Callable, Optional
from handcalcs.parsing.nodes import HcNode
from handcalcs.parsing.sequence import HcSequence

class ContextValueError(Exception):
    pass

class ContextKeyError(Exception):

@dataclass
class RenderContext:
    
    def __init__(self, **kwargs):
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
        self._handlers: dict[str, Callable] = dict(self.handlers)
        self._symbolic_rules: dict[str, Callable] = dict(self.symbolic_rules)
        self._numeric_rules: dict[str, Callable] = dict(self.numeric_rules)
        self._root_pre_renderers: dict[str, Callable] = dict(self.root_pre_renderers)
        self._root_post_renderers: dict[str, Callable] = dict(self.root_post_renderers)


    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.handlers = dict(cls.handlers)
        cls.symbolic_rules = dict(cls.symbolic_rules)
        cls.numeric_rules = dict(cls.numeric_rules)
        cls.root_pre_renderers = dict(cls.root_pre_renderers)
        cls.root_post_renderers = dict(cls.root_post_renderers)

    def create_context(self, node: Optional[HcNode] = None) -> RenderContext:
        return RenderContext()

    def render(self, node: HcNode, context: Optional[RenderContext] = None) -> str:
        """
        Render a node.

        If 'context' is None, a new context is created.
        """
        if context is None:
            context = self.create_context(node)
        if node.name == 'root':
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
        handler = self._handlers.get(node.name)
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
                cls.handlers.update({node_classifier: handler})
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




