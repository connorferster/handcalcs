from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional
from .null_values import NoValue


@dataclass
class HcNode:
    pass
    # type: str

    def render(self):
        raise NotImplementedError(
            f"The render method for {__class__.__name__} has not been implemented yet."
        )


@dataclass
class Name(HcNode):
    identifier: str
    value: Any = NoValue()
    type: str = "name"


@dataclass
class Constant(HcNode):
    """
    A scalar value: a literal from the source (``calculated=False``, with its
    text as written in ``source_text``) or a value computed at runtime and shown
    in a substitution or result (``calculated=True``).
    """

    value: Any
    source_text: str = field(default="", compare=False)
    calculated: bool = False
    type: str = "constant"


@dataclass
class Attribute(HcNode):
    namespace: str
    identifier: str
    value: Any = NoValue()
    type: str = "attribute"


@dataclass
class List(HcNode):
    elems: deque[Any]
    type: str = "list"


@dataclass
class Tuple(HcNode):
    elems: deque[Any]
    type: str = "tuple"


@dataclass
class Set(HcNode):
    elems: deque[Any]
    type: str = "set"


@dataclass
class Dictionary(HcNode):
    keys: deque[Any]
    values: deque[Any]
    type: str = "dictionary"
