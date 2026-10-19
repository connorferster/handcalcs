import re
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Any
from handcalcs.renderers.base import (
    BaseRenderer,
    RenderContext,
    BaseRenderContext,
    ContextKeyError,
    ContextValueError,
    render_condition,
    OP_PRECEDENCE,
    is_source_number,
    literal_text,
)

from handcalcs.renderers.identifiers import has_greek, split_greek

# Node type imports only used for typing
from handcalcs.parsing.nodes import (
    HcNode,
    Name,
    Attribute,
    NoValue,
    Constant,
    List,
    Tuple,
    Set,
    Dictionary,
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
    HcUnaryOp,
    EqOp,
    GtOp,
    GtEOp,
    LtOp,
    LtEOp,
    NeqOp,
    HcCompOp,
)
from handcalcs.parsing.inline_nodes import InlineComment, FunctionCall, Keyword, Compare
from handcalcs.parsing.line_nodes import (
    CalcLine,
    ExprLine,
    Import,
    Heading,
    CommentLine,
)
from handcalcs.parsing.block_nodes import (
    IfBlock,
    ElseBlock,
    ElifBlock,
    CalcsBlock,
    ForBlock,
    FunctionBlock,
)

BRC = BaseRenderContext


LATEX_SPECIAL_CHARS = {
    "\\": "\\textbackslash{}",
    "&": "\\&",
    "%": "\\%",
    "$": "\\$",
    "#": "\\#",
    "_": "\\_",
    "{": "\\{",
    "}": "\\}",
    "~": "\\textasciitilde{}",
    "^": "\\textasciicircum{}",
}


def latex_escape(text: str) -> str:
    """
    Escape the LaTeX special characters in a plain-text string so it can be
    emitted in text mode (headings, comment paragraphs, inline comments, ...).
    """
    return "".join(LATEX_SPECIAL_CHARS.get(char, char) for char in text)


def latex_prose(text: str) -> str:
    """
    Escape a comment written as prose (headings, comment paragraphs, inline
    comments) and typeset its light markup: a pair of backticks becomes
    ``\\texttt{}`` and an opening quote becomes a left quote (TeX otherwise sets
    ``'a'`` as two right quotes). An unpaired backtick is kept literally.
    """
    segments = text.split("`")
    if len(segments) % 2 == 0:
        segments[-2:] = [f"{segments[-2]}`{segments[-1]}"]
    typeset = []
    for idx, segment in enumerate(segments):
        if idx % 2:
            typeset.append(f"\\texttt{{{latex_escape(segment)}}}")
            continue
        segment = latex_escape(segment).replace("`", "\\textasciigrave{}")
        segment = re.sub(r'(^|[\s(\[])"', r"\1``", segment)
        segment = re.sub(r"(^|[\s(\[])'", r"\1`", segment)
        typeset.append(segment.replace('"', "''"))
    return "".join(typeset)


GREEK_LOWER = {
    name: f"\\{name}"
    for name in (
        "alpha",
        "beta",
        "gamma",
        "delta",
        "epsilon",
        "varepsilon",
        "zeta",
        "eta",
        "theta",
        "vartheta",
        "iota",
        "kappa",
        "mu",
        "nu",
        "xi",
        "pi",
        "varpi",
        "rho",
        "varrho",
        "sigma",
        "varsigma",
        "tau",
        "upsilon",
        "phi",
        "varphi",
        "chi",
        "psi",
        "omega",
    )
} | {"omicron": "o", "lamb": "\\lambda"}

# LaTeX only defines the capitals that differ from a Latin letter; the rest are
# typeset as the upright Latin letter they look like.
GREEK_UPPER = (
    {
        name: f"\\{name}"
        for name in (
            "Gamma",
            "Delta",
            "Theta",
            "Xi",
            "Pi",
            "Sigma",
            "Upsilon",
            "Phi",
            "Psi",
            "Omega",
        )
    }
    | {
        name: f"\\mathrm{{{letter}}}"
        for name, letter in (
            ("Alpha", "A"),
            ("Beta", "B"),
            ("Epsilon", "E"),
            ("Zeta", "Z"),
            ("Eta", "H"),
            ("Iota", "I"),
            ("Kappa", "K"),
            ("Mu", "M"),
            ("Nu", "N"),
            ("Omicron", "O"),
            ("Rho", "P"),
            ("Tau", "T"),
            ("Chi", "X"),
        )
    }
    | {"Lamb": "\\Lambda"}
)

GREEK = GREEK_LOWER | GREEK_UPPER

# Namespaces whose attributes are mathematical constants (``math.pi``); the
# namespace is dropped when the attribute is shown symbolically.
MATH_NAMESPACES = ("math", "cmath", "numpy", "np", "scipy.constants")
MATH_CONSTANTS = {"inf": "\\infty", "nan": "\\mathrm{NaN}"}


def latex_word(text: str) -> str:
    """One character in math italic; a longer word (not a number) upright."""
    typeset = text.replace("\0", "\\_").replace("\1", "\\ ")
    if len(text) > 1 and not text.isdigit():
        return f"\\mathrm{{{typeset}}}"
    return typeset


def latex_identifier(identifier: str, greek_prefixes: bool = True) -> str:
    """
    Typeset a Python identifier as a LaTeX math symbol.

    - Single underscores are nested subscripts: ``x_a_b`` -> ``x_{a_{b}}``.
    - Double underscores are spaces and triple underscores literal underscores.
    - A component that names a greek letter becomes that letter
      (``omega_2`` -> ``\\omega_{2}``), and so does a Unicode Greek letter
      (``σ_R`` -> ``\\sigma_{R}``, ``ΔH`` -> ``\\Delta H``) and, with
      ``greek_prefixes``, a leading Greek name followed by an uppercase letter
      or a digit (``DeltaH`` -> ``\\Delta H``). Each ``__``-separated word gets
      the same lookup (``Delta__H`` -> ``\\Delta\\ H``).
    - Any other component longer than one character is a word, set upright
      (``class_section`` -> ``\\mathrm{class}_{\\mathrm{section}}``).

    An identifier that already contains LaTeX (a backslash or brace, which no
    Python identifier can) is returned unchanged, so the swap is idempotent.
    """
    if not identifier or "\\" in identifier or "{" in identifier:
        return identifier
    # Placeholders for the double/triple underscores, which are not subscripts.
    identifier = identifier.replace("___", "\0").replace("__", "\1")
    components = []
    for component in identifier.split("_"):
        words = [split_greek(word, greek_prefixes) for word in component.split("\1")]
        if not any(has_greek(pieces) for pieces in words):
            # No Greek letter: the component is one symbol or one upright word.
            components.append(latex_word(component))
            continue
        components.append(
            "\\ ".join(
                " ".join(
                    GREEK[text] if is_greek else latex_word(text)
                    for is_greek, text in pieces
                )
                for pieces in words
            )
        )
    head, *subscripts = components
    return head + "".join(f"_{{{sub}" for sub in subscripts) + "}" * len(subscripts)


# The LaTeX symbol of each operator node type (see ``swap_operator_symbols``).
OPERATOR_SYMBOLS = {
    "mult_op": "\\cdot",
    "add_op": "+",
    "sub_op": "-",
    "modulo_op": "\\bmod",
    "lt_op": " < ",
    "gt_op": " > ",
    "lte_op": " \\le ",
    "gte_op": " \\ge ",
    "eq_op": " == ",
    "neq_op": " \\ne ",
    "in_op": " \\in ",
    "not_in_op": " \\notin ",
    "is_op": " \\;\\mathrm{is}\\; ",
    "is_not_op": " \\;\\mathrm{is\\ not}\\; ",
    "and_op": "\\;\\mathrm{and}\\;",
    "or_op": "\\;\\mathrm{or}\\;",
}


# Python math functions typeset as LaTeX operators (see ``swap_func_symbols``).
MATH_FUNCS = {
    "sin": "\\sin",
    "cos": "\\cos",
    "tan": "\\tan",
    "sqrt": "\\sqrt",
    "exp": "\\exp",
    "sinh": "\\sinh",
    "tanh": "\\tanh",
    "cosh": "\\cosh",
    "asin": "\\arcsin",
    "acos": "\\arccos",
    "atan": "\\arctan",
    "atan2": "\\arctan",
    "asinh": "\\operatorname{arcsinh}",
    "acosh": "\\operatorname{arccosh}",
    "atanh": "\\operatorname{arctanh}",
}


class LatexRenderer(BaseRenderer):
    """
    Renders a HandCalcs sequence as a LaTeX fragment (requires amsmath) that can
    be pasted into the body of a .tex document.

    Prose (headings, comment paragraphs, imports, block headers) is emitted as
    text-mode paragraphs. Each run of calc lines (a CalcsBlock) becomes one
    flush-left display-style ``aligned`` group, aligned on the first ``=`` of every row. The
    body of a nested block (if/for/def) is indented with a ``list`` environment.

    The class attributes below are the structural tokens; override them in a
    subclass to change the document wrappers.
    """

    name = "latex"

    # Math groups are set flush-left as displaystyle boxes (not centred
    # displays), so they line up with the prose and show a nested block's indent.
    MATH_OPEN = "\\noindent$\\displaystyle\n\\begin{aligned}[t]"
    MATH_CLOSE = "\\end{aligned}$"
    # Vertical space before and after each math group (a box has none of the
    # display skip a centred display gets).
    MATH_SKIP = "\\medskip"
    PARAGRAPH = "\\noindent "
    ROW_SEP = " \\\\\n"
    LINE_BREAK = "\\medskip"
    CONTINUATION_INDENT = "\\quad"
    BLOCK_OPEN = "\\begin{list}{}{\\setlength{\\leftmargin}{1.5em}}\\item[]"
    BLOCK_CLOSE = "\\end{list}"
    # Collections longer than MAX_ITEMS show only their first and last
    # EDGE_ITEMS items (see ``join_items``).
    MAX_ITEMS = 10
    # An inline comment renders as COMMENT_OPEN + text + COMMENT_CLOSE.
    COMMENT_OPEN = "\\quad\\text{("
    COMMENT_CLOSE = ")}"
    EDGE_ITEMS = 3
    HEADINGS = ("section*", "subsection*", "subsubsection*", "paragraph*")
    # Symbol tables used by the swap rules; override in a subclass to change them.
    OPERATOR_SYMBOLS = OPERATOR_SYMBOLS
    MATH_FUNCS = MATH_FUNCS

    def create_context(self, **kwargs):
        # Spacing inside math mode is insignificant, so space/newline stay plain
        # whitespace; all LaTeX structure is added by ``join_item``.
        context = BaseRenderContext(
            global_context=RenderContext(
                space=" ",
                newline="\n",
                indent="",
                lpar="\\left(",
                rpar="\\right)",
                **kwargs,
            ),
            line_context=RenderContext.sparse(),
        )
        return context

    def complete(self, tree: list, base_context: BRC):
        body = self.join(tree, base_context)
        return body.strip() + "\n"

    def join_item(self, item, depth: int, base_context: BRC) -> list[str]:
        """
        LaTeX counterpart of ``BaseRenderer.join_item``. Master-list shapes:

        - bare string -> a text paragraph (headings, the params grid, which is
          already a complete math group); a one-shot line break -> ``\\medskip``;
        - headerless block whose body is opened by MATH_OPEN (a CalcsBlock) ->
          one ``aligned`` math group, rows separated by ``\\\\``, no group at
          all when every row is empty (e.g. all lines ``# hc: -i``);
        - other headerless block (a CommentsBlock) -> its body at this level;
        - ``[header, body]`` -> the header paragraph, then the body indented in
          a ``list`` environment;
        - all-string list -> a text paragraph whose parts join with a space.
        """
        if not item:
            return []
        context = base_context.current
        if isinstance(item, str):
            if not item.strip():
                return [f"{self.LINE_BREAK}\n\n"]
            return [f"{self.paragraph(item)}\n\n"]
        if isinstance(item[-1], list):
            header, body = item[0], item[-1]
            if body and body[0] == self.MATH_OPEN:
                return self.join_math_group(body[1:-1], depth, base_context)
            if not (isinstance(header, str) and header.strip()):
                return self.join_items(body, depth, base_context)
            return [
                f"{self.paragraph(header)}\n\n",
                f"{self.BLOCK_OPEN}\n",
                *self.join_items(body, depth + 1, base_context),
                f"{self.BLOCK_CLOSE}\n\n",
            ]
        joined = context.space.join(item)
        if not joined.strip():
            return []
        return [f"{self.paragraph(joined)}\n\n"]

    def paragraph(self, text: str) -> str:
        """
        Prefix a text paragraph with PARAGRAPH (``\\noindent``) unless it is
        already a complete structural command (a heading or a math group).
        """
        if text.startswith(
            (
                "\\section",
                "\\subsection",
                "\\subsubsection",
                "\\paragraph",
                self.MATH_SKIP,
                self.PARAGRAPH,
            )
        ):
            return text
        return f"{self.PARAGRAPH}{text}"

    def join_math_group(self, rows: list, depth: int, base_context: BRC) -> list[str]:
        """
        Join the rows of a CalcsBlock into a single ``aligned`` math group.
        """
        math_rows = [self.join_math_row(row, base_context) for row in rows]
        math_rows = [row for row in math_rows if row]
        if not math_rows:
            return []
        return [f"{self.math_group(math_rows)}\n\n"]

    def math_group(self, rows: list[str]) -> str:
        """
        Wrap pre-joined ``aligned`` rows in MATH_OPEN/MATH_CLOSE, with MATH_SKIP
        paragraphs before and after.
        """
        body = self.ROW_SEP.join(rows)
        return f"{self.MATH_SKIP}\n{self.MATH_OPEN}\n{body}\n{self.MATH_CLOSE}\n\n{self.MATH_SKIP}"

    def join_math_row(self, row, base_context: BRC) -> str:
        """
        Join one calc line's components into an ``aligned`` row, placing the
        alignment point ``&`` before its first assignment symbol. A string row
        (a pre-formatted multiline grid, or a one-shot line break) passes
        through unchanged; a line break is dropped since rows are already
        separated.

        The inline comment of a calc line that shows substitution columns
        (more than ``target = value``) moves to its own row, at the alignment
        point, so it does not lengthen an already long row.
        """
        context = base_context.current
        if isinstance(row, str):
            return row.strip()
        parts = list(row)
        if parts and parts[0] == "":
            return ""
        comment_row = ""
        if (
            parts
            and parts[-1].startswith(self.COMMENT_OPEN)
            and parts.count(context.assign) > 1
        ):
            comment_row = f"{self.ROW_SEP}&{parts.pop()}"
        if context.assign in parts:
            idx = parts.index(context.assign)
            parts[idx] = f"&{parts[idx]}"
        return context.space.join(parts).strip() + comment_row

    def format_param_grid(self, rows: list, base_context: BRC) -> str:
        """
        A params grid is its own ``aligned`` group, laid out like the v1 params
        cell: each ``id = value [comment]`` cell is an ``r l`` column pair and
        cells are joined by a bare ``&``. As in v1, a thin ``\\;`` after each value
        is the gap between cells. In a grid with comments, a comment sits one ``\\;``
        after its value (its leading ``\\quad`` is dropped) and every non-last cell
        is followed by a ``\\qquad``, so the gap to the next assignment is wider
        than the gap inside a cell, whether or not that cell has a comment.
        """
        _ = base_context.current.space
        has_comments = any(
            cell is not None and len(cell) > 3 and str(cell[3])
            for row in rows
            for cell in row
        )
        lines = []
        for row in rows:
            # ``aligned`` allows ragged rows, so trailing padding cells are dropped.
            row = list(row)
            while row and row[-1] is None:
                row.pop()
            cells = []
            for k, cell in enumerate(row):
                if cell is None:
                    cells.append("&")
                    continue
                ident, eq, val, *comment = list(map(str, cell)) + ["", "", ""]
                text = f"{ident} &{eq}{_}{val}"
                if not has_comments:
                    text += f"{_}\\;"
                else:
                    if comment and comment[0]:
                        text += f"{_}\\;{_}{comment[0].removeprefix(chr(92) + 'quad')}"
                    if k < len(row) - 1:
                        text += f"{_}\\qquad"
                cells.append(text)
            lines.append(f"{_}&".join(cells))
        return self.math_group(lines)

    def format_calc_grid(self, rows: list, base_context: BRC) -> str:
        """
        A multiline (``# hc: -m``) calc: one ``aligned`` row per ``[id, eq, value]``
        triple, all aligned on ``eq``. Returned as a single pre-joined string that
        sits as one row inside its CalcsBlock's math group.

        A row with an empty ``eq`` continues the row above (a line continuation in
        the source) and is indented by ``CONTINUATION_INDENT``. An empty group
        ``{}`` closes the row before it and opens the continuation, so an operator
        at the break keeps its binary spacing.
        """
        _ = base_context.current.space
        lines = []
        for k, (ident, eq, val) in enumerate(rows):
            if not eq:
                val = f"{self.CONTINUATION_INDENT}{_}{{}}{val}"
            if k + 1 < len(rows) and not rows[k + 1][1]:
                val = f"{val}{{}}"
            lines.append(f"{ident}{_}&{eq}{_}{val}".strip())
        return self.ROW_SEP.join(lines)


LR = LatexRenderer


## TEXT-MODE HANDLERS


@LR.register("heading")
def render_heading(renderer: LR, node: Heading, base_context: BRC) -> str:
    level = min(node.heading_level, len(renderer.HEADINGS)) - 1
    return f"\\{renderer.HEADINGS[level]}{{{latex_prose(node.content)}}}"


@LR.register("comment_line")
def render_comment_line(renderer: LR, node: CommentLine, base_context: BRC) -> str:
    return latex_prose(node.content)


@LR.register("import")
def render_import(renderer: LR, node: Import, base_context: BRC) -> str:
    """
    An import renders as a single typewriter line of the Python source.
    """
    return f"\\texttt{{{latex_escape(import_source(node))}}}"


def import_source(node: Import) -> str:
    """The Python source of an import statement, rebuilt from its node."""
    names = ", ".join(
        (
            f"{name.identifier} as {name.value}"
            if name.value is not None
            else f"{name.identifier}"
        )
        for name in node.names
    )
    if node.import_from:
        dots = "." * (node.import_from_level or 0)
        module = node.import_from_module or ""
        source = f"from {dots}{module} import {names}"
    else:
        source = f"import {names}"
    return source


@LR.register("header:if_block")
def if_block_header(renderer: LR, node: IfBlock, base_context: BRC) -> str:
    sym_expr = render_condition(renderer, node.test, base_context, "sym")
    num_expr = render_condition(renderer, node.test, base_context, "num")
    # Fixed-size \\bigl( \\bigr) rather than \\left( \\right): TeX cannot break
    # a line inside a \\left...\\right group, and a long condition must wrap.
    return (
        f"Since $\\bigl({sym_expr}\\bigr) \\rightarrow "
        f"\\bigl({num_expr}\\bigr)$ is True:"
    )


@LR.register("header:for_block")
def for_block_header(renderer: LR, node: ForBlock, base_context: BRC) -> str:
    base_context.line_context.current_mode = "sym"
    target = renderer.render(node.assigns[0], base_context)
    iterable = renderer.render(node.iterator[0], base_context)
    return f"Iterating over each ${target}$ in ${iterable}$:"


@LR.register("header:function_block")
def function_block_header(renderer: LR, node: FunctionBlock, base_context: BRC) -> str:
    base_context.line_context.current_mode = "sym"
    name = "".join(
        renderer.render(part, base_context) if hasattr(part, "type") else str(part)
        for part in node.function_name
    )
    params = ", ".join(str(param) for param in node.params)
    return f"Evaluating ${name}\\left({params}\\right)$:"


@LR.register("function_call")
def render_function_call(renderer: LR, node: FunctionCall, base_context: BRC) -> str:
    """
    A function's name and namespace are symbols, not values, so they render
    symbolically in both columns (``acc.append(11.31)``, not the
    namespace's runtime value). The symbolic pass applies the 'name:sym' swaps
    to the identifiers in place, so the numeric pass reuses those identifiers
    rather than re-rendering (which would apply the non-idempotent swaps twice).
    """
    context = base_context.current
    symbolic = getattr(context, "current_mode", "sym") == "sym"
    namespace_node = node.namespace
    if not namespace_node or getattr(namespace_node, "identifier", None) == "__main__":
        namespace = ""
    elif symbolic:
        namespace = renderer.render(namespace_node, base_context)
    else:
        namespace = getattr(namespace_node, "identifier", "")
    if symbolic:
        function_name = renderer.render(node.function_name, base_context)
    else:
        function_name = node.function_name.identifier
    args = ", ".join(renderer.render(arg, base_context) for arg in node.args)
    prefix = f"{namespace}." if namespace else ""
    return f"{prefix}{function_name}{node.pre}{args}{node.post}"


@LR.register("keyword")
def render_keyword(renderer: LR, node: Keyword, base_context: BRC) -> str:
    """
    A keyword argument. The keyword is a symbol in both columns, typeset like
    an identifier (``days=3`` -> ``\\mathrm{days} = 3``); a ``**mapping``
    unpacking renders as ``\\ast\\ast`` before the mapping.
    """
    value = renderer.render(node.value, base_context)
    if node.arg is None:
        return f"\\ast\\ast {value}"
    return f"{latex_identifier(node.arg, renderer.GREEK_PREFIXES)} = {value}"


@LR.register("calcs_block:pre")
def calcs_block_pre_post(
    renderer: LR, node: CalcsBlock, base_context: BRC
) -> CalcsBlock:
    """
    Marks the body of a CalcsBlock as a math group: ``join_item`` recognises
    the MATH_OPEN/MATH_CLOSE sentinels and joins the rows between them as one
    ``aligned`` environment.
    """
    node.body_pre = renderer.MATH_OPEN
    node.body_post = renderer.MATH_CLOSE
    return node


## SWAP RULES


@LR.register("name:sym")
def swap_identifier(renderer: LR, node: Name, base_context: BRC) -> Name:
    """
    Typeset a Name's identifier (see ``latex_identifier``).

    Registered as a 'sym' rule on the Name node: the identifier is only shown in
    symbolic mode (numeric mode renders the Name's value instead).
    """
    node.identifier = latex_identifier(node.identifier, renderer.GREEK_PREFIXES)
    return node


@LR.register("attribute")
def render_attribute(renderer: LR, node: Attribute, base_context: BRC) -> str:
    """
    An attribute access. Math-library namespaces are dropped so that constants
    read as symbols (``math.pi`` -> ``\\pi``); any other namespace is kept and
    typeset like a Name (``\\mathrm{beam}.\\mathrm{length}``). The numeric
    column shows the captured value, as for a Name.
    """
    context = base_context.current
    if context.current_mode == "num" and not isinstance(node.value, NoValue):
        return renderer.render_node(node.value, base_context)
    identifier = MATH_CONSTANTS.get(node.identifier) or latex_identifier(
        node.identifier, renderer.GREEK_PREFIXES
    )
    namespace = node.namespace
    if namespace in ("", "__main__", None) or namespace in MATH_NAMESPACES:
        return identifier
    namespace = ".".join(
        latex_identifier(part, renderer.GREEK_PREFIXES) for part in namespace.split(".")
    )
    return f"{namespace}.{identifier}"


@LR.register("mult_op:pre")
@LR.register("add_op:pre")
@LR.register("sub_op:pre")
@LR.register("modulo_op:pre")
@LR.register("lt_op:pre")
@LR.register("gt_op:pre")
@LR.register("lte_op:pre")
@LR.register("gte_op:pre")
@LR.register("eq_op:pre")
@LR.register("neq_op:pre")
@LR.register("in_op:pre")
@LR.register("not_in_op:pre")
@LR.register("is_op:pre")
@LR.register("is_not_op:pre")
@LR.register("and_op:pre")
@LR.register("or_op:pre")
def swap_operator_symbols(renderer: LR, node: HcNode, base_context: BRC) -> HcNode:
    """
    Swap an operator's Python symbol for its LaTeX form.

    The symbol is looked up by node type (not by its current symbol), so the
    swap is idempotent across the symbolic and numeric passes. Comparison and
    membership symbols carry their own spacing because Compare joins its parts
    with no separator.
    """
    node.symbol = renderer.OPERATOR_SYMBOLS[node.type]
    return node


@LR.register("unary_op:pre")
def swap_unary_not(renderer: LR, node: HcUnaryOp, base_context: BRC) -> HcUnaryOp:
    if node.symbol.strip() == "not":
        node.symbol = "\\mathrm{not}\\;"
    return node


def _wrap_signed(rendered: str, base_context: BRC) -> str:
    """Parenthesise an operand that renders with a leading sign."""
    context = base_context.current
    if rendered.lstrip().startswith(("-", "+")):
        return f"{context.lpar}{rendered}{context.rpar}"
    return rendered


@LR.register("pow_op")
def render_pow_op(renderer: LR, node: PowOp, base_context: BRC) -> str:
    """
    ``{base}^{exponent}``. The exponent is braced, so it never needs parens. The
    base is parenthesised when it binds no tighter than the power (including a
    left-nested power, since ``**`` is right-associative) or renders signed.
    """
    context = base_context.current
    base = renderer.render_node(node.left, base_context)
    exponent = renderer.render_node(node.right, base_context)
    base_pre = OP_PRECEDENCE.get(type(node.left), float("inf"))
    if base_pre <= OP_PRECEDENCE[PowOp]:
        base = f"{context.lpar}{base}{context.rpar}"
    else:
        base = _wrap_signed(base, base_context)
    return f"{base}^{{{exponent}}}"


@LR.register("div_op")
def render_div_op(renderer: LR, node: DivOp, base_context: BRC) -> str:
    """``\\frac{num}{den}``: the fraction bar groups both operands, so no parens."""
    numerator = renderer.render_node(node.left, base_context)
    denominator = renderer.render_node(node.right, base_context)
    return f"\\frac{{{numerator}}}{{{denominator}}}"


@LR.register("floor_op")
def render_floor_op(renderer: LR, node: FloorOp, base_context: BRC) -> str:
    numerator = renderer.render_node(node.left, base_context)
    denominator = renderer.render_node(node.right, base_context)
    return f"\\left\\lfloor\\frac{{{numerator}}}{{{denominator}}}\\right\\rfloor"


## VALUES


def format_latex_number(value, format_code: str) -> str:
    """
    Format a real number with ``format_code`` and typeset any exponent as
    ``\times 10^{n}`` (e.g. ``2e+05`` -> ``2 \times 10^{5}``).
    """
    try:
        formatted = f"{value:{format_code}}"
    except (ValueError, TypeError):
        formatted = f"{value}"
    return typeset_latex_number(formatted)


def typeset_latex_number(formatted: str) -> str:
    """
    Typeset a number already written out as text: any exponent becomes
    ``\times 10^{n}`` and infinities and NaN get their maths symbols.
    """
    if formatted in ("inf", "+inf"):
        return "\\infty"
    if formatted == "-inf":
        return "-\\infty"
    if formatted == "nan":
        return "\\mathrm{NaN}"
    mantissa, sep, exponent = formatted.lower().partition("e")
    if not sep:
        return formatted
    try:
        power = int(exponent)
    except ValueError:
        return formatted
    if mantissa in ("1", "1.0"):
        return f"10^{{{power}}}"
    return f"{mantissa} \\times 10^{{{power}}}"


@LR.register("constant")
def render_constant(renderer: LR, node: Constant, base_context: BRC) -> str:
    value = node.value
    fc = base_context.current.format_code
    if isinstance(value, bool) or value is None:
        return f"\\mathrm{{{value}}}"
    # A number literal from the source keeps its digits as written (the format
    # code is for calculated values); only an exponent is typeset.
    # (A hex, octal or binary literal has no exponent: 0xe5 is not 0x * 10^5.)
    if is_source_number(node):
        text = literal_text(node)
        if isinstance(value, complex) or text.lower().startswith(("0x", "0o", "0b")):
            return text
        return typeset_latex_number(text)
    if isinstance(value, str):
        return f"\\text{{``{latex_escape(value)}''}}"
    if isinstance(value, complex):
        real = format_latex_number(value.real, fc)
        imag = format_latex_number(abs(value.imag), fc)
        sign = "-" if value.imag < 0 else "+"
        if value.real == 0:
            return f"{'-' if value.imag < 0 else ''}{imag}j"
        return f"{real} {sign} {imag}j"
    if isinstance(value, (int, float)):
        return format_latex_number(value, fc)
    return latex_escape(f"{value}")


def join_items(renderer: LR, items: list[str]) -> str:
    """
    Comma-join a collection's rendered items. An ``aligned`` row cannot
    break, so a collection with more than MAX_ITEMS items is elided to its
    first and last EDGE_ITEMS items around ``\\ldots``.
    """
    edge = renderer.EDGE_ITEMS
    if len(items) > renderer.MAX_ITEMS:
        items = [*items[:edge], "\\ldots", *items[-edge:]]
    return ", ".join(items)


@LR.register("list")
def render_list(renderer: LR, node: List, base_context: BRC) -> str:
    elems = [renderer.render(elem, base_context) for elem in node.elems]
    return f"[{join_items(renderer, elems)}]"


@LR.register("tuple")
def render_tuple(renderer: LR, node: Tuple, base_context: BRC) -> str:
    elems = [renderer.render(elem, base_context) for elem in node.elems]
    return f"({join_items(renderer, elems)})"


@LR.register("set")
def render_set(renderer: LR, node: Set, base_context: BRC) -> str:
    elems = [renderer.render(elem, base_context) for elem in node.elems]
    return f"\\{{{join_items(renderer, elems)}\\}}"


@LR.register("dictionary")
def render_dictionary(renderer: LR, node: Dictionary, base_context: BRC) -> str:
    keys = [renderer.render(elem, base_context) for elem in node.keys]
    values = [renderer.render(elem, base_context) for elem in node.values]
    items = [f"{key}\\colon {value}" for key, value in zip(keys, values)]
    return f"\\{{{join_items(renderer, items)}\\}}"


@LR.register("inline_comment")
def render_inline_comment(renderer: LR, node: InlineComment, base_context: BRC) -> str:
    return f"{renderer.COMMENT_OPEN}{latex_prose(node.content)}{renderer.COMMENT_CLOSE}"


MATH_CONSTANTS = {
    "pi": "\\pi",
    "tau": "\\tau",
    "e": "e",
    "inf": "\\infty",
    "nan": "\\mathrm{NaN}",
}


@LR.register("attribute:sym")
def swap_math_constants(renderer: LR, node: Attribute, base_context: BRC) -> Attribute:
    """
    Show a math/numpy constant as its symbol (``math.pi`` -> ``\\pi``),
    dropping the module namespace. Idempotent: once swapped, the namespace is
    empty and the rule no longer matches.
    """
    if (
        node.namespace in ("math", "cmath", "numpy", "np")
        and node.identifier in MATH_CONSTANTS
    ):
        node.namespace = ""
        node.identifier = MATH_CONSTANTS[node.identifier]
    return node


@LR.register("function_call:pre")
def swap_func_symbols(
    renderer: LR, node: FunctionCall, base_context: BRC
) -> FunctionCall:
    """
    Swap function names for special function symbols in Latex. e.g. swap a ``sqrt(...)`` call's
    function name for the '\\sqrt{}' symbol.

    Registered as a 'pre' rule on function_call: the function name is shown in
    both symbolic and numeric columns, so the swap must be mode-independent. The
    mutation is idempotent across the two render passes.
    """
    # This rule runs on both the symbolic and numeric passes over the same node.
    # A name that has already been swapped (a LaTeX command, or emptied for
    # floor/ceil) must be left alone so the second pass does not re-wrap it.
    identifier = node.function_name.identifier
    if identifier == "" or identifier.startswith("\\"):
        return node
    node.pre = "\\left("
    node.post = "\\right)"
    # A math-library prefix reads as noise on a math function (e.g.
    # 'math.\\lfloor x\\rfloor'), so drop the namespace, as for attributes.
    if getattr(node.namespace, "identifier", None) in MATH_NAMESPACES:
        node.namespace = deque()
    if node.function_name.identifier == "sqrt":
        node.function_name.identifier = "\\sqrt"
        node.function_name.value = "\\sqrt"
        node.pre = "{"
        node.post = "}"
    elif node.function_name.identifier == "floor":
        node.function_name.identifier = ""
        node.function_name.value = ""
        node.pre = "\\lfloor "
        node.post = "\\rfloor"
    elif node.function_name.identifier == "ceil":
        node.function_name.identifier = ""
        node.function_name.value = ""
        node.pre = "\\lceil "
        node.post = "\\rceil"
    elif node.function_name.identifier in renderer.MATH_FUNCS:
        func_identifier = node.function_name.identifier
        latex_func_name = renderer.MATH_FUNCS[func_identifier]
        node.function_name.identifier = latex_func_name
        node.function_name.value = latex_func_name
    else:
        # A method (one that keeps its namespace) is set upright with ordinary
        # spacing; \\operatorname would add an operator's gap after the '.'.
        new_func_name = node.function_name.identifier.replace("_", "\\_")
        is_method = getattr(node.namespace, "identifier", "") not in ("", "__main__")
        wrapper = "\\mathrm" if is_method else "\\operatorname"
        wrapped_func_name = f"{wrapper}{{{new_func_name}}}"
        node.function_name.identifier = wrapped_func_name
        node.function_name.value = wrapped_func_name
    return node
