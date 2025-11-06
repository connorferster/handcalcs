from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional


# Six basic line types
@dataclass
class CalcLine:
    assigns: deque = field(default_factory=deque)
    expression_tree: deque = field(default_factory=deque)
    symbolic: deque = field(default_factory=deque)
    numeric: deque = field(default_factory=deque)
    result: Optional[Any] = None
    comment: str = ""
    latex: str = ""


@dataclass
class ExprLine:
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
    module_name: str
    attr_name: str

@dataclass
class HCNotImplemented:
    node_name: str