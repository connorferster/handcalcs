"""
Units: pint Quantities and forallpeople Physicals on a live worksheet.

Excel cells hold plain numbers, so a value with units is written as its
magnitude in its *display* unit (``300`` for ``300 mm``) with the unit text in
the unit column. Formulas stay correct across mixed units by working in SI
base units. Each row has a display -> SI factor, and the formula builder
carries these factors through the expression, writing one only where it does
not cancel (see ``formulas``)::

    M = F * L          # F = 12 kN, L = 300 mm, M displays in kN·m
    =F*L/1000

Factors are computed in Python from the units library: exact fractions for
forallpeople (from ``Physical.display()``, forallpeople 3.5+), floats for pint.
Offset units (°C, °F) raise. A bare unit name in an expression
(``x = a * mm``) is the constant ``0.001``.

Neither library is imported here: values are recognized by duck typing, so
the renderer works without them installed.
"""

from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from types import ModuleType
from typing import Any, Optional, Union

from .compat import incompatible

# Significant digits kept in a unit constant (``mm`` -> 0.001): removes float
# noise such as 0.3 / 300 = 0.0009999999999999998.
FACTOR_DIGITS = 12

# Modules whose imports and setup lines (``si.environment(...)``) are skipped.
UNITS_MODULES = ("pint", "forallpeople")


@dataclass(frozen=True)
class UnitValue:
    magnitude: float  # in the display unit
    unit: str  # display unit text ('' when dimensionless)
    # display unit -> SI base unit: a Fraction when exact (forallpeople), else
    # a float (pint)
    factor: Union[Fraction, float]


def _clean(factor: float) -> float:
    return float(f"{factor:.{FACTOR_DIGITS}g}")


def is_pint_quantity(value: Any) -> bool:
    return (
        hasattr(value, "magnitude")
        and hasattr(value, "units")
        and hasattr(value, "to_base_units")
    )


def is_pint_unit(value: Any) -> bool:
    return (
        type(value).__name__ == "Unit"
        and hasattr(value, "dimensionality")
        and hasattr(value, "_REGISTRY")
    )


def is_pint_registry(value: Any) -> bool:
    return type(value).__name__.endswith("UnitRegistry") and hasattr(value, "Quantity")


def is_physical(value: Any) -> bool:
    """A forallpeople Physical."""
    return (
        type(value).__name__ == "Physical"
        and hasattr(value, "dimensions")
        and hasattr(value, "value")
    )


def has_units(value: Any) -> bool:
    return is_pint_quantity(value) or is_pint_unit(value) or is_physical(value)


def is_units_setup(value: Any) -> bool:
    """
    A value that only sets up units: a pint registry or unit, a units module,
    or a function/class from one (``si.environment``). Quantities are values.
    """
    if is_pint_registry(value) or is_pint_unit(value):
        return True
    if has_units(value):
        return False
    if isinstance(value, ModuleType):
        module = value.__name__
    elif callable(value):
        module = getattr(value, "__module__", None) or ""
    else:
        return False
    return module.split(".")[0] in UNITS_MODULES


def _pint_unit_value(quantity: Any) -> UnitValue:
    if not getattr(quantity, "_is_multiplicative", True):
        raise incompatible(
            f"the offset unit '{quantity.units}' cannot be scaled inside a formula; "
            "use an absolute unit such as kelvin"
        )
    unit = f"{quantity.units:~P}"
    factor = quantity._REGISTRY.Quantity(1, quantity.units).to_base_units().magnitude
    return UnitValue(float(quantity.magnitude), unit, float(factor))


def _physical_unit_value(physical: Any) -> UnitValue:
    # forallpeople picks the display unit (and prefix) itself.
    display = getattr(physical, "display", None)
    if callable(display):
        # forallpeople 3.5+: the shown number and unit, and the exact factor
        # from the SI value to the number.
        shown = display()
        factor = shown.factor
        if isinstance(factor, (int, Fraction)):
            to_si = 1 / Fraction(factor)
        else:
            to_si = 1 / float(factor)
        return UnitValue(float(shown.magnitude), shown.unit, to_si)
    # Older versions: read the display back at full precision and derive the
    # factor from the SI value.
    text = format(physical, f".{15}g")
    number, _, unit = text.partition(" ")
    magnitude = float(number)
    si_value = float(physical.value)
    factor = 1.0 if magnitude == 0 else _clean(si_value / magnitude)
    return UnitValue(magnitude, unit.strip(), factor)


def unit_value(value: Any) -> Optional[UnitValue]:
    """The display magnitude, unit and SI factor of ``value``; None if unitless."""
    if is_pint_quantity(value):
        return _pint_unit_value(value)
    if is_physical(value):
        return _physical_unit_value(value)
    return None


def unit_factor(value: Any) -> Optional[Union[Fraction, float]]:
    """
    The SI value of a bare unit (``mm`` -> 1/1000), exact when the units
    library allows, or None.

    A pint ``Unit``, or a quantity of magnitude 1 (forallpeople defines ``mm``
    as ``1 mm``), counts as a unit; any other quantity is a value, which must be
    a row on the sheet.
    """
    if is_pint_unit(value):
        return float(value._REGISTRY.Quantity(1, value).to_base_units().magnitude)
    info = unit_value(value)
    if info is not None and info.magnitude == 1:
        return info.factor
    return None


def unit_constant(value: Any) -> Optional[float]:
    """The SI value of a bare unit as a float (``mm`` -> 0.001), or None."""
    factor = unit_factor(value)
    return None if factor is None else _clean(float(factor))
