from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Any
from handcalcs.renderers.base import BaseRenderer, RenderContext, render_condition, infix_binop, BaseRenderContext, ContextKeyError, ContextValueError


# Node type imports only used for typing
from handcalcs.parsing.nodes import (
    HcNode,
    Name,
    Constant,
    
)
from handcalcs.parsing.operator_nodes import (
    AddOp,
    MultOp,
    SubOp,
    DivOp,
    ModuloOp,
    FloorOp,
    PowOp,
    HcBinOp,
    EqOp,
    GtOp,
    GtEOp,
    LtOp,
    LtEOp,
    NeqOp,
    HcCompOp
)
from handcalcs.parsing.inline_nodes import (
    InlineComment,
    FunctionCall,
    Compare
)
from handcalcs.parsing.line_nodes import (
    CalcLine,
    ExprLine,
    Import,
    Heading,
    CommentLine
)
from handcalcs.parsing.block_nodes import (
    IfBlock,
    ElseBlock,
    ElifBlock,
    CommentsBlock,
    CalcsBlock,
    ForBlock
)



class HTMLRenderer(BaseRenderer):
    name = 'html'

    # One scoped stylesheet owns ALL vertical rhythm and indentation. Emitted
    # once by ``complete``; every rule uses ``:where()`` so it contributes zero
    # specificity and a host page's own styles always win. ``--hc-gap`` and
    # ``--hc-indent`` are the two knobs everything else references.
    STYLE = (
        ".handcalcs{"
        "--hc-gap:0.35em;--hc-indent:1.5em;--hc-param-gap:2em;--hc-eq-gap:0.3em;"
        "display:flex;flex-direction:column;gap:var(--hc-gap);"
        "line-height:1.6;font-variant-numeric:tabular-nums;}"
        ".handcalcs :where(.hc-block,.hc-body){"
        "display:flex;flex-direction:column;gap:var(--hc-gap);}"
        ".handcalcs :where(.hc-body){padding-inline-start:var(--hc-indent);}"
        ".handcalcs :where(.hc-line,.hc-header,.hc-comment){"
        "margin-block:0;}"
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
        # the alignment to left (see below).
        ".handcalcs :where(table.hc-params){"
        "margin-block:0;border-collapse:collapse;table-layout:auto;"
        "width:auto;align-self:center;"
        "font-variant-numeric:tabular-nums;}"
        ".handcalcs :where(table.hc-multiline){align-self:start;}"
        ".handcalcs :where(table.hc-params td){"
        "padding:0;border:0;vertical-align:baseline;}"
        ".handcalcs :where(.hc-param-id){"
        "text-align:right;padding-inline-end:var(--hc-eq-gap);}"
        ".handcalcs :where(.hc-param-eq){text-align:center;}"
        ".handcalcs :where(.hc-param-val){"
        "text-align:left;padding-inline-start:var(--hc-eq-gap);}"
        ".handcalcs :where(.hc-param-gap){width:var(--hc-param-gap);}"
        ".handcalcs :where(.hc-pre){white-space:pre;}"
        "@media (prefers-color-scheme:dark){.handcalcs{color:#e6e6e6;}}"
    )

    def complete(self, tree: list, base_context: BaseRenderContext) -> str:
        # ``self.join`` (inherited) walks the master list via the overridden
        # ``_join_item`` below, emitting nested ``<div>``s. Wrap the whole body
        # once in ``.handcalcs`` and inject the scoped stylesheet a single time.
        body = self.join(tree, base_context)
        return f'<div class="handcalcs"><style>{self.STYLE}</style>{body}</div>'

    def create_context(self, **config_kwargs):
        # Indentation is now structural (``.hc-body`` padding), not a text
        # prefix, so no ``&nbsp;`` indent is injected into the context.
        return BaseRenderContext(RenderContext(**config_kwargs), RenderContext.sparse())

    def _join_item(self, item, depth: int, base_context: BaseRenderContext) -> list[str]:
        """
        HTML counterpart of ``BaseRenderer._join_item``: same master-list
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
            inner = "".join(self._join_items(body, depth + 1, base_context))
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

    def _cell_tds(self, cell) -> str:
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
        ident, eq, val = (parts + ["", "", ""])[:3]
        return (
            f'<td class="hc-param-id">{ident}</td>'
            f'<td class="hc-param-eq">{eq}</td>'
            f'<td class="hc-param-val">{val}</td>'
        )

    def format_param_grid(self, rows: list, base_context: BaseRenderContext) -> str:
        # Emit a real table instead of the plain-text grid: every cell becomes an
        # id / ``=`` / value triple of ``<td>``s. Adjacent groups in a row are
        # separated by an empty spacer ``<td>``. The table stays centered (the
        # ``hc-params`` rule) and sizes to its content.
        gap = '<td class="hc-param-gap"></td>'
        body = "".join(
            f'<tr>{gap.join(self._cell_tds(cell) for cell in row)}</tr>' for row in rows
        )
        return f'<table class="hc-params">{body}</table>'

    def format_calc_grid(self, rows: list, base_context: BaseRenderContext) -> str:
        # A multi-line ("long") calc: each row is a single ``[id, eq, value]`` triple
        # → one ``<tr>`` of three ``<td>``s, reusing the params id/eq/val column
        # alignment so every row lines up on its ``=``. The extra ``hc-multiline``
        # class left-aligns the whole table (the params grid stays centered).
        body = "".join(f'<tr>{self._cell_tds(row)}</tr>' for row in rows)
        return f'<table class="hc-params hc-multiline">{body}</table>'


HTMLR = HTMLRenderer
BRC = BaseRenderContext


## SWAP RULES

@HTMLRenderer.register('heading')
def render_heading(renderer: HTMLR, node: Heading, base_context: BaseRenderContext) -> str:
    # A heading renders as a single block-level element in the master list, its
    # markdown level reproduced from the node's ``heading_level``. It carries no
    # trailing newline: ``join`` passes block-level HTML through as a flex child
    # and the container's ``gap`` supplies the spacing.
    return f"<h{node.heading_level}>{node.content}</h{node.heading_level}>"

@HTMLRenderer.register('comment_line')
def render_comment_line(renderer: HTMLR, node: CommentLine, base_context: BaseRenderContext) -> str:
    # A standalone comment renders as a plain-text line (a single string in the
    # master list). The trailing newline is inserted by the join step, not here.
    return f"{node.content}"


@HTMLRenderer.register('comments_block')
def render_comments_block(renderer: HTMLR, node: CommentsBlock, base_context: BaseRenderContext) -> str:
    # A run of consecutive comment lines is true prose, so it renders as a single
    # flowing ``<p>`` paragraph (its lines joined by a space) rather than one
    # ``.hc-line`` per source line. ``join`` passes the ``<p>`` through as a
    # block-level flex child; ``.hc-comment`` tames its margin. Comment commands
    # (``# hc: ...``) in the run render to '' and drop out; an all-empty block
    # (e.g. only commands) emits nothing.
    context = base_context.current
    _ = context.space
    lines = [renderer.render(line, base_context) for line in node.lines]
    texts = [line for line in lines if isinstance(line, str) and line.strip()]
    if not texts:
        return ''
    return f'<p class="hc-comment">{_.join(texts)}</p>'


# ``calcs_block`` intentionally has no HTML override: the inherited
# ``BaseRenderer`` handler returns a clean headerless ``[header, body]`` group
# and the overridden ``_join_item`` emits one ``.hc-line`` per calc line, with
# vertical rhythm owned by the stylesheet's ``gap`` (no per-line ``<br>``, no
# wrapping ``<p>``). An ignored/``-i`` line renders to '' and is skipped, so no
# empty element is emitted.

@HTMLRenderer.register("header:if_block")
def if_block_header(renderer: HTMLRenderer, node: IfBlock, base_context: BaseRenderContext) -> str:
    context = base_context.current
    _ = context.space
    sym_expr = render_condition(renderer, node.test.comparison, base_context, 'sym')
    num_expr = render_condition(renderer, node.test.comparison, base_context, 'num')
    # No trailing <br>: the ``.hc-header`` div supplies the break structurally.
    return f"Since{_}({sym_expr}){_}->{_}({num_expr}){_}is{_}True:"


@HTMLRenderer.register("header:for_block")
def for_block_header(renderer: HTMLRenderer, node: ForBlock, base_context: BaseRenderContext) -> str:
    context = base_context.current
    _ = context.space
    base_context.line_context.current_mode = 'sym'
    target = renderer.render(node.assigns[0], base_context)
    iterable = renderer.render(node.iterator[0], base_context)
    # No trailing <br>: the ``.hc-header`` div supplies the break structurally.
    return f"Iterating{_}over{_}each{_}{target}{_}in{_}{iterable}:"

@HTMLR.register("name:sym")
def swap_greeks(renderer: HTMLR, node: Name, base_context: BRC) -> HcNode:
    """
    Swaps out any greek substrings or unicode symbols in a Name's identifier.

    Registered as a 'sym' rule on the Name node: the identifier is only shown in
    symbolic mode (numeric mode renders the Name's value instead).
    """
    GREEK_LOWER = {
        "alpha": "α",
        "beta": "β",
        "gamma": "γ",
        "delta": "δ",
        "epsilon": "ε",
        "varepsilon": "ϵ",
        "zeta": "ζ",
        "theta": "θ",
        "vartheta": "ϑ",
        "iota": "ι",
        "kappa": "κ",
        "mu": "μ",
        "nu": "ν",
        "xi": "ξ",
        "omicron": "ο",
        "pi": "π",
        "varpi": "ϖ",
        "rho": "ρ",
        "varrho": "ϱ",
        "sigma": "σ",
        "varsigma": "ς",
        "tau": "τ",
        "upsilon": "υ",
        "phi": "φ",
        "varphi": "ϕ",
        "chi": "χ",
        "omega": "ω",
        "eta": "η",
        "psi": "ψ",
        "lamb": "λ",
    }

    GREEK_UPPER = {
        "Alpha": "Α",
        "Beta": "Β",
        "Gamma": "Γ",
        "Delta": "Δ",
        "Epsilon": "Ε",
        "Zeta": "Ζ",
        "Theta": "Θ",
        "Iota": "Ι",
        "Kappa": "Κ",
        "Mu": "Μ",
        "Nu": "Ν",
        "Xi": "Ξ",
        "Omicron": "Ο",
        "Pi": "Π",
        "Rho": "Ρ",
        "Sigma": "Σ",
        "Tau": "Τ",
        "Upsilon": "Υ",
        "Phi": "Φ",
        "Chi": "Χ",
        "Omega": "Ω",
        "Eta": "Η",
        "Psi": "Ψ",
        "Lamb": "Λ",
    }

    for name, unicode in (GREEK_LOWER | GREEK_UPPER).items():
        id_components = node.identifier.split("_")
        swapped_components = []
        for comp in id_components:
            if comp == name:
                comp = unicode
            swapped_components.append(comp)
        swapped_id = "_".join(swapped_components)
        node.identifier = swapped_id
    return node

@HTMLR.register("name:sym")
def swap_special_symbols(renderer: HTMLR, node: Name, base_context: BRC) -> Name:
    """
    Swaps '_prime', '_star', '_bar' and '_hat' symbols
    """
    identifier = node.identifier
    identifier = identifier.replace("_hat_", "\u0302_")
    identifier = identifier.replace("_prime_", f"\u2032_")
    identifier = identifier.replace("_star_", "<sup>*</sup>_")
    identifier = identifier.replace("_bar_", "\u0305_")
    node.identifier = identifier
    return node

@HTMLR.register("name:sym")
def swap_subscripts(renderer: HTMLR, node: Name, base_context: BRC) -> Name:
    """
    Interprets single underscores as subscripts, double underscores as spaces,
    triple underscores as literal underscores
    """
    context = base_context.current
    _ = context.space
    identifier = node.identifier
    # Replace all extra underscores with non-identifier characters for later
    identifier = identifier.replace('___', '|')
    identifier = identifier.replace("__", "^")
    under_count = identifier.count("_")
    identifier = identifier.replace("_", "<sub>")
    closers = "</sub>" * under_count
    identifier = f"{identifier}{closers}"
    identifier = identifier.replace("^", _)
    identifier = identifier.replace("|", "_")
    node.identifier = identifier
    return node
    
@HTMLR.register('pow_op')
def render_pow_op(renderer: HTMLR, node: AddOp, base_context: BaseRenderContext) -> str:
    as_infix = infix_binop(
        node, renderer, False, base_context)
    return f"{node.pre}{as_infix}{node.post}"

@HTMLR.register("mult_op:pre")
@HTMLR.register("pow_op:pre")
@HTMLR.register("div_op:pre")
@HTMLR.register("floor_op:pre")
@HTMLR.register("add_op:pre")
@HTMLR.register("sub_op:pre")
def swap_py_operators(renderer: HTMLR, node: HcBinOp, base_context: BRC) -> HcBinOp:
    """
    Rewrite a binary operator's display symbol/pre/post to the plain-text form.

    Registered as a 'pre' rule on each arithmetic operator node: the swap is
    mode-independent (the same symbol is shown in both the symbolic and numeric
    columns), so it must run before rendering regardless of mode. The mutation
    is idempotent, so re-running it on the second (numeric) pass is harmless.
    """
    context = base_context.current
    _ = context.space
    if node.type not in ('mult_op', 'pow_op', 'div_op', 'floor_op', 'add_op', 'sub_op'):
        return node
    elif node.type == 'mult_op':
        node.symbol = '·'
        node.pre = ''
        node.post = ''
        return node
    elif node.type == 'div_op':
        # Division always renders with its '/' symbol. Any parentheses around an
        # operand come from the infix precedence logic (lpar/rpar), not from
        # pre/post, so pre/post stay empty regardless of operand type.
        node.symbol = "/"
        node.pre = ""
        node.post = ""
        return node
    elif node.type == 'floor_op':
        node.symbol = '//'
        node.pre = ''
        node.post = ''
        return node
    elif node.type == 'add_op':
        node.symbol = '+'
        return node
    elif node.type == 'sub_op':
        node.symbol = '-'
        return node
    elif node.type == 'pow_op' and isinstance(node.right, Constant):
        exp_str = str(node.right.value)
        node.symbol = '<sup>'
        node.post = "</sup>"
        return node
    else:
        return node


@HTMLR.register("function_call:pre")
def swap_sqrt_symbol(renderer: HTMLR, node: FunctionCall, base_context: BRC) -> FunctionCall:
    """
    Swap a ``sqrt(...)`` call's function name for the '√' symbol.

    Registered as a 'pre' rule on function_call: the function name is shown in
    both symbolic and numeric columns, so the swap must be mode-independent. The
    mutation is idempotent across the two render passes.
    """
    if node.function_name.identifier == 'sqrt':
        node.function_name.identifier = '√'
        node.function_name.value = '√'
    return node


            

