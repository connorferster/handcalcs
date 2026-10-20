"""
Partial inputs: rendering one calculation script with different given values.

``bind_inputs`` rewrites the source so that the first top-level assignment of each
input name assigns the input instead. The rewritten source is then executed and
parsed exactly like any other script, so the document shows the input values and
everything computed from them. The keys of the inputs dict designate the inputs;
the script needs no comment commands.

When the input is a plain number and the assignment is a number times units
(``w = 4.5 * kN / m``), only the number is replaced, so the script's units are kept.
"""

import ast
import pathlib
import re
from dataclasses import dataclass
from typing import Optional

__all__ = ["bind_inputs", "find_inputs"]


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
    a TypeError for a value that cannot be written as a Python literal.
    """
    tree = ast.parse(source)
    bindings = first_bindings(tree)
    edits = []
    unknown = []
    for name, value in inputs.items():
        binding = bindings.get(name)
        if binding is None:
            line = other_binding_line(tree, name)
            if line is not None:
                raise ValueError(
                    f"The input '{name}' cannot be bound: it is only assigned on line "
                    f"{line} inside a block or function, by an augmented assignment "
                    "or by unpacking. Inputs bind to a top-level 'name = value' "
                    "assignment."
                )
            unknown.append(name)
            continue
        if not binding.is_given and not allow_computed:
            raise ValueError(
                f"'{name}' is computed on line {binding.value.lineno}; pass "
                "allow_computed=True to replace the calculation with the input."
            )
        text = literal_text(name, value)
        if binding.magnitude is not None and is_number(value):
            edits.append((binding.magnitude, text))
        else:
            edits.append((binding.value, text))
    if unknown and strict:
        raise KeyError(
            f"The source never assigns the input(s) {', '.join(map(repr, unknown))}. "
            "Check the names, or pass strict=False to ignore inputs the source "
            "does not use."
        )
    return apply_edits(source, edits)


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


def literal_text(name: str, value) -> str:
    """``value`` as Python source, checking that it reads back as the same value."""
    text = repr(value)
    try:
        round_trips = ast.literal_eval(text) == value
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        round_trips = False
    if not round_trips:
        raise TypeError(
            f"The input '{name}' ({type(value).__name__}) cannot be written as a "
            "Python literal. Inputs must be numbers, strings, booleans, None, or "
            "lists, tuples and dicts of these."
        )
    return text


def apply_edits(source: str, edits: list[tuple[ast.expr, str]]) -> str:
    """
    Replaces the source span of each node with its text. Node offsets are UTF-8
    byte offsets, so the edits are made on the encoded source, last edit first.
    """
    encoded = source.encode()
    # Python ends lines at \n, \r\n or \r only (str.splitlines() splits at more)
    line_starts = [0] + [match.end() for match in re.finditer(rb"\r\n|\r|\n", encoded)]

    def offset(lineno: int, col: int) -> int:
        return line_starts[lineno - 1] + col

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
