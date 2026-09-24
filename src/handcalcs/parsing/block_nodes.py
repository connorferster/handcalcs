from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from .nodes import Attribute, List, Tuple, Dictionary, Set, HcNode
from .line_nodes import CalcLine, ExprLine, Heading, CommentCommand, CommentLine


@dataclass
class HcBlockNode(HcNode):
    level: int = 0

@dataclass
class ParamsBlock(HcBlockNode):
    lines: deque[CalcLine] = field(default_factory=deque)
    type: str = 'params_block'

@dataclass
class CommentsBlock(HcBlockNode):
    """CommentsBlock is an abstraction to allow formatting to apply to a group of CommentLines
    recognizing that the linebreaks in the code are not necessarily important
    to the rendered result."""
    lines: deque[CommentLine] = field(default_factory=deque)
    type: str = 'comments_block'

@dataclass
class CalcsBlock(HcBlockNode):
    """CalcsBlock is an abstraction to allow formatting to apply to a group of CalcLines
    recognizing that groups of calcs look good if they are grouped together."""
    lines: deque[CalcLine] = field(default_factory=deque)
    type: str = 'calcs_block'

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
            acc = deque([ib])
            orelse = ib.orelse
            if len(orelse) == 1 and isinstance(orelse[0], IfBlock):
                # `elif`: the parser wraps the chained branch in a single nested
                # IfBlock, which continues the flattened chain.
                acc.extend(flatten_if_tree(orelse[0]))
            elif orelse:
                # Plain `else` (one *or more* statements): the whole orelse body
                # becomes the ElseBlock's lines. Passing it positionally would
                # bind it to the inherited `level` field, so name it explicitly.
                acc.append(ElseBlock(lines=orelse))
            # An empty `orelse` deque means there was no else/elif branch.
            return acc
        flattened_tree = flatten_if_tree(ib)
        return cls(lines=flattened_tree)