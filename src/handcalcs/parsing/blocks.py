from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class HandCalcsBlock:
    _options: dict = field(default_factory=dict)
    # _items: list = field(default_factory=list)
    level: int = 0

    def __getitem__(self, index: int):
        attrs = [attr for attr in dir(self) if not attr.startswith("_")]
        attr = attrs[index]
        return {attr: getattr(self, attr)}


# Six basic line types
@dataclass
class CalcLine(HandCalcsBlock):
    level: int = 0
    assigns: deque = field(default_factory=deque)
    expression_tree: deque = field(default_factory=deque)
    _numeric: deque = field(default_factory=deque)
    _result: Optional[Any] = None
    _comment: str = ""
    _latex: str = ""


@dataclass
class ExprLine(HandCalcsBlock):
    level: int = 0
    expression_tree: deque = field(default_factory=deque)
    _numeric: deque = field(default_factory=deque)
    _return_expr: bool = False
    _result: Optional[Any] = None
    _comment: str = ""
    _latex: str = ""


@dataclass
class MarkdownHeading(HandCalcsBlock):
    _comment: str
    _latex: str = ""
    # TODO: Fill this in correctly based on historic



@dataclass
class CommentLine(HandCalcsBlock):
    _comment: str


@dataclass
class CommentCommand(HandCalcsBlock):
    _raw_commands: str
    _parsed_commands: dict


# Use leading underscores for attribute 
@dataclass
class ForBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock | CalcLine | ExprLine] = field(default_factory=deque)
    assigns: deque[str] = field(default_factory=deque)
    iterator: deque[HandCalcsBlock | FunctionBlock | ExprLine | List | Tuple | Dictionary | str] = field(default_factory=deque)




@dataclass
class IfBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock | CalcLine | ExprLine] = field(default_factory=deque)
    test: deque[HandCalcsBlock | str | float | int | Any] = field(default_factory=deque)
    orelse: deque[HandCalcsBlock | CalcLine | ExprLine] = field(default_factory=deque)

