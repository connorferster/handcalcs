
from collections import deque
from dataclasses import dataclass, field
from typing import Any
from .nodes import Attribute, Tuple, List, Dictionary, Set, HcNode, Constant, Name
from .operator_nodes import (
    EqOp,
    GtOp,
    GtEOp,
    LtOp,
    LtEOp,
    NeqOp,
    HcCompOp
)
from .commands import command_parser
from .comment_parser import is_comment_command, is_markdown_heading, parse_kwargs, split_commands

# All attributes with renderable content should contain deques
# even if only a single value is expected (and not a collection).

@dataclass
class HcInlineNode(HcNode):
    pass

@dataclass
class FunctionCall(HcInlineNode):
    namespace: deque[str] = field(default_factory=deque)
    function_name: deque[Attribute | str] = field(default_factory=deque)
    args: deque[Any] = field(default_factory=deque)
    type: str = "function_call"


@dataclass
class Compare(HcNode):
    comparison: deque[Constant | FunctionCall | Name | HcCompOp]
    type: str = 'compare'

@dataclass
class InlineComment(HcInlineNode):
    content: str
    type: str = "inline_comment"


@dataclass
class InlineCommand(HcInlineNode):
    content: str
    commands: dict = field(default_factory=dict)
    type: str = "inline_command"

    @classmethod
    def from_raw_comment(cls, comment: str):
        if is_comment_command(comment):
            try:
                parsed = parse_kwargs(comment)
            except SyntaxError:
                parsed = vars(command_parser.parse_args(split_commands(comment)))
            return cls(content=comment, commands=parsed)
        else:
            return InlineComment(content=comment)


@dataclass
class Comprehension(HcInlineNode):
    assigns: deque[str | Tuple]
    iterator: deque[str | FunctionCall | List | Tuple | Dictionary | Set]
    _is_async: bool
    type: str = "comprehension"


@dataclass
class ComprehensionChain(HcInlineNode):
    _type: str = ""
    assign: deque[str | FunctionCall | List | Tuple | Dictionary | Set] = field(default_factory=deque)
    key: deque[str] = field(default_factory=deque)
    value: deque[str] = field(default_factory=deque)
    comprehensions: deque[Comprehension] = field(default_factory=deque)
    type: str = "comprehension_chain"
    
