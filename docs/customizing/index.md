# Customizing a renderer

The built-in renderers are designed to be adjusted. Most changes take a few lines and
fall into one of three levers, from lightest to most powerful.

| Lever | What it changes | How | Example |
|---|---|---|---|
| **1. Settings** | Values the renderer reads while rendering: number format, the `=` symbol, indentation, which steps are shown | [Configuration](../getting-started/configuration.md), `# hc:` commands, `render_context=` | `# hc: format_code = ".2f"` |
| **2. Class attributes** | A renderer's fixed tokens: its stylesheet, math delimiters, symbol tables | A subclass that overrides the attribute | `STYLE = HTMLRenderer.STYLE + "..."` |
| **3. Rules and handlers** | How a particular kind of node is rendered | A function registered with `@Renderer.register(...)` | color every result |

## A first customization

Subclass a renderer, override an attribute, register a rule. This HTML renderer colors
headings and highlights each calculated result:

```{literalinclude} ../_examples/html_colors.py
:language: python
```

```{hc-example}
:renderer-file: _examples/html_colors.py
:renderer-class: ThemedHTMLRenderer
## Beam check
# Simply supported beam with a uniform load.
w = 5  # kN/m
L = 6  # m
M = w * L**2 / 8  # kN m
```

Use it like any renderer: `HandCalcs(ThemedHTMLRenderer())`. Because it declares a
`name`, it can also be chosen in Jupyter with `%hc_default_renderer themed_html`, and it
is displayed as HTML because it inherits from `HTMLRenderer`.

## Go deeper

::::{grid} 1 2 2 2
:gutter: 2

:::{grid-item-card} Settings and the render context
:link: render-context
:link-type: doc
Every setting a renderer reads, and the four ways to set one.
:::

:::{grid-item-card} Styling the HTML output
:link: html-styling
:link-type: doc
CSS classes and custom properties, colors, dark mode, highlighting.
:::

:::{grid-item-card} LaTeX and Markdown tokens
:link: latex-markdown-tokens
:link-type: doc
Math delimiters, headings, indentation, colors in math.
:::

:::{grid-item-card} Symbols and functions
:link: symbols-and-functions
:link-type: doc
Add your own symbols, function names and operator symbols.
:::

:::{grid-item-card} Customizing one instance
:link: per-instance-handlers
:link-type: doc
Change a single renderer object without a subclass.
:::

:::{grid-item-card} Recipes
:link: recipes
:link-type: doc
Short, tested snippets for common changes.
:::
::::

When a change goes beyond adjusting (a new output format, or a different structure),
[build a renderer](../building-renderers/index.md) instead. The same three levers are
the whole of the renderer API, so nothing here is wasted.

```{toctree}
:hidden:

render-context
html-styling
latex-markdown-tokens
symbols-and-functions
per-instance-handlers
recipes
```
