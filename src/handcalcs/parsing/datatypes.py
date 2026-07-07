from collections import deque
from dataclasses import dataclass
from typing import Any

@dataclass
class Attribute:
    namespace: str
    attr_name: str

@dataclass
class List:
    elems: deque[Any]

@dataclass
class Tuple:
    elems: deque[Any]

@dataclass
class Set:
    elems: deque[Any]

@dataclass
class Dictionary:
    keys: deque[Any]
    values: deque[Any]

@dataclass
class HCNotImplemented:
    node_name: str