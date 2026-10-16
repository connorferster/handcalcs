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

from typing import Optional
from xml.sax.saxutils import escape

from reportlab.lib.styles import StyleSheet1
from reportlab.platypus import Flowable, Paragraph, Spacer

from handcalcs.renderers.base import BaseRenderContext, RenderContext
from handcalcs.renderers.html import HTMLRenderer

from .fonts import Fonts, missing_fonts, register_families
from .markers import CalcComponents, Grid, Tagged
from .styles import Metrics, Palette, build_stylesheet

# Node type imports only used for typing
from handcalcs.parsing.line_nodes import CommentLine, Heading, Import
from handcalcs.parsing.block_nodes import CommentsBlock

BRC = BaseRenderContext


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
        return Paragraph(text, self.style("hcBody"))

    def calc_flowable(self, calc: CalcComponents, depth: int) -> Flowable:
        return Paragraph(" ".join(calc), self.style("hcCalc"))

    def header_flowable(self, header: str, depth: int) -> Flowable:
        return Paragraph(header, self.style("hcBlockHeader"))

    def tagged_flowables(self, item: Tagged, depth: int) -> list[Flowable]:
        if item.kind == "heading":
            level = min(max(item.level, 1), 3)
            return [Paragraph(str(item), self.style(f"hcH{level}"))]
        if item.kind == "prose":
            return [Paragraph(str(item), self.style("hcComment"))]
        if item.kind == "import":
            return [Paragraph(str(item), self.style("hcImport"))]
        return [Paragraph(str(item), self.style("hcNote"))]

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
@RLR.register("expr_line:post")
def mark_calc_components(renderer: RLR, rendered, node, base_context: BRC):
    # Tag a rendered line's component list so ``join_item`` can style its columns.
    if isinstance(rendered, list) and rendered and not isinstance(rendered, CalcComponents):
        return CalcComponents(rendered)
    return rendered
