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
from reportlab.platypus import Flowable, HRFlowable, Paragraph, Spacer

from handcalcs.renderers.base import BaseRenderContext, RenderContext
from handcalcs.renderers.html import HTMLRenderer

from .flowables import Chip
from .fonts import Fonts, missing_fonts, register_families
from .markers import CalcComponents, Grid, Tagged
from .styles import Metrics, Palette, build_stylesheet

# Node type imports only used for typing
from handcalcs.parsing.nodes import Constant
from handcalcs.parsing.inline_nodes import InlineComment
from handcalcs.parsing.line_nodes import CommentLine, ExprLine, Heading, Import
from handcalcs.parsing.block_nodes import CommentsBlock

BRC = BaseRenderContext

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
                return self.join_items(body, depth, base_context)
            return [
                self.header_flowable(header, depth),
                *self.join_items(body, depth + 1, base_context),
            ]
        if all(isinstance(part, str) for part in item):
            line = base_context.current.space.join(item)
            return [self.line_flowable(line, depth)] if line.strip() else []
        # A mixed list (e.g. a grid wrapped by ``render_block_body``): join each part.
        return self.join_items(item, depth, base_context)

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
            text += f"\u2003{self.comment_markup(calc.comment)}"
        return text

    def result_markup(self, text: str) -> str:
        p = self.palette
        return f'<font color="{p.accent}" backColor="{p.highlight}"><b>{text}</b></font>'

    def comment_markup(self, text: str) -> str:
        text = code_spans(text, self.fonts.mono.italic)
        return f'<font color="{self.palette.muted}"><i>{text}</i></font>'

    def calc_flowable(self, calc: CalcComponents, depth: int) -> Flowable:
        return Paragraph(self.calc_markup(calc), self.style("hcCalc"))

    def header_flowable(self, header: str, depth: int) -> Flowable:
        return Paragraph(header, self.style("hcBlockHeader"))

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

    def grid_flowable(self, grid: Grid, depth: int) -> Flowable:
        lines = [" ".join(str(part) for part in row if part) for row in grid.rows]
        return Paragraph("<br/>".join(lines), self.style("hcBody"))

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
    context = base_context.current
    return f"{context.lpar}{escape(node.content)}{context.rpar}"


@RLR.register("elif_block:post")
def mark_no_condition_note(renderer: RLR, rendered, node, base_context: BRC):
    # "No conditions were satisfied ..." is a note, not a calc line.
    if isinstance(rendered, str) and rendered:
        return Tagged(escape(rendered), "note")
    return rendered
