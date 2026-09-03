from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from .nodes import Attribute, List, Tuple, Dictionary, Set, HcNode
from .line_nodes import CalcLine, ExprLine, Heading, CommentCommand, CommentLine


@dataclass
class HcBlockNode(HcNode):
    level: int = 0

@dataclass
class FunctionBlock(HcBlockNode):
    lines: deque[HcBlockNode | CalcLine | ExprLine | Heading | CommentCommand | CommentLine] = field(default_factory=deque)
    namespace: deque[str] = field(default_factory=deque)
    function_name: deque[Attribute | str] = field(default_factory=deque)
    args: deque[Any] = field(default_factory=deque)
    params: deque[str] = field(default_factory=deque)
    type: str = 'function_block'


# Use leading underscores for attribute 
@dataclass
class ForBlock(HcBlockNode):
    lines: deque[HcBlockNode | CalcLine | ExprLine] = field(default_factory=deque)
    assigns: deque[str] = field(default_factory=deque)
    iterator: deque[HcBlockNode | FunctionBlock | ExprLine | List | Tuple | Dictionary | str] = field(default_factory=deque)
    type: str = 'for_block'

@dataclass
class IfBlock(HcBlockNode):
    lines: deque[HcBlockNode | CalcLine | ExprLine] = field(default_factory=deque)
    test: deque[HcBlockNode | str | float | int | Any] = field(default_factory=deque)
    orelse: deque[HcBlockNode | CalcLine | ExprLine] = field(default_factory=deque)
    is_true: Optional[bool] = None
    type: str = 'if_block'
    
@dataclass
class ElseBlock(HcBlockNode):
    lines: deque[Any] = field(default_factory=deque)
    type: str = 'else_block'


@dataclass
class ElifBlock(HcBlockNode):
    lines: deque[IfBlock] = field(default_factory=deque)
    type: str = 'elif_block'
    
    @classmethod
    def from_if_tree(cls, ib: IfBlock):
        def flatten_if_tree(ib: IfBlock) -> deque[IfBlock]:
            acc = deque([])
            if len(ib.orelse) == 1: # deque has something in it
                orelse = ib.orelse[0]
                orelse_full = ib.orelse
            else: # Empty deque, no alternative branch for the if provided
                orelse = None
                orelse_full = None
            acc.extend(deque([ib]))
            if isinstance(orelse, IfBlock):
                acc.extend(flatten_if_tree(orelse))
            else:
                if orelse_full is not None:
                    acc.extend(deque([ElseBlock(orelse_full)]))
                return acc
            return acc  
        flattened_tree = flatten_if_tree(ib)
        return cls(lines=flattened_tree)