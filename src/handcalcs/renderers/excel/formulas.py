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

Unit factors are folded through the expression. Rows hold magnitudes in their
display units, so each translated piece carries the factor that makes it SI
(``Formula.factor``: text x factor = SI value). Products, quotients and powers
combine factors without writing them; a factor is written only where values
must agree (``+``, ``-``, comparisons, ``IF``, ``min``/``max``), where a
function needs SI (``SQRT`` and the rest), and at the end, when what is left
does not match the row's own unit. It is written in its simplest form
(``/12``, ``*25.4``; see ``factor_text``). With US units,
``M = w * L**2 / 8`` is ``=w*L^2/8``, not
``=w*14593.9029372*(L*0.3048)^2/8/1355.81794833``.

Two Excel precedence traps are handled here:

- negation binds *tighter* than ``^`` (``-2^2`` is 4), so ``-a**2`` becomes
  ``-(a^2)``;
- ``^`` is *left*-associative (``2^3^2`` is 64), so ``a**b**c`` becomes
  ``a^(b^c)``.
"""

from __future__ import annotations
import builtins
import math
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Any, Callable, Optional, Union

from handcalcs.parsing.nodes import Attribute, Constant, Name, Subscript
from handcalcs.parsing.null_values import NoValue
from handcalcs.parsing.inline_nodes import Compare, FunctionCall, IfExp, Keyword
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
from .units import (
    has_units,
    is_physical,
    is_pint_quantity,
    is_pint_unit,
    unit_constant,
    unit_factor,
    unit_value,
)

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


# A display -> SI factor: exact (a Fraction) where the units library allows.
Factor = Union[Fraction, float]

# Relative difference below which two factors are the same, and a factor is
# written as a shorter number: float noise from pint (or a non-integer power)
# is about 1e-16 per operation.
FACTOR_TOLERANCE = 1e-13


@dataclass(frozen=True)
class Formula:
    """
    Formula text, the precedence of its outermost operator, and the factor
    that makes its value SI (``1`` for a plain number or an SI value).
    """

    text: str
    precedence: float = ATOM
    factor: Factor = 1
    # A bare unit (``mm``): the text is "1" and the unit is all factor, so
    # ``12 * mm`` is written ``12``, with the factor of mm.
    unit: bool = False

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


def _cbrt(args: list[str]) -> Formula:
    # x^(1/3) is #NUM! for a negative x in Excel; math.cbrt is not.
    return Formula(f"SIGN({args[0]})*ABS({args[0]})^(1/3)", MULTIPLICATIVE)


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
    math.cbrt: ExcelFunction("CBRT", (1,), build=_cbrt),
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
    # A plain number: float() is the number itself and int() truncates toward
    # zero. A value with units is handled in FormulaBuilder.unit_call.
    builtins.float: ExcelFunction(
        "", (1,), build=lambda args: Formula(args[0], COMPARISON)
    ),
    builtins.int: _simple("TRUNC"),
}

# Builtins whose result depends on the units of their first argument.
UNIT_SENSITIVE = (builtins.round, builtins.float, builtins.int)

# math constants, by object identity (``from math import pi`` binds the same
# float object as ``math.pi``).
DEFAULT_CONSTANTS: dict[int, Formula] = {
    id(math.pi): Formula("PI()"),
    id(math.e): Formula("EXP(1)"),
    id(math.tau): Formula("2*PI()", MULTIPLICATIVE),
}


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


def resolve_function(node: FunctionCall, global_ns: dict) -> tuple[Any, str]:
    """
    The callable a call refers to (or None) and its display name.

    A namespaced call resolves through the module captured in ``global_ns``; a
    bare name through ``global_ns``, then builtins. With no captured namespace
    (e.g. ``supplied_globals`` without the import) a ``math`` name is used.
    """
    function_name = node.function_name
    identifier = getattr(function_name, "identifier", str(function_name))
    if node.namespace and not isinstance(node.namespace, Name):
        # A method of an expression, (a * b).to("mm"): not a known function.
        return None, f"(...).{identifier}"
    namespace = getattr(node.namespace, "identifier", "") or ""
    display = f"{namespace}.{identifier}" if namespace else identifier
    missing = object()
    if namespace:
        first, *rest = namespace.split(".")
        module = global_ns.get(first, missing)
        if module is missing:
            if namespace == "math":
                return getattr(math, identifier, None), display
            return None, display
        for attr in rest:  # a dotted namespace, e.g. np.linalg
            module = getattr(module, attr, None)
        return getattr(module, identifier, None), display
    obj = global_ns.get(identifier, missing)
    if obj is missing:
        obj = getattr(builtins, identifier, missing)
    if obj is missing:
        obj = getattr(math, identifier, None)
    return obj, display


def _is_unit_argument(node: Any) -> bool:
    """
    A ``.to()`` target: a unit name string (``"kip"``), a unit object, or a
    product, quotient or power of units (``ureg.kip * ureg.ft``).
    """
    if isinstance(node, Constant):
        return isinstance(node.value, str)
    if isinstance(node, (Name, Attribute)):
        value = getattr(node, "value", None)
        return is_pint_unit(value) or unit_constant(value) is not None
    if isinstance(node, (MultOp, DivOp)):
        return _is_unit_argument(node.left) and _is_unit_argument(node.right)
    if isinstance(node, PowOp):
        return _is_unit_argument(node.left) and isinstance(node.right, Constant)
    return False


def unit_conversion_receiver(node: FunctionCall, global_ns: dict) -> Any:
    """
    The value converted by a unit conversion, ``x`` in ``x.to("kip")`` or
    ``(F * L).to(ureg.kN * ureg.m)``; None for any other call.

    A conversion only changes the display unit. Formulas already work in SI
    and scale each row by its own display unit, so the conversion becomes no
    Excel at all: the row's unit (read from the converted Python value) does it.
    """
    identifier = getattr(node.function_name, "identifier", node.function_name)
    if identifier != "to" or not node.namespace:
        return None
    args = list(node.args)
    if len(args) != 1 or isinstance(args[0], Keyword) or not _is_unit_argument(args[0]):
        return None
    receiver = node.namespace
    if isinstance(receiver, Name):
        # A name must hold a quantity: ``si.to(...)`` (a module) is not one. A
        # receiver Name carries its identifier as its value, so look it up.
        if not has_units(global_ns.get(receiver.identifier)):
            return None
    return receiver


def exact(factor: Any) -> Factor:
    """``factor`` as a Fraction: exactly, or from a float's shortest decimal."""
    if isinstance(factor, (int, Fraction)):
        return Fraction(factor)
    factor = float(factor)
    if math.isfinite(factor) and factor:
        return Fraction(repr(factor))
    return factor


def same_factor(a: Factor, b: Factor) -> bool:
    return abs(a - b) <= FACTOR_TOLERANCE * abs(b)


# Significant digits of an exact decimal factor worth writing in full
# (4.4482216152605 N per lbf). A pint float such as 0.30479999999999996 has
# 17, and is written to tolerance instead (0.3048).
EXACT_DIGITS = 15


def _decimal(value: Fraction) -> Optional[tuple[Fraction, bool]]:
    """
    ``value`` as a decimal and whether it is exact: the exact decimal when it
    has at most EXACT_DIGITS significant digits, else the one with the fewest
    digits within tolerance (None if there is none).
    """
    approximate = None
    for digits in range(EXACT_DIGITS + 1):
        scale = 10**digits
        scaled = round(value * scale)
        candidate = Fraction(scaled, scale)
        if candidate == value and len(str(abs(scaled))) <= EXACT_DIGITS:
            return candidate, True
        if approximate is None and candidate and same_factor(candidate, value):
            approximate = candidate
    return None if approximate is None else (approximate, False)


def _number_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return format_number(float(value))


def factor_text(ratio: Factor) -> Optional[tuple[str, str]]:
    """
    How to write a factor that remains, as ``(operator, number)``: ``("/",
    "12")`` rather than ``("*", "0.0833333333333")``. None for a factor of 1.

    Of ``*ratio`` and ``/(1/ratio)``, an integer is preferred, then an exact
    decimal, then the shorter number, then ``*``: ``*1000``, ``/1000``, ``/8``
    (not ``*0.125``), ``*25.4``, ``/25.4``, ``/0.3048``, ``/4.4482216152605``
    (not ``*0.2248089430997``).
    """
    ratio = exact(ratio)
    if same_factor(ratio, 1):
        return None
    candidates = []
    for operator, value in (("*", ratio), ("/", 1 / ratio)):
        found = _decimal(value)
        if found is not None:
            decimal, is_exact = found
            text = _number_text(decimal)
            candidates.append(
                (
                    decimal.denominator != 1,
                    not is_exact,
                    len(text),
                    operator != "*",
                    operator,
                    text,
                )
            )
    if candidates:
        *_, operator, text = min(candidates)
        return operator, text
    if ratio >= 1:  # pragma: no cover - every factor has a short decimal
        return "*", format_number(float(f"{float(ratio):.12g}"))
    return "/", format_number(float(f"{float(1 / ratio):.12g}"))


def is_zero(formula: Formula) -> bool:
    """A literal 0, which is 0 in any unit."""
    return formula.text in ("0", "-0")


def convert(formula: Formula, factor: Factor) -> Formula:
    """
    ``formula`` re-expressed so that its text times ``factor`` is the SI
    value: the ratio of the two factors is written, when it is not 1.
    """
    factor = exact(factor)
    if is_zero(formula):
        return replace(formula, factor=factor, unit=False)
    written = factor_text(exact(formula.factor) / factor)
    if written is None:
        return replace(formula, factor=factor, unit=False)
    operator, number = written
    text = formula.wrapped(formula.precedence < MULTIPLICATIVE)
    return Formula(f"{text}{operator}{number}", MULTIPLICATIVE, factor)


def common_factor(formulas: list[Formula], hint: Optional[Factor] = None) -> Factor:
    """
    The factor to bring values to before they meet (``a + b``, ``a < b``):
    the one that writes the fewest factors, counting the conversion to
    ``hint`` (the unit the result is wanted in), if given. Ties go to the
    first value's, as Python gives a sum the unit of its left side. A literal
    0 fits any.
    """
    factors = [exact(f.factor) for f in formulas if not is_zero(f)]
    hint = None if hint is None else exact(hint)
    candidates = factors + ([hint] if hint is not None else [])
    if not candidates:
        return Fraction(1)

    def cost(candidate: Factor) -> int:
        written = sum(not same_factor(f, candidate) for f in factors)
        if hint is not None and not same_factor(candidate, hint):
            written += 1
        return written

    return min(candidates, key=cost)


def _power_factor(factor: Factor, exponent: Union[int, float]) -> Factor:
    if float(exponent).is_integer():
        return exact(factor) ** int(exponent)
    return exact(float(factor) ** exponent)


def _literal_exponent(node: Any) -> Optional[Union[int, float]]:
    """The number an exponent is written as (``2``, ``0.5``, ``-1``), or None."""
    if isinstance(node, Constant):
        value = node.value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        return None
    if isinstance(node, HcUnaryOp) and node.symbol.strip() in ("-", "+"):
        value = _literal_exponent(node.operand)
        if value is None:
            return None
        return -value if node.symbol.strip() == "-" else value
    return None


# Functions whose result is in the unit of their arguments: their arguments
# need only agree with each other, not be SI.
HOMOGENEOUS = (builtins.min, builtins.max, builtins.abs)


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
        factors: Optional[dict] = None,
        value_of: Optional[Callable[[Any], Any]] = None,
    ) -> None:
        self.symbols = symbols
        # The Python value of an expression at the current row (raises if it
        # cannot be found): round/float/int need their argument's units.
        self.value_of = value_of
        # Excel name -> display-unit-to-SI factor, for rows with units.
        self.factors = {} if factors is None else factors
        self.global_ns = global_ns if isinstance(global_ns, dict) else {}
        self.functions = DEFAULT_FUNCTIONS if functions is None else functions
        self.constants = DEFAULT_CONSTANTS if constants is None else constants

    def build(self, expression: Any) -> str:
        """The formula body (no leading ``=``) for an expression tree, in SI."""
        return self.build_scaled(expression, 1)

    def build_scaled(self, expression: Any, factor: Factor = 1) -> str:
        """
        The formula body of an expression, in the display unit whose factor
        to SI is ``factor`` (1: SI, or a plain number).
        """
        if hasattr(expression, "__iter__") and not hasattr(expression, "type"):
            nodes = list(expression)
            if len(nodes) != 1:
                raise incompatible(
                    "the expression could not be parsed into a single formula"
                )
            expression = nodes[0]
        formula = self.translate(expression, hint=exact(factor))
        return convert(formula, factor).text

    # --- dispatch ---

    def translate(self, node: Any, hint: Optional[Factor] = None) -> Formula:
        """
        ``node`` as a Formula, with the factor that makes it SI. ``hint`` is
        the factor the result is wanted in, used to choose the unit that the
        terms of a sum are brought to.
        """
        if isinstance(node, NoValue):
            raise incompatible(
                "the expression uses Python syntax handcalcs does not parse "
                "(e.g. a lambda)",
                node,
            )
        if isinstance(node, Constant):
            return self.constant(node)
        if isinstance(node, Name):
            return self.name(node)
        if isinstance(node, Attribute):
            return self.attribute(node)
        if isinstance(node, HcUnaryOp):
            return self.unary(node, hint)
        if isinstance(node, FloorOp):
            return self.floor_div(node)
        if isinstance(node, ModuloOp):
            left, right = self.agree([node.left, node.right], hint)
            return Formula(f"MOD({left.text},{right.text})", ATOM, left.factor)
        if isinstance(node, HcBinOp) and type(node) in BINARY_OPERATORS:
            return self.binary(node, hint)
        if isinstance(node, Compare):
            return self.compare(node)
        if isinstance(node, (AndOp, OrOp)):
            # Truth does not depend on units: a value is 0 in any of them.
            function = "AND" if isinstance(node, AndOp) else "OR"
            args = ",".join(self.translate(value).text for value in node.values)
            return Formula(f"{function}({args})")
        if isinstance(node, FunctionCall):
            return self.function_call(node, hint)
        if isinstance(node, IfExp):
            test = self.translate(node.test).text
            body, orelse = self.agree([node.body, node.orelse], hint)
            return Formula(f"IF({test},{body.text},{orelse.text})", ATOM, body.factor)
        if isinstance(node, Subscript):
            raise incompatible(
                "an index or key lookup (e.g. xs[0]) has no Excel formula equivalent",
                node,
            )
        node_type = getattr(node, "type", type(node).__name__)
        raise incompatible(f"'{node_type}' has no Excel formula equivalent", node)

    def agree(self, nodes: list, hint: Optional[Factor] = None) -> list[Formula]:
        """
        Translate values that meet (the terms of a sum, the sides of a
        comparison), brought to one common factor.
        """
        formulas = [self.translate(node, hint) for node in nodes]
        factor = common_factor(formulas, hint)
        return [convert(formula, factor) for formula in formulas]

    def si(self, node: Any) -> Formula:
        """``node`` in SI: for a function argument, an exponent, an index."""
        return convert(self.translate(node), 1)

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
            excel_name = self.symbols.lookup(identifier, node)
            # The row holds a magnitude in its display unit.
            return Formula(excel_name, ATOM, exact(self.factors.get(excel_name, 1)))
        value = self.global_ns.get(identifier, node.value)
        if isinstance(value, NoValue):
            # Python's lookup order: globals, then builtins (forallpeople's
            # ``top_level=True`` puts unit names such as ``mm`` there).
            value = getattr(builtins, identifier, value)
        constant = self._math_constant(value)
        if constant is not None:
            return constant
        unit = unit_factor(value)
        if unit is not None:
            return Formula("1", ATOM, exact(unit), unit=True)
        return Formula(self.symbols.lookup(identifier, node))

    def attribute(self, node: Attribute) -> Formula:
        if node.receiver is not None:
            raise incompatible(
                f"the attribute '.{node.identifier}' of an expression has no Excel "
                "equivalent",
                node,
            )
        module = self.global_ns.get(node.namespace)
        if module is math or (module is None and node.namespace == "math"):
            value = getattr(math, node.identifier, None)
            constant = self._math_constant(value)
            if constant is not None:
                return constant
        unit = unit_factor(node.value)
        if unit is not None:  # e.g. ureg.mm
            return Formula("1", ATOM, exact(unit), unit=True)
        raise incompatible(
            f"the attribute '{node.namespace}.{node.identifier}' has no Excel equivalent",
            node,
        )

    def _math_constant(self, value: Any) -> Optional[Formula]:
        if isinstance(value, float):
            return self.constants.get(id(value))
        return None

    # --- operators ---

    def unary(self, node: HcUnaryOp, hint: Optional[Factor] = None) -> Formula:
        symbol = node.symbol.strip()
        if symbol == "not":
            return Formula(f"NOT({self.translate(node.operand).text})")
        operand = self.translate(node.operand, hint)
        if symbol == "+":
            return operand
        if symbol == "-":
            return Formula(
                "-" + operand.wrapped(operand.precedence <= NEGATION),
                NEGATION,
                operand.factor,
            )
        raise incompatible(
            f"the unary operator '{symbol}' has no Excel equivalent", node
        )

    def binary(self, node: HcBinOp, hint: Optional[Factor] = None) -> Formula:
        symbol, precedence = BINARY_OPERATORS[type(node)]
        if precedence == ADDITIVE:
            left, right = self.agree([node.left, node.right], hint)
            factor = left.factor
        elif precedence == POWER:
            left = self.translate(node.left)
            right = self.si(node.right)
            exponent = _literal_exponent(node.right)
            if exponent is None:
                # The power of a factor is unknown until the sheet runs.
                left = convert(left, 1)
                factor = 1
            else:
                factor = _power_factor(left.factor, exponent)
                if left.unit:  # mm**2: still a bare unit
                    return Formula("1", ATOM, factor, unit=True)
        else:
            left = self.translate(node.left)
            right = self.translate(node.right)
            if isinstance(node, MultOp):
                factor = exact(left.factor) * exact(right.factor)
            else:
                factor = exact(left.factor) / exact(right.factor)
            # A bare unit multiplies or divides only the factor: 12 * mm is 12.
            if right.unit or (left.unit and isinstance(node, MultOp)):
                kept = left if right.unit else right
                return replace(kept, factor=factor, unit=left.unit and right.unit)
        left_parens = left.precedence < precedence
        if precedence == POWER:
            # Any non-atomic base is wrapped: a negated base reads ambiguously
            # (-a^2 is (-a)^2 in Excel) and (a^b)^c is clearer than a^b^c.
            left_parens = left.precedence <= NEGATION
        # All Excel binary operators are left-associative, so an operand of
        # equal precedence on the right keeps its parentheses: a-(b-c), a^(b^c).
        # A negated right operand is wrapped too: a-(-b), not a--b.
        right_parens = right.precedence <= precedence or right.precedence == NEGATION
        return Formula(
            f"{left.wrapped(left_parens)}{symbol}{right.wrapped(right_parens)}",
            precedence,
            factor,
        )

    def floor_div(self, node: FloorOp) -> Formula:
        # INT floors toward -inf, matching Python's //. The quotient must be a
        # plain number before it is floored.
        left = self.translate(node.left)
        right = self.translate(node.right)
        quotient = Formula(
            f"{left.wrapped(left.precedence < MULTIPLICATIVE)}"
            f"/{right.wrapped(right.precedence <= MULTIPLICATIVE)}",
            MULTIPLICATIVE,
            exact(left.factor) / exact(right.factor),
        )
        return Formula(f"INT({convert(quotient, 1).text})")

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
                raise incompatible(
                    f"the '{symbol}' comparison has no Excel equivalent", operator
                )
            excel_ops.append(excel_op)
        rendered = [
            formula.wrapped(formula.precedence <= COMPARISON)
            for formula in self.agree(operands)
        ]
        parts = [
            f"{rendered[i]}{excel_op}{rendered[i + 1]}"
            for i, excel_op in enumerate(excel_ops)
        ]
        if len(parts) == 1:
            return Formula(parts[0], COMPARISON)
        return Formula(f"AND({','.join(parts)})")

    # --- function calls ---

    def resolve_function(self, node: FunctionCall) -> tuple[Any, str]:
        return resolve_function(node, self.global_ns)

    def function_call(
        self, node: FunctionCall, hint: Optional[Factor] = None
    ) -> Formula:
        receiver = unit_conversion_receiver(node, self.global_ns)
        if receiver is not None:
            return self.translate(receiver, hint)
        function, display = self.resolve_function(node)
        try:
            spec = self.functions.get(function)
        except TypeError:  # unhashable object in the function position
            spec = None
        if spec is None:
            raise incompatible(
                f"the function '{display}()' has no Excel equivalent", node
            )
        args = list(node.args)
        if any(isinstance(arg, Keyword) for arg in args):
            raise incompatible(
                f"keyword arguments to '{display}()' cannot be written in Excel", node
            )
        if not spec.accepts(len(args)):
            raise incompatible(
                f"'{display}()' with {len(args)} argument(s) has no Excel equivalent",
                node,
            )
        if function in UNIT_SENSITIVE and args:
            converted = self.unit_call(function, args, display, node)
            if converted is not None:
                return converted
        if any(function is f for f in HOMOGENEOUS):
            # min, max, abs: the result is in the arguments' unit.
            formulas = self.agree(args, hint)
            result = spec.translate([formula.text for formula in formulas])
            return replace(result, factor=formulas[0].factor)
        return spec.translate([self.si(arg).text for arg in args])

    def unit_call(
        self, function: Any, args: list, display: str, node: FunctionCall
    ) -> Optional[Formula]:
        """
        ``round``, ``float`` or ``int`` of a value with units, matching Python;
        None for a plain number (the ordinary translation applies), except
        that ``float`` of a plain number is the number itself.

        References are in SI, so the argument's formula is its SI value:

        - forallpeople: ``float(x)``/``int(x)`` are the magnitude in x's display
          unit (``float(4 ksi)`` is 4), and ``round(x, n)`` only sets how many
          digits x prints with, so it leaves the value unchanged;
        - pint: ``round(q, n)`` rounds the magnitude in q's unit, and
          ``float(q)``/``int(q)`` (dimensionless only) are its SI value.
        """
        if function is builtins.float and not isinstance(args[0], Keyword):
            plain = self.translate(args[0])  # kept if the argument has no units
        else:
            plain = None
        if self.value_of is None:
            return plain
        try:
            value = self.value_of(args[0])
        except Exception:
            raise incompatible(
                f"the units of the value passed to '{display}()' could not be "
                "determined",
                node,
            ) from None
        if not (is_physical(value) or is_pint_quantity(value)):
            return plain
        argument = plain or self.translate(args[0])
        if function is builtins.round:
            if is_physical(value):
                return argument
            factor = exact(unit_value(value).factor)
            digits = self.si(args[1]).text if len(args) == 2 else "0"
            in_unit = convert(argument, factor)
            return Formula(f"ROUND({in_unit.text},{digits})", ATOM, factor)
        # A plain number: forallpeople's magnitude in the display unit, or
        # pint's SI value (pint allows only dimensionless values).
        unit = exact(unit_value(value).factor) if is_physical(value) else 1
        number = replace(convert(argument, unit), factor=1)
        if function is builtins.int:
            return Formula(f"TRUNC({number.text})")
        return number
