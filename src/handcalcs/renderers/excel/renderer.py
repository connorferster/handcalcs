from __future__ import annotations
import math
import os
import pathlib
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

from handcalcs.parsing.inline_nodes import FunctionCall
from handcalcs.parsing.nodes import Constant, Name
from handcalcs.parsing.null_values import NoValue
from handcalcs.parsing.operator_nodes import HcUnaryOp
from handcalcs.renderers.base import (
    PAGE_BREAK,
    BaseRenderContext,
    is_boolean,
    BaseRenderer,
    RenderContext,
    render_comment_command as base_render_comment_command,
)
from .compat import ExcelRendererIncompatibleError, incompatible
from . import demo as excel_demo
from .conditionals import render_conditional
from .evaluate import EvaluationError, ValueEvaluator
from .formulas import DEFAULT_CONSTANTS, DEFAULT_FUNCTIONS, FormulaBuilder
from .units import UNITS_MODULES, is_units_setup, unit_value
from .names import SymbolTable
from .number_formats import to_excel_number_format
from .options import (
    DEFAULT_FORMULA_FORMAT,
    DEFAULT_VALUE_FORMAT,
    merge_cell_format,
    validate_sheet_name,
)
from .rich_text import parse_markup
from .rows import (
    BlankRow,
    CalcRow,
    CommentRow,
    HeadingRow,
    PageBreakRow,
    ParamRow,
    Row,
)
from .symbolic import register_symbolic_rules, symbolic_markup
from .writer import ExcelWorkbook, build_workbook, write_sheet


class ExcelRenderer(BaseRenderer):
    """
    Renders a HandCalcs sequence as a live, formula-based Excel worksheet.

    Every calculation becomes a real Excel formula that references other rows
    through worksheet-scoped defined names, so editing an input in Excel
    recalculates the sheet.

    Options (all validated here, at instantiation):

    - ``sheet_name``: the worksheet name (Excel's naming rules apply).
    - ``value_format`` / ``formula_format``: how the value column (E) is
      styled; see "Cell formats" below.
    - ``filepath``: if given, ``complete()`` also saves the workbook there.
    - ``general_format``: the Excel number format used for format codes that
      have no exact Excel equivalent (e.g. the default ``.5g``).

    Cell formats
    ------------
    ``value_format`` and ``formula_format`` style the two kinds of cell in the
    value column, so a reader can tell at a glance which cells to edit:

    - ``value_format`` styles **input** cells: literal assignments such as
      ``a = 2`` or ``L = 300*mm``. These hold plain numbers and are the cells
      a user edits.
    - ``formula_format`` styles **formula** cells: every calculation such as
      ``x = (-b + sqrt(b**2 - 4*a*c)) / (2*a)``. A calculation forced into the
      input layout with ``# hc: -p`` still holds a formula, so it also takes
      ``formula_format``.

    Both are dicts with any of these keys:

    - ``"bold"``: ``True`` or ``False``.
    - ``"text_color"``: the font colour.
    - ``"cell_color"``: the cell's fill colour; ``None`` for no fill.

    A colour is ``"#RRGGBB"``, ``"RRGGBB"`` or an ``(r, g, b)`` tuple of ints
    from 0 to 255. Every key is optional: the keys you give are merged over the
    defaults, and the keys you leave out keep their default. The defaults are::

        value_format   = {"bold": False, "text_color": "#000000", "cell_color": "#FFF2CC"}
        formula_format = {"bold": True,  "text_color": "#000000", "cell_color": None}

    That is, inputs sit on a light-yellow fill (the common engineering
    convention for "edit me") and formulas are bold with no fill. An unknown
    key, a non-bool ``"bold"`` or a malformed colour raises ``ValueError``
    when the renderer is created. The merged result is available as the
    ``value_format`` and ``formula_format`` attributes.

    Examples::

        from handcalcs import HandCalcs
        from handcalcs.renderers.excel import ExcelRenderer

        # Defaults: yellow inputs, bold formulas.
        renderer = ExcelRenderer()

        # Blue text, bold text for inputs, keeping the default yellow fill; for
        renderer = ExcelRenderer(value_format={"text_color": "#0000FF", 'bold': True})

        # No fill on inputs; formulas on a light-green fill, not bold.
        renderer = ExcelRenderer(
            sheet_name='Calculations',
            value_format={"cell_color": None},
            formula_format={"bold": False, "cell_color": (226, 239, 218)},
            filepath='my_calc_sheet.xlsx'
        )

        # Plain sheet: no highlighting at all.
        renderer = ExcelRenderer(
            value_format={"cell_color": None},
            formula_format={"bold": False},
        )

        workbook = HandCalcs(renderer=renderer)(source)
        workbook.save("calcs.xlsx")

    ``functions`` maps Python callables to ``formulas.ExcelFunction``
    translations; extend a renderer's copy to support more functions.
    """

    name = "excel"
    # HandCalcs.demo() renders this instead of the general demo, which uses
    # loops and collections that have no worksheet form.
    demo_source = excel_demo.source

    def __init__(
        self,
        sheet_name: str = "Calculations",
        value_format: Optional[dict] = None,
        formula_format: Optional[dict] = None,
        filepath: Optional[str | pathlib.Path] = None,
        general_format: str = "General",
    ) -> None:
        super().__init__()
        self.sheet_name = validate_sheet_name(sheet_name)
        self.value_format = merge_cell_format(
            value_format, DEFAULT_VALUE_FORMAT, "value_format"
        )
        self.formula_format = merge_cell_format(
            formula_format, DEFAULT_FORMULA_FORMAT, "formula_format"
        )
        self.filepath = pathlib.Path(filepath) if filepath is not None else None
        if not isinstance(general_format, str) or not general_format:
            raise ValueError(
                "general_format must be a non-empty Excel number format string."
            )
        self.general_format = general_format
        self.functions = dict(DEFAULT_FUNCTIONS)
        self.constants = dict(DEFAULT_CONSTANTS)

    def __repr__(self) -> str:
        return f"ExcelRenderer(sheet_name={self.sheet_name!r})"

    def render_root(self, root, base_context: BaseRenderContext) -> list[Row]:
        """Render every statement into one flat list of rows."""
        base_context.global_context.excel_state = ExcelState.create(self, base_context)
        rows: list[Row] = []
        for node in root.sequence:
            rows.extend(self.render(node, base_context))
        return rows

    def complete(
        self, tree: list[Row], base_context: BaseRenderContext
    ) -> ExcelWorkbook:
        """Lay the rows out as a one-sheet workbook; save it if ``filepath`` is set."""
        workbook = build_workbook(
            tree, self.sheet_name, self.value_format, self.formula_format
        )
        if self.filepath is not None:
            self.to_file(workbook, self.filepath)
        return workbook

    def to_file(self, rendered: ExcelWorkbook, path: str | os.PathLike) -> pathlib.Path:
        """Save the workbook ``complete()`` returned to ``path`` (an .xlsx)."""
        return rendered.save(path)

    def write_sheet(self, workbook, rows: list[Row], sheet_name: Optional[str] = None):
        """
        Write ``rows`` (from ``render()``) as a new sheet of an open
        ``xlsxwriter.Workbook``, for several cells in one workbook. Names are
        worksheet-scoped, so each sheet may reuse the same variables.
        """
        sheet_name = (
            self.sheet_name if sheet_name is None else validate_sheet_name(sheet_name)
        )
        return write_sheet(
            workbook, rows, sheet_name, self.value_format, self.formula_format
        )


@dataclass
class ExcelState:
    """Per-render state carried on the global render context."""

    symbols: SymbolTable
    builder: FormulaBuilder
    evaluator: ValueEvaluator
    factors: dict  # Excel name -> display-unit-to-SI factor (rows with units)

    @classmethod
    def create(
        cls, renderer: ExcelRenderer, base_context: BaseRenderContext
    ) -> "ExcelState":
        global_ns = getattr(base_context.global_context, "global_ns", None)
        symbols = SymbolTable()
        factors: dict = {}
        builder = FormulaBuilder(
            symbols, global_ns, renderer.functions, renderer.constants, factors
        )
        return cls(symbols, builder, ValueEvaluator(global_ns), factors)


def excel_state(renderer: ExcelRenderer, base_context: BaseRenderContext) -> ExcelState:
    """The render's state, created on first use (e.g. a handler rendered alone)."""
    state = getattr(base_context.global_context, "excel_state", None)
    if state is None:
        state = ExcelState.create(renderer, base_context)
        base_context.global_context.excel_state = state
    return state


ER = ExcelRenderer
BRC = BaseRenderContext

# Python statements and blocks with no worksheet equivalent.
INCOMPATIBLE_BLOCKS = {
    "for_block": "for loops have no Excel equivalent",
    "if_block": "if blocks are only supported as complete if/elif/else trees",
    "else_block": "else blocks are only supported as part of an if/elif/else tree",
}


def _literal_value(expression: list) -> Any:
    """The value of a bare literal right-hand side (``2``, ``-1.5``, ``"a"``), else NoValue."""
    if len(expression) != 1:
        return NoValue()
    node = expression[0]
    if isinstance(node, Constant) and isinstance(node.value, (bool, int, float, str)):
        return node.value
    if (
        isinstance(node, HcUnaryOp)
        and node.symbol.strip() in ("-", "+")
        and isinstance(node.operand, Constant)
        and isinstance(node.operand.value, (int, float))
        and not isinstance(node.operand.value, bool)
    ):
        return -node.operand.value if node.symbol.strip() == "-" else node.operand.value
    return NoValue()


def _references_sheet(node: Any, symbols: SymbolTable) -> bool:
    """True if the expression reads any variable assigned on the sheet."""
    if isinstance(node, Name):
        return node.identifier in symbols
    if isinstance(node, (list, tuple, deque)):
        return any(_references_sheet(item, symbols) for item in node)
    if hasattr(node, "__dataclass_fields__"):
        return any(
            _references_sheet(getattr(node, f), symbols)
            for f in node.__dataclass_fields__
            if f not in ("type", "symbol", "pre", "post", "value")
        )
    return False


def _cached_value(state: ExcelState, expression: list, target: Name) -> Any:
    """The row's own result: re-evaluated in order, else the captured value."""
    try:
        return state.evaluator.evaluate(expression)
    except EvaluationError:
        value = target.value
        return None if isinstance(value, NoValue) else value


@ER.register("calc_line")
def render_calc_line(renderer: ER, node, base_context: BRC) -> list[Row]:
    """
    A CalcLine becomes one row: a ``ParamRow`` for a literal (or ``-p``) line,
    otherwise a ``CalcRow`` whose value cell holds a live formula.
    """
    state = excel_state(renderer, base_context)
    # The calc_line:pre rule may already have flagged a param line; an inline
    # command replaces the line context, so read the flag first.
    param_line = getattr(base_context.current, "param_line", False)
    comment = None
    if node.comment is not None:
        if node.comment.type == "inline_comment":
            comment = node.comment.content
        else:
            renderer.render(node.comment, base_context)
    context = base_context.current
    param_line = param_line or getattr(context, "param_line", False)
    try:
        targets = list(node.assigns)
        if len(targets) != 1:
            raise incompatible(
                "chained assignment (a = b = 1) has no Excel equivalent", node
            )
        target = targets[0]
        if not isinstance(target, Name):
            raise incompatible(
                "only single-name assignments can become worksheet rows "
                "(tuple unpacking and attribute/item targets are not supported)",
                node,
            )
        identifier = target.identifier
        if is_units_setup(target.value):
            # ``ureg = pint.UnitRegistry()``, ``mm = ureg.mm``: no row; a unit
            # name read later becomes its SI constant.
            return []
        expression = list(node.expression_tree)
        try:
            literal = _literal_value(expression)
            formula = None
            unit = None
            if isinstance(literal, NoValue):
                value = _cached_value(state, expression, target)
                unit = unit_value(value) or unit_value(target.value)
                if unit is not None and not _references_sheet(
                    expression, state.symbols
                ):
                    # ``L = 300 * mm``: an input of 300 in the unit column's mm.
                    cached = unit.magnitude
                else:
                    factor = unit.factor if unit is not None else 1
                    formula = "=" + state.builder.build_scaled(expression, factor)
                    cached = unit.magnitude if unit is not None else value
            else:
                value = cached = literal
            if isinstance(cached, float) and not math.isfinite(cached):
                raise incompatible(
                    f"Excel has no number for {cached!r} (infinity or NaN)", node
                )
        except ExcelRendererIncompatibleError as error:
            raise error.with_target(identifier) from None

        # Assign after building the formula: ``x = x * 2`` refers to the
        # previous version of x.
        name = state.symbols.assign(identifier)
        state.evaluator.assign(identifier, value)
        if unit is not None and unit.factor != 1:
            state.factors[name] = unit.factor
        unit_text = unit.unit if unit is not None and unit.unit else None
        number_format = to_excel_number_format(
            context.format_code, renderer.general_format
        )
        symbol = parse_markup(symbolic_markup(renderer, node.assigns, base_context))
        hidden = bool(getattr(context, "ignore", False))
        check = bool(getattr(context, "check", False)) and is_boolean(cached)

        if param_line or formula is None:
            row: Row = ParamRow(
                name=name,
                symbol=symbol,
                value=cached,
                number_format=number_format,
                formula=formula,
                unit=unit_text,
                comment=comment,
                hidden=hidden,
                check=check,
            )
        else:
            row = CalcRow(
                name=name,
                symbol=symbol,
                symbolic=parse_markup(
                    symbolic_markup(renderer, expression, base_context)
                ),
                formula=formula,
                cached=cached,
                number_format=number_format,
                unit=unit_text,
                comment=comment,
                hidden=hidden,
                check=check,
            )
        rows: list[Row] = [row]
        if getattr(context, "line_break", False):
            rows.append(BlankRow())
        return rows
    finally:
        base_context.line_context = RenderContext.sparse()


@ER.register("calcs_block")
def render_calcs_block(renderer: ER, node, base_context: BRC) -> list[Row]:
    rows: list[Row] = []
    for line in node.lines:
        rows.extend(renderer.render(line, base_context))
    return rows


@ER.register("params_block")
def render_params_block(renderer: ER, node, base_context: BRC) -> list[Row]:
    """Each line of a ``;`` or ``# hc: -h`` params block is its own ParamRow."""
    rows: list[Row] = []
    for line in node.lines:
        base_context.line_context.param_line = True
        rows.extend(renderer.render(line, base_context))
    return rows


@ER.register("comments_block")
def render_comments_block(renderer: ER, node, base_context: BRC) -> list[Row]:
    """Consecutive comment lines become one paragraph row."""
    texts = []
    for line in node.lines:
        rendered = renderer.render(line, base_context)
        if (
            line.type == "comment_line"
            and isinstance(rendered, str)
            and rendered.strip()
        ):
            texts.append(rendered.strip())
    return [CommentRow(" ".join(texts))] if texts else []


@ER.register("heading")
def render_heading(renderer: ER, node, base_context: BRC) -> list[Row]:
    return [HeadingRow(node.content, node.heading_level)]


@ER.register("comment_command")
def render_comment_command(renderer: ER, node, base_context: BRC) -> list[Row]:
    """Updates the global context (e.g. ``-f``); ``-b`` inserts a blank row."""
    rendered = base_render_comment_command(renderer, node, base_context)
    if rendered == PAGE_BREAK:
        return [PageBreakRow()]
    return [BlankRow()] if rendered else []


@ER.register("expr_line")
def render_expr_line(renderer: ER, node, base_context: BRC) -> list[Row]:
    """A bare string (docstring) becomes a comment row; other expressions raise."""
    tree = list(node.expression_tree)
    if (
        len(tree) == 1
        and isinstance(tree[0], Constant)
        and isinstance(tree[0].value, str)
    ):
        return [CommentRow(tree[0].value.strip())]
    if (
        len(tree) == 1
        and isinstance(tree[0], FunctionCall)
        and _is_units_call(tree[0], excel_state(renderer, base_context))
    ):
        return []  # e.g. si.environment('structural')
    raise incompatible(
        "an expression statement (e.g. print(...)) has no worksheet equivalent; "
        "only assignments become rows",
        node,
    )


def _is_units_call(node: FunctionCall, state: ExcelState) -> bool:
    """A call into a units library, e.g. ``si.environment('structural')``."""
    function, _ = state.builder.resolve_function(node)
    return function is not None and is_units_setup(function)


@ER.register("ignored_line")
def render_ignored_line(renderer: ER, node, base_context: BRC) -> list[Row]:
    return []


@ER.register("import")
def render_import(renderer: ER, node, base_context: BRC) -> list[Row]:
    """
    Imports of ``math`` (its functions map to Excel) and of the units
    libraries (pint, forallpeople) are skipped; others raise.
    """
    if node.import_from:
        modules = [node.import_from_module]
    else:
        modules = [name.identifier for name in node.names]
    allowed = ("math",) + UNITS_MODULES
    for module in modules:
        if (module or "").split(".")[0] not in allowed:
            raise incompatible(
                f"importing '{module}' has no Excel equivalent "
                "(only 'math', 'pint' and 'forallpeople' may be imported)",
                node,
            )
    return []


@ER.register("elif_block")
def render_elif_block(renderer: ER, node, base_context: BRC) -> list[Row]:
    """An if/elif/else tree: one IF-formula row per assigned variable."""
    return render_conditional(
        renderer, node, excel_state(renderer, base_context), base_context
    )


def _incompatible_block(renderer: ER, node, base_context: BRC) -> list[Row]:
    raise incompatible(INCOMPATIBLE_BLOCKS[node.type], node)


for _block_type in INCOMPATIBLE_BLOCKS:
    ER.register(_block_type)(_incompatible_block)


@ER.register("no_value")
@ER.register("not_implemented")
def render_unparsed_statement(renderer: ER, node, base_context: BRC) -> list[Row]:
    raise incompatible(
        "a statement handcalcs does not parse (e.g. a function or class definition, "
        "augmented assignment 'x += 1', while, with or try) has no worksheet equivalent",
        node,
    )


register_symbolic_rules(ExcelRenderer)
