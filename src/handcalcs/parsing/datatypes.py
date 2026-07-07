from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class NoValue:
    pass

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return True
        return False
    
    def __neq__(self, other):
        return False


@dataclass
class Name:
    identifier: str
    value: Optional[Any] = None


@dataclass
class Attribute:
    namespace: str
    identifier: str
    value: Optional[Any] = None

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