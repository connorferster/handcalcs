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


# Unary Operators

@dataclass
class HcUnaryOp(HcNode):
    operand: object
    symbol: str = "-"
    pre: str = ""
    post: str = ""
    type: str = 'unary_op'


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


# Identity and membership operators (``is``, ``is not``, ``in``, ``not in``).
# Like the other comparison ops these live inside a ``Compare`` deque, which the
# renderer joins with no separator -- so, being word operators, their symbols
# carry their own surrounding spaces (``a is b``, not ``aisb``), unlike the
# symbolic relational ops above which render tight (``a<b``).

@dataclass
class IsOp(HcCompOp):
    symbol: str = " is "
    type: str = 'is_op'


@dataclass
class IsNotOp(HcCompOp):
    symbol: str = " is not "
    type: str = 'is_not_op'


@dataclass
class InOp(HcCompOp):
    symbol: str = " in "
    type: str = 'in_op'


@dataclass
class NotInOp(HcCompOp):
    symbol: str = " not in "
    type: str = 'not_in_op'


# Boolean Operators (``and``, ``or``)
#
# A boolean operator is n-ary in Python (``a and b and c`` is one ``BoolOp`` with
# three ``values``), so unlike ``HcBinOp`` it holds a single ``values`` deque
# rather than a left/right pair.

@dataclass
class HcBoolOp(HcNode):
    pass


@dataclass
class AndOp(HcBoolOp):
    values: deque
    symbol: str = "and"
    pre: str = ""
    post: str = ""
    type: str = 'and_op'


@dataclass
class OrOp(HcBoolOp):
    values: deque
    symbol: str = "or"
    pre: str = ""
    post: str = ""
    type: str = 'or_op'