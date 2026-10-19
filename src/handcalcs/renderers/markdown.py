import re

from handcalcs.renderers.base import BaseRenderContext
from handcalcs.renderers.latex import LatexRenderer, OPERATOR_SYMBOLS, import_source

# Node type imports only used for typing
from handcalcs.parsing.nodes import Constant
from handcalcs.parsing.inline_nodes import InlineComment
from handcalcs.parsing.line_nodes import (
    Import,
    Heading,
    CommentLine,
)

BRC = BaseRenderContext


# Markdown punctuation that can change meaning anywhere in a line. CommonMark
# allows a backslash before any ASCII punctuation, so over-escaping is harmless.
# '$' is included because Jupyter front-ends read a bare '$' in prose as math.
MARKDOWN_SPECIAL = set("\\*_[]<>#|~$&")
# Line starts that open a list, thematic break or setext underline.
MARKDOWN_LINE_START = re.compile(r"^(\d+)([.)])|^([-+=])")


def markdown_escape(text: str) -> str:
    """Backslash-escape the Markdown specials in a plain-text string."""
    return "".join(f"\\{char}" if char in MARKDOWN_SPECIAL else char for char in text)


def markdown_prose(text: str) -> str:
    """
    Escape a comment written as prose (headings, comment paragraphs) for
    Markdown. A pair of backticks is a code span already, so it passes through
    untouched; an unpaired backtick is escaped. A leading list marker, rule or
    setext underline character is escaped so a comment cannot become one.
    """
    segments = text.split("`")
    unpaired = ""
    if len(segments) % 2 == 0:
        unpaired = f"\\`{markdown_escape(segments.pop())}"
    escaped = [
        segment if idx % 2 else markdown_escape(segment)
        for idx, segment in enumerate(segments)
    ]
    prose = "`".join(escaped) + unpaired
    return MARKDOWN_LINE_START.sub(
        lambda m: f"{m[1]}\\{m[2]}" if m[1] else f"\\{m[3]}", prose, count=1
    )


# Characters that cannot appear raw inside ``\text{}`` in both MathJax 3 and
# KaTeX (KaTeX reads '%' as a comment, '&' as a column break, and rejects '^',
# '_' and '#' in text mode; MathJax has no text-mode \textasciicircum etc.).
# Each is emitted in math mode between ``\text{}`` runs instead. '<' and '>'
# are included so the raw Markdown never holds something that looks like an
# HTML tag.
MATH_TEXT_SPECIAL = {
    "\\": "\\backslash ",
    "{": "\\{",
    "}": "\\}",
    "$": "\\$",
    "%": "\\%",
    "&": "\\&",
    "#": "\\#",
    "_": "\\_",
    "^": "\\hat{}",
    "~": "\\tilde{}",
    "<": "\\lt ",
    ">": "\\gt ",
}


def math_text(text: str, wrapper: str = "\\text") -> str:
    """
    Typeset plain text inside math: runs of ordinary characters become
    ``\\text{...}`` (or ``wrapper``) groups and each special character its
    math-mode symbol, e.g. ``mm^4`` -> ``\\text{mm}\\hat{}\\text{4}``.
    """
    pieces, run = [], []
    for char in text:
        if char in MATH_TEXT_SPECIAL:
            if run:
                pieces.append(f"{wrapper}{{{''.join(run)}}}")
                run = []
            pieces.append(MATH_TEXT_SPECIAL[char])
        else:
            run.append(char)
    if run:
        pieces.append(f"{wrapper}{{{''.join(run)}}}")
    return "".join(pieces).rstrip()


def math_prose(text: str) -> str:
    """
    ``math_text`` for a comment written as prose: a pair of backticks becomes
    ``\\texttt{}`` (its content still escaped); an unpaired backtick is kept.
    """
    segments = text.split("`")
    if len(segments) % 2 == 0:
        segments[-2:] = [f"{segments[-2]}`{segments[-1]}"]
    return "".join(
        math_text(segment, "\\texttt" if idx % 2 else "\\text")
        for idx, segment in enumerate(segments)
        if segment
    )


class MarkdownRenderer(LatexRenderer):
    """
    Renders a HandCalcs sequence as Markdown prose with LaTeX math, for Jupyter-type
    front-ends that typeset ``$...$`` / ``$$...$$`` with MathJax or KaTeX.

    It is the default renderer of the ``%%render`` cell magic (the
    ``jupyter_renderer`` config option); its output is shown with
    ``IPython.display.Markdown``.

    Math is inherited from LatexRenderer, with a few changes for MathJax and
    KaTeX: comparisons use ``\\lt``/``\\gt``, and text inside math (inline
    comments, strings) goes through ``math_text``. The text-mode structure is
    replaced:

    - headings are ``#`` headings, comment lines are plain paragraphs and
      imports are code spans, all Markdown-escaped (``markdown_prose``);
    - each calc group is one ``$$\\begin{aligned} ... \\end{aligned}$$`` on a
      single physical line, with ``\\\\`` between the rows;
    - a ``# hc: -b`` line break is an ``&nbsp;`` spacer paragraph;
    - the body of an if/for/def block is a blockquote, with one ``>`` per
      nesting level. Blank lines inside a body are quoted too, and every quote
      ends with an unquoted blank line, so Markdown's lazy continuation never
      pulls the following text into a deeper quote (see ``quote``).

    See ``markdown_renderer_plan.md`` for the reasoning behind each rule.
    """

    name = "markdown"

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
    # A raw '<' before a letter in the Markdown source can be taken for an HTML
    # tag by a front-end that does not protect math, so comparisons use \lt/\gt.
    OPERATOR_SYMBOLS = OPERATOR_SYMBOLS | {"lt_op": " \\lt ", "gt_op": " \\gt "}

    def join_item(self, item, depth: int, base_context: BRC) -> list[str]:
        """
        As ``LatexRenderer.join_item``, except that:

        - the body of a ``[header, body]`` block is a blockquote (see ``quote``)
          rather than a ``list`` environment;
        - an all-string line made of complete math groups (consecutive params
          grids in a block body arrive this way) emits each group as its own
          paragraph, since two ``$$`` groups cannot share a line.
        """
        if (
            item
            and isinstance(item, list)
            and all(isinstance(part, str) for part in item)
            and any(part.startswith(self.MATH_OPEN) for part in item)
        ):
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


@MR.register("heading")
def render_heading(renderer: MR, node: Heading, base_context: BRC) -> str:
    level = min(node.heading_level, 6)
    return f"{'#' * level} {markdown_prose(node.content)}"


@MR.register("comment_line")
def render_comment_line(renderer: MR, node: CommentLine, base_context: BRC) -> str:
    return markdown_prose(node.content)


@MR.register("import")
def render_import(renderer: MR, node: Import, base_context: BRC) -> str:
    """An import renders as a single code span of the Python source."""
    return f"`{import_source(node)}`"


## MATH-MODE TEXT


@MR.register("inline_comment")
def render_inline_comment(renderer: MR, node: InlineComment, base_context: BRC) -> str:
    """
    ``\\quad`` + the parenthesised comment as math text. It still starts with
    COMMENT_OPEN, which ``join_math_row`` and ``format_param_grid`` look for.
    """
    return f"\\quad{math_prose(f'({node.content})')}"


@MR.register("constant")
def render_constant(renderer: MR, node: Constant, base_context: BRC) -> str:
    """
    A string is shown in straight double quotes as math text (MathJax does not
    turn TeX's ``\\`\\``...``''`` into curly quotes); other constants render
    as in LaTeX.
    """
    if isinstance(node.value, str):
        return math_text(f'"{node.value}"')
    return LatexRenderer.node_handlers["constant"](renderer, node, base_context)
