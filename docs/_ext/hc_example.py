"""
The ``hc-example`` directive: run handcalcs at build time and show the source
next to the real output, so examples in the docs cannot go stale.

Usage (MyST)::

    ```{hc-example}
    :renderer: markdown
    a = 2
    b = 3
    c = 2*a + b/3
    ```

Options:

``:renderer:``
    The registered name of a built-in renderer (``plain_text``, ``latex``,
    ``markdown``, ``html``, ``base``). Default ``markdown``.
``:renderer-file:`` / ``:renderer-class:``
    A Python file (relative to the docs directory) that defines a custom
    renderer, and the class to use from it. Takes precedence over ``:renderer:``.
``:output:``
    How to show the output: ``code`` (a code block), ``markdown`` (parsed as
    MyST, so math is typeset), ``html`` (embedded as raw HTML) or ``none``.
    The default depends on the renderer.
``:output-language:``
    The highlight language of a ``code`` output (default from the renderer).
``:hide-source:``
    Show only the output.
``:setup:``
    Python run before the example but not shown (e.g. ``import math``).
"""

import os
import pathlib
import pprint
import runpy
import tempfile

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective

# Render with the built-in defaults, never with the builder's own saved config.
os.environ.setdefault(
    "HANDCALCS_CONFIG", str(pathlib.Path(tempfile.gettempdir()) / "hc-docs-no-config.json")
)

from handcalcs import HandCalcs  # noqa: E402
from handcalcs.renderers import get_renderer  # noqa: E402

# Default output display and code language per built-in renderer.
_DEFAULT_OUTPUT = {
    "markdown": ("markdown", "markdown"),
    "html": ("html", "html"),
    "latex": ("code", "latex"),
    "plain_text": ("code", "text"),
    "base": ("code", "python"),
}

_RENDERER_FILE_CACHE: dict[str, dict] = {}


def _heading_to_bold(markdown: str) -> str:
    """Headings are not allowed inside a directive; show them as bold paragraphs."""
    lines = []
    for line in markdown.split("\n"):
        stripped = line.lstrip("> ")
        prefix = line[: len(line) - len(stripped)]
        if stripped.startswith("#"):
            text = stripped.lstrip("#").strip()
            line = f"{prefix}**{text}**"
        lines.append(line)
    return "\n".join(lines)


class HcExampleDirective(SphinxDirective):
    has_content = True
    option_spec = {
        "renderer": directives.unchanged,
        "renderer-file": directives.unchanged,
        "renderer-class": directives.unchanged,
        "output": lambda arg: directives.choice(arg, ("code", "markdown", "html", "none")),
        "output-language": directives.unchanged,
        "hide-source": directives.flag,
        "setup": directives.unchanged,
        "caption": directives.unchanged,
    }

    def _renderer(self):
        renderer_file = self.options.get("renderer-file")
        if renderer_file:
            path = pathlib.Path(self.env.srcdir) / renderer_file
            self.env.note_dependency(str(path))
            namespace = _RENDERER_FILE_CACHE.get(str(path))
            if namespace is None:
                namespace = runpy.run_path(str(path))
                _RENDERER_FILE_CACHE[str(path)] = namespace
            class_name = self.options.get("renderer-class")
            if not class_name:
                raise self.error("hc-example: ':renderer-file:' needs ':renderer-class:'")
            return namespace[class_name](), None
        name = self.options.get("renderer", "markdown")
        renderer_cls = get_renderer(name)
        if renderer_cls is None:
            raise self.error(f"hc-example: no renderer registered as {name!r}")
        return renderer_cls(), name

    def run(self):
        source = "\n".join(self.content)
        setup = self.options.get("setup", "")
        renderer, _name = self._renderer()
        # A custom renderer is shown like the built-in renderer it inherits from.
        output_kind, language = next(
            (_DEFAULT_OUTPUT[cls.__dict__["name"]] for cls in type(renderer).__mro__
             if cls.__dict__.get("name") in _DEFAULT_OUTPUT),
            ("code", "text"),
        )
        output_kind = self.options.get("output", output_kind)
        language = self.options.get("output-language", language)

        globals_: dict = {}
        try:
            exec(compile(setup + "\n" + source, "<hc-example>", "exec"), globals_)
            rendered = HandCalcs(renderer=renderer)(source, globals_)
        except Exception as error:  # surface the failure in the build log
            raise self.error(f"hc-example failed: {type(error).__name__}: {error}")
        if not isinstance(rendered, str):
            rendered = pprint.pformat(rendered, width=88)

        container = nodes.container(classes=["hc-example"])
        lines: list[str] = []
        if "hide-source" not in self.options:
            lines += ["```python", *source.split("\n"), "```", ""]
        if output_kind != "none":
            label = self.options.get("caption") or f"Output ({type(renderer).__name__})"
            lines += [f"<div class=\"hc-example-label\">{label}</div>", ""]
        self.state.nested_parse(StringList(lines, source="hc-example"), self.content_offset, container)

        if output_kind == "none":
            return [container]
        output = nodes.container(classes=["hc-example-output", f"hc-output-{output_kind}"])
        if output_kind == "code":
            block = nodes.literal_block(rendered, rendered)
            block["language"] = language
            output += block
        elif output_kind == "html":
            output += nodes.raw("", rendered, format="html")
        else:
            text = _heading_to_bold(rendered)
            self.state.nested_parse(
                StringList(text.split("\n"), source="hc-example-output"), self.content_offset, output
            )
        container += output
        return [container]


class HcRegistryDirective(SphinxDirective):
    """
    ``hc-registry``: a table of the handlers, header handlers and rules of a
    renderer, read from its registration tables at build time. With ``:own:``,
    only those that differ from its parent class.
    """
    has_content = False
    required_arguments = 1  # the registered renderer name
    option_spec = {"own": directives.flag}

    def run(self):
        renderer_cls = get_renderer(self.arguments[0])
        if renderer_cls is None:
            raise self.error(f"hc-registry: no renderer registered as {self.arguments[0]!r}")
        parent = renderer_cls.__mro__[1]
        own = "own" in self.options

        def link(fn):
            return f"{{src}}`{fn.__name__} <{fn.__module__}.{fn.__qualname__}>`"

        rows = []
        for node_type, fn in sorted(renderer_cls.node_handlers.items()):
            if own and getattr(parent, "node_handlers", {}).get(node_type) is fn:
                continue
            rows.append((f"`{node_type}`", "handler", link(fn)))
        for node_type, fn in sorted(renderer_cls.header_handlers.items()):
            if own and getattr(parent, "header_handlers", {}).get(node_type) is fn:
                continue
            rows.append((f"`header:{node_type}`", "header", link(fn)))
        for node_type, categories in sorted(renderer_cls.rule_handlers.items()):
            for category, fns in categories.items():
                inherited = getattr(parent, "rule_handlers", {}).get(node_type, {}).get(category, [])
                for fn in fns:
                    if own and fn in inherited:
                        continue
                    rows.append((f"`{node_type}:{category}`", "rule", link(fn)))
        lines = ["| Classifier | Kind | Function |", "|---|---|---|"]
        lines += [f"| {a} | {b} | {c} |" for a, b, c in rows]
        container = nodes.container()
        self.state.nested_parse(StringList(lines, source="hc-registry"), self.content_offset, container)
        return container.children


def setup(app):
    app.add_directive("hc-example", HcExampleDirective)
    app.add_directive("hc-registry", HcRegistryDirective)
    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
