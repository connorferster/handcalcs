"""
Recognizing units (pint and forallpeople) without importing either library.

Used by the ``# hc: -u`` command, which shows a number-times-units line
(``P = 5 * kN``) as its value alone (``P = 5 kN``), and by the Excel renderer.
Values are recognized by duck typing, so handcalcs works without the libraries
installed.
"""

from typing import Any

from .parsing.nodes import Attribute, Constant, Name
from .parsing.operator_nodes import DivOp, HcUnaryOp, MultOp, PowOp

__all__ = ["is_pint_unit", "is_physical", "is_unit", "is_units_input"]


def is_pint_unit(value: Any) -> bool:
    """A pint ``Unit`` (``ureg.kN``), as opposed to a Quantity."""
    return (
        type(value).__name__ == "Unit"
        and hasattr(value, "dimensionality")
        and hasattr(value, "_REGISTRY")
    )


def is_physical(value: Any) -> bool:
    """A forallpeople Physical."""
    return (
        type(value).__name__ == "Physical"
        and hasattr(value, "dimensions")
        and hasattr(value, "value")
    )


def _bare(text: str) -> str:
    """Unit text or a name without its separators: ``kN·m``, ``kN_m`` -> ``kNm``."""
    return "".join(ch for ch in text if ch not in "·⋅*_ ")


def is_unit(node: Any) -> bool:
    """
    True if ``node`` (a Name or Attribute) is a unit, not a variable:

    - a pint ``Unit``;
    - a forallpeople Physical flagged as a defined unit (``is_unit``,
      forallpeople 4 and later);
    - a forallpeople Physical of exactly 1 whose unit text is its own name
      (``kN`` is ``1 kN``). The name check keeps a variable that happens to be
      one unit (``F = 1 * kN``, used as ``3 * F``) from counting as one.
    """
    if not isinstance(node, (Name, Attribute)):
        return False
    value = getattr(node, "value", None)
    if is_pint_unit(value):
        return True
    if not is_physical(value):
        return False
    if getattr(value, "is_unit", None) is True:
        return True
    number, _, unit = format(value, ".15g").partition(" ")
    try:
        magnitude = float(number)
    except ValueError:
        return False
    name = getattr(node, "source_identifier", "") or node.identifier
    return magnitude == 1 and bool(unit) and _bare(unit) == _bare(name)


def is_number(node: Any) -> bool:
    """A numeric literal from the source, optionally signed: ``5``, ``-12.5``."""
    if isinstance(node, HcUnaryOp) and node.symbol in ("-", "+"):
        node = node.operand
    return (
        isinstance(node, Constant)
        and not node.calculated
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    )


def is_units_input(node: Any) -> bool:
    """
    True if ``node`` is a number times units: exactly one numeric literal,
    scaling the value (not in a divisor or the base of a power), and otherwise
    only units joined by ``*``, ``/`` and ``**`` with a literal exponent.
    ``5 * kN``, ``-12 * kN``, ``4.5 * kN / m``, ``300 * mm**2`` qualify;
    ``5 * kN * 2``, ``3 * m + 200 * mm``, ``1 / (5 * m)`` and ``3 * F`` do not.
    """
    numbers: list = []
    return _units_expression(node, numbers, scales=True) and len(numbers) == 1


def _units_expression(node: Any, numbers: list, scales: bool) -> bool:
    if is_number(node):
        numbers.append(node)
        return scales
    if isinstance(node, (Name, Attribute)):
        return is_unit(node)
    if isinstance(node, MultOp):
        return _units_expression(node.left, numbers, scales) and _units_expression(
            node.right, numbers, scales
        )
    if isinstance(node, DivOp):
        return _units_expression(node.left, numbers, scales) and _units_expression(
            node.right, numbers, False
        )
    if isinstance(node, PowOp):
        return is_unit(node.left) and is_number(node.right)
    return False
