from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

class HandCalcsObj:
    pass

# Six basic line types
@dataclass
class CalcLine(HandCalcsObj):
    assigns: deque = field(default_factory=deque)
    expression_tree: deque = field(default_factory=deque)
    _symbolic: deque = field(default_factory=deque)
    _numeric: deque = field(default_factory=deque)
    _result: Optional[Any] = None
    _comment: str = ""
    _latex: str = ""


@dataclass
class ExprLine(HandCalcsObj):
    expression_tree: deque = field(default_factory=deque)
    _symbolic: deque = field(default_factory=deque)
    _numeric: deque = field(default_factory=deque)
    _return_expr: bool = False
    _result: Optional[Any] = None
    _comment: str = ""
    _latex: str = ""


@dataclass
class MarkdownHeading:
    _comment: str
    _latex: str = ""
    # TODO: Fill this in correctly based on historic


@dataclass
class InlineComment:
    _comment: str


@dataclass
class CommentLine:
    _comment: str


@dataclass
class CommentCommand:
    _raw_commands: str
    _parsed_commands: dict


@dataclass
class Attribute:
    namespace: str
    attr_name: str


@dataclass
class List(HandCalcsObj):
    elems: deque[Any]

@dataclass
class Tuple(HandCalcsObj):
    elems: deque[Any]

@dataclass
class Set(HandCalcsObj):
    elems: deque[Any]

@dataclass
class Dictionary(HandCalcsObj):
    keys: deque[Any]
    values: deque[Any]


@dataclass
class String:
    value: str


@dataclass
class HCNotImplemented:
    node_name: str
