from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional
from .nodes import Attribute, Tuple, List, Dictionary, Set, HcNode, Constant, Name
from .operator_nodes import EqOp, GtOp, GtEOp, LtOp, LtEOp, NeqOp, HcCompOp
from .commands import parse_commands
from .comment_parser import (
    is_comment_command,
    is_markdown_heading,
    parse_kwargs,
    split_commands,
)

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
    pre: str = ""
    post: str = ""
    type: str = "function_call"


@dataclass
class Keyword(HcInlineNode):
    """
    A keyword argument of a function call, ``arg=value``. ``arg`` is None for
    a ``**mapping`` unpacking. Stored in ``FunctionCall.args`` after the
    positional arguments, in source order.
    """

    arg: str | None
    value: Any
    type: str = "keyword"


@dataclass
class Compare(HcNode):
    comparison: deque[Constant | FunctionCall | Name | HcCompOp]
    type: str = "compare"


@dataclass
class InlineComment(HcInlineNode):
    content: str
    type: str = "inline_comment"
    # The values ``{{ }}`` in the comment are filled from (set by the parser
    # when the values of each line were recorded); None for the namespace
    # after the run.
    namespace: Any = field(default=None, compare=False, repr=False)


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
            except (SyntaxError, NameError):
                parsed = parse_commands(comment, split_commands(comment))
            return cls(content=comment, commands=parsed)
        else:
            return InlineComment(content=comment)


@dataclass
class Comprehension(HcInlineNode):
    assigns: deque[str | Tuple]
    iterator: deque[str | FunctionCall | List | Tuple | Dictionary | Set]
    is_async: bool
    # The clause's ``if`` filters (``for x in xs if x > 0``), each an expression.
    conditions: deque = field(default_factory=deque)
    pre: str = ""
    post: str = ""
    type: str = "comprehension"


@dataclass
class ComprehensionChain(HcInlineNode):
    comp_type: str = ""
    assign: deque[str | FunctionCall | List | Tuple | Dictionary | Set] = field(
        default_factory=deque
    )
    key: deque[str] = field(default_factory=deque)
    value: deque[str] = field(default_factory=deque)
    comprehensions: deque[Comprehension] = field(default_factory=deque)
    # A generator expression that is a call's only argument is written without
    # its own brackets: ``sum(x**2 for x in xs)``.
    bare: bool = False
    type: str = "comprehension_chain"


@dataclass
class Lambda(HcInlineNode):
    """
    A lambda, ``lambda x, y: x * y``: its ``params`` (names, or a starred
    ``*args``/``**kwargs``) and its ``body``. It is shown as written: a lambda
    is a function, so it has no values to substitute.
    """

    params: deque = field(default_factory=deque)
    body: Any = None
    type: str = "lambda"


@dataclass
class IfExp(HcInlineNode):
    """
    A conditional expression, ``body if test else orelse``. ``is_true`` is the
    value of ``test`` in the namespace (None when it could not be evaluated),
    so a renderer can show which branch was taken.
    """

    test: Any = None
    body: Any = None
    orelse: Any = None
    is_true: Optional[bool] = None
    type: str = "if_exp"
