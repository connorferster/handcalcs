from collections import deque
from dataclasses import dataclass, field
from typing import Optional
from .nodes import HcNode

# Arithmetic Operators

@dataclass
class HcBinOp(HcNode):
    pass

@dataclass
class PowOp(HcBinOp):
    base: deque
    exponent: deque
    symbol: Optional[str] = "**"
    pre: Optional[str] = None
    post: Optional[str] = None
    type: str = 'pow_op'

@dataclass
class DivOp(HcBinOp):
    numerator: deque
    denominator: deque
    symbol: Optional[str] = "/"
    pre: Optional[str] = None
    post: Optional[str] = None
    type: str = 'div_op'

@dataclass
class FloorOp(HcBinOp):
    numerator: deque
    denominator: deque
    symbol: Optional[str] = "//"
    pre: Optional[str] = None
    post: Optional[str] = None
    type: str = 'floor_op'

@dataclass
class ModuloOp(HcBinOp):
    numerator: deque
    denominator: deque
    symbol: Optional[str] = "%"
    pre: Optional[str] = None
    post: Optional[str] = None
    type: str = 'modulo_op'

@dataclass
class MultOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "*"
    pre: Optional[str] = None
    post: Optional[str] = None
    type: str = 'mult_op'

@dataclass
class AddOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "+"
    pre: Optional[str] = None
    post: Optional[str] = None
    type: str = 'add_op'

@dataclass
class SubOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "-"
    pre: Optional[str] = None
    post: Optional[str] = None
    type: str = 'sub_op'


# Comparison Operators

@dataclass
class HcCompOp(HcNode):
    pass


@dataclass 
class EqOp(HcCompOp):
    left: deque
    right: deque
    symbol: str = "=="
    type: str = 'eq_op'


@dataclass 
class NeqOp(HcCompOp):
    left: deque
    right: deque
    symbol: str = "!="
    type: str = 'neq_op'


@dataclass
class GtOp(HcCompOp):
    left: deque
    right: deque
    symbol: str = ">"
    type: str = 'gt_op'


@dataclass 
class GtEOp(HcCompOp):
    left: deque
    right: deque
    symbol: str = ">="
    type: str = 'gte_op'


@dataclass 
class LtOp(HcCompOp):
    left: deque
    right: deque
    symbol: str = "<"
    type: str = 'lt_op'


@dataclass 
class LtEOp(HcCompOp):
    left: deque
    right: deque
    symbol: str = "<="
    type: str = 'lte_op'