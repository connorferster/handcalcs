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
    left: deque
    right: deque
    symbol: str = "**"
    pre: str = ""
    post: str = ""
    type: str = 'pow_op'

@dataclass
class DivOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "/"
    pre: str = ""
    post: str = ""
    type: str = 'div_op'

@dataclass
class FloorOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "//"
    pre: str = ""
    post: str = ""
    type: str = 'floor_op'

@dataclass
class ModuloOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "%"
    pre: str = ""
    post: str = ""
    type: str = 'modulo_op'

@dataclass
class MultOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "*"
    pre: str = ""
    post: str = ""
    type: str = 'mult_op'

@dataclass
class AddOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "+"
    pre: str = ""
    post: str = ""
    type: str = 'add_op'

@dataclass
class SubOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "-"
    pre: str = ""
    post: str = ""
    type: str = 'sub_op'


# Comparison Operators

@dataclass
class HcCompOp(HcNode):
    pass


@dataclass 
class EqOp(HcCompOp):
    symbol: str = "=="
    type: str = 'eq_op'


@dataclass 
class NeqOp(HcCompOp):
    symbol: str = "!="
    type: str = 'neq_op'


@dataclass
class GtOp(HcCompOp):
    symbol: str = ">"
    type: str = 'gt_op'


@dataclass 
class GtEOp(HcCompOp):
    symbol: str = ">="
    type: str = 'gte_op'


@dataclass 
class LtOp(HcCompOp):
    symbol: str = "<"
    type: str = 'lt_op'


@dataclass 
class LtEOp(HcCompOp):
    symbol: str = "<="
    type: str = 'lte_op'