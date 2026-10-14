from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Any
from handcalcs.renderers.base import BaseRenderer, RenderContext, BaseRenderContext, ContextKeyError, ContextValueError, render_condition


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


class LatexRenderer(BaseRenderer):
    """
    Renders a HandCalcs sequence as a LaTeX fragment (requires amsmath) that can
    be pasted into the body of a .tex document.

    Prose (headings, comment paragraphs, imports, block headers) is emitted as
    text-mode paragraphs. Each run of calc lines (a CalcsBlock) becomes one
    display-math ``aligned`` group, aligned on the first ``=`` of every row. The
    body of a nested block (if/for/def) is indented with a ``list`` environment.

    The class attributes below are the structural tokens; override them in a
    subclass to change the document wrappers.
    """
    name = 'latex'

    MATH_OPEN = "\\[\n\\begin{aligned}"
    MATH_CLOSE = "\\end{aligned}\n\\]"
    # Inside a nested block a centred display would hide the indentation, so
    # the group is set flush-left at the block's indent as a displaystyle box.
    NESTED_MATH_OPEN = "\\noindent$\\displaystyle\n\\begin{aligned}[t]"
    NESTED_MATH_CLOSE = "\\end{aligned}$"
    PARAGRAPH = "\\noindent "
    ROW_SEP = " \\\\\n"
    LINE_BREAK = "\\medskip"
    BLOCK_OPEN = "\\begin{list}{}{\\setlength{\\leftmargin}{1.5em}}\\item[]"
    BLOCK_CLOSE = "\\end{list}"
    HEADINGS = ("section*", "subsection*", "subsubsection*", "paragraph*")

    def create_context(
        self,
        **kwargs
    ):
        # Spacing inside math mode is insignificant, so space/newline stay plain
        # whitespace; all LaTeX structure is added by ``join_item``.
        context = BaseRenderContext(
            global_context=RenderContext(
                space=' ',
                newline='\n',
                indent='',
                lpar="\\left(",
                rpar="\\right)",
                **kwargs
            ),
            line_context=RenderContext.sparse()
        )
        return context

    def complete(
        self, tree: list, base_context: BRC
    ):
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
        if text.startswith(("\\section", "\\subsection", "\\subsubsection",
                            "\\paragraph", "\\[", self.PARAGRAPH)):
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
        opener, closer = self.MATH_OPEN, self.MATH_CLOSE
        if depth > 0:
            opener, closer = self.NESTED_MATH_OPEN, self.NESTED_MATH_CLOSE
        return [f"{opener}\n{self.ROW_SEP.join(math_rows)}\n{closer}\n\n"]

    def join_math_row(self, row, base_context: BRC) -> str:
        """
        Join one calc line's components into an ``aligned`` row, placing the
        alignment point ``&`` before its first assignment symbol. A string row
        (a pre-formatted multiline grid, or a one-shot line break) passes
        through unchanged; a line break is dropped since rows are already
        separated.
        """
        context = base_context.current
        if isinstance(row, str):
            return row.strip()
        parts = list(row)
        if parts and parts[0] == "":
            return ""
        if context.assign in parts:
            idx = parts.index(context.assign)
            parts[idx] = f"&{parts[idx]}"
        return context.space.join(parts).strip()

    def format_param_grid(self, rows: list, base_context: BRC) -> str:
        """
        A params grid is its own ``aligned`` group: each ``id = value`` cell is
        an aligned pair of columns, with a ``\\qquad`` gap between cells.
        """
        context = base_context.current
        _ = context.space
        lines = []
        for row in rows:
            cells = []
            for cell in row:
                if cell is None:
                    cells.append("&")
                    continue
                ident, eq, val = (list(map(str, cell)) + ["", "", ""])[:3]
                cells.append(f"{ident} &{eq}{_}{val}")
            lines.append(f"{_}&\\qquad{_}".join(cells))
        return f"{self.MATH_OPEN}\n{self.ROW_SEP.join(lines)}\n{self.MATH_CLOSE}"

    def format_calc_grid(self, rows: list, base_context: BRC) -> str:
        """
        A multiline (``# hc: -m``) calc: one ``aligned`` row per ``[id, eq, value]``
        triple, all aligned on ``eq``. Returned as a single pre-joined string that
        sits as one row inside its CalcsBlock's math group.
        """
        _ = base_context.current.space
        lines = [f"{ident}{_}&{eq}{_}{val}".strip() for ident, eq, val in rows]
        return self.ROW_SEP.join(lines)


LR = LatexRenderer


## TEXT-MODE HANDLERS

@LR.register('heading')
def render_heading(renderer: LR, node: Heading, base_context: BRC) -> str:
    level = min(node.heading_level, len(renderer.HEADINGS)) - 1
    return f"\\{renderer.HEADINGS[level]}{{{latex_escape(node.content)}}}"


@LR.register('comment_line')
def render_comment_line(renderer: LR, node: CommentLine, base_context: BRC) -> str:
    return latex_escape(node.content)


@LR.register('import')
def render_import(renderer: LR, node: Import, base_context: BRC) -> str:
    """
    An import renders as a single typewriter line of the Python source.
    """
    names = ", ".join(
        f"{name.identifier} as {name.value}" if name.value is not None
        else f"{name.identifier}"
        for name in node.names
    )
    if node.import_from:
        dots = "." * (node.import_from_level or 0)
        module = node.import_from_module or ""
        source = f"from {dots}{module} import {names}"
    else:
        source = f"import {names}"
    return f"\\texttt{{{latex_escape(source)}}}"


@LR.register("header:if_block")
def if_block_header(renderer: LR, node: IfBlock, base_context: BRC) -> str:
    sym_expr = render_condition(renderer, node.test, base_context, 'sym')
    num_expr = render_condition(renderer, node.test, base_context, 'num')
    return (
        f"Since $\\left({sym_expr}\\right) \\rightarrow "
        f"\\left({num_expr}\\right)$ is True:"
    )


@LR.register("header:for_block")
def for_block_header(renderer: LR, node: ForBlock, base_context: BRC) -> str:
    base_context.line_context.current_mode = 'sym'
    target = renderer.render(node.assigns[0], base_context)
    iterable = renderer.render(node.iterator[0], base_context)
    return f"Iterating over each ${target}$ in ${iterable}$:"


@LR.register("header:function_block")
def function_block_header(renderer: LR, node: FunctionBlock, base_context: BRC) -> str:
    base_context.line_context.current_mode = 'sym'
    name = "".join(
        renderer.render(part, base_context) if hasattr(part, 'type') else str(part)
        for part in node.function_name
    )
    params = ", ".join(str(param) for param in node.params)
    return f"Evaluating ${name}\\left({params}\\right)$:"


@LR.register('calcs_block:pre')
def calcs_block_pre_post(renderer: LR, node: CalcsBlock, base_context: BRC) -> CalcsBlock:
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
def swap_greeks(renderer: LR, node: Name, base_context: BRC) -> HcNode:
    """
    Swaps out any greek substrings or unicode symbols in a Name's identifier.

    Registered as a 'sym' rule on the Name node: the identifier is only shown in
    symbolic mode (numeric mode renders the Name's value instead).
    """
    GREEK_LOWER = {
        "alpha": "\\alpha",
        "beta": "\\beta",
        "gamma": "\\gamma",
        "delta": "\\delta",
        "epsilon": "\\epsilon",
        "varepsilon": "\\varepsilon",
        "zeta": "\\zeta",
        "theta": "\\theta",
        "vartheta": "\\vartheta",
        "iota": "\\iota",
        "kappa": "\\kappa",
        "mu": "\\mu",
        "nu": "\\nu",
        "xi": "\\xi",
        "omicron": "\\omicron",
        "pi": "\\pi",
        "varpi": "\\varpi",
        "rho": "\\rho",
        "varrho": "\\varrho",
        "sigma": "\\sigma",
        "varsigma": "\\varsigma",
        "tau": "\\tau",
        "upsilon": "\\upsilon",
        "phi": "\\phi",
        "varphi": "\\varphi",
        "chi": "\\chi",
        "omega": "\\omega",
        "eta": "\\eta",
        "psi": "\\psi",
        "lamb": "\\lambda",
    }

    GREEK_UPPER = {
        "Alpha": "\\Alpha",
        "Beta": "\\Beta",
        "Gamma": "\\Gamma",
        "Delta": "\\Delta",
        "Epsilon": "\\Epsilon",
        "Zeta": "\\Zeta",
        "Theta": "\\Theta",
        "Iota": "\\Iota",
        "Kappa": "\\Kappa",
        "Mu": "\\Mu",
        "Nu": "\\Nu",
        "Xi": "\\Xi",
        "Omicron": "\\Omicron",
        "Pi": "\\Pi",
        "Rho": "\\Rho",
        "Sigma": "\\Sigma",
        "Tau": "\\Tau",
        "Upsilon": "\\Upsilon",
        "Phi": "\\Phi",
        "Chi": "\\Chi",
        "Omega": "\\Omega",
        "Eta": "\\Eta",
        "Psi": "\\Psi",
        "Lamb": "\\Lambda",
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
    
    
@LR.register("mult_op:pre")
@LR.register("pow_op:pre")
@LR.register("div_op:pre")
@LR.register("floor_op:pre")
@LR.register("add_op:pre")
@LR.register("sub_op:pre")
@LR.register("mod_op:pre")
def swap_py_operators(renderer: LR, node: HcBinOp, base_context: BRC) -> HcBinOp:
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
        node.symbol = '\\cdot'
        node.pre = ''
        node.post = ''
        return node
    elif node.type == 'div_op':
        # Division always renders with its '/' symbol. Any parentheses around an
        # operand come from the infix precedence logic (lpar/rpar), not from
        # pre/post, so pre/post stay empty regardless of operand type.
        node.symbol = "}{"
        node.pre = "\\frac{"
        node.post = "}"
        return node
    elif node.type == 'floor_op':
        node.symbol = '}{'
        node.pre = '\\lfloor \\frac{'
        node.post = '} \\rfloor'
        return node
    elif node.type == 'add_op':
        node.symbol = '+'
        return node
    elif node.type == 'mod_op':
        node.symbol = '\\bmod'
    elif node.type == 'sub_op':
        node.symbol = '-'
        return node
    elif node.type == 'pow_op' and isinstance(node.right, Constant):
        node.symbol = '^{'
        node.post = '}'
        return node
    else:
        return node


@LR.register("gt_op:pre")
@LR.register("lt_op:pre")
@LR.register("gte_op:pre")
@LR.register("lte_op:pre")
@LR.register("neq_op:pre")
def swap_angle_ops(renderer: LR, node: HcCompOp, base_context: BRC) -> HcCompOp:
    """
    Swaps the <=, >= and != operator symbols for their LaTeX commands.

    Compare joins its parts with no separator, so each command carries a
    trailing space: without it '\\ne' followed by 'r' would read as '\\ner'.
    """
    context = base_context.current
    _ = context.space
    if node.symbol == "<=":
        node.symbol = f"{_} \\le {_}"
    elif node.symbol == ">=":
        node.symbol = f"{_} \\ge {_}"
    elif node.symbol == "!=":
        node.symbol = f"{_} \\ne {_}"
    elif node.symbol == "<":
        node.symbol = f"{_} < {_}"
    elif node.symbol == ">":
        node.symbol = f"{_} > {_}"
    elif node.symbol == "==":
        node.symbol = f"{_} == {_}"
    return node


@LR.register("name:sym")
def swap_subscripts(renderer: LR, node: Name, base_context: BRC) -> Name:
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
    name_elems = identifier.split("_")

    # If any of the elements of the identifier qualify as being "long" elements
    # (words that should not be italicized as a typical math symbol)
    if test_for_long_var_strs(name_elems[0], BRC):
        name_elems[0] = f"\\mathrm{{{name_elems[0]}}}"
    identifier = "_".join(name_elems)

    # Do the subscript substitution
    identifier = identifier.replace("_", "_{")
    closers = "}" * under_count
    identifier = f"{identifier}{closers}"

    # Replace the other subscript options (the double and triple)
    identifier = identifier.replace("^", _)
    identifier = identifier.replace("|", "_")

    # Ready to ship!
    node.identifier = identifier
    return node



@LR.register("function_call:pre")
def swap_func_symbols(renderer: LR, node: FunctionCall, base_context: BRC) -> FunctionCall:
    """
    Swap function names for special function symbols in Latex. e.g. swap a ``sqrt(...)`` call's 
    function name for the '\\sqrt{}' symbol.

    Registered as a 'pre' rule on function_call: the function name is shown in
    both symbolic and numeric columns, so the swap must be mode-independent. The
    mutation is idempotent across the two render passes.
    """
    latex_math_funcs = {
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
        "asinh": "\\arcsinh",
        "acosh": "\\arccosh",
        "atanh": "\\arctanh",
    }
    # This rule runs on both the symbolic and numeric passes over the same node.
    # A name that has already been swapped (a LaTeX command, or emptied for
    # floor/ceil) must be left alone so the second pass does not re-wrap it.
    identifier = node.function_name.identifier
    if identifier == '' or identifier.startswith('\\'):
        return node
    node.pre = '\\left('
    node.post = '\\right)'
    # sqrt, floor and ceil render as bare symbols, where a 'math.' prefix
    # reads as noise (e.g. 'math.\\lfloor x\\rfloor'), so drop the namespace.
    if (
        identifier in ('sqrt', 'floor', 'ceil')
        and getattr(node.namespace, 'identifier', None) == 'math'
    ):
        node.namespace = deque()
    if node.function_name.identifier == 'sqrt':
        node.function_name.identifier = '\\sqrt'
        node.function_name.value = '\\sqrt'
        node.pre = '{'
        node.post = '}'
    elif node.function_name.identifier == 'floor':
        node.function_name.identifier = ''
        node.function_name.value = ''
        node.pre = '\\lfloor '
        node.post = '\\rfloor'
    elif node.function_name.identifier == 'ceil':
        node.function_name.identifier = ''
        node.function_name.value = ''
        node.pre = '\\lceil '
        node.post = '\\rceil'
    elif node.function_name.identifier in latex_math_funcs:
        func_identifier = node.function_name.identifier
        latex_func_name = latex_math_funcs.get(func_identifier)
        node.function_name.identifier = latex_func_name
        node.function_name.value = latex_func_name
    else:
        new_func_name = node.function_name.identifier
        wrapped_func_name = f"\\operatorname{{{new_func_name}}} "
        node.function_name.identifier = wrapped_func_name
        node.function_name.value = wrapped_func_name
    return node


def test_for_long_var_strs(elem: str, base_context: BRC) -> bool:
    """
    Returns True if 'elem' is a variable string that has more than one character
    in it's "top-level" name (as opposed to it's subscript).
    False, otherwise.

    e.g. elem = "Rate_annual" -> True
         elem = "x_rake_red" -> False
         elem = "AB_x_y" -> True
         elem = "category_x" -> True
         elem = "x" -> False
         elem = "xy" -> True
    """
    if not elem or "\\" in elem or "{" in elem or "}" in elem:
        return False
    components = elem.replace("'", "").split("_")
    if len(components) != 1:
        top_level, *_remainders = components
        if not getattr(base_context.current, "underscore_subscripts", True):
            if len(top_level) + len(_remainders) == 1:
                return False
            else:
                return True
        else:
            if len(top_level) > 1:
                return True
            else:
                return False
    if len(components[0]) == 1:
        return False
    return True