# Documentation

The docs are built with [Sphinx](https://www.sphinx-doc.org/) and the
[Shibuya](https://shibuya.lepture.com/) theme, and written in
[MyST Markdown](https://myst-parser.readthedocs.io/).

```console
$ uv run --extra doc sphinx-build -b html docs docs/_build/html
$ uv run --extra doc sphinx-build -E -W -b html docs docs/_build/html   # clean, warnings as errors
```

Use `-E` after changing anything in `docs/_ext/` or `docs/_examples/`; Sphinx only
re-reads pages whose source changed.

## Layout

| Path | Contents |
|---|---|
| `docs/conf.py` | Configuration, including `HC_SOURCE_REF` (see below) and the theme's navigation bar. |
| `docs/index.md` | The landing page. |
| `docs/<section>/index.md` | Each section's first page: the short "what you need to get going" page, with cards to the rest of the section. |
| `docs/_ext/` | Local Sphinx extensions: `hc_example.py`, `hc_source.py`. |
| `docs/_examples/` | Example renderers used by the docs; each is run by the build. |
| `docs/_static/handcalcs-docs.css` | Styles for the live examples. |

## Writing pages

Each section follows the same layered structure, so readers always know where to look:

1. The **section index** gets someone going: the common task, one example, then a grid of
   cards to the other pages.
2. **Topic pages** cover one task or concept fully, and end with a "Next" link.
3. The **reference** holds exhaustive tables and the API.

Start pages with what the reader can do, show a working example early, and link to the
reference rather than repeating it.

## Live examples: `hc-example`

````md
```{hc-example}
:renderer: markdown
a = 2
b = 3
c = 2*a + b/3
```
````

The directive runs the code, renders it, and shows the source followed by the output. The
output is shown according to the renderer: Markdown is parsed (so math is typeset), HTML
is embedded, everything else is a code block.

| Option | Meaning |
|---|---|
| `:renderer:` | A registered renderer name (default `markdown`). |
| `:renderer-file:`, `:renderer-class:` | A file in `docs/` defining a renderer, and the class (or factory function) to call. |
| `:output:` | `code`, `markdown`, `html` or `none`, to override the default. |
| `:output-language:` | Highlighting for a `code` output. |
| `:hide-source:` | Show the output only. |
| `:setup:` | Code run before the example but not shown (e.g. `from math import sqrt`). |
| `:caption:` | Replaces the "Output (Renderer)" label. |

Examples are rendered with handcalcs' built-in defaults, never a builder's saved config.
Prefer `hc-example` to a hand-written output block wherever handcalcs can produce the
output, so the docs cannot drift from the code.

## Source links

Two roles link to the source on GitHub, at the git ref in `HC_SOURCE_REF`:

- ``{src}`handcalcs.renderers.base.render_calcline` `` links a Python object to its exact
  lines, found at build time, so the link follows the code. Use
  ``{src}`label <dotted.path>` `` for a custom label.
- ``{source}`tests/test_jupyter.py` `` links a file by path.

The API reference gets `[source]` links the same way, through `sphinx.ext.linkcode`.

`HC_SOURCE_REF` defaults to `hc2/dev` and can be set in the environment:
`HC_SOURCE_REF=v2.0.0 sphinx-build ...`. Set it to the release tag when publishing docs
for a release (see [Releasing](releasing.md)).
