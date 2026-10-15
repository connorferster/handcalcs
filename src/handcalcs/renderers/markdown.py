from handcalcs.renderers.base import BaseRenderContext
from handcalcs.renderers.latex import LatexRenderer, import_source

# Node type imports only used for typing
from handcalcs.parsing.line_nodes import (
    Import,
    Heading,
    CommentLine,
)

BRC = BaseRenderContext


class MarkdownRenderer(LatexRenderer):
    """
    Renders a HandCalcs sequence as Markdown prose with LaTeX math, for Jupyter-type
    front-ends that typeset ``$...$`` / ``$$...$$`` with MathJax or KaTeX.

    Everything inside math is inherited from LatexRenderer; this class only
    replaces the text-mode structure (headings, paragraphs, imports) and the
    structural tokens below. See ``markdown_renderer_plan.md``.
    """
    name = 'markdown'

    MATH_OPEN = "$$\n\\begin{aligned}\n"
    MATH_CLOSE = "\n\\end{aligned}\n$$"
    PARAGRAPH = ""
    ROW_SEP = "<br>"

    def paragraph(self, text: str) -> str:
        return text


MR = MarkdownRenderer


## TEXT-MODE HANDLERS

@MR.register('heading')
def render_heading(renderer: MR, node: Heading, base_context: BRC) -> str:
    return f"{'#' * node.heading_level} {node.content}"


@MR.register('comment_line')
def render_comment_line(renderer: MR, node: CommentLine, base_context: BRC) -> str:
    return node.content


@MR.register('import')
def render_import(renderer: MR, node: Import, base_context: BRC) -> str:
    """An import renders as a single code span of the Python source."""
    return f"`{import_source(node)}`"
