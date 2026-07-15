
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from .nodes import Attribute, Tuple, List, Dictionary, Set, HcNode

# All attributes with renderable content should contain deques
# even if only a single value is expected (and not a collection).

@dataclass
class HcInlineNode(HcNode):
    pass

@dataclass
class FunctionCall(HcInlineNode):
    namespace: deque[str] = field(default_factory=deque)
    function_name: deque[Attribute | str] = field(default_factory=deque)
    args: deque[Any] = field(default_factory=deque)
    type: str = "function_call"


@dataclass
class InlineComment(HcInlineNode):
    comment: str
    type: str = "inline_node"


@dataclass
class Comprehension(HcInlineNode):
    assigns: deque[str | Tuple]
    iterator: deque[str | FunctionCall | List | Tuple | Dictionary | Set]
    _is_async: bool
    type: str = "comprehension"


@dataclass
class ComprehensionChain(HcInlineNode):
    _type: str = ""
    assign: deque[str | FunctionCall | List | Tuple | Dictionary | Set] = field(default_factory=deque)
    key: deque[str] = field(default_factory=deque)
    value: deque[str] = field(default_factory=deque)
    comprehensions: deque[Comprehension] = field(default_factory=deque)
    type: str = "comprehension_chain"
    
