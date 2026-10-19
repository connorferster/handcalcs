# Overridable methods

Handlers and rules decide what each node becomes. The methods on this page decide
everything around them: the starting settings, the layout of lines and blocks, and the
final output. They are listed roughly in the order you are likely to need them.

| Method | Override it to | Built-in overrides |
|---|---|---|
| [`complete`](#complete) | produce the final output | every built-in renderer |
| [`join_item`](#join-item) | lay out lines and blocks | LaTeX, Markdown, HTML |
| [`create_context`](#create-context) | set default settings | LaTeX, HTML |
| [`format_param_grid`](#format-param-grid) | lay out parameter grids | LaTeX, HTML |
| [`format_calc_grid`](#format-calc-grid) | lay out multi-line (`-m`) calculations | LaTeX, HTML |
| [`render_root`](#render-root) | change how the top level is walked | Excel |
| [`join`, `join_items`](#join-and-join-items) | change the joining walk itself | (none) |

All are defined on {src}`BaseRenderer <handcalcs.renderers.base.BaseRenderer>`.

(complete)=
## `complete(tree, base_context)`

Called once, after rendering, with the whole [render tree](output-tree.md). Its return
value is what the interface returns. `BaseRenderer.complete` returns the tree unchanged.

For a text format, join and finish:

```python
def complete(self, tree, base_context):
    body = self.join(tree, base_context)
    return f"<section class='calc'>{body}</section>"
```

For anything else, walk the tree yourself: the Excel renderer turns its rows into a
workbook ({src}`ExcelRenderer.complete <handcalcs.renderers.excel.renderer.ExcelRenderer.complete>`),
the Word renderer writes its tree into a .docx
({src}`WordRenderer.complete <handcalcs.renderers.word.renderer.WordRenderer.complete>`),
and the [structured data example](example-json.md) flattens the tree into dicts.

Built-in versions:
{src}`PlainTextRenderer.complete <handcalcs.renderers.plaintext.PlainTextRenderer.complete>`,
{src}`LatexRenderer.complete <handcalcs.renderers.latex.LatexRenderer.complete>`,
{src}`HTMLRenderer.complete <handcalcs.renderers.html.HTMLRenderer.complete>`.

(join-item)=
## `join_item(item, depth, base_context)`

Called by `join` for each item of the tree, with its nesting `depth`. Returns a **list of
strings** that are concatenated into the output. This is where a renderer's layout lives.

The base version handles the [tree shapes](output-tree.md): a string is a whole line, a
list of strings is one line's parts (joined with `context.space`), and `[header, body]` is
a block (header at this depth, body one level deeper, indented with `context.indent`).
Every line ends with `context.newline`.

Override it to change how lines or blocks are written, and hand everything else back to
the parent:

```python
def join_item(self, item, depth, base_context):
    if item and isinstance(item, list) and isinstance(item[-1], list):
        header, body = item[0], item[-1]
        if isinstance(header, str) and header.strip():
            inner = "".join(self.join_items(body, depth + 1, base_context))
            return [f"<details><summary>{header}</summary>{inner}</details>"]
    return super().join_item(item, depth, base_context)
```

Built-in versions show three styles:
{src}`HTML <handcalcs.renderers.html.HTMLRenderer.join_item>` (nested `<div>`s),
{src}`LaTeX <handcalcs.renderers.latex.LatexRenderer.join_item>` (paragraphs, math groups,
`list` environments), and
{src}`Markdown <handcalcs.renderers.markdown.MarkdownRenderer.join_item>` (blockquotes).

(create-context)=
## `create_context(**kwargs)`

Called once per render with the configuration as keyword arguments. Returns the
`BaseRenderContext`. Override it to give your renderer its own defaults; merge them
*under* `kwargs` so the configuration can still override them:

```python
from handcalcs.renderers.base import BaseRenderContext, RenderContext

def create_context(self, **kwargs):
    defaults = {"lpar": "\\left(", "rpar": "\\right)", "indent": ""}
    return BaseRenderContext(RenderContext(**(defaults | kwargs)), RenderContext.sparse())
```

See [The render context](render-context.md).

(format-param-grid)=
## `format_param_grid(rows, base_context)`

Called by the `params_block` handler. `rows` is a list of rows; each cell is the rendered
parameter as a list of parts, `[identifier, "=", value]` plus a comment for `# hc: -h`
grids, or `None` to pad the last row. Return the grid's rendered form, usually one string.

The base version pads columns to line up the `=` signs in plain text. The LaTeX version
builds an `aligned` group
({src}`LatexRenderer.format_param_grid <handcalcs.renderers.latex.LatexRenderer.format_param_grid>`),
the HTML version a `<table>`
({src}`HTMLRenderer.format_param_grid <handcalcs.renderers.html.HTMLRenderer.format_param_grid>`).

(format-calc-grid)=
## `format_calc_grid(rows, base_context)`

Called by the `calc_line` handler for a multi-line (`# hc: -m`) calculation. `rows` is a
list of `[identifier, "=", value]` triples: the first has the target, the rest an empty
identifier. Return the rendered calculation, usually one string.

(render-root)=
## `render_root(root, base_context)`

Walks the top-level nodes, running `root:pre` and `root:post` rules around them, and
returns the tree as a list. Override it when the top level needs different handling, such
as flattening: the Excel renderer flattens every statement into one list of rows
({src}`ExcelRenderer.render_root <handcalcs.renderers.excel.renderer.ExcelRenderer.render_root>`).
For adding a title or a footer, a `root:pre` or `root:post` rule is simpler.

(join-and-join-items)=
## `join(tree, base_context)` and `join_items(items, depth, base_context)`

`join` calls `join_items(tree, 0, ...)` and concatenates the result; `join_items` calls
`join_item` for each item. You rarely need to override them; call them from your own
`complete` and `join_item`.

## Renderer-specific hooks

The LaTeX family splits its layout into smaller methods you can override instead of the
whole `join_item`:

| Method | Does |
|---|---|
| `paragraph(text)` | Prefixes a prose paragraph (`\noindent `) |
| `math_group(rows)` | Wraps joined rows in `MATH_OPEN` / `MATH_CLOSE` |
| `join_math_group(rows, depth, base_context)` | Joins a `CalcsBlock`'s rows into one group |
| `join_math_row(row, base_context)` | Joins one line's parts into an `aligned` row, placing `&` |
| `quote(chunks)` (Markdown) | Blockquotes a block body |

The [reStructuredText example](example-restructuredtext.md) overrides `math_group` and
`paragraph`.

## Class attributes

| Attribute | Purpose |
|---|---|
| `name` | Registers the renderer for selection by name (config, `%hc_default_renderer`). |
| `demo_source` | Source for `HandCalcs.demo()` when the general demo doesn't suit the renderer. |
| `node_handlers`, `header_handlers`, `rule_handlers` | The [registration tables](registration.md#the-tables). |

**Next:** [The render tree](output-tree.md).
