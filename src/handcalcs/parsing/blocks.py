from dataclasses import dataclass, field
from collections import deque
from handcalcs.parsing.linetypes import (
    CalcLine, 
    MarkdownHeading, 
    ExprLine, 
    CommentCommand, 
    CommentLine, 
    InlineComment,
    List,
    Tuple,
    Dictionary,
    Attribute
)
from typing import Union, Optional, Any


class CalcOptions(dict):
    pass


class FunctionOptions(dict):
    pass


class ForOptions(dict):
    pass


class IfOptions(dict):
    pass


@dataclass
class HandCalcsBlock:
    options: dict


@dataclass
class FunctionBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock | CalcLine | ExprLine | MarkdownHeading | CommentCommand | CommentLine | InlineComment] = field(default_factory=deque)
    options: FunctionOptions | dict = field(default_factory=dict)
    namespace: str = ""
    function_name: Attribute | str = ""
    args: deque[Any] = field(default_factory=deque)
    params: deque[str] = field(default_factory=deque)


@dataclass
class CalcBlock(HandCalcsBlock):
    lines: deque[Union[CalcLine, ExprLine, FunctionBlock]] = field(default_factory=deque)
    options: Optional[CalcOptions | dict] = field(default_factory=dict)

@dataclass
class ForBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock | CalcLine | ExprLine] = field(default_factory=deque)
    options: Optional[ForOptions | dict] = field(default_factory=dict)
    assigns: deque[str] = field(default_factory=deque)
    iterator: deque[HandCalcsBlock | FunctionBlock | ExprLine | List | Tuple | Dictionary | str] = field(default_factory=deque)


@dataclass
class IfBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock | CalcLine | ExprLine] = field(default_factory=deque)
    options: Optional[IfOptions | dict] = field(default_factory=dict)
    test: deque[HandCalcsBlock | str | float | int | Any] = field(default_factory=deque)
    orelse: deque[HandCalcsBlock | CalcLine | ExprLine] = field(default_factory=deque)

