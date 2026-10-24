"""
Partial inputs: rendering one calculation script with different given values.

``bind_inputs`` rewrites the source so that the first top-level assignment of each
input name assigns the input instead. The rewritten source is then executed and
parsed exactly like any other script, so the document shows the input values and
everything computed from them. The keys of the inputs dict designate the inputs;
the script needs no comment commands.

When the input is a plain number and the assignment is a number times units
(``w = 4.5 * kN / m``), only the number is replaced, so the script's units are kept.

``InputBinding`` also takes inputs that cannot be written as source text, such as
quantities and arrays. A quantity bound to a number times units is converted to the
script's units while the script runs, and its number is written into the rendered
source. Any other object is passed to the script unchanged and shown as the line's
value.
"""

import ast
import dataclasses
import numbers
import pathlib
import re
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

from .nodes import Constant

__all__ = ["bind_inputs", "find_inputs", "InputBinding"]

# The function an object input's assignment calls while the script runs
RESOLVER = "__hc_input__"
# The text an object input's value is written as for parsing, before the object
# itself is placed in the parsed tree
PLACEHOLDER = "\x00hc-input:"


@dataclass
class Binding:
    """The first top-level ``name = <expr>`` assignment of a name."""

    name: str
    value: ast.expr
    magnitude: Optional[ast.expr]  # the number of a number-times-units value
    is_given: bool  # a literal or a number times units, i.e. not computed


def bind_inputs(
    source: str,
    inputs: dict,
    *,
    strict: bool = True,
    allow_computed: bool = False,
) -> str:
    """
    Returns ``source`` with each name in ``inputs`` assigned its input value.

    The first top-level simple assignment (``name = <expr>``, also as one
    statement of a ``a = 1; b = 2`` line) of each name is bound; later
    reassignments are left to run. A number replaces the number of a
    number-times-units value (``L = 6 * m`` becomes ``L = 8 * m``); any other
    input replaces the whole right-hand side.

    Raises a KeyError for an input the source never assigns (unless ``strict`` is
    False, then it is ignored), a ValueError for an input that is only assigned
    inside a block or function, by an augmented assignment or by unpacking, or
    whose assignment computes its value (unless ``allow_computed`` is True), and
    a TypeError for a value that cannot be written as a Python literal. Use
    ``InputBinding`` (or ``HandCalcs(..., inputs=...)``) for such values.
    """
    binding = InputBinding(source, inputs, strict=strict, allow_computed=allow_computed)
    if binding.objects:
        name, value = next(iter(binding.objects.items()))
        raise TypeError(
            f"The input '{name}' ({type(value).__name__}) cannot be written as a "
            "Python literal. Inputs must be numbers, strings, booleans, None, or "
            "lists, tuples and dicts of these. HandCalcs(..., inputs=...) also "
            "takes quantities and other objects."
        )
    return binding.exec_source


class InputBinding:
    """
    The inputs of one render of ``source``, in three steps:

    1. Run ``exec_source`` in a namespace that starts as ``namespace()``.
    2. Parse ``parse_source(namespace)``, the source as it is shown.
    3. Call ``place_objects(tree)`` on the parsed tree.

    Inputs that can be written as literals are bound as in ``bind_inputs``. An
    object input (a quantity, an array) makes its assignment call the resolver.
    If the assignment is a number times units and the object divided by those
    units is a plain number, the object is converted to them (``6200 N/m``
    against ``w = 4.5 * kN / m`` runs and renders as ``w = 6.2 * kN / m``);
    if the division leaves units, a ValueError is raised. Otherwise the object
    is assigned as it is, and shown as the line's value.
    """

    def __init__(
        self,
        source: str,
        inputs: dict,
        *,
        strict: bool = True,
        allow_computed: bool = False,
    ):
        tree = ast.parse(source)
        bindings = first_bindings(tree)
        self.source = source
        self.objects = {}  # name -> an input that cannot be written as a literal
        self.converted = {}  # name -> the number of a converted object input
        self.literal_edits = []
        self.object_bindings = {}  # name -> Binding
        unknown = []
        for name, value in inputs.items():
            binding = bindings.get(name)
            if binding is None:
                line = other_binding_line(tree, name)
                if line is not None:
                    raise ValueError(
                        f"The input '{name}' cannot be bound: it is only assigned on "
                        f"line {line} inside a block or function, by an augmented "
                        "assignment or by unpacking. Inputs bind to a top-level "
                        "'name = value' assignment."
                    )
                unknown.append(name)
                continue
            if not binding.is_given and not allow_computed:
                raise ValueError(
                    f"'{name}' is computed on line {binding.value.lineno}; pass "
                    "allow_computed=True to replace the calculation with the input."
                )
            value = plain_number(value)
            text = literal_text(value)
            if text is None:
                self.objects[name] = value
                self.object_bindings[name] = binding
            elif binding.magnitude is not None and is_number(value):
                self.literal_edits.append((binding.magnitude, text))
            else:
                self.literal_edits.append((binding.value, text))
        if unknown and strict:
            raise KeyError(
                "The source never assigns the input(s) "
                f"{', '.join(map(repr, unknown))}. Check the names, or pass "
                "strict=False to ignore inputs the source does not use."
            )
        edits = list(self.literal_edits)
        for name, binding in self.object_bindings.items():
            if has_units(binding):
                # The units are the value with its number replaced by 1
                units = splice(source, binding.value, [(binding.magnitude, "1")])
                call = f"{RESOLVER}({name!r}, {units})"
            else:
                call = f"{RESOLVER}({name!r})"
            edits.append((binding.value, call))
        self.exec_source = apply_edits(source, edits)

    def namespace(self) -> dict:
        """The namespace ``exec_source`` must start running in."""
        return {RESOLVER: self._resolve} if self.objects else {}

    def _resolve(self, name: str, units: Any = None) -> Any:
        """The value an object input's assignment assigns, while the script runs."""
        value = self.objects[name]
        if units is None:
            return value
        try:
            ratio = in_registry_of(units, value) / units
        except Exception:
            return value
        if not is_number(ratio) and getattr(ratio, "dimensionless", None) is False:
            raise ValueError(
                f"The input '{name}' ({value}) cannot be converted to the units of "
                f"line {self.object_bindings[name].value.lineno} ({units})."
            )
        try:
            number = float(ratio)
        except (TypeError, ValueError):
            return value  # e.g. an array of quantities
        number = float(f"{number:.15g}")  # without floating-point noise
        source_number = ast.literal_eval(self.object_bindings[name].magnitude)
        if isinstance(source_number, int) and number.is_integer():
            number = int(number)
        self.converted[name] = number
        return number * units

    def parse_source(self, namespace: dict) -> str:
        """
        The source to parse and show, once ``exec_source`` has run in
        ``namespace`` (the resolver is removed from it).
        """
        namespace.pop(RESOLVER, None)
        edits = list(self.literal_edits)
        for name, binding in self.object_bindings.items():
            if name in self.converted:
                edits.append((binding.magnitude, repr(self.converted[name])))
            else:
                edits.append((binding.value, repr(PLACEHOLDER + name)))
        return apply_edits(self.source, edits)

    def place_objects(self, tree: Any) -> None:
        """Puts each object input that was not converted in its line of ``tree``."""
        placed = {
            PLACEHOLDER + name: value
            for name, value in self.objects.items()
            if name not in self.converted
        }
        if not placed:
            return
        for node in walk(tree):
            if (
                isinstance(node, Constant)
                and isinstance(node.value, str)
                and node.value in placed
            ):
                node.value = placed[node.value]
                node.source_text = ""


def has_units(binding: Binding) -> bool:
    """True if ``binding`` assigns a number times units (``6 * m``, not ``6``)."""
    return binding.magnitude is not None and binding.magnitude is not binding.value


def in_registry_of(units: Any, value: Any) -> Any:
    """
    A pint quantity ``value`` made again in the unit registry of ``units``, since
    pint does not mix registries and a script usually makes its own; any other
    value unchanged.
    """
    registry = getattr(units, "_REGISTRY", None)
    if registry is None or getattr(value, "_REGISTRY", registry) is registry:
        return value
    return registry.Quantity(value.magnitude, str(value.units))


def walk(node: Any, seen: Optional[set] = None):
    """Every dataclass node in a parsed tree, through fields, deques and lists."""
    if seen is None:
        seen = set()
    if id(node) in seen:
        return
    if isinstance(node, (deque, list, tuple)):
        seen.add(id(node))
        for item in node:
            yield from walk(item, seen)
    elif dataclasses.is_dataclass(node) and not isinstance(node, type):
        seen.add(id(node))
        yield node
        for field in dataclasses.fields(node):
            yield from walk(getattr(node, field.name), seen)
    elif hasattr(node, "lines"):  # HcSequence
        seen.add(id(node))
        yield from walk(node.lines, seen)


def find_inputs(source_or_path: str | pathlib.Path) -> dict:
    """
    The candidate inputs of a script: each name whose first top-level assignment
    is a literal or a number times units, with its value in the script (only the
    number, for a number times units). The result is a template for ``inputs``.
    """
    if isinstance(source_or_path, pathlib.Path):
        source = source_or_path.read_text(encoding="utf-8")
    else:
        source = source_or_path
    found = {}
    for name, binding in first_bindings(ast.parse(source)).items():
        if not binding.is_given:
            continue
        node = binding.magnitude if binding.magnitude is not None else binding.value
        found[name] = ast.literal_eval(node)
    return found


def first_bindings(tree: ast.Module) -> dict[str, Binding]:
    """The first top-level simple assignment of each name, in source order."""
    variables = script_variables(tree)
    bindings = {}
    for stmt in tree.body:
        if not (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
        ):
            continue
        name = stmt.targets[0].id
        if name in bindings:
            continue
        magnitude = magnitude_literal(stmt.value, variables)
        bindings[name] = Binding(
            name=name,
            value=stmt.value,
            magnitude=magnitude,
            is_given=magnitude is not None or is_literal(stmt.value),
        )
    return bindings


def other_binding_line(tree: ast.Module, name: str) -> Optional[int]:
    """The line of the first assignment to ``name`` anywhere in ``tree``, if any."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id == name
            and isinstance(node.ctx, ast.Store)
        ):
            return node.lineno
    return None


def script_variables(tree: ast.Module) -> set[str]:
    """
    The names the script assigns, other than unit aliases.

    In ``b = 2 * a`` the name ``a`` may be a unit or a variable; it is a variable
    if the script assigns it. A name whose every assignment is a units-only
    expression of other units (``kN = ureg.kN``, ``kPa = kN / m**2``) is an alias
    for a unit, not a variable.
    """
    aliases = {}  # id of an assigned Name node -> the units-only value it is given
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            numbers = []
            if units_expression(node.value, numbers, scales=True) and not numbers:
                aliases[id(node.targets[0])] = node.value
    stored = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    ]
    variables = {node.id for node in stored if id(node) not in aliases}
    # An alias of a variable is a variable too, e.g. c = a * b
    changed = True
    while changed:
        changed = False
        for node in stored:
            if node.id in variables or id(node) not in aliases:
                continue
            if not units_expression(aliases[id(node)], [], True, variables):
                variables.add(node.id)
                changed = True
    return variables


def magnitude_literal(
    value: ast.expr, variables: frozenset[str] | set[str] = frozenset()
) -> Optional[ast.expr]:
    """
    The number of a number-times-units value, or None if ``value`` is not one.

    A number times units has exactly one numeric literal (optionally negated),
    and otherwise only units (attributes, and names that are not ``variables``),
    ``*``, ``/`` and ``**`` with a literal exponent. The number must multiply the
    value: a number in a divisor or the base of a power does not qualify, since
    replacing it would not scale the value by the input.
    """
    numbers = []
    if units_expression(value, numbers, scales=True, variables=variables) and (
        len(numbers) == 1
    ):
        return numbers[0]
    return None


def units_expression(
    node: ast.expr,
    numbers: list,
    scales: bool,
    variables: frozenset[str] | set[str] = frozenset(),
) -> bool:
    """
    True if ``node`` is made of units, ``*``, ``/``, ``**`` with a literal
    exponent and numbers that scale it; the numbers are appended to ``numbers``.
    """
    if is_number_node(node):
        if not scales:
            return False
        numbers.append(node)
        return True
    if isinstance(node, ast.Attribute):
        # A unit of a module or registry: si.kN, ureg.m
        return True
    if isinstance(node, ast.Name):
        return node.id not in variables
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return units_expression(
            node.left, numbers, scales, variables
        ) and units_expression(node.right, numbers, scales, variables)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return units_expression(
            node.left, numbers, scales, variables
        ) and units_expression(node.right, numbers, False, variables)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        # Units raised to a literal power, e.g. m**2
        return (
            isinstance(node.left, (ast.Name, ast.Attribute))
            and units_expression(node.left, [], False, variables)
            and is_number_node(node.right)
        )
    return False


def is_number_node(node: ast.expr) -> bool:
    """True for a numeric literal, optionally negated: ``6``, ``4.5``, ``-12``."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        node = node.operand
    return isinstance(node, ast.Constant) and is_number(node.value)


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_literal(node: ast.expr) -> bool:
    """True if ``node`` is a Python literal (a number, string, list of numbers...)."""
    try:
        ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False
    return True


def plain_number(value: Any) -> Any:
    """
    A number of another type (``numpy.float64``, ``numpy.int64``) as an ``int``
    or ``float``, if it converts exactly; any other value unchanged.
    """
    if isinstance(value, bool) or type(value) in (int, float):
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return value
        if number == value:
            return number
    return value


def literal_text(value: Any) -> Optional[str]:
    """``value`` as Python source, or None if it does not read back as ``value``."""
    text = repr(value)
    try:
        round_trips = ast.literal_eval(text) == value
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        round_trips = False
    return text if round_trips is True else None


def splice(source: str, node: ast.expr, edits: list[tuple[ast.expr, str]]) -> str:
    """
    The source text of ``node``, in parentheses, with ``edits`` (of nodes within
    it) applied.
    """
    encoded, offset = encode_with_offsets(source)
    start = offset(node.lineno, node.col_offset)
    end = offset(node.end_lineno, node.end_col_offset)
    segment = encoded[start:end]
    for inner_start, inner_end, text in sorted(
        (
            (
                offset(inner.lineno, inner.col_offset) - start,
                offset(inner.end_lineno, inner.end_col_offset) - start,
                text,
            )
            for inner, text in edits
        ),
        reverse=True,
    ):
        segment = segment[:inner_start] + text.encode() + segment[inner_end:]
    return "(" + segment.decode() + ")"


def encode_with_offsets(source: str):
    """
    ``source`` as UTF-8, and a function from an AST (line, column) position to an
    offset in it. AST columns are UTF-8 byte offsets.
    """
    encoded = source.encode()
    # Python ends lines at \n, \r\n or \r only (str.splitlines() splits at more)
    line_starts = [0] + [match.end() for match in re.finditer(rb"\r\n|\r|\n", encoded)]

    def offset(lineno: int, col: int) -> int:
        return line_starts[lineno - 1] + col

    return encoded, offset


def apply_edits(source: str, edits: list[tuple[ast.expr, str]]) -> str:
    """
    Replaces the source span of each node with its text. Node offsets are UTF-8
    byte offsets, so the edits are made on the encoded source, last edit first.
    """
    encoded, offset = encode_with_offsets(source)
    spans = [
        (
            offset(node.lineno, node.col_offset),
            offset(node.end_lineno, node.end_col_offset),
            text,
        )
        for node, text in edits
    ]
    for start, end, text in sorted(spans, reverse=True):
        encoded = encoded[:start] + text.encode() + encoded[end:]
    return encoded.decode()
