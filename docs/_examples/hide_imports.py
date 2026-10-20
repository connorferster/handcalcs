"""Per-instance customization: one MarkdownRenderer that hides import lines."""
from handcalcs.renderers import MarkdownRenderer


def hide_import(renderer, node, base_context):
    return ""


def make_renderer():
    renderer = MarkdownRenderer()
    renderer.register_handler("import", hide_import)
    return renderer
