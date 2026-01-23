from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class HandCalcsObj:    
    def render(self, config_options = dict()):
        raise NotImplementedError

# Six basic line types
@dataclass
class CalcLine(HandCalcsObj):
    level: int = 0
    assigns: deque = field(default_factory=deque)
    expression_tree: deque = field(default_factory=deque)
    _numeric: deque = field(default_factory=deque)
    _result: Optional[Any] = None
    _comment: str = ""
    _latex: str = ""

    def render(self, config_options = dict()):
        opts = config_options
        assign_elems = opts.get('assign_sep', '').join(self.assigns)
        assigns = f"{opts.get('pre_assign', '')}{assign_elems}{opts.get('post_assign', '')}"
        assign_eq = opts.get('eq_op', '')
        assigns = f"{assigns}{assign_eq}"


@dataclass
class ExprLine(HandCalcsObj):
    level: int = 0
    expression_tree: deque = field(default_factory=deque)
    _numeric: deque = field(default_factory=deque)
    _return_expr: bool = False
    _result: Optional[Any] = None
    _comment: str = ""
    _latex: str = ""


@dataclass
class MarkdownHeading(HandCalcsObj):
    _comment: str
    _latex: str = ""
    # TODO: Fill this in correctly based on historic


@dataclass
class InlineComment(HandCalcsObj):
    _comment: str


@dataclass
class CommentLine(HandCalcsObj):
    _comment: str


@dataclass
class CommentCommand(HandCalcsObj):
    _raw_commands: str
    _parsed_commands: dict


@dataclass
class Attribute(HandCalcsObj):
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
class HCNotImplemented(HandCalcsObj):
    node_name: str
