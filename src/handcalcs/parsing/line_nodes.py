from collections import deque
from dataclasses import dataclass, field
from typing import Optional
from .nodes import HcNode
from .inline_nodes import InlineComment


@dataclass
class HcLineNode(HcNode):
    level: int = 0

@dataclass
class CalcLine(HcLineNode):
    assigns: deque = field(default_factory=deque)
    expression_tree: deque = field(default_factory=deque)
    symbolic: deque = field(default_factory=deque)
    numeric: deque = field(default_factory=deque)
    comment: Optional[InlineComment] = None
    type: str = "calc_line"


@dataclass
class ExprLine(HcLineNode):
    expression_tree: deque = field(default_factory=deque)
    symbolic: deque = field(default_factory=deque)
    numeric: deque = field(default_factory=deque)
    comment: Optional[InlineComment] = None
    return_expr: bool = False
    type: str = "expr_line"


@dataclass
class CommentLine(HcLineNode):
    content: Optional[str] = None
    type: str = "comment_line"


@dataclass
class MarkdownHeading(HcLineNode):
    comment: Optional[CommentLine] = None
    heading_level: Optional[int] = None
    content: Optional[str] = None
    type: str = "markdown_heading"

@dataclass
class CommentCommand(HcLineNode):
    comment: Optional[CommentLine] = None
    commands: Optional[list[str]] = None
    type: str = "comment_command"