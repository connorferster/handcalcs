"""A custom context field read by a rule: '# hc: flag = "..."' marks lines."""
from handcalcs.renderers import ASCIIRenderer


class FlagASCIIRenderer(ASCIIRenderer):
    """ASCII output that can mark lines with a note."""


@FlagASCIIRenderer.register("calc_line:post")
def flag_line(renderer, rendered, node, base_context):
    # A line's own commands are reset before 'post' rules run, so read them from the line.
    commands = getattr(node.comment, "commands", None) or {}
    flag = commands.get("flag", getattr(base_context.current, "flag", None))
    if not flag:
        return rendered
    if isinstance(rendered, list):
        return rendered + [f"<-- {flag}"]
    return rendered + f"  <-- {flag}"  # a multi-line (# hc: -m) calc is one string
