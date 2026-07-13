from dataclasses import dataclass, field
from .node import HcNode
from .inline_nodes import InlineComment


@dataclass
class HcLineNode(HcNode):
    level: int

@dataclass
class CalcLine(HcBlockNode):
    assigns: deque = field(default_factory=deque)
    expression_tree: deque = field(default_factory=deque)
    symbolic: deque = field(default_factory=deque)
    numeric: field(default_factory=deque)
    comment: Optional[InlineComment] = None


@dataclass
class ExprLine(HcBlockNode):
    expression_tree: deque = field(default_factory=deque)
    symbolic: deque = field(default_factory=deque)
    numeric: field(default_factory=deque)
    comment: Optional[InlineComment] = None
    return_expr: bool = False


@dataclass
class CommentLine(HcLineNode):
    content: Optional[str] = None


@dataclass
class MarkdownHeading(HcLineNode):
    comment: Optional[CommentLine] = None
    heading_level: Optional[int] = None
    content: Optional[str] = None

@dataclass
class CommentCommand(HcLineNode):
    comment: Optional[CommentLine] = None
    commands: Optional[list[str]] = None