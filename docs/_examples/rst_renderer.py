"""
A reStructuredText renderer: LaTeX math in ``.. math::`` directives, reST
headings, and indented block bodies. Built on LatexRenderer by changing its
tokens, a few handlers and the join step.
"""
import re

from handcalcs.renderers import LatexRenderer

INDENT = "   "
UNDERLINES = "=-~^\""
# The inherited block headers ("Since $...$ is True:") use LaTeX inline math.
INLINE_MATH = re.compile(r"\$(.+?)\$")


class RstRenderer(LatexRenderer):
    name = "rst"

    # Inside a math group the rows are plain LaTeX; ``math_group`` below wraps
    # them in the directive.
    MATH_OPEN = "\\begin{aligned}"
    MATH_CLOSE = "\\end{aligned}"
    MATH_SKIP = ""
    PARAGRAPH = ""
    LINE_BREAK = "|"  # a reST line block with one empty line

    def math_group(self, rows):
        body = self.ROW_SEP.join(rows)
        lines = [self.MATH_OPEN, *body.split("\n"), self.MATH_CLOSE]
        return ".. math::\n\n" + "\n".join(INDENT + line for line in lines)

    def paragraph(self, text):
        return text

    def join_item(self, item, depth, base_context):
        """A block body becomes an indented (block-quoted) paragraph group."""
        if item and isinstance(item, list) and isinstance(item[-1], list):
            header, body = item[0], item[-1]
            is_math = bool(body) and body[0] == self.MATH_OPEN
            if not is_math and isinstance(header, str) and header.strip():
                inner = "".join(self.join_items(body, depth + 1, base_context))
                indented = "\n".join(
                    INDENT + line if line else line for line in inner.strip("\n").split("\n")
                )
                header = INLINE_MATH.sub(r":math:`\1`", header)
                return [f"{header}\n\n", f"{indented}\n\n"]
        return super().join_item(item, depth, base_context)

    def complete(self, tree, base_context):
        return self.join(tree, base_context).strip() + "\n"


@RstRenderer.register("heading")
def rst_heading(renderer, node, base_context):
    underline = UNDERLINES[min(node.heading_level, len(UNDERLINES)) - 1]
    return f"{node.content}\n{underline * len(node.content)}"


@RstRenderer.register("comment_line")
def rst_comment_line(renderer, node, base_context):
    return node.content


@RstRenderer.register("import")
def rst_import(renderer, node, base_context):
    names = ", ".join(name.identifier for name in node.names)
    if node.import_from:
        return f"``from {node.import_from_module} import {names}``"
    return f"``import {names}``"
