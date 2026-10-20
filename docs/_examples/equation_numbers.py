"""Equation numbers on calculation lines (#218)."""
from handcalcs.renderers import LatexRenderer, MarkdownRenderer


def number_equations(renderer, rendered, node, base_context):
    """
    '# hc: eq_numbers = True' numbers every calculated line (1), (2), ...
    'x = ...  # hc: label = "4.2"' gives one line its own number.
    """
    commands = getattr(node.comment, "commands", None) or {}
    label = commands.get("label")
    # A parameter (target = value) has one assign symbol; a calculation has two or more.
    is_param = isinstance(rendered, list) and rendered.count(base_context.current.assign) < 2
    if label is None and getattr(base_context.current, "eq_numbers", False) and not is_param:
        count = getattr(base_context.global_context, "eq_count", 0) + 1
        base_context.global_context.eq_count = count
        label = count
    if label is None:
        return rendered
    tag = f"\\qquad ({label})"
    if isinstance(rendered, list):
        # Tag the result, which is right after the last assign symbol (a comment may follow it).
        assign = base_context.current.assign
        result = max(i for i, part in enumerate(rendered) if part == assign) + 1
        rendered[result] = rendered[result] + tag
        return rendered
    return rendered + tag  # a multi-line (# hc: -m) calc is one string


class NumberedMarkdownRenderer(MarkdownRenderer):
    name = "numbered_markdown"


class NumberedLatexRenderer(LatexRenderer):
    name = "numbered_latex"


NumberedMarkdownRenderer.register("calc_line:post")(number_equations)
NumberedLatexRenderer.register("calc_line:post")(number_equations)
