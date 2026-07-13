from dataclasses import dataclass, field
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

@dataclass
class DivOp(HcBinOp):
    numerator: deque
    denominator: deque
    symbol: Optional[str] = "/"
    pre: Optional[str] = None
    post: Optional[str] = None

@dataclass
class FloorOp(HcBinOp):
    numerator: deque
    denominator: deque
    symbol: Optional[str] = "//"
    pre: Optional[str] = None
    post: Optional[str] = None

@dataclass
class ModuloOp(HcBinOp):
    numerator: deque
    denominator: deque
    symbol: Optional[str] = "%"
    pre: Optional[str] = None
    post: Optional[str] = None

@dataclass
class MultOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "*"
    pre: Optional[str] = None
    post: Optional[str] = None

@dataclass
class AddOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "+"
    pre: Optional[str] = None
    post: Optional[str] = None

@dataclass
class SubOp(HcBinOp):
    left: deque
    right: deque
    symbol: str = "-"
    pre: Optional[str] = None
    post: Optional[str] = None


# Comparison Operators

@dataclass
class HcCompOp(HcNode):
    pass

COMPARE_OPS = {
    "Eq": "==",
    "Ne": "!=",
    "GtE": ">=",
    "Gt": ">",
    "LtE": "<=",
    "Lt": "<",
}

@dataclass 
class EqOp(HCCompOp):
    left: deque
    right: deque
    symbol: str = "=="


@dataclass 
class NeqOp(HCCompOp):
    left: deque
    right: deque
    symbol: str = "!="


@dataclass
class GtOp(HcCompOp):
    left: deque
    right: deque
    symbol: str = ">"


@dataclass 
class GtEOp(HCCompOp):
    left: deque
    right: deque
    symbol: str = ">="


@dataclass 
class LtOp(HCCompOp):
    left: deque
    right: deque
    symbol: str = "<"


@dataclass 
class LtEOp(HcCompOp):
    left: deque
    right: deque
    symbol: str = "<="