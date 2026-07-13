from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional
from .datatypes import Attribute, List, Tuple, Dictionary, Set
from typing import Callable
from .node import HcNode

@dataclass
class HcBlockNode(HcNode):
    level: int

@dataclass
class FunctionBlock(HcBlockNode):
    lines: deque[HcBlockNode | CalcLine | ExprLine | MarkdownHeading | CommentCommand | CommentLine] = field(default_factory=deque)
    namespace: deque[str] = field(default_factory=deque)
    function_name: deque[Attribute | str] = field(default_factory=deque)
    args: deque[Any] = field(default_factory=deque)
    params: deque[str] = field(default_factory=deque)


# Use leading underscores for attribute 
@dataclass
class ForBlock(HcBlockNode):
    lines: deque[HcBlockNode | CalcLine | ExprLine] = field(default_factory=deque)
    assigns: deque[str] = field(default_factory=deque)
    iterator: deque[HcBlockNode | FunctionBlock | ExprLine | List | Tuple | Dictionary | str] = field(default_factory=deque)


@dataclass
class IfBlock(HcBlockNode):
    lines: deque[HcBlockNode | CalcLine | ExprLine] = field(default_factory=deque)
    test: deque[HcBlockNode | str | float | int | Any] = field(default_factory=deque)
    orelse: deque[HcBlockNode | CalcLine | ExprLine] = field(default_factory=deque)
    
@dataclass
class ElseBlock(HcBlockNode):
    lines: deque[Any]


@dataclass
class ElifBlock(HcBlockNode):
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

