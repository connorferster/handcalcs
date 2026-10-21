"""Index lookups shown in brackets, as written in the code, instead of as subscripts."""
from handcalcs.renderers import MarkdownRenderer


class BracketMarkdownRenderer(MarkdownRenderer):
    """xs[0] in brackets rather than as xs with subscript 0."""


@BracketMarkdownRenderer.register("subscript:pre")
def brackets(renderer, node, base_context):
    node.labels = None  # without subscript labels, the lookup is shown in brackets
    return node
