from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional
from .datatypes import Attribute, List, Tuple, Dictionary, Set
from typing import Callable


@dataclass
class HandCalcsBlock:
    # _items: list = field(default_factory=list)
    # level: int = 0
    pass

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
    _comment: Optional[str] = None
    _latex: str = ""
    # TODO: Fill this in correctly based on historic



@dataclass
class CommentLine(HandCalcsBlock):
    _comment: Optional[str] = None


@dataclass
class CommentCommand(HandCalcsBlock):
    _raw_commands: Optional[str] = None
    _parsed_commands: Optional[dict] = None


@dataclass
class FunctionBlock(HandCalcsBlock):
    lines: deque[HandCalcsBlock | CalcLine | ExprLine | MarkdownHeading | CommentCommand | CommentLine] = field(default_factory=deque)
    namespace: deque[str] = field(default_factory=deque)
    function_name: deque[Attribute | str] = field(default_factory=deque)
    args: deque[Any] = field(default_factory=deque)
    params: deque[str] = field(default_factory=deque)


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
    
@dataclass
class ElseBlock(HandCalcsBlock):
    lines: deque[Any]


@dataclass
class ElifBlock(HandCalcsBlock):
    lines: deque[IfBlock]
    
    @classmethod
    def from_if_tree(cls, ib: IfBlock):
        def flatten_if_tree(ib: IfBlock) -> deque[IfBlock]:
            acc = deque([])
            orelse = ib.orelse[0]
            orelse_full = ib.orelse
            ib.orelse = None
            acc.extend(deque([ib]))
            if isinstance(orelse, IfBlock):
                acc.extend(flatten_if_tree(orelse))
            else:
                acc.extend(deque([ElseBlock(orelse_full)]))
                return acc
            return acc  
        flattened_tree = flatten_if_tree(ib)
        return cls(flattened_tree)

