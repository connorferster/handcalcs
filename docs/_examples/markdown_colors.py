"""A MarkdownRenderer that colors results and comments."""
from handcalcs.renderers import MarkdownRenderer


class ColorMarkdownRenderer(MarkdownRenderer):
    name = "color_markdown"

    RESULT_COLOR = "teal"
    COMMENT_COLOR = "gray"


@ColorMarkdownRenderer.register("calc_line:post")
def color_result(renderer, rendered, node, base_context):
    """Color the result of a calculation with \\color (MathJax and KaTeX)."""
    if not isinstance(rendered, list):
        return rendered
    assign = base_context.current.assign
    positions = [i for i, part in enumerate(rendered) if part == assign]
    if len(positions) < 2:
        return rendered  # a parameter (target = value): leave inputs plain
    result = positions[-1] + 1
    rendered[result] = f"\\color{{{renderer.RESULT_COLOR}}}{{{rendered[result]}}}"
    return rendered


@ColorMarkdownRenderer.register("inline_comment:post")
def color_comment(renderer, rendered, node, base_context):
    """Color inline comments with \\color (MathJax and KaTeX)."""
    body = rendered.removeprefix("\\quad")
    return f"\\quad\\color{{{renderer.COMMENT_COLOR}}}{{{body}}}"
