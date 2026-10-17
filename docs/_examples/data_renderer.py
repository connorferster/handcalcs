"""
A renderer whose output is data, not text: a list of dicts that a web front-end
(or a template) can lay out however it likes. It keeps the Unicode symbol rules
of PlainTextRenderer and replaces the line handlers and complete().
"""
from handcalcs.renderers import PlainTextRenderer
from handcalcs.renderers.base import RenderContext


class DataRenderer(PlainTextRenderer):
    name = "data"

    def complete(self, tree, base_context):
        """Flatten the render tree into a list of dicts."""
        return list(self._entries(tree))

    def _entries(self, items):
        for item in items:
            if not item:
                continue  # an ignored line, a command, a spacer
            if isinstance(item, dict):
                yield item
            elif isinstance(item, str):
                yield {"kind": "text", "text": item}
            elif all(isinstance(part, str) for part in item):  # a line's parts
                yield {"kind": "text", "text": " ".join(item)}
            elif isinstance(item[-1], list):  # a block: [header, body]
                header, body = item[0], item[-1]
                body = list(self._entries(body))
                if header.strip():
                    yield {"kind": "block", "header": header, "body": body}
                else:
                    yield from body  # a headerless group of lines


def columns(renderer, nodes, mode, base_context):
    base_context.line_context.current_mode = mode
    return ", ".join(renderer.render(node, base_context) for node in nodes)


@DataRenderer.register("calc_line")
def calc_line(renderer, node, base_context):
    # Render the comment first: an inline ``# hc:`` command sets the line context.
    comment = renderer.render(node.comment, base_context) if node.comment else ""
    context = base_context.current
    if getattr(context, "ignore", False):
        base_context.line_context = RenderContext.sparse()
        return None
    entry = {
        "kind": "param" if getattr(context, "param_line", False) else "calc",
        "target": columns(renderer, node.assigns, "sym", base_context),
        "result": columns(renderer, node.assigns, "num", base_context),
        "comment": comment,
    }
    if entry["kind"] == "calc":
        base_context.line_context.current_mode = "sym"
        entry["symbolic"] = "".join(renderer.render(n, base_context) for n in node.expression_tree)
        base_context.line_context.current_mode = "num"
        entry["numeric"] = "".join(renderer.render(n, base_context) for n in node.expression_tree)
    base_context.line_context = RenderContext.sparse()  # end of the line's overrides
    return entry


@DataRenderer.register("params_block")
def params_block(renderer, node, base_context):
    cells = []
    for line in node.lines:
        base_context.line_context.param_line = True
        cells.append(renderer.render(line, base_context))
    return {"kind": "params", "cells": [cell for cell in cells if cell]}


@DataRenderer.register("heading")
def heading(renderer, node, base_context):
    return {"kind": "heading", "level": node.heading_level, "text": node.content}


@DataRenderer.register("inline_comment")
def inline_comment(renderer, node, base_context):
    return node.content
