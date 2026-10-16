"""
ReportLabRenderer: renders handcalcs to a ReportLab story.

``complete`` returns ``{"stylesheet": StyleSheet1, "story": list[Flowable]}``.
The renderer builds on ``HTMLRenderer``: ReportLab's paragraph markup accepts
the inline HTML that renderer emits (``<sub>``, ``<sup>``, ``&le;``), so the
inline rules (Greek letters, subscripts, operator symbols) are inherited as-is.
Line- and block-level output is overridden: handlers return markers
(``markers.py``) and ``join_item`` turns them into flowables once the nesting
depth is known.
"""
from __future__ import annotations

import itertools
import re
from typing import Optional
from xml.sax.saxutils import escape

from reportlab.lib.styles import StyleSheet1
from reportlab.platypus import Flowable, HRFlowable, KeepTogether, Paragraph, Spacer

from handcalcs.renderers.base import BaseRenderContext, RenderContext, render_condition
from handcalcs.renderers.html import HTMLRenderer

from .flowables import BreakingParagraph, CalcBlock, CalcLine, Chip, DepthGuides, ParamGrid
from .fonts import Fonts, missing_fonts, register_families
from .markers import CalcComponents, Grid, Tagged
from .styles import Metrics, Palette, build_stylesheet

# Node type imports only used for typing
from handcalcs.parsing.nodes import Constant
from handcalcs.parsing.inline_nodes import InlineComment
from handcalcs.parsing.line_nodes import CommentLine, ExprLine, Heading, Import
from handcalcs.parsing.block_nodes import CommentsBlock, ElseBlock, ForBlock, IfBlock

BRC = BaseRenderContext

class _Placed:
    """A flowable that a nested ``join_items`` call has already placed at its depth."""

    __slots__ = ("flowable",)

    def __init__(self, flowable: Flowable) -> None:
        self.flowable = flowable


def _unwrap(flowable: Flowable) -> Flowable:
    while isinstance(flowable, DepthGuides):
        flowable = flowable.content
    return flowable


# Heading bookmark keys must be unique across every render in a document.
_ANCHORS = itertools.count(1)


def plain_text(markup: str) -> str:
    """Paragraph markup with its tags removed (for bookmark titles)."""
    return re.sub(r"<[^>]+>", "", markup).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def code_spans(text: str, font: str) -> str:
    """Set each pair of `backticks` in prose in the monospaced font."""
    return re.sub(r"`([^`]+)`", rf'<font name="{font}">\1</font>', text)


class ReportLabRenderer(HTMLRenderer):
    name = "reportlab"

    def __init__(
        self,
        stylesheet: Optional[StyleSheet1] = None,
        palette: Palette = Palette(),
        fonts: Fonts = Fonts(),
        base_size: float = 9.5,
    ) -> None:
        super().__init__()
        missing = missing_fonts(fonts)
        if missing:
            raise ValueError(
                "These fonts are not registered with ReportLab: "
                f"{', '.join(missing)}. ymprint registers them at start-up; outside "
                "ymprint call ym_handcalcs.fonts.ensure_dejavu_registered() first."
            )
        register_families(fonts)
        self.palette = palette
        self.fonts = fonts
        self.metrics = Metrics(base_size)
        self.stylesheet = stylesheet if stylesheet is not None else build_stylesheet(
            palette, fonts, base_size
        )

    # -- Completion ---------------------------------------------------------

    def complete(self, tree: list, base_context: BaseRenderContext) -> dict:
        story = self.join_items(tree, 0, base_context)
        return {"stylesheet": self.stylesheet, "story": story}

    def create_context(self, **config_kwargs) -> BaseRenderContext:
        return BaseRenderContext(RenderContext(**config_kwargs), RenderContext.sparse())

    # -- Join: master list -> flowables -------------------------------------

    def join_item(self, item, depth: int, base_context: BaseRenderContext) -> list[Flowable]:
        """
        ReportLab counterpart of ``HTMLRenderer.join_item``: same master-list
        dispatch, but each line becomes a flowable. The story stays flat;
        ``depth`` is carried by the flowables themselves.
        """
        return [self.at_depth(flowable, depth) for flowable in self.item_flowables(item, depth, base_context)]

    def item_flowables(self, item, depth: int, base_context: BaseRenderContext) -> list[Flowable]:
        # Leaf items become flowables here (``join_item`` places them at their
        # depth); blocks recurse through ``join_items``, which places their own
        # leaves, so the depth wrapper is never applied twice.
        if isinstance(item, Grid):
            return [self.grid_flowable(item, depth)]
        if not item:
            return []
        if isinstance(item, str):
            # A one-shot line-break directive is a bare newline.
            if not item.strip("\n"):
                return [Spacer(1, self.metrics.base_size * 0.6)]
            if isinstance(item, Tagged):
                return self.tagged_flowables(item, depth)
            return [self.line_flowable(item, depth)]
        if isinstance(item, CalcComponents):
            return [self.calc_flowable(item, depth)]
        # A block is ``[header, body]`` -- detected by its body being a list.
        if isinstance(item[-1], list):
            header, body = item[0], item[-1]
            if not (isinstance(header, str) and header.strip()):
                return self.group(self.join_items(body, depth, base_context))
            return [
                self.header_flowable(header, depth),
                *(_Placed(f) for f in self.join_items(body, depth + 1, base_context)),
            ]
        if all(isinstance(part, str) for part in item):
            line = base_context.current.space.join(item)
            return [self.line_flowable(line, depth)] if line.strip() else []
        # A mixed list (e.g. a grid wrapped by ``render_block_body``): join each part.
        return [_Placed(f) for f in self.join_items(item, depth, base_context)]

    def join_items(self, items: list, depth: int, base_context: BaseRenderContext) -> list:
        return self.merge_calc_runs(super().join_items(items, depth, base_context))

    def merge_calc_runs(self, flowables: list) -> list:
        """
        Merge each run of consecutive calc lines at one depth into a
        ``CalcBlock``, so the run is one table aligned on ``=``.
        """
        merged: list = []
        run: list[CalcLine] = []
        run_wrapper = None

        def flush():
            if run:
                block = CalcBlock(run)
                if run_wrapper is None:
                    merged.append(block)
                else:
                    merged.append(DepthGuides(block, run_wrapper.depth, run_wrapper.indent, run_wrapper.colors))
                run.clear()

        for flowable in flowables:
            wrapper = flowable if isinstance(flowable, DepthGuides) else None
            line = wrapper.content if wrapper is not None else flowable
            if isinstance(line, CalcLine):
                depth = wrapper.depth if wrapper is not None else 0
                run_depth = run_wrapper.depth if run_wrapper is not None else 0
                if run and depth != run_depth:
                    flush()
                run.append(line)
                run_wrapper = wrapper
                continue
            flush()
            merged.append(flowable)
        flush()
        return merged

    # A headerless group (a run of calc lines) this short is kept on one page.
    keep_together_max = 6

    def group(self, placed: list[Flowable]) -> list:
        lines = sum(len(f.lines) if isinstance(f, CalcBlock) else 1 for f in map(_unwrap, placed))
        if 2 <= lines <= self.keep_together_max:
            return [_Placed(KeepTogether(placed))]
        return [_Placed(f) for f in placed]

    def at_depth(self, flowable: Flowable, depth: int) -> Flowable:
        """Indent a leaf flowable to ``depth`` and draw its indent guides."""
        if isinstance(flowable, _Placed):
            return flowable.flowable
        if depth <= 0:
            return flowable
        guides = [self.palette.guide(level) for level in range(1, depth + 1)]
        return DepthGuides(flowable, depth, self.metrics.indent, guides)

    # -- Flowable builders (overridable) ------------------------------------

    def style(self, name: str):
        return self.stylesheet[name]

    def line_flowable(self, text: str, depth: int) -> Flowable:
        return Paragraph(text, self.style("hcCalc"))

    def calc_markup(self, calc: CalcComponents) -> str:
        """
        ``target = sym = num = result  (comment)`` as paragraph markup. When the
        line has a substitution (three or more columns), the result is set bold
        in the accent colour on a faint highlight. The comment is muted italic.
        """
        columns = list(calc.columns)
        if len(columns) >= 3:
            columns[-1] = self.result_markup(columns[-1])
        text = " = ".join(columns)
        if calc.comment:
            text += f"\u2003{calc.comment}"
        return text

    def result_markup(self, text: str) -> str:
        p = self.palette
        return f'<font color="{p.accent}" backColor="{p.highlight}"><b>{text}</b></font>'

    def comment_markup(self, text: str) -> str:
        text = code_spans(text, self.fonts.mono.italic)
        return f"{self.comment_open}{text}</i></font>"

    def calc_flowable(self, calc: CalcComponents, depth: int) -> Flowable:
        return self.calc_line(calc.columns, calc.comment, forced_grid=False)

    def calc_line(self, columns: list[str], comment: Optional[str], forced_grid: bool) -> CalcLine:
        styles = self.cell_styles()
        styles["line"] = self.style("hcCalc")
        return CalcLine(
            columns, comment, forced_grid=forced_grid, styles=styles,
            result_markup=self.result_markup, table_style=self.style("hcCalcGrid"),
            pad=self.metrics.base_size * 0.3,
        )

    def header_flowable(self, header: str, depth: int) -> Flowable:
        marker = f'<font color="{self.palette.accent}">\u25B8</font>\u2002'
        return BreakingParagraph(
            marker + header, self.style("hcBlockHeader"), background=self.palette.color("accent_soft")
        )

    def tagged_flowables(self, item: Tagged, depth: int) -> list[Flowable]:
        if item.kind == "heading":
            return self.heading_flowables(item)
        if item.kind == "prose":
            return [Paragraph(code_spans(str(item), self.fonts.mono.regular), self.style("hcComment"))]
        if item.kind == "import":
            return [Chip(Paragraph(str(item), self.style("hcImport")), self.palette.color("code_bg"))]
        return [Paragraph(str(item), self.style("hcNote"))]

    def heading_flowables(self, item: Tagged) -> list[Flowable]:
        """
        A heading paragraph, followed by an accent rule for levels 1 and 2. The
        paragraph carries ``hc_outline = (key, text, level)`` so a doc template
        can add a PDF bookmark for it (``build_pdf`` does).
        """
        level = min(max(item.level, 1), 3)
        heading = Paragraph(str(item), self.style(f"hcH{level}"))
        heading.hc_outline = (f"hc-h-{next(_ANCHORS)}", plain_text(str(item)), level - 1)
        if level == 3:
            return [heading]
        rule = HRFlowable(
            width="100%",
            thickness=1.5 if level == 1 else 0.5,
            color=self.palette.color("accent" if level == 1 else "rule"),
            spaceBefore=1,
            spaceAfter=self.metrics.base_size * 0.45,
            hAlign="LEFT",
        )
        rule.keepWithNext = 1
        return [heading, rule]

    def cell_styles(self) -> dict:
        return {
            "right": self.style("hcCellRight"),
            "center": self.style("hcCellCenter"),
            "left": self.style("hcCellLeft"),
            "value": self.style("hcCellValue"),
            "comment": self.style("hcCellComment"),
        }

    def grid_flowable(self, grid: Grid, depth: int) -> Flowable:
        m = self.metrics
        if grid.kind == "params":
            cells = [cell for row in grid.rows for cell in row]
            cols = max((len(row) for row in grid.rows), default=1)
            return ParamGrid(
                cells, cols, self.cell_styles(), self.style("hcParams"),
                gap=m.base_size * 1.6, pad=m.base_size * 0.3,
                zebra=self.palette.color("zebra"),
                space_before=m.gap * 2, space_after=m.gap,
            )
        # A ``# hc: -m`` calc: ``[target, '=', sym]``, ``['', '=', num]``, ... The
        # last value may end with the inline comment.
        rows = [[str(ident), str(eq), str(val)] for ident, eq, val in grid.rows]
        columns = [rows[0][0]] + [row[2] for row in rows]
        value, sep, comment = columns[-1].rpartition(f" {self.comment_open}")
        comment_markup = None
        if sep:
            columns[-1] = value
            comment_markup = f"{self.comment_open}{comment}"
        return self.calc_line(columns, comment_markup, forced_grid=True)

    @property
    def comment_open(self) -> str:
        """Opening markup of every rendered inline comment (see ``render_inline_comment``)."""
        return f'<font color="{self.palette.muted}"><i>'

    # -- Grid hooks called by the base handlers -----------------------------

    def format_param_grid(self, rows: list, base_context: BaseRenderContext) -> Grid:
        return Grid("params", rows)

    def format_calc_grid(self, rows: list, base_context: BaseRenderContext) -> Grid:
        return Grid("calc", rows)


RLR = ReportLabRenderer


## LINE AND BLOCK HANDLERS

@RLR.register("heading")
def render_heading(renderer: RLR, node: Heading, base_context: BRC) -> Tagged:
    return Tagged(escape(node.content), "heading", node.heading_level)


@RLR.register("comment_line")
def render_comment_line(renderer: RLR, node: CommentLine, base_context: BRC) -> str:
    return escape(node.content)


@RLR.register("comments_block")
def render_comments_block(renderer: RLR, node: CommentsBlock, base_context: BRC) -> str:
    # A run of comment lines is prose: one paragraph, lines joined by a space.
    # Comment commands render to '' and drop out.
    lines = [renderer.render(line, base_context) for line in node.lines]
    texts = [line for line in lines if isinstance(line, str) and line.strip()]
    if not texts:
        return ""
    return Tagged(" ".join(texts), "prose")


@RLR.register("import")
def render_import(renderer: RLR, node: Import, base_context: BRC) -> Tagged:
    names = ", ".join(
        f"{name.identifier} as {name.value}" if name.value is not None else name.identifier
        for name in node.names
    )
    if node.import_from:
        dots = "." * (node.import_from_level or 0)
        module = f"{dots}{node.import_from_module or ''}"
        text = f"from {module} import {names}"
    else:
        text = f"import {names}"
    return Tagged(escape(text), "import")


@RLR.register("calc_line:post")
def mark_calc_components(renderer: RLR, rendered, node, base_context: BRC):
    # Tag a rendered line's component list so ``join_item`` can style its columns.
    if isinstance(rendered, list) and rendered and not isinstance(rendered, CalcComponents):
        return CalcComponents(rendered)
    return rendered


@RLR.register("expr_line:post")
def mark_expr_components(renderer: RLR, rendered, node: ExprLine, base_context: BRC):
    tree = node.expression_tree
    if len(tree) == 1 and isinstance(tree[0], Constant) and isinstance(tree[0].value, str):
        # A docstring / bare string statement is prose, not a calc.
        return Tagged(escape(tree[0].value), "prose") if isinstance(rendered, list) else rendered
    return mark_calc_components(renderer, rendered, node, base_context)


@RLR.register("constant:post")
def escape_string_constant(renderer: RLR, rendered, node: Constant, base_context: BRC):
    # String values are user text: escape them for paragraph markup.
    if isinstance(node.value, str) and isinstance(rendered, str):
        return escape(rendered)
    return rendered


@RLR.register("inline_comment")
def render_inline_comment(renderer: RLR, node: InlineComment, base_context: BRC) -> str:
    # Comments are styled here (muted italic), so they read the same in calc
    # lines, multi-line grids and params grids.
    context = base_context.current
    return renderer.comment_markup(f"{context.lpar}{escape(node.content)}{context.rpar}")


@RLR.register("elif_block:post")
def mark_no_condition_note(renderer: RLR, rendered, node, base_context: BRC):
    # "No conditions were satisfied ..." is a note, not a calc line.
    if isinstance(rendered, str) and rendered:
        return Tagged(escape(rendered), "note")
    return rendered


## BLOCK HEADERS

def keyword(renderer: RLR, text: str) -> str:
    return f'<font color="{renderer.palette.accent}"><b>{text}</b></font>'


@RLR.register("header:if_block")
def if_block_header(renderer: RLR, node: IfBlock, base_context: BRC) -> str:
    sym_expr = render_condition(renderer, node.test, base_context, "sym")
    num_expr = render_condition(renderer, node.test, base_context, "num")
    return f"{keyword(renderer, 'Since')} ({sym_expr}) \u2192 ({num_expr}) {keyword(renderer, 'is True:')}"


@RLR.register("header:else_block")
def else_block_header(renderer: RLR, node: ElseBlock, base_context: BRC) -> str:
    return keyword(renderer, "Otherwise:")


@RLR.register("header:for_block")
def for_block_header(renderer: RLR, node: ForBlock, base_context: BRC) -> str:
    base_context.line_context.current_mode = "sym"
    target = renderer.render(node.assigns[0], base_context)
    iterable = renderer.render(node.iterator[0], base_context)
    return f"{keyword(renderer, 'Iterating over each')} {target} {keyword(renderer, 'in')} {iterable}:"


## COMPARISONS

@RLR.register("gt_op:post")
@RLR.register("lt_op:post")
@RLR.register("gte_op:post")
@RLR.register("lte_op:post")
@RLR.register("eq_op:post")
@RLR.register("neq_op:post")
def space_comparison(renderer: RLR, rendered, node, base_context: BRC) -> str:
    # Space comparison operators like the arithmetic ones (``a < b``, not
    # ``a<b``); ``!=`` becomes ``≠``. ``breaking`` treats them as relations.
    symbol = "\u2260" if rendered == "!=" else rendered
    return f" {symbol} "
