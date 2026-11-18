"""
SymPy substitution: ``x = f  # hc: -y`` runs and renders as ``x = <the expression f
holds>``, so a SymPy expression worked out symbolically becomes a calculation with
the values its symbols have when the line runs::

    a, b = sp.symbols("a b")
    f = sp.integrate(a**2 + b * a, a)    # a**3/3 + a**2*b/2
    a = 5
    b = 10
    x = f  # hc: -y                      # runs as x = a**3/3 + b*a**2/2

The line is rewritten just before it runs (see ``run_staged``): ``x`` holds the
number the render shows, not the expression. A standalone ``# hc: -y`` does the
same for every following ``name = name`` line whose right-hand name holds a SymPy
expression, until ``# hc: sympy = False``.

The expression is written as Python source with the names of the functions and
constants it uses (``sqrt``, ``sin``, ``pi``), from the namespace (``from math
import sqrt``) or through the ``math`` module (``import math``). A SymPy function
with no Python equivalent (``Integral``, ``Piecewise``) is an error, as is a
symbol whose name is not a Python name or (on a top-level line) still holds a
SymPy object when the line runs.

SymPy is not a dependency: an object is recognised by its ``__sympy__``
attribute, and SymPy is imported only to print one.
"""

from __future__ import annotations

import ast
import builtins
import io
import math
import tokenize
from dataclasses import dataclass, field
from types import ModuleType
from typing import Callable, Iterable, Mapping, Optional

from .comment_parser import is_comment_command, parse_kwargs, split_commands
from .commands import CommentCommandError, parse_commands
from .inputs import apply_edits

__all__ = [
    "SympySubstitutionError",
    "Substitution",
    "has_sympy_commands",
    "is_sympy",
    "run_staged",
    "substitute",
    "to_python",
]


class SympySubstitutionError(ValueError):
    """A ``# hc: -y`` line that cannot be substituted."""


# SymPy function -> the Python function that computes it.
MATH_FUNCTIONS = {
    "sqrt": "sqrt",
    "exp": "exp",
    "log": "log",
    "sin": "sin",
    "cos": "cos",
    "tan": "tan",
    "asin": "asin",
    "acos": "acos",
    "atan": "atan",
    "atan2": "atan2",
    "sinh": "sinh",
    "cosh": "cosh",
    "tanh": "tanh",
    "asinh": "asinh",
    "acosh": "acosh",
    "atanh": "atanh",
    "floor": "floor",
    "ceiling": "ceil",
    "factorial": "factorial",
    "gamma": "gamma",
    "erf": "erf",
}
BUILTIN_FUNCTIONS = {"Abs": "abs", "Max": "max", "Min": "min"}
MATH_CONSTANTS = {"pi": math.pi, "e": math.e, "inf": math.inf}


def is_sympy(value) -> bool:
    """True for a SymPy object (without importing SymPy)."""
    return getattr(value, "__sympy__", False) is True


def from_sympy(value) -> bool:
    """True for a SymPy object or function, e.g. ``sympy.sqrt`` or ``sympy.pi``."""
    module = getattr(value, "__module__", None) or type(value).__module__ or ""
    return is_sympy(value) or module.split(".")[0] == "sympy"


def expression_of(value):
    """
    The expression a substituted name holds: an equation's right-hand side, and
    the one solution in a one-item list (``sp.solve(...)``). None for anything else.
    """
    if isinstance(value, (list, tuple)) and len(value) == 1:
        value = value[0]
    if not is_sympy(value):
        return None
    rhs = getattr(value, "rhs", None)
    if type(value).__name__ == "Equality" and rhs is not None:
        value = rhs
    if not getattr(value, "is_Atom", False) and not getattr(value, "args", None):
        return None
    return value


# --- Writing an expression as Python ---


class Names:
    """
    How the rewritten line names a function or constant: by its own name when
    the namespace has it (and it is not SymPy's), else through the ``math``
    module.
    """

    def __init__(self, lookup: Callable[[str], object]):
        self.lookup = lookup
        self.used: set[str] = set()

    def get(self, name: str) -> object:
        try:
            return self.lookup(name)
        except KeyError:
            return None

    def __call__(self, name: str) -> str:
        if name in BUILTIN_FUNCTIONS.values():
            return name
        value = self.get(name)
        if value is not None and not from_sympy(value):
            constant = MATH_CONSTANTS.get(name)
            if constant is None and callable(value):
                self.used.add(name)
                return name
            if constant is not None and value == constant:
                self.used.add(name)
                return name
        module = self.get("math")
        if isinstance(module, ModuleType) and module.__name__ == "math":
            self.used.add("math")
            return f"math.{name}"
        kind = "constant" if name in MATH_CONSTANTS else "function"
        raise SympySubstitutionError(
            f"The expression uses the {kind} '{name}': import it before this line "
            f"(from math import {name}) or import math."
        )


def check_supported(expr) -> None:
    """Raise for a part of ``expr`` that has no Python equivalent here."""
    import sympy

    allowed = (
        sympy.Add,
        sympy.Mul,
        sympy.Pow,
        sympy.Symbol,
        sympy.Number,
        sympy.NumberSymbol,
        sympy.Max,
        sympy.Min,
    )
    constants = ("ImaginaryUnit", "Infinity", "NegativeInfinity", "Exp1", "Pi")
    for node in sympy.preorder_traversal(expr):
        name = type(node).__name__
        if isinstance(node, sympy.NumberSymbol) and name not in constants:
            raise SympySubstitutionError(
                f"The expression uses SymPy's constant {node}, which has no Python "
                "equivalent here."
            )
        if isinstance(node, allowed) or name in constants:
            continue
        if isinstance(node, sympy.Function) and (
            name in MATH_FUNCTIONS or name in BUILTIN_FUNCTIONS
        ):
            continue
        raise SympySubstitutionError(
            f"The expression uses SymPy's {name}, which has no Python equivalent "
            "handcalcs can run (evaluate it with SymPy first, e.g. .doit())."
        )


def to_python(expr, names: Callable[[str], str]) -> str:
    """
    ``expr`` as Python source, naming functions and constants with ``names``
    (e.g. ``Names``). Raises SympySubstitutionError for a part with no Python
    equivalent and for a symbol that is not a Python name.
    """
    from sympy import S
    from sympy.printing.str import StrPrinter

    check_supported(expr)

    class PythonPrinter(StrPrinter):
        def _print_Symbol(self, symbol):
            if not symbol.name.isidentifier():
                raise SympySubstitutionError(
                    f"The symbol '{symbol.name}' is not a Python name, so it can't "
                    "be given a value: name it like a variable (sp.Symbol('M_f'))."
                )
            return symbol.name

        def _print_Function(self, function):
            name = type(function).__name__
            python = MATH_FUNCTIONS.get(name) or BUILTIN_FUNCTIONS[name]
            args = ", ".join(self._print(arg) for arg in function.args)
            return f"{names(python)}({args})"

        def _print_Max(self, expr):
            return f"max({', '.join(self._print(arg) for arg in expr.args)})"

        def _print_Min(self, expr):
            return f"min({', '.join(self._print(arg) for arg in expr.args)})"

        def _print_Pow(self, power, rational=False):
            if power.exp is S.Half:
                return f"{names('sqrt')}({self._print(power.base)})"
            if power.exp == -S.Half:
                return f"1/{names('sqrt')}({self._print(power.base)})"
            return super()._print_Pow(power, rational)

        def _print_Pi(self, expr):
            return names("pi")

        def _print_Exp1(self, expr):
            return names("e")

        def _print_ImaginaryUnit(self, expr):
            return "1j"

        def _print_Infinity(self, expr):
            return names("inf")

        def _print_NegativeInfinity(self, expr):
            return f"-{names('inf')}"

    return PythonPrinter({"order": "none"}).doprint(expr)


# --- Finding the lines ---


@dataclass
class Marks:
    """
    The lines ``# hc: -y`` applies to: ``inline`` lines carry it themselves;
    ``regions`` maps the line of each standalone ``-y``/``sympy = False`` to its
    setting, which holds until the next one.
    """

    inline: set[int] = field(default_factory=set)
    regions: list[tuple[int, bool]] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.inline) or any(on for _, on in self.regions)

    def region_at(self, line: int) -> bool:
        setting = False
        for start, on in self.regions:
            if start > line:
                break
            setting = on
        return setting


def sympy_setting(comment: str) -> Optional[bool]:
    """The ``sympy`` setting of a ``# hc:`` comment, or None if it has none."""
    stripped = comment.lstrip("# ")
    if not is_comment_command(stripped):
        return None
    try:
        try:
            commands = parse_kwargs(stripped)
        except (SyntaxError, NameError):
            commands = parse_commands(stripped, split_commands(stripped))
    except CommentCommandError:
        return None  # the parser reports it when the line is rendered
    return commands.get("sympy")


def find_marks(source: str) -> Marks:
    marks = Marks()
    if "hc:" not in source:
        return marks
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError):
        return marks
    lines = source.splitlines()
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        setting = sympy_setting(token.string)
        if setting is None:
            continue
        line, column = token.start
        if lines[line - 1][:column].strip():
            if setting:
                marks.inline.add(line)
        else:
            marks.regions.append((line, bool(setting)))
    return marks


def has_sympy_commands(source: str) -> bool:
    """True if ``# hc: -y`` (inline or standalone) appears in ``source``."""
    return bool(find_marks(source))


# --- Rewriting ---


@dataclass
class Substitution:
    """One rewritten line: its statement's first line and the names it now uses."""

    line: int
    names: frozenset


def assignments(tree: ast.AST) -> Iterable[ast.Assign]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            yield node


def substitute(
    source: str,
    lookup: Callable[[str], object],
    *,
    within: Optional[tuple[int, int]] = None,
    check_lines: frozenset = frozenset(),
    marks: Optional[Marks] = None,
) -> tuple[str, list[Substitution]]:
    """
    ``source`` with each ``# hc: -y`` line's right-hand name replaced by the
    expression it holds (looked up with ``lookup``, which raises KeyError for a
    name it doesn't have). Only the statements starting ``within`` the given
    first and last lines are rewritten, if given. Lines keep their numbers.

    On the lines in ``check_lines`` (top-level lines about to run), each symbol
    of the expression must have a value that is not a SymPy object. A line in a
    block isn't checked: its symbols may get their values in the block.
    """
    marks = find_marks(source) if marks is None else marks
    if not marks:
        return source, []
    tree = ast.parse(source)
    edits = []
    substitutions = []
    for node in assignments(tree):
        line = node.lineno
        if within is not None and not within[0] <= line <= within[1]:
            continue
        inline = line in marks.inline
        if not inline and not marks.region_at(line):
            continue
        if not isinstance(node.value, ast.Name):
            if inline:
                raise SympySubstitutionError(
                    f"Line {line}: '# hc: -y' substitutes the SymPy expression a "
                    "name holds, so the line must be 'name = expression_name' "
                    f"(not '{ast.unparse(node)}')."
                )
            continue
        name = node.value.id
        try:
            value = lookup(name)
        except KeyError:
            if inline:
                raise SympySubstitutionError(
                    f"Line {line}: '{name}' is not defined when the line runs; "
                    "'# hc: -y' needs the SymPy expression to exist before then."
                ) from None
            continue
        expr = expression_of(value)
        if expr is None or (not inline and not getattr(expr, "free_symbols", None)):
            if inline:
                raise SympySubstitutionError(
                    f"Line {line}: '{name}' holds a {type(value).__name__}, not a "
                    "SymPy expression, so '# hc: -y' has nothing to substitute."
                )
            continue
        symbols = sorted(symbol.name for symbol in expr.free_symbols)
        if line in check_lines:
            check_symbol_values(line, name, symbols, lookup)
        names = Names(lookup)
        try:
            text = to_python(expr, names)
        except SympySubstitutionError as error:
            raise SympySubstitutionError(f"Line {line}: {error}") from None
        edits.append((node.value, text))
        substitutions.append(Substitution(line, frozenset(symbols) | names.used))
    if not edits:
        return source, []
    return apply_edits(source, edits), substitutions


def check_symbol_values(
    line: int, name: str, symbols: list[str], lookup: Callable[[str], object]
) -> None:
    for symbol in symbols:
        try:
            value = lookup(symbol)
        except KeyError:
            raise SympySubstitutionError(
                f"Line {line}: '{name}' uses the symbol '{symbol}', which has no "
                "value when the line runs: assign it one before this line."
            ) from None
        if from_sympy(value):
            raise SympySubstitutionError(
                f"Line {line}: '{name}' uses the symbol '{symbol}', which is still "
                "a SymPy symbol when the line runs: assign it a value before this line."
            )


def namespace_lookup(*namespaces: Mapping) -> Callable[[str], object]:
    """A lookup through ``namespaces`` in order, then ``builtins``."""

    def lookup(name: str) -> object:
        for namespace in namespaces:
            if name in namespace:
                return namespace[name]
        if hasattr(builtins, name):
            return getattr(builtins, name)
        raise KeyError(name)

    return lookup


# --- Running in stages ---


def statement_chunks(tree: ast.Module, total_lines: int, marks: Marks):
    """
    The top-level statements in runs to execute one after the other, as
    ``(first_line, last_line, rewrite)``: a statement with a ``# hc: -y`` line
    in it (``rewrite``) runs on its own, the others together.
    """
    starts = []
    for stmt in tree.body:
        first = min(
            [stmt.lineno, *(d.lineno for d in getattr(stmt, "decorator_list", []))]
        )
        marked = any(
            node.lineno in marks.inline or marks.region_at(node.lineno)
            for node in assignments(stmt)
        )
        starts.append((first, stmt.end_lineno, marked))
    chunks: list[list] = []
    for index, (first, last, marked) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else total_lines
        if marked or not chunks or chunks[-1][2]:
            chunks.append([first, end, marked])
        else:
            chunks[-1][1] = end
    if chunks:
        chunks[0][0] = 1
    return [tuple(chunk) for chunk in chunks]


def run_staged(
    source: str,
    namespace: dict,
    run_chunk: Callable[[str], bool],
    on_substitution: Optional[Callable[[Substitution], None]] = None,
) -> str:
    """
    Run ``source`` in ``namespace`` one top-level statement at a time, rewriting
    each ``# hc: -y`` line just before its statement runs. ``run_chunk`` runs a
    piece of the source, given with the lines above it blanked as comments so
    that its line numbers are the source's, and returns False to stop (an error).
    ``on_substitution`` is told the names each rewritten line now uses. Returns
    the rewritten source.
    """
    marks = find_marks(source)
    tree = ast.parse(source)
    total = len(source.splitlines())
    lookup = namespace_lookup(namespace)
    top_level_lines = frozenset(stmt.lineno for stmt in tree.body)
    for first, last, rewrite in statement_chunks(tree, total, marks):
        if rewrite:
            source, substitutions = substitute(
                source,
                lookup,
                within=(first, last),
                check_lines=top_level_lines,
                marks=marks,
            )
            if on_substitution is not None:
                for substitution in substitutions:
                    on_substitution(substitution)
        lines = source.splitlines(keepends=True)
        chunk = "#\n" * (first - 1) + "".join(lines[first - 1 : last])
        if not run_chunk(chunk):
            break
    return source
