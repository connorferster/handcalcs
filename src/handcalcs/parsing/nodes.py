from collections import deque
from dataclasses import dataclass
from typing import Any, Optional
from .null_values import NoValue

@dataclass
class HcNode:
    pass
    # type: str

@dataclass
class Name(HcNode):
    identifier: str
    value: Any = NoValue()
    type: str = "name"


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