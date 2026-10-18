"""
Row-by-row Python values for the cached results of formula cells.

The values handcalcs captures on ``Name`` nodes are the variables' values at
the *end* of the cell, so a reassigned variable (``M_u`` twice) would cache
its last value on every row. ``ValueEvaluator`` re-evaluates each expression
against the values assigned so far, with Python's own operators and the same
callables the formula pass resolved, so each row caches its own result.
"""

from __future__ import annotations
import builtins
import math
import operator
from typing import Any, Optional

from handcalcs.parsing.nodes import Attribute, Constant, Name
from handcalcs.parsing.inline_nodes import Compare, FunctionCall
from handcalcs.parsing.operator_nodes import (
    AddOp,
    AndOp,
    DivOp,
    EqOp,
    FloorOp,
    GtEOp,
    GtOp,
    HcUnaryOp,
    LtEOp,
    LtOp,
    ModuloOp,
    MultOp,
    NeqOp,
    OrOp,
    PowOp,
    SubOp,
)
from .formulas import resolve_function

BINARY = {
    AddOp: operator.add,
    SubOp: operator.sub,
    MultOp: operator.mul,
    DivOp: operator.truediv,
    FloorOp: operator.floordiv,
    ModuloOp: operator.mod,
    PowOp: operator.pow,
}

COMPARE = {
    EqOp: operator.eq,
    NeqOp: operator.ne,
    LtOp: operator.lt,
    LtEOp: operator.le,
    GtOp: operator.gt,
    GtEOp: operator.ge,
}


class EvaluationError(Exception):
    """The expression could not be evaluated; the caller falls back."""


class ValueEvaluator:
    """
    Evaluates expression trees against ``values`` (identifier -> the value
    assigned so far on the sheet), falling back to ``global_ns`` for names
    not assigned on the sheet (e.g. ``pi`` from ``from math import pi``).
    """

    def __init__(self, global_ns: Optional[dict] = None) -> None:
        self.global_ns = global_ns if isinstance(global_ns, dict) else {}
        self.values: dict[str, Any] = {}

    def assign(self, identifier: str, value: Any) -> None:
        self.values[identifier] = value

    def evaluate(self, expression: Any) -> Any:
        if hasattr(expression, "__iter__") and not hasattr(expression, "type"):
            nodes = list(expression)
            if len(nodes) != 1:
                raise EvaluationError("not a single expression")
            expression = nodes[0]
        try:
            return self._eval(expression)
        except EvaluationError:
            raise
        except Exception as error:
            raise EvaluationError(str(error)) from error

    def _eval(self, node: Any) -> Any:
        if isinstance(node, Constant):
            return node.value
        if isinstance(node, Name):
            if node.identifier in self.values:
                return self.values[node.identifier]
            if node.identifier in self.global_ns:
                return self.global_ns[node.identifier]
            if hasattr(builtins, node.identifier):  # e.g. forallpeople top_level units
                return getattr(builtins, node.identifier)
            raise EvaluationError(f"'{node.identifier}' has no value")
        if isinstance(node, Attribute):
            module = self.global_ns.get(node.namespace)
            if module is None and node.namespace == "math":
                module = math
            return getattr(module, node.identifier)
        if isinstance(node, HcUnaryOp):
            operand = self._eval(node.operand)
            symbol = node.symbol.strip()
            if symbol == "not":
                return not operand
            if symbol == "-":
                return -operand
            if symbol == "+":
                return +operand
            raise EvaluationError(f"unary '{symbol}'")
        function = BINARY.get(type(node))
        if function is not None:
            return function(self._eval(node.left), self._eval(node.right))
        if isinstance(node, Compare):
            items = list(node.comparison)
            left = self._eval(items[0])
            for op, right_node in zip(items[1::2], items[2::2]):
                right = self._eval(right_node)
                if not COMPARE[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, AndOp):
            result = True
            for value in node.values:
                result = self._eval(value)
                if not result:
                    return result
            return result
        if isinstance(node, OrOp):
            result = False
            for value in node.values:
                result = self._eval(value)
                if result:
                    return result
            return result
        if isinstance(node, FunctionCall):
            function, _ = resolve_function(node, self.global_ns)
            if function is None:
                raise EvaluationError("unresolved function")
            return function(*(self._eval(arg) for arg in node.args))
        raise EvaluationError(f"cannot evaluate {getattr(node, 'type', node)!r}")
