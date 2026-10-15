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

    # A math group is a single physical line: Jupyter front-ends extract math
    # from the raw text before parsing Markdown, so a multi-line group inside a
    # blockquote would carry the inner lines' ``> `` prefixes into the LaTeX.
    MATH_OPEN = "$$\\begin{aligned}"
    MATH_CLOSE = "\\end{aligned}$$"
    ROW_SEP = " \\\\ "
    MATH_SKIP = ""
    PARAGRAPH = ""
    # A one-shot line break is a spacer paragraph, the counterpart of \medskip.
    LINE_BREAK = "&nbsp;"
    # The body of a nested block (if/for/def) is quoted once per level.
    BLOCK_PREFIX = ">"

    def join_item(self, item, depth: int, base_context: BRC) -> list[str]:
        """
        As ``LatexRenderer.join_item``, except that:

        - the body of a ``[header, body]`` block is a blockquote (see ``quote``)
          rather than a ``list`` environment;
        - an all-string line made of complete math groups (consecutive params
          grids in a block body arrive this way) emits each group as its own
          paragraph, since two ``$$`` groups cannot share a line.
        """
        if (item and isinstance(item, list) and all(isinstance(part, str) for part in item)
                and any(part.startswith(self.MATH_OPEN) for part in item)):
            return [f"{part}\n\n" for part in item if part.strip()]
        if item and isinstance(item, list) and isinstance(item[-1], list):
            header, body = item[0], item[-1]
            is_math = bool(body) and body[0] == self.MATH_OPEN
            if not is_math and isinstance(header, str) and header.strip():
                return [
                    f"{self.paragraph(header)}\n\n",
                    *self.quote(self.join_items(body, depth + 1, base_context)),
                ]
        return super().join_item(item, depth, base_context)

    def quote(self, chunks: list[str]) -> list[str]:
        """
        Quote a joined block body: every line gets one BLOCK_PREFIX, so a block
        nested in a quoted body ends up quoted twice. Blank lines between the
        body's paragraphs are quoted too (a bare ``>``), which keeps the quote
        continuous and stops a ``> text`` line after a ``> > text`` line from
        being absorbed into the inner quote by lazy continuation. The quote ends
        with an unquoted blank line, so the following text is not absorbed either.
        """
        text = "".join(chunks).strip("\n")
        if not text:
            return []
        prefix = self.BLOCK_PREFIX
        lines = [f"{prefix} {line}" if line else prefix for line in text.split("\n")]
        return ["\n".join(lines) + "\n\n"]

    def paragraph(self, text: str) -> str:
        return text

    def math_group(self, rows: list[str]) -> str:
        """Wrap pre-joined ``aligned`` rows in MATH_OPEN/MATH_CLOSE, on one line."""
        return f"{self.MATH_OPEN} {self.ROW_SEP.join(rows)} {self.MATH_CLOSE}"


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
