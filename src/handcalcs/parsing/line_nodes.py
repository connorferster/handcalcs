from collections import deque
from dataclasses import dataclass, field
from typing import Optional
from .nodes import HcNode, Name
from .inline_nodes import InlineComment, InlineCommand
from .commands import command_parser
from .comment_parser import is_comment_command, is_markdown_heading, parse_kwargs, split_commands


@dataclass
class HcLineNode(HcNode):
    level: int = 0

@dataclass
class CalcLine(HcLineNode):
    assigns: deque = field(default_factory=deque)
    expression_tree: deque = field(default_factory=deque)
    symbolic: deque = field(default_factory=deque)
    numeric: deque = field(default_factory=deque)
    comment: Optional[InlineComment | InlineCommand] = None
    type: str = "calc_line"


@dataclass
class ExprLine(HcLineNode):
    expression_tree: deque = field(default_factory=deque)
    symbolic: deque = field(default_factory=deque)
    numeric: deque = field(default_factory=deque)
    comment: Optional[InlineComment | InlineCommand] = None
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
    commands: dict = field(default_factory=dict)
    type: str = "comment_command"

    @classmethod
    def from_raw_comment(cls, comment: str):
        if is_comment_command(comment):
            # parsed = parse_kwargs(comment)
            try:
                parsed = parse_kwargs(comment)
            except SyntaxError:
                parsed = vars(command_parser.parse_args(split_commands(comment)))
            return cls(comment=comment, commands=parsed)
        else:
            return CommentLine(comment=comment)

@dataclass
class Import(HcLineNode):
    import_from: bool = False
    names: deque[str] = field(default_factory=deque)
    import_from_module: Optional[str] = None
    import_from_level: Optional[int] = None
    type: str = 'import'
