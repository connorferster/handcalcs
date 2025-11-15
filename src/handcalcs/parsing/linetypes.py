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
    symbolic: deque = field(default_factory=deque)
    numeric: deque = field(default_factory=deque)
    result: Optional[Any] = None
    comment: str = ""
    latex: str = ""


@dataclass
class ExprLine(HandCalcsObj):
    expression_tree: deque = field(default_factory=deque)
    symbolic: deque = field(default_factory=deque)
    numeric: deque = field(default_factory=deque)
    return_expr: bool = False
    result: Optional[Any] = None
    comment: str = ""
    latex: str = ""


@dataclass
class MarkdownHeading:
    comment: str
    latex: str = ""
    # TODO: Fill this in correctly based on historic


@dataclass
class InlineComment:
    comment: str


@dataclass
class CommentLine:
    comment: str


@dataclass
class CommentCommand:
    raw_commands: str
    parsed_commands: dict


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
