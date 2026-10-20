import colorsys
import re
from html import escape
from collections import deque
from typing import Optional, Any
from handcalcs.renderers.base import (
    BaseRenderer,
    RenderContext,
    render_condition,
    infix_binop,
    BaseRenderContext,
    ROOT_SYMBOLS,
    math_call_name,
    postfix_factorial,
)

from handcalcs.renderers.identifiers import (
    GREEK_UNICODE,
    Symbol,
    identifier_options,
    is_identifier,
    parse_identifier,
)

# Node type imports only used for typing
from handcalcs.parsing.nodes import HcNode, Name, Constant
from handcalcs.parsing.operator_nodes import AddOp, HcBinOp, HcCompOp
from handcalcs.parsing.inline_nodes import Attribute, InlineComment, FunctionCall
from handcalcs.parsing.line_nodes import Import, Heading, CommentLine
from handcalcs.parsing.block_nodes import (
    IfBlock,
    ElseBlock,
    CommentsBlock,
    CalcsBlock,
    ForBlock,
)

# The default theme colour ("petrol").
DEFAULT_THEME = "#0B5F66"

# Ancestors that mark a dark host page: JupyterLab / Notebook 7 dark themes, VS
# Code's dark and high-contrast notebook themes, and the ``data-theme="dark"``
# convention of most Sphinx themes. ``prefers-color-scheme`` is deliberately not
# used: a light Jupyter theme on a dark OS would pick up the dark colours.
DARK_HOSTS = (
    '[data-jp-theme-light="false"]',
    ".vscode-dark",
    ".vscode-high-contrast",
    '[data-theme="dark"]',
)


def _rgb(color: str) -> tuple[float, float, float]:
    color = color.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", color):
        raise ValueError(f"theme_color must be a '#RRGGBB' hex colour, not {color!r}")
    return tuple(int(color[k : k + 2], 16) / 255 for k in (0, 2, 4))


def _hls(hue: float, light: float, sat: float) -> str:
    r, g, b = colorsys.hls_to_rgb(hue % 1.0, light, min(sat, 1.0))
    return "#" + "".join(f"{round(c * 255):02X}" for c in (r, g, b))


def theme_variables(theme_color: str) -> dict[str, str]:
    """
    The CSS custom properties derived from one dark theme colour: the theme is
    the accent, and the three indent-guide colours keep its hue for the first
    level and turn it by +210 and +40 degrees for the next two. A lighter accent
    (``--hc-accent-dark``) is used for text on dark host pages.
    """
    rgb = _rgb(theme_color)
    hue, _, sat = colorsys.rgb_to_hls(*rgb)
    return {
        "--hc-accent": "#" + "".join(f"{round(c * 255):02X}" for c in rgb),
        "--hc-accent-dark": _hls(hue, 0.70, sat * 0.55),
        "--hc-guide-1": _hls(hue, 0.63, sat * 0.37),
        "--hc-guide-2": _hls(hue + 210 / 360, 0.68, sat * 0.60),
        "--hc-guide-3": _hls(hue + 40 / 360, 0.72, sat * 0.27),
    }


class HTMLRenderer(BaseRenderer):
    """
    Renders a calculation as a self-contained HTML fragment for Jupyter, VS Code
    or any web page.

    Fonts, text colour and headings are left to the host page. On top of that,
    one theme colour (``theme_color``, default petrol ``#0B5F66``) gives the
    calculation a quiet visual structure: each result is highlighted, inline
    comments are muted, imports sit in small code chips, block headers (``Since
    ... is True:``, ``Iterating over ...``) are tinted callouts, params grids sit
    on a tinted panel, multi-line calcs carry an accent bar, and nested block
    bodies get coloured indent guides. Backgrounds are translucent tints of the
    theme, so they work on light and dark pages alike.

    Every colour is a CSS custom property on ``.handcalcs`` (``--hc-accent``,
    ``--hc-guide-1`` to ``--hc-guide-3``, ``--hc-tint``, ``--hc-muted``, ...), so
    a host stylesheet can restyle the output without changing the renderer.
    """

    name = "html"

    def __init__(self, theme_color: str = DEFAULT_THEME) -> None:
        super().__init__()
        self.theme_color = theme_color
        self.theme = theme_variables(theme_color)

    # One scoped stylesheet owns ALL vertical rhythm and indentation. Emitted
    # once by ``complete``; every rule except the table rules uses ``:where()``
    # so it contributes zero specificity and a host page's own styles win. ``--hc-gap`` and
    # ``--hc-indent`` are the two knobs everything else references.
    # Leads a continuation row of a multi-line calc (see ``format_calc_grid``).
    CONTINUATION_INDENT = "&emsp;&emsp;"
    STYLE = (
        ".handcalcs{"
        "--hc-gap:0.35em;--hc-indent:1.5em;--hc-param-gap:2em;--hc-eq-gap:0.3em;"
        "--hc-accent-text:var(--hc-accent);"
        "--hc-tint:color-mix(in srgb,var(--hc-accent) 9%,transparent);"
        "--hc-highlight:color-mix(in srgb,var(--hc-accent) 12%,transparent);"
        "--hc-muted:color-mix(in srgb,currentColor 60%,transparent);"
        "--hc-chip:color-mix(in srgb,currentColor 6%,transparent);"
        "display:flex;flex-direction:column;gap:var(--hc-gap);"
        "line-height:1.6;font-variant-numeric:tabular-nums;}"
        ".handcalcs :where(.hc-block,.hc-body){"
        "display:flex;flex-direction:column;gap:var(--hc-gap);}"
        # A nested body is indented with an indent guide: a thin vertical line
        # under the header's marker, one colour per level (cycled), like a code
        # editor's indent guides.
        ".handcalcs :where(.hc-body){"
        "margin-inline-start:0.55em;"
        "padding-inline-start:calc(var(--hc-indent) - 0.55em);"
        "border-inline-start:2px solid var(--hc-guide);--hc-guide:var(--hc-guide-1);}"
        ".handcalcs :where(.hc-body .hc-body){--hc-guide:var(--hc-guide-2);}"
        ".handcalcs :where(.hc-body .hc-body .hc-body){--hc-guide:var(--hc-guide-3);}"
        ".handcalcs :where(.hc-body .hc-body .hc-body .hc-body){--hc-guide:var(--hc-guide-1);}"
        ".handcalcs :where(.hc-body .hc-body .hc-body .hc-body .hc-body){--hc-guide:var(--hc-guide-2);}"
        ".handcalcs :where(.hc-line,.hc-header,.hc-comment){"
        "margin-block:0;}"
        # Block headers (``Since ... is True:``) are callouts: a tinted band with
        # an accent marker; their keywords (``.hc-kw``) are set in the accent.
        ".handcalcs :where(.hc-header){"
        "background:var(--hc-tint);border-radius:4px;padding:0.1em 0.5em;}"
        ".handcalcs :where(.hc-header)::before{"
        'content:"\\25B8";color:var(--hc-accent-text);margin-inline-end:0.4em;}'
        ".handcalcs :where(.hc-kw){color:var(--hc-accent-text);}"
        # The result of a calc with a substitution is highlighted; inline
        # comments are muted.
        ".handcalcs :where(.hc-result){"
        "color:var(--hc-accent-text);background:var(--hc-highlight);font-weight:600;"
        "padding:0 0.25em;border-radius:3px;"
        "-webkit-box-decoration-break:clone;box-decoration-break:clone;}"
        ".handcalcs :where(.hc-note){color:var(--hc-muted);}"
        # Imports are small, quiet monospace chips.
        ".handcalcs :where(.hc-import){"
        "align-self:start;font-family:var(--jp-code-font-family,"
        "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace);"
        "font-size:0.85em;color:var(--hc-muted);background:var(--hc-chip);"
        "padding:0.05em 0.5em;border-radius:3px;}"
        ".handcalcs :where(.hc-comment,.hc-note) :where(code){"
        "font-size:0.9em;background:var(--hc-chip);padding:0 0.25em;border-radius:3px;}"
        # A params block is a real table so each ``id = value`` group aligns on
        # its ``=`` (identifier right, ``=`` centered, value left), separated by
        # an empty spacer column. Alignment no longer depends on the fragile
        # ``white-space: pre`` (a zero-specificity rule any host style can beat).
        # ``table-layout:auto`` (the default, stated for intent) sizes every
        # column to its own widest cell; the ``=`` column carries no padding so
        # it shrinks to the sign itself, and the breathing room around it lives
        # on the id/value columns instead (``--hc-eq-gap``).
        # ``width:auto`` + ``align-self:center`` stop the table from stretching to
        # the full flex-container width (the default ``align-items:stretch`` would
        # otherwise blow the columns out and make the ``=`` look over-padded); the
        # table shrinks to its content and sits centered. ``hc-multiline`` overrides
        # the alignment to left (see below). The table sits on a tinted panel
        # (``border-collapse:separate`` so its corners can round).
        # Unlike the rest of the sheet, the table rules carry real specificity
        # (``.handcalcs table.hc-params ...``): notebook hosts style every table
        # (JupyterLab sets a fixed layout, a 12px font, padded right-aligned cells
        # and zebra rows), which would otherwise break the alignment on ``=``.
        ".handcalcs table.hc-params{"
        "margin:0;border:0;border-collapse:separate;border-spacing:0;table-layout:auto;"
        "width:auto;align-self:center;font-size:inherit;color:inherit;"
        "font-variant-numeric:tabular-nums;"
        "background:var(--hc-tint);border-radius:4px;padding:0.1em 0.6em;}"
        # A multi-line calc reads as one unit: no panel, an accent bar on its left.
        ".handcalcs table.hc-params.hc-multiline{align-self:start;"
        "background:none;border-radius:0;padding:0 0 0 0.5em;"
        "border-inline-start:2px solid var(--hc-accent-text);}"
        ".handcalcs table.hc-params tr:nth-child(n){background:none;}"
        ".handcalcs table.hc-params td{"
        "padding:0;border:0;vertical-align:baseline;line-height:inherit;"
        "white-space:normal;max-width:none;}"
        ".handcalcs table.hc-params td.hc-param-id{"
        "text-align:right;padding-inline-end:var(--hc-eq-gap);}"
        ".handcalcs table.hc-params td.hc-param-eq{text-align:center;}"
        ".handcalcs table.hc-params td.hc-param-val{"
        "text-align:left;padding-inline-start:var(--hc-eq-gap);}"
        ".handcalcs table.hc-params td.hc-param-gap{width:var(--hc-param-gap);}"
        ".handcalcs table.hc-params td.hc-param-comment{"
        "text-align:left;padding-inline-start:var(--hc-eq-gap);}"
        ".handcalcs :where(.hc-pre){white-space:pre;}"
    )

    def theme_style(self) -> str:
        """
        The theme's custom properties on ``.handcalcs``, plus the dark-host
        overrides: a lighter accent for text and stronger tints. The dark rule
        uses ``:is()`` so it outranks the light defaults on ``.handcalcs``.
        """
        props = "".join(f"{key}:{value};" for key, value in self.theme.items())
        return (
            f".handcalcs{{{props}}}"
            f":is({','.join(DARK_HOSTS)}) .handcalcs{{--hc-accent-text:var(--hc-accent-dark);"
            "--hc-tint:color-mix(in srgb,var(--hc-accent) 30%,transparent);"
            "--hc-highlight:color-mix(in srgb,var(--hc-accent) 38%,transparent);}"
        )

    def complete(self, tree: list, base_context: BaseRenderContext) -> str:
        # ``self.join`` (inherited) walks the master list via the overridden
        # ``join_item`` below, emitting nested ``<div>``s. Wrap the whole body
        # once in ``.handcalcs`` and inject the scoped stylesheet a single time.
        body = self.join(tree, base_context)
        style = self.theme_style() + self.STYLE
        return f'<div class="handcalcs"><style>{style}</style>{body}</div>'

    def create_context(self, **config_kwargs):
        # Indentation is now structural (``.hc-body`` padding), not a text
        # prefix, so no ``&nbsp;`` indent is injected into the context.
        return BaseRenderContext(RenderContext(**config_kwargs), RenderContext.sparse())

    def join_item(self, item, depth: int, base_context: BaseRenderContext) -> list[str]:
        """
        HTML counterpart of ``BaseRenderer.join_item``: same master-list
        dispatch, but every line becomes a block-level ``<div>`` and nesting
        (not an indent prefix) expresses depth. ``depth`` is unused because the
        scoped stylesheet's ``.hc-body`` padding supplies indentation.

        Master-list shapes (identical to the base renderer):
        - bare string -> a whole line; block-level HTML (headings, prose ``<p>``,
          etc.) passes through untouched, plain text is wrapped in ``.hc-line``,
          and a multi-line plain string keeps its whitespace via ``.hc-pre``;
        - ``[header, body]`` with a non-empty header -> ``.hc-block`` wrapping a
          ``.hc-header`` line and an indented ``.hc-body``;
        - a headerless (flat) block -- a CommentsBlock/CalcsBlock group -- emits
          its body lines directly, at the current level (no wrapper);
        - an all-string list -> one ``.hc-line`` whose components join with a
          single space.
        Falsy items (``''``/``None``/``[]``) and one-shot line-break directives
        emit nothing -- CSS ``gap`` owns inter-line spacing.
        """
        if not item:
            return []
        context = base_context.current
        if isinstance(item, str):
            # A one-shot line-break directive is a bare newline; the CSS gap
            # already supplies vertical rhythm, so it emits nothing.
            if not item.strip("\n"):
                return []
            stripped = item.strip()
            # Block-level HTML built by a handler (a heading, a prose <p>) is
            # already a complete element; pass it through as a flex child.
            if stripped.startswith("<"):
                return [stripped]
            # A multi-line plain string keeps its embedded newlines/whitespace
            # via ``white-space: pre`` on ``.hc-pre`` (params grids now render as
            # a table, so this is only a fallback for any other pre-formatted text).
            if "\n" in item:
                return [f'<div class="hc-line hc-pre">{item}</div>']
            return [f'<div class="hc-line">{item}</div>']
        # A block is ``[header, body]`` -- detected by its body being a list.
        if isinstance(item[-1], list):
            header, body = item[0], item[-1]
            inner = "".join(self.join_items(body, depth + 1, base_context))
            # A headerless (flat) block only groups consecutive lines and
            # introduces no intro line: emit its body directly, no wrapper.
            if not (isinstance(header, str) and header.strip()):
                return [inner] if inner else []
            return [
                f'<div class="hc-block"><div class="hc-header">{header}</div>'
                f'<div class="hc-body">{inner}</div></div>'
            ]
        # An all-string list is a rendered line (calc line, import, ...).
        line = context.space.join(item)
        if not line.strip():
            return []
        return [f'<div class="hc-line">{line}</div>']

    def _cell_tds(self, cell, with_comment: bool = False) -> str:
        # Turn an ``["id", "=", "value"]`` triple (or ``None`` padding) into three
        # ``<td>``s -- identifier / ``=`` / value -- so the assignment aligns on its
        # ``=``. Cell components are already rendered HTML (e.g. ``c<sub>x</sub>``),
        # so they are interpolated as-is, not escaped. Shared by the params grid and
        # the multi-line calc grid.
        if isinstance(cell, (list, tuple, deque)):
            parts = [str(part) for part in cell]
        elif cell is None:
            parts = []
        else:
            parts = [str(cell)]
        ident, eq, val, *rest = parts + ["", "", ""]
        comment = rest[0] if rest else ""
        tds = (
            f'<td class="hc-param-id">{ident}</td>'
            f'<td class="hc-param-eq">{eq}</td>'
            f'<td class="hc-param-val">{val}</td>'
        )
        if with_comment:
            tds += f'<td class="hc-param-comment">{comment}</td>'
        return tds

    def format_param_grid(self, rows: list, base_context: BaseRenderContext) -> str:
        # Emit a real table instead of the plain-text grid: every cell becomes an
        # id / ``=`` / value triple of ``<td>``s. Adjacent groups in a row are
        # separated by an empty spacer ``<td>``. The table stays centered (the
        # ``hc-params`` rule) and sizes to its content.
        gap = '<td class="hc-param-gap"></td>'
        body = "".join(
            f"<tr>{gap.join(self._cell_tds(cell, True) for cell in row)}</tr>"
            for row in rows
        )
        return f'<table class="hc-params">{body}</table>'

    def format_calc_grid(self, rows: list, base_context: BaseRenderContext) -> str:
        # A multi-line ("long") calc: each row is a single ``[id, eq, value]`` triple
        # → one ``<tr>`` of three ``<td>``s, reusing the params id/eq/val column
        # alignment so every row lines up on its ``=``. The extra ``hc-multiline``
        # class left-aligns the whole table (the params grid stays centered).
        # The last row holds the result (and any trailing comment); it is
        # highlighted like the result of a one-line calc. A row with an empty ``eq``
        # continues the value above it (a source line continuation) and is indented.
        rows = [list(row) for row in rows]
        for row in rows:
            if not row[1]:
                row[2] = f"{self.CONTINUATION_INDENT}{row[2]}"
        if len(rows) > 1 and rows[-1][1]:
            value, sep, note = str(rows[-1][2]).partition(NOTE_OPEN)
            rows[-1][2] = result_span(value.rstrip()) + (f" {sep}{note}" if sep else "")
        body = "".join(f"<tr>{self._cell_tds(row)}</tr>" for row in rows)
        return f'<table class="hc-params hc-multiline">{body}</table>'


HTMLR = HTMLRenderer
BRC = BaseRenderContext

# Opening tag of every rendered inline comment (see ``render_inline_comment``).
NOTE_OPEN = '<span class="hc-note">'


def result_span(text: str) -> str:
    return f'<span class="hc-result">{text}</span>'


def keyword(text: str) -> str:
    return f'<span class="hc-kw">{text}</span>'


def code_spans(text: str) -> str:
    """Turn each `backtick` span in comment text into ``<code>``."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


## SWAP RULES


@HTMLRenderer.register("heading")
def render_heading(
    renderer: HTMLR, node: Heading, base_context: BaseRenderContext
) -> str:
    # A heading renders as a single block-level element in the master list, its
    # markdown level reproduced from the node's ``heading_level``. It carries no
    # trailing newline: ``join`` passes block-level HTML through as a flex child
    # and the container's ``gap`` supplies the spacing.
    return f"<h{node.heading_level}>{node.content}</h{node.heading_level}>"


@HTMLRenderer.register("comments_block")
def render_comments_block(
    renderer: HTMLR, node: CommentsBlock, base_context: BaseRenderContext
) -> str:
    # A run of consecutive comment lines is true prose, so it renders as a single
    # flowing ``<p>`` paragraph (its lines joined by a space) rather than one
    # ``.hc-line`` per source line. ``join`` passes the ``<p>`` through as a
    # block-level flex child; ``.hc-comment`` tames its margin. Comment commands
    # (``# hc: ...``) in the run render to '' and drop out; an all-empty block
    # (e.g. only commands) emits nothing. A `backtick` span becomes ``<code>``.
    context = base_context.current
    _ = context.space
    lines = [renderer.render(line, base_context) for line in node.lines]
    texts = [line for line in lines if isinstance(line, str) and line.strip()]
    if not texts:
        return ""
    return f'<p class="hc-comment">{code_spans(_.join(texts))}</p>'


# ``calcs_block`` intentionally has no HTML override: the inherited
# ``BaseRenderer`` handler returns a clean headerless ``[header, body]`` group
# and the overridden ``join_item`` emits one ``.hc-line`` per calc line, with
# vertical rhythm owned by the stylesheet's ``gap`` (no per-line ``<br>``, no
# wrapping ``<p>``). An ignored/``-i`` line renders to '' and is skipped, so no
# empty element is emitted.


@HTMLRenderer.register("import")
def render_import(
    renderer: HTMLR, node: Import, base_context: BaseRenderContext
) -> str:
    # An import is a quiet monospace chip (``.hc-import``) showing the import
    # statement as written; the chip itself marks it as an import.
    names = ", ".join(
        (
            f"{name.identifier} as {name.value}"
            if name.value is not None
            else name.identifier
        )
        for name in node.names
    )
    if node.import_from:
        dots = "." * (node.import_from_level or 0)
        text = f"from {dots}{node.import_from_module or ''} import {names}"
    else:
        text = f"import {names}"
    return f'<div class="hc-import">{escape(text)}</div>'


@HTMLRenderer.register("inline_comment")
def render_inline_comment(
    renderer: HTMLR, node: InlineComment, base_context: BaseRenderContext
) -> str:
    # Inline comments are muted (``.hc-note``), so they read the same in calc
    # lines, multi-line grids and params grids.
    context = base_context.current
    content = code_spans(escape(node.content, quote=False))
    return f"{NOTE_OPEN}{context.lpar}{content}{context.rpar}</span>"


@HTMLRenderer.register("calc_line:post")
@HTMLRenderer.register("expr_line:post")
def mark_result(renderer: HTMLR, rendered, node, base_context: BaseRenderContext):
    """
    Highlight the result of a one-line calc that shows a substitution.

    A rendered line is ``[col, '=', col, '=', col, comment?]``: the columns
    interleave with the ``=`` sign, so the list has an odd length unless a
    comment trails it. Only a line with three or more columns (target, an
    expression and its result) has a result worth highlighting; a param line
    (``a = 5``) stays plain. Grids and ignored lines are strings and pass through.
    """
    if not isinstance(rendered, list):
        return rendered
    has_comment = len(rendered) % 2 == 0
    result_idx = len(rendered) - 1 - has_comment
    if result_idx < 4:
        return rendered
    rendered = list(rendered)
    rendered[result_idx] = result_span(rendered[result_idx])
    return rendered


@HTMLRenderer.register("header:if_block")
def if_block_header(
    renderer: HTMLRenderer, node: IfBlock, base_context: BaseRenderContext
) -> str:
    context = base_context.current
    _ = context.space
    sym_expr = render_condition(renderer, node.test, base_context, "sym")
    num_expr = render_condition(renderer, node.test, base_context, "num")
    # No trailing <br>: the ``.hc-header`` div supplies the break structurally.
    return f"{keyword('Since')}{_}({sym_expr}){_}\u2192{_}({num_expr}){_}{keyword(f'is{_}True:')}"


@HTMLRenderer.register("header:else_block")
def else_block_header(
    renderer: HTMLRenderer, node: ElseBlock, base_context: BaseRenderContext
) -> str:
    return keyword("Otherwise:")


@HTMLRenderer.register("header:for_block")
def for_block_header(
    renderer: HTMLRenderer, node: ForBlock, base_context: BaseRenderContext
) -> str:
    context = base_context.current
    _ = context.space
    base_context.line_context.current_mode = "sym"
    target = renderer.render(node.assigns[0], base_context)
    iterable = renderer.render(node.iterator[0], base_context)
    # No trailing <br>: the ``.hc-header`` div supplies the break structurally.
    over_each = keyword(f"Iterating{_}over{_}each")
    return f"{over_each}{_}{target}{_}{keyword('in')}{_}{iterable}:"


GREEK = GREEK_UNICODE


# What an accent component adds after the symbol it decorates.
ACCENT_MARKS = {
    "hat": "\u0302",
    "bar": "\u0305",
    "dot": "\u0307",
    "ddot": "\u0308",
}
PRIME_MARK = "\u2032"


def html_symbol(symbol: Symbol, space: str = " ") -> str:
    """A parsed ``Symbol`` as HTML: Greek letters, combining accents, primes,
    ``<sup>`` and ``<sub>`` (sibling subscripts separated by commas)."""
    markup = space.join(
        "".join(GREEK[text] if is_greek else escape(text) for is_greek, text in pieces)
        for pieces in symbol.words
    )
    markup += "".join(ACCENT_MARKS[accent] for accent in symbol.accents)
    markup += PRIME_MARK * symbol.primes
    if symbol.superscripts:
        sups = ",".join(html_symbol(sup, space) for sup in symbol.superscripts)
        markup += f"<sup>{sups}</sup>"
    if symbol.subscripts:
        subs = ",".join(html_symbol(sub, space) for sub in symbol.subscripts)
        markup += f"<sub>{subs}</sub>"
    return markup


@HTMLR.register("name:sym")
def swap_identifier(renderer: HTMLR, node: Name, base_context: BRC) -> Name:
    """
    Typeset a Name's identifier as HTML from its parsed ``Symbol`` (see
    ``identifiers.parse_identifier``): ``sigma_max`` -> ``σ<sub>max</sub>``,
    ``N_pl_Rd`` -> ``N<sub>pl,Rd</sub>`` (or nested, with the ``subscripts``
    option), ``DeltaH`` -> ``ΔH``, ``x_hat`` -> x̂, ``M_star`` ->
    ``M<sup>*</sup>``; ``__`` is a space and ``___`` an underscore. An identifier
    in the ``symbols`` option is typeset from its spec.

    Text that isn't an identifier (markup from a ``name:pre`` rule) is left
    alone. Registered as a 'sym' rule on the Name node: the identifier is only
    shown in symbolic mode (numeric mode renders the Name's value instead).
    """
    options = identifier_options(renderer, base_context)
    identifier = node.identifier
    if identifier in options.symbols or is_identifier(identifier):
        symbol = parse_identifier(identifier, options)
        node.identifier = html_symbol(symbol, base_context.current.space)
    return node


@HTMLR.register("pow_op")
def render_pow_op(renderer: HTMLR, node: AddOp, base_context: BaseRenderContext) -> str:
    as_infix = infix_binop(node, renderer, False, base_context)
    return f"{node.pre}{as_infix}{node.post}"


# The display symbol of each arithmetic operator: ``*`` is a centred dot, the
# others keep their Python symbol. Multiplication and both divisions carry no
# pre/post wrapping of their own: any brackets around an operand come from the
# infix precedence logic (lpar/rpar).
OPERATOR_SYMBOLS = {
    "mult_op": "·",
    "div_op": "/",
    "floor_op": "//",
    "add_op": "+",
    "sub_op": "-",
}
UNWRAPPED_OPERATORS = {"mult_op", "div_op", "floor_op"}


@HTMLR.register("mult_op:pre")
@HTMLR.register("pow_op:pre")
@HTMLR.register("div_op:pre")
@HTMLR.register("floor_op:pre")
@HTMLR.register("add_op:pre")
@HTMLR.register("sub_op:pre")
def swap_py_operators(renderer: HTMLR, node: HcBinOp, base_context: BRC) -> HcBinOp:
    """
    Rewrite a binary operator's display symbol/pre/post to the HTML form. A
    power with a literal exponent becomes a superscript (``a<sup>2</sup>``).

    Registered as a 'pre' rule on each arithmetic operator node: the swap is
    mode-independent (the same symbol is shown in both the symbolic and numeric
    columns), so it must run before rendering regardless of mode. The mutation
    is idempotent, so re-running it on the second (numeric) pass is harmless.
    """
    if node.type in OPERATOR_SYMBOLS:
        node.symbol = OPERATOR_SYMBOLS[node.type]
        if node.type in UNWRAPPED_OPERATORS:
            node.pre = ""
            node.post = ""
    elif node.type == "pow_op" and isinstance(node.right, Constant):
        node.symbol = "<sup>"
        node.post = "</sup>"
    return node


@HTMLR.register("gt_op:pre")
@HTMLR.register("lt_op:pre")
@HTMLR.register("gte_op:pre")
@HTMLR.register("lte_op:pre")
def swap_angle_ops(renderer: HTMLR, node: HcCompOp, base_context: BRC) -> HcCompOp:
    """
    Modifies the symbol in the <, <=, >, >= operators to be HTML safe
    """
    if node.symbol == "<":
        node.symbol = "&lt;"
    elif node.symbol == "<=":
        node.symbol = "&le;"
    elif node.symbol == ">":
        node.symbol = "&gt;"
    elif node.symbol == ">=":
        node.symbol = "&ge;"
    return node


@HTMLR.register("gt_op:post")
@HTMLR.register("lt_op:post")
@HTMLR.register("gte_op:post")
@HTMLR.register("lte_op:post")
@HTMLR.register("eq_op:post")
@HTMLR.register("neq_op:post")
def space_comparison(
    renderer: HTMLR, rendered, node: HcCompOp, base_context: BRC
) -> str:
    """
    Space comparison operators like the arithmetic ones (``a &lt; b``, not
    ``a&lt;b``); ``!=`` becomes ``≠``.
    """
    _ = base_context.current.space
    symbol = "\u2260" if rendered == "!=" else rendered
    return f"{_}{symbol}{_}"


# Modules whose functions and constants read as plain maths, so their module
# prefix is dropped: ``math.sqrt(x)`` shows as ``√(x)``, ``math.sin(x)`` as
# ``sin(x)`` and ``math.pi`` as ``π``. Every ``math``/``cmath`` function
# qualifies; numpy also holds array functions (``np.linspace``), so only its
# elementwise maths functions do. A module is recognised by its real name (via
# the render context's ``global_ns``, so ``import math as m`` works) or, when
# no namespace was supplied, by the conventional alias.
MATH_MODULES = {"math": "math", "cmath": "cmath", "numpy": "numpy", "np": "numpy"}
NUMPY_MATH_FUNCTIONS = {
    "sqrt",
    "cbrt",
    "exp",
    "log",
    "log2",
    "log10",
    "abs",
    "sin",
    "cos",
    "tan",
    "arcsin",
    "arccos",
    "arctan",
    "arctan2",
    "sinh",
    "cosh",
    "tanh",
    "degrees",
    "radians",
    "deg2rad",
    "rad2deg",
    "floor",
    "ceil",
    "hypot",
}
MATH_CONSTANTS = {"pi": "π", "tau": "τ", "e": "e", "inf": "∞"}


def math_module(alias: str, base_context: BRC) -> Optional[str]:
    """The maths module ('math', 'cmath' or 'numpy') that ``alias`` names, if any."""
    global_ns = getattr(base_context.current, "global_ns", None) or {}
    module = getattr(global_ns.get(alias), "__name__", alias)
    return MATH_MODULES.get(module)


@HTMLR.register("function_call:pre")
def drop_math_namespace(
    renderer: HTMLR, node: FunctionCall, base_context: BRC
) -> FunctionCall:
    """
    Drop the module prefix of a maths function call (``math.sqrt(x)`` →
    ``sqrt(x)``, which ``swap_sqrt_symbol`` then shows as ``√(x)``).

    A mode-independent 'pre' rule, registered before ``swap_sqrt_symbol`` so it
    still sees the ``sqrt`` name. Clearing the namespace is idempotent, and the
    base handler renders an empty namespace as nothing.
    """
    namespace = getattr(node.namespace, "identifier", None)
    if not isinstance(namespace, str):
        return node
    module = math_module(namespace, base_context)
    name = getattr(node.function_name, "identifier", None)
    if module in ("math", "cmath") or (
        module == "numpy" and name in NUMPY_MATH_FUNCTIONS
    ):
        node.namespace = deque()
    return node


@HTMLR.register("attribute:sym")
def swap_math_constants(
    renderer: HTMLR, node: Attribute, base_context: BRC
) -> Attribute:
    """
    Show a maths constant as its symbol in the symbolic column: ``math.pi`` →
    ``π``, ``math.tau`` → ``τ``, ``math.e`` → ``e``, ``math.inf`` → ``∞`` (also
    for ``cmath`` and numpy). The numeric column still shows the value.
    """
    if node.identifier in MATH_CONSTANTS and math_module(
        node.namespace or "", base_context
    ):
        node.namespace = ""
        node.identifier = MATH_CONSTANTS[node.identifier]
    return node


@HTMLR.register("function_call:pre")
def swap_sqrt_symbol(
    renderer: HTMLR, node: FunctionCall, base_context: BRC
) -> FunctionCall:
    """
    Swap a ``sqrt(...)`` call's function name for the '√' symbol.

    Registered as a 'pre' rule on function_call: the function name is shown in
    both symbolic and numeric columns, so the swap must be mode-independent. The
    mutation is idempotent across the two render passes.
    """
    name = math_call_name(node)
    if name == "":  # already set in its own notation
        return node
    node.pre = "("
    node.post = ")"
    if name == "factorial":
        return postfix_factorial(node, "(", ")")
    if name in ROOT_SYMBOLS:
        node.function_name.identifier = ROOT_SYMBOLS[name]
        node.function_name.value = ROOT_SYMBOLS[name]
    return node
