from collections import deque
from dataclasses import dataclass
from typing import Any, Optional
from .null_values import NoValue

@dataclass
class HcNode:
    pass

@dataclass
class Name(HcNode):
    identifier: str
    value: Any = NoValue()


@dataclass
class Attribute(HcNode):
    namespace: str
    identifier: str
    value: Any = NoValue()

@dataclass
class List(HcNode):
    elems: deque[Any]

@dataclass
class Tuple(HcNode):
    elems: deque[Any]

@dataclass
class Set(HcNode):
    elems: deque[Any]

@dataclass
class Dictionary(HcNode):
    keys: deque[Any]
    values: deque[Any]