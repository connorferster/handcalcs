from collections import deque
from dataclasses import dataclass, field
import re
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
    comment: Optional[InlineComment | InlineCommand] = None
    pars_nesting: bool = False
    type: str = "calc_line"


@dataclass
class ExprLine(HcLineNode):
    expression_tree: deque = field(default_factory=deque)
    comment: Optional[InlineComment | InlineCommand] = None
    return_expr: bool = False
    pars_nesting: bool = False
    type: str = "expr_line"


@dataclass
class CommentLine(HcLineNode):
    content: Optional[str] = None
    type: str = "comment_line"

    @classmethod
    def from_raw_comment(cls, comment: str):
        return cls(content=comment.lstrip("# "))


@dataclass
class MarkdownComment(HcLineNode):
    content: Optional[str] = None
    type: str = "markdown_comment"

    @classmethod
    def from_raw_comment(cls, comment: str):
        pattern = r"^#[ ]*(.+)"
        matches = re.search(pattern, comment)
        if matches is not None:
            content = matches.groups()[0]
        return cls(content=content)

@dataclass
class CommentCommand(HcLineNode):
    commands: dict = field(default_factory=dict)
    type: str = "comment_command"

    @classmethod
    def from_raw_comment(cls, comment: str):
        stripped = comment.lstrip("# ")
        try:
            parsed = parse_kwargs(stripped)
        except SyntaxError:
            parsed = vars(command_parser.parse_args(split_commands(stripped)))
        return cls(commands=parsed)

@dataclass
class Import(HcLineNode):
    import_from: bool = False
    names: deque[str] = field(default_factory=deque)
    import_from_module: Optional[str] = None
    import_from_level: Optional[int] = None
    type: str = 'import'
