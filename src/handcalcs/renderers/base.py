from dataclasses import dataclass, field
from typing import ClassVar, Callable
from handcalcs.parsing.nodes import HcNode

RenderHandler = Callable[..., str]

@dataclass
class BaseRenderer:
    name: ClassVar[str] = 'base'
    handlers: ClassVar[dict[str, Callable]] = field(default_factory = dict)

    def render_node(self, node: HcNode) -> str:
        handler = self._handlers.get(node.type)
        if handler is None:
            return str(node)
        else:
            return handler(node)

    @classmethod
    def register(cls, node_type: str) -> Callable[[RenderHandler], RenderHandler]:
        def decorator(hander: RenderHandler) -> RenderHandler
            cls.handlers[node_type] = handler
            return handler
        return decorator


    def register_handler(self, node_type: str, handler: RenderHandler) -> None:
        self._handlers[node_type] = handler
