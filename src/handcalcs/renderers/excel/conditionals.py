"""
If/elif/else trees -> one ``IF`` formula row per assigned variable.

An ``ElifBlock`` is normalized into a ``Conditional``: a list of branches,
each a test (``None`` for ``else``) and a body of assignments and nested
conditionals. Every variable assigned anywhere in the tree gets one row,
in first-appearance order::

    =IF(test_1, expr_1, IF(test_2, expr_2, else_expr))

Nested ``IF`` is used rather than ``IFS`` so the sheet works in every Excel
version and in LibreOffice.

**Scoping.** Python runs a branch top to bottom, so a name read inside a
branch means the value assigned *earlier on that branch path*, else the value
from before the tree. Each expression is therefore built against a
``Scope``: the names as they were before the tree, overridden by the new rows
of variables already assigned on the path. Because a variable's new row picks
the same branch as the expression reading it, ``if c: a = 1; b = a * 2``
gives ``b`` a formula that references ``a``'s row and still evaluates right.

**Fallbacks** (D8): a branch that does not assign ``v`` keeps the previous
version of ``v``, or ``NA()`` when there is none.

**Compatibility.** Branch bodies may hold single-name assignments, nested
if/elif/else trees, comment lines and comment commands (which have no effect
inside a tree). A variable assigned twice in the same branch body raises, as
does anything else.

The symbolic column (D9) is piecewise: one line per case, nested tests joined
with "and"::

    1, if hw/tw ≤ 1100/√Fy
    2, if hw/tw ≤ 1700/√Fy
    4, otherwise
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

from handcalcs.parsing.block_nodes import ElifBlock, ElseBlock
from handcalcs.parsing.line_nodes import CalcLine
from handcalcs.parsing.nodes import Name
from handcalcs.parsing.null_values import NoValue
from .compat import ExcelRendererIncompatibleError, incompatible
from .evaluate import EvaluationError
from .formulas import Formula, FormulaBuilder, scale_formula
from .names import SymbolTable
from .number_formats import to_excel_number_format
from .rich_text import escape, parse_markup
from .rows import CalcRow, Row
from handcalcs.renderers.identifiers import identifier_options
from .symbolic import symbolic_identifier, symbolic_markup
from .units import unit_value

NA = "NA()"
NA_DISPLAY = "#N/A"

# Lines that group or annotate and carry no assignment of their own.
_TRANSPARENT = ("calcs_block", "params_block")
_IGNORED = ("comments_block", "comment_line", "comment_command")


@dataclass
class Assignment:
    target: str
    line: CalcLine


@dataclass
class Branch:
    test: Any  # None for else
    body: list = field(default_factory=list)  # Assignment | Conditional


@dataclass
class Conditional:
    branches: list[Branch]

    @property
    def has_else(self) -> bool:
        return bool(self.branches) and self.branches[-1].test is None

    def variables(self) -> list[str]:
        """Assigned variables, in first-appearance order."""
        found: list[str] = []
        for branch in self.branches:
            for item in branch.body:
                names = (
                    [item.target] if isinstance(item, Assignment) else item.variables()
                )
                found.extend(name for name in names if name not in found)
        return found

    def assigns(self, variable: str) -> bool:
        return variable in self.variables()


# --- normalizing the parsed tree ---


def _clauses(node: Any) -> list:
    """The if/elif/else clauses of an ElifBlock or a raw (nested) IfBlock."""
    if isinstance(node, ElifBlock):
        return list(node.lines)
    return list(ElifBlock.from_if_tree(node).lines)


def build_conditional(node: Any) -> Conditional:
    """Normalize an ElifBlock (or nested IfBlock) and check it is compatible."""
    branches = []
    for clause in _clauses(node):
        test = None if isinstance(clause, ElseBlock) else clause.test
        branch = Branch(test)
        _collect(clause.lines, branch)
        branches.append(branch)
    return Conditional(branches)


def _collect(lines: Any, branch: Branch) -> None:
    for line in lines:
        kind = getattr(line, "type", type(line).__name__)
        if kind in _TRANSPARENT:
            _collect(line.lines, branch)
        elif kind in _IGNORED:
            continue
        elif kind == "calc_line":
            branch.body.append(Assignment(_target(line), line))
        elif kind in ("elif_block", "if_block"):
            branch.body.append(build_conditional(line))
        else:
            raise incompatible(
                f"'{kind}' inside an if/elif/else tree has no Excel equivalent; "
                "branches may only assign variables",
                line,
            )
    direct = [item.target for item in branch.body if isinstance(item, Assignment)]
    for name in direct:
        if direct.count(name) > 1:
            raise incompatible(
                f"'{name}' is assigned more than once in one branch of an if/elif/else tree"
            )


def _target(line: CalcLine) -> str:
    targets = list(line.assigns)
    if len(targets) != 1 or not isinstance(targets[0], Name):
        raise incompatible(
            "only single-name assignments are supported inside an if/elif/else tree",
            line,
        )
    return targets[0].identifier


# --- scoped name lookup ---


class Scope:
    """
    The names visible at one point of a branch path, in the SymbolTable
    interface the FormulaBuilder uses (``in`` and ``lookup``).
    """

    def __init__(
        self, before: dict[str, str], overrides: Optional[dict[str, str]] = None
    ) -> None:
        self.before = before
        self.overrides = dict(overrides or {})

    def __contains__(self, identifier: str) -> bool:
        return identifier in self.overrides or identifier in self.before

    def lookup(self, identifier: str, node: Any = None) -> str:
        if identifier in self.overrides:
            return self.overrides[identifier]
        if identifier in self.before:
            return self.before[identifier]
        return SymbolTable().lookup(identifier, node)  # raises the standard error

    def with_name(self, identifier: str, name: str) -> "Scope":
        return Scope(self.before, {**self.overrides, identifier: name})


class ConditionalRenderer:
    """Builds the rows for one top-level if/elif/else tree."""

    def __init__(self, renderer, state, base_context) -> None:
        self.renderer = renderer
        self.state = state
        self.base_context = base_context
        self.before = state.symbols.names
        self.new_names: dict[str, str] = {}

    def builder(self, scope: Scope) -> FormulaBuilder:
        base = self.state.builder
        return FormulaBuilder(
            scope, base.global_ns, base.functions, base.constants, base.factors
        )

    # --- formulas ---

    def formula(
        self, conditional: Conditional, variable: str, scope: Scope, fallback: str
    ) -> str:
        """``IF(...)`` text for ``variable`` over the tree, nested innermost-last."""
        text = fallback
        for branch in reversed(conditional.branches):
            value = self.branch_formula(branch, variable, scope, fallback)
            if branch.test is None:
                text = value
            else:
                test = self.builder(scope).build(branch.test)
                text = f"IF({test},{value},{text})"
        return text

    def branch_formula(
        self, branch: Branch, variable: str, scope: Scope, fallback: str
    ) -> str:
        current = fallback
        for item in branch.body:
            if isinstance(item, Assignment):
                if item.target == variable:
                    current = self.builder(scope).build(item.line.expression_tree)
                scope = scope.with_name(item.target, self.new_names[item.target])
            else:
                if item.assigns(variable):
                    current = self.formula(item, variable, scope, current)
                for name in item.variables():
                    scope = scope.with_name(name, self.new_names[name])
        return current

    # --- piecewise display ---

    def cases(
        self, conditional: Conditional, variable: str, fallback: str
    ) -> list[tuple[str, list[str]]]:
        """``(value markup, [condition markups])`` per case, in order."""
        found = []
        for branch in conditional.branches:
            condition = [] if branch.test is None else [self.markup([branch.test])]
            for value, inner in self.branch_cases(branch, variable, fallback):
                found.append((value, condition + inner))
        if not conditional.has_else:
            found.append((fallback, []))
        return found

    def branch_cases(
        self, branch: Branch, variable: str, fallback: str
    ) -> list[tuple[str, list[str]]]:
        current = [(fallback, [])]
        for item in branch.body:
            if isinstance(item, Assignment) and item.target == variable:
                current = [(self.markup(item.line.expression_tree), [])]
            elif isinstance(item, Conditional) and item.assigns(variable):
                expanded = []
                for value, condition in current:
                    for inner_value, inner in self.cases(item, variable, value):
                        expanded.append((inner_value, condition + inner))
                current = expanded
        return current

    def markup(self, nodes: Any) -> str:
        return symbolic_markup(self.renderer, list(nodes), self.base_context)

    def piecewise(self, conditional: Conditional, variable: str) -> str:
        previous = self.before.get(variable)
        fallback = (
            symbolic_identifier(
                variable, identifier_options(self.renderer, self.base_context)
            )
            if previous
            else escape(NA_DISPLAY)
        )
        lines = []
        for value, condition in self.cases(conditional, variable, fallback):
            if condition:
                lines.append(f"{value},  if {' and '.join(condition)}")
            else:
                lines.append(f"{value},  otherwise")
        return "\n".join(lines)

    # --- cached values (Python's own run of the tree) ---

    def run(self, conditional: Conditional) -> None:
        """Execute the taken path on the evaluator, so later rows see its values."""
        evaluator = self.state.evaluator
        for branch in conditional.branches:
            if branch.test is not None and not evaluator.evaluate(branch.test):
                continue
            for item in branch.body:
                if isinstance(item, Assignment):
                    evaluator.assign(
                        item.target, evaluator.evaluate(item.line.expression_tree)
                    )
                else:
                    self.run(item)
            return

    # --- rows ---

    def rows(self, conditional: Conditional) -> list[Row]:
        variables = conditional.variables()
        lines = _assignment_lines(conditional)
        for variable in variables:
            self.new_names[variable] = self.state.symbols.assign(variable)

        # Values first: a row's unit factor must be known before any formula
        # that references the row is built.
        evaluator = self.state.evaluator
        try:
            self.run(conditional)
        except EvaluationError:
            for v in variables:
                evaluator.assign(v, _captured(lines[v]))
        # A variable the taken path left unassigned, with no earlier value, is
        # #N/A in Excel: no cached value.
        values = {v: evaluator.values.get(v) for v in variables}
        units = {}
        for v in variables:
            try:
                units[v] = unit_value(values[v])
            except ExcelRendererIncompatibleError as error:
                raise error.with_target(v) from None
            if units[v] is not None and units[v].factor != 1:
                self.state.factors[self.new_names[v]] = units[v].factor

        formulas = {}
        scope = Scope(self.before)
        for variable in variables:
            try:
                previous = self.before.get(variable)
                fallback = (
                    self.builder(scope).name(Name(variable)).text if previous else NA
                )
                text = self.formula(conditional, variable, scope, fallback)
            except ExcelRendererIncompatibleError as error:
                raise error.with_target(variable) from None
            unit = units[variable]
            if unit is not None:
                text = scale_formula(Formula(text), unit.factor).text
            formulas[variable] = "=" + text

        context = self.base_context.current
        number_format = to_excel_number_format(
            context.format_code, self.renderer.general_format
        )
        rows: list[Row] = []
        for variable in variables:
            unit = units[variable]
            rows.append(
                CalcRow(
                    name=self.new_names[variable],
                    symbol=parse_markup(
                        symbolic_identifier(
                            variable,
                            identifier_options(self.renderer, self.base_context),
                        )
                    ),
                    symbolic=parse_markup(self.piecewise(conditional, variable)),
                    formula=formulas[variable],
                    cached=unit.magnitude if unit is not None else values[variable],
                    number_format=number_format,
                    unit=(unit.unit or None) if unit is not None else None,
                    comment=_first_comment(lines[variable]),
                )
            )
        return rows


def _assignment_lines(conditional: Conditional) -> dict[str, list[CalcLine]]:
    found: dict[str, list[CalcLine]] = {}
    for branch in conditional.branches:
        for item in branch.body:
            if isinstance(item, Assignment):
                found.setdefault(item.target, []).append(item.line)
            else:
                for name, lines in _assignment_lines(item).items():
                    found.setdefault(name, []).extend(lines)
    return found


def _first_comment(lines: list[CalcLine]) -> Optional[str]:
    for line in lines:
        comment = line.comment
        if comment is not None and comment.type == "inline_comment" and comment.content:
            return comment.content
    return None


def _captured(lines: list[CalcLine]) -> Any:
    """The parser's captured (end-of-cell) value, the last resort for caching."""
    value = lines[0].assigns[0].value
    return None if isinstance(value, NoValue) else value


def render_conditional(renderer, node: Any, state, base_context) -> list[Row]:
    """The rows for an if/elif/else tree (one IF-formula row per variable)."""
    conditional = build_conditional(node)
    return ConditionalRenderer(renderer, state, base_context).rows(conditional)
