"""
Python expression nodes -> Excel formula text (the renderer's ``'xl'`` mode).

``FormulaBuilder`` walks a CalcLine's expression tree and returns the formula
body (without the leading ``=``). Variables become the worksheet-scoped defined
names held in a ``SymbolTable``; operators, constants and functions become
their Excel equivalents. Anything without a faithful Excel form raises
``ExcelRendererIncompatibleError``.

The walk is a standalone translator rather than a set of renderer handlers:
Excel needs its own precedence table, its own spelling of nearly every node,
and must never mutate the nodes that the symbolic pass renders afterwards.

Two Excel precedence traps are handled here:

- negation binds *tighter* than ``^`` (``-2^2`` is 4), so ``-a**2`` becomes
  ``-(a^2)``;
- ``^`` is *left*-associative (``2^3^2`` is 64), so ``a**b**c`` becomes
  ``a^(b^c)``.
"""
from __future__ import annotations
import builtins
import math
from dataclasses import dataclass
from typing import Any, Callable, Optional

from handcalcs.parsing.nodes import Attribute, Constant, Name
from handcalcs.parsing.null_values import NoValue
from handcalcs.parsing.inline_nodes import Compare, FunctionCall, Keyword
from handcalcs.parsing.operator_nodes import (
    AddOp,
    AndOp,
    DivOp,
    EqOp,
    FloorOp,
    GtEOp,
    GtOp,
    HcBinOp,
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
from .compat import ExcelRendererIncompatibleError, incompatible
from .names import SymbolTable

# Excel operator precedence, loosest to tightest. Atoms (names, numbers,
# function calls) are ATOM and never need parentheses.
COMPARISON = 0
ADDITIVE = 1
MULTIPLICATIVE = 2
POWER = 3
NEGATION = 4
ATOM = math.inf

BINARY_OPERATORS = {
    AddOp: ("+", ADDITIVE),
    SubOp: ("-", ADDITIVE),
    MultOp: ("*", MULTIPLICATIVE),
    DivOp: ("/", MULTIPLICATIVE),
    PowOp: ("^", POWER),
}

COMPARISON_OPERATORS = {
    EqOp: "=",
    NeqOp: "<>",
    LtOp: "<",
    LtEOp: "<=",
    GtOp: ">",
    GtEOp: ">=",
}


@dataclass(frozen=True)
class Formula:
    """Formula text plus the precedence of its outermost operator."""
    text: str
    precedence: float = ATOM

    def wrapped(self, needs_parens: bool) -> str:
        return f"({self.text})" if needs_parens else self.text


@dataclass(frozen=True)
class ExcelFunction:
    """
    How one Python callable becomes an Excel formula.

    ``excel`` is the Excel function name; ``arity`` the accepted argument
    counts (``None`` = any count >= ``min_args``). ``build``, when given,
    replaces the default ``NAME(arg, ...)`` spelling: it receives the rendered
    argument texts and returns a ``Formula``.
    """
    excel: str
    arity: Optional[tuple[int, ...]] = (1,)
    min_args: int = 1
    build: Optional[Callable[[list[str]], Formula]] = None

    def accepts(self, n_args: int) -> bool:
        if self.arity is None:
            return n_args >= self.min_args
        return n_args in self.arity

    def translate(self, args: list[str]) -> Formula:
        if self.build is not None:
            return self.build(args)
        return Formula(f"{self.excel}({','.join(args)})")


def _log(args: list[str]) -> Formula:
    if len(args) == 1:
        return Formula(f"LN({args[0]})")
    return Formula(f"LOG({args[0]},{args[1]})")


def _atan2(args: list[str]) -> Formula:
    # math.atan2(y, x) == Excel ATAN2(x, y)
    return Formula(f"ATAN2({args[1]},{args[0]})")


def _hypot(args: list[str]) -> Formula:
    return Formula(f"SQRT(SUMSQ({','.join(args)}))")


def _round(args: list[str]) -> Formula:
    digits = args[1] if len(args) == 2 else "0"
    return Formula(f"ROUND({args[0]},{digits})")


def _simple(excel: str, *arity: int) -> ExcelFunction:
    return ExcelFunction(excel, arity or (1,))


# Python callable -> Excel translation. Keyed by the callable object itself so
# that a user's own ``sqrt`` is never mistaken for ``math.sqrt``.
DEFAULT_FUNCTIONS: dict[Any, ExcelFunction] = {
    math.sqrt: _simple("SQRT"),
    math.exp: _simple("EXP"),
    math.sin: _simple("SIN"),
    math.cos: _simple("COS"),
    math.tan: _simple("TAN"),
    math.asin: _simple("ASIN"),
    math.acos: _simple("ACOS"),
    math.atan: _simple("ATAN"),
    math.sinh: _simple("SINH"),
    math.cosh: _simple("COSH"),
    math.tanh: _simple("TANH"),
    math.asinh: _simple("ASINH"),
    math.acosh: _simple("ACOSH"),
    math.atanh: _simple("ATANH"),
    math.radians: _simple("RADIANS"),
    math.degrees: _simple("DEGREES"),
    math.fabs: _simple("ABS"),
    math.floor: _simple("INT"),  # INT floors toward -inf, like math.floor
    math.ceil: _simple("CEILING.MATH"),
    math.trunc: _simple("TRUNC"),
    math.log10: _simple("LOG10"),
    math.factorial: _simple("FACT"),
    math.log: ExcelFunction("LOG", (1, 2), build=_log),
    math.atan2: ExcelFunction("ATAN2", (2,), build=_atan2),
    math.pow: _simple("POWER", 2),
    math.hypot: ExcelFunction("SUMSQ", None, min_args=1, build=_hypot),
    builtins.abs: _simple("ABS"),
    builtins.pow: _simple("POWER", 2),
    builtins.min: ExcelFunction("MIN", None, min_args=2),
    builtins.max: ExcelFunction("MAX", None, min_args=2),
    # Python rounds half to even; Excel rounds half away from zero.
    builtins.round: ExcelFunction("ROUND", (1, 2), build=_round),
}

# math constants, by object identity (``from math import pi`` binds the same
# float object as ``math.pi``).
DEFAULT_CONSTANTS: dict[int, Formula] = {
    id(math.pi): Formula("PI()"),
    id(math.e): Formula("EXP(1)"),
    id(math.tau): Formula("2*PI()", MULTIPLICATIVE),
}


def has_units(value: Any) -> bool:
    """True for a pint Quantity or a forallpeople Physical (or similar)."""
    if isinstance(value, (bool, int, float, str)):
        return False
    return hasattr(value, "units") or type(value).__name__ == "Physical"


def format_number(value: int | float) -> str:
    """A Python number as an Excel numeric literal."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise incompatible(f"Excel has no literal for {value!r}")
        text = repr(value)
        if text.endswith(".0"):
            text = text[:-2]
        return text.upper()  # 1e-05 -> 1E-05
    return str(value)


def format_string(value: str) -> str:
    """A Python str as an Excel string literal (quotes doubled)."""
    return '"' + value.replace('"', '""') + '"'


class FormulaBuilder:
    """
    Translates one expression tree into Excel formula text.

    ``symbols`` maps Python names to Excel defined names; ``global_ns`` is the
    namespace the cell was executed in, used to identify functions and
    constants by object. ``functions`` and ``constants`` default to the module
    tables and may be extended per renderer.
    """

    def __init__(
        self,
        symbols: SymbolTable,
        global_ns: Optional[dict] = None,
        functions: Optional[dict] = None,
        constants: Optional[dict] = None,
    ) -> None:
        self.symbols = symbols
        self.global_ns = global_ns if isinstance(global_ns, dict) else {}
        self.functions = DEFAULT_FUNCTIONS if functions is None else functions
        self.constants = DEFAULT_CONSTANTS if constants is None else constants

    def build(self, expression: Any) -> str:
        """The formula body (no leading ``=``) for an expression tree."""
        if hasattr(expression, "__iter__") and not hasattr(expression, "type"):
            nodes = list(expression)
            if len(nodes) != 1:
                raise incompatible("the expression could not be parsed into a single formula")
            expression = nodes[0]
        return self.translate(expression).text

    # --- dispatch ---

    def translate(self, node: Any) -> Formula:
        if isinstance(node, NoValue):
            raise incompatible(
                "the expression uses Python syntax handcalcs does not parse "
                "(e.g. a conditional expression or a lambda)",
                node,
            )
        if isinstance(node, Constant):
            return self.constant(node)
        if isinstance(node, Name):
            return self.name(node)
        if isinstance(node, Attribute):
            return self.attribute(node)
        if isinstance(node, HcUnaryOp):
            return self.unary(node)
        if isinstance(node, FloorOp):
            return self.floor_div(node)
        if isinstance(node, ModuloOp):
            return Formula(f"MOD({self.translate(node.left).text},{self.translate(node.right).text})")
        if isinstance(node, HcBinOp) and type(node) in BINARY_OPERATORS:
            return self.binary(node)
        if isinstance(node, Compare):
            return self.compare(node)
        if isinstance(node, (AndOp, OrOp)):
            function = "AND" if isinstance(node, AndOp) else "OR"
            args = ",".join(self.translate(value).text for value in node.values)
            return Formula(f"{function}({args})")
        if isinstance(node, FunctionCall):
            return self.function_call(node)
        node_type = getattr(node, "type", type(node).__name__)
        raise incompatible(f"'{node_type}' has no Excel formula equivalent", node)

    # --- leaves ---

    def constant(self, node: Constant) -> Formula:
        value = node.value
        if isinstance(value, bool):
            return Formula("TRUE" if value else "FALSE")
        if isinstance(value, (int, float)):
            return Formula(format_number(value))
        if isinstance(value, str):
            return Formula(format_string(value))
        if value is None:
            raise incompatible("None has no Excel equivalent", node)
        raise incompatible(f"the literal {value!r} has no Excel equivalent", node)

    def name(self, node: Name) -> Formula:
        identifier = node.identifier
        if identifier in self.symbols:
            if has_units(node.value):
                raise incompatible("values with units are not yet supported", node)
            return Formula(self.symbols.lookup(identifier, node))
        constant = self._math_constant(self.global_ns.get(identifier, NoValue()))
        if constant is not None:
            return constant
        return Formula(self.symbols.lookup(identifier, node))

    def attribute(self, node: Attribute) -> Formula:
        module = self.global_ns.get(node.namespace)
        if module is math or (module is None and node.namespace == "math"):
            value = getattr(math, node.identifier, None)
            constant = self._math_constant(value)
            if constant is not None:
                return constant
        raise incompatible(
            f"the attribute '{node.namespace}.{node.identifier}' has no Excel equivalent", node
        )

    def _math_constant(self, value: Any) -> Optional[Formula]:
        if isinstance(value, float):
            return self.constants.get(id(value))
        return None

    # --- operators ---

    def unary(self, node: HcUnaryOp) -> Formula:
        symbol = node.symbol.strip()
        operand = self.translate(node.operand)
        if symbol == "not":
            return Formula(f"NOT({operand.text})")
        if symbol == "+":
            return operand
        if symbol == "-":
            return Formula("-" + operand.wrapped(operand.precedence <= NEGATION), NEGATION)
        raise incompatible(f"the unary operator '{symbol}' has no Excel equivalent", node)

    def binary(self, node: HcBinOp) -> Formula:
        symbol, precedence = BINARY_OPERATORS[type(node)]
        left = self.translate(node.left)
        right = self.translate(node.right)
        left_parens = left.precedence < precedence
        if precedence == POWER:
            # Any non-atomic base is wrapped: a negated base reads ambiguously
            # (-a^2 is (-a)^2 in Excel) and (a^b)^c is clearer than a^b^c.
            left_parens = left.precedence <= NEGATION
        # All Excel binary operators are left-associative, so an operand of
        # equal precedence on the right keeps its parentheses: a-(b-c), a^(b^c).
        # A negated right operand is wrapped too: a-(-b), not a--b.
        right_parens = right.precedence <= precedence or right.precedence == NEGATION
        return Formula(f"{left.wrapped(left_parens)}{symbol}{right.wrapped(right_parens)}", precedence)

    def floor_div(self, node: FloorOp) -> Formula:
        # INT floors toward -inf, matching Python's //.
        left = self.translate(node.left)
        right = self.translate(node.right)
        quotient = (
            f"{left.wrapped(left.precedence < MULTIPLICATIVE)}"
            f"/{right.wrapped(right.precedence <= MULTIPLICATIVE)}"
        )
        return Formula(f"INT({quotient})")

    def compare(self, node: Compare) -> Formula:
        items = list(node.comparison)
        operands = items[0::2]
        operators = items[1::2]
        if len(operands) != len(operators) + 1:
            raise incompatible("the comparison could not be parsed", node)
        excel_ops = []
        for operator in operators:
            excel_op = COMPARISON_OPERATORS.get(type(operator))
            if excel_op is None:
                symbol = getattr(operator, "symbol", "?").strip()
                raise incompatible(f"the '{symbol}' comparison has no Excel equivalent", operator)
            excel_ops.append(excel_op)
        rendered = []
        for operand in operands:
            formula = self.translate(operand)
            rendered.append(formula.wrapped(formula.precedence <= COMPARISON))
        parts = [
            f"{rendered[i]}{excel_op}{rendered[i + 1]}" for i, excel_op in enumerate(excel_ops)
        ]
        if len(parts) == 1:
            return Formula(parts[0], COMPARISON)
        return Formula(f"AND({','.join(parts)})")

    # --- function calls ---

    def resolve_function(self, node: FunctionCall) -> tuple[Any, str]:
        """The callable a call refers to (or None) and its display name."""
        function_name = node.function_name
        identifier = getattr(function_name, "identifier", str(function_name))
        namespace = getattr(node.namespace, "identifier", "") or ""
        display = f"{namespace}.{identifier}" if namespace else identifier
        missing = object()
        if namespace:
            module = self.global_ns.get(namespace, missing)
            if module is missing:
                # No namespace captured: fall back to the plain 'math.' name.
                if namespace == "math":
                    return getattr(math, identifier, None), display
                return None, display
            return getattr(module, identifier, None), display
        obj = self.global_ns.get(identifier, missing)
        if obj is missing:
            obj = getattr(builtins, identifier, missing)
        if obj is missing:
            # Fallback by name: a bare math function name (e.g. supplied_globals
            # without the import).
            obj = getattr(math, identifier, None)
        return obj, display

    def function_call(self, node: FunctionCall) -> Formula:
        function, display = self.resolve_function(node)
        try:
            spec = self.functions.get(function)
        except TypeError:  # unhashable object in the function position
            spec = None
        if spec is None:
            raise incompatible(f"the function '{display}()' has no Excel equivalent", node)
        args = list(node.args)
        if any(isinstance(arg, Keyword) for arg in args):
            raise incompatible(f"keyword arguments to '{display}()' cannot be written in Excel", node)
        if not spec.accepts(len(args)):
            raise incompatible(
                f"'{display}()' with {len(args)} argument(s) has no Excel equivalent", node
            )
        rendered = [self.translate(arg).text for arg in args]
        return spec.translate(rendered)
