
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from .datatypes import Attribute, Tuple, List, Dictionary, Set

# All attributes with renderable content should contain deques
# even if only a single value is expected (and not a collection).


@dataclass
class FunctionCall:
    namespace: deque[str] = field(default_factory=deque)
    function_name: deque[Attribute | str] = field(default_factory=deque)
    args: deque[Any] = field(default_factory=deque)


@dataclass
class InlineComment:
    _comment: str


@dataclass
class Comprehension:
    assigns: deque[str | Tuple]
    iterator: deque[str | FunctionCall | List | Tuple | Dictionary | Set]
    _is_async: bool


@dataclass
class ComprehensionChain:
    _type: str = ""
    assign: deque[str | FunctionCall | List | Tuple | Dictionary | Set] = field(default_factory=deque)
    key: deque[str] = field(default_factory=deque)
    value: deque[str] = field(default_factory=deque)
    comprehensions: deque[Comprehension] = field(default_factory=deque)
