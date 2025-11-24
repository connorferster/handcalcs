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
    Attribute,
    Set
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
    _options: dict = field(default_factory=dict)

# Use leading underscores for attribute names that do not contain renderable
# content.
# All attributes with renderable content should contain deques
# even if only a single value is expected (and not a collection).


@dataclass
class FunctionBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock | CalcLine | ExprLine | MarkdownHeading | CommentCommand | CommentLine | InlineComment] = field(default_factory=deque)
    namespace: deque[str] = field(default_factory=deque)
    function_name: deque[Attribute | str] = field(default_factory=deque)
    args: deque[Any] = field(default_factory=deque)
    params: deque[str] = field(default_factory=deque)


@dataclass
class ForBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock | CalcLine | ExprLine] = field(default_factory=deque)
    assigns: deque[str] = field(default_factory=deque)
    iterator: deque[HandCalcsBlock | FunctionBlock | ExprLine | List | Tuple | Dictionary | str] = field(default_factory=deque)


@dataclass
class Comprehension:
    assigns: deque[str | Tuple]
    iterator: deque[str | FunctionBlock | List | Tuple | Dictionary | Set]
    _is_async: bool


@dataclass
class ComprehensionBlock(HandCalcsBlock):
    _type: str = ""
    assign: deque[str | FunctionBlock | List | Tuple | Dictionary | Set] = field(default_factory=deque)
    key: deque[str] = field(default_factory=deque)
    value: deque[str] = field(default_factory=deque)
    comprehensions: deque[Comprehension] = field(default_factory=deque)


@dataclass
class IfBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock | CalcLine | ExprLine] = field(default_factory=deque)
    test: deque[HandCalcsBlock | str | float | int | Any] = field(default_factory=deque)
    orelse: deque[HandCalcsBlock | CalcLine | ExprLine] = field(default_factory=deque)

