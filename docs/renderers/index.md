# Renderers

A **renderer** decides what a calculation looks like. handcalcs parses your code once,
and the renderer turns the parsed calculation into Markdown, LaTeX, HTML, plain text, an
Excel workbook, or anything else you write a renderer for.

## Choosing a renderer

| Renderer | Name | Produces | Use it for |
|---|---|---|---|
| [`MarkdownRenderer`](markdown.md) | `markdown` | Markdown text with `$$` LaTeX math | Jupyter (the default), MyST/Sphinx, Quarto, any Markdown + MathJax/KaTeX site |
| [`LatexRenderer`](latex.md) | `latex` | A LaTeX fragment | `.tex` reports, PDF through LaTeX, Jupyter's LaTeX display |
| [`HTMLRenderer`](html.md) | `html` | An HTML fragment with a scoped stylesheet, no math engine needed | Web apps, emails, HTML reports, Jupyter |
| [`PlainTextRenderer`](plain-text.md) | `plain_text` | Unicode text | Terminals, logs, test snapshots, plain-text reports |
| [`ExcelRenderer`](excel.md) | `excel` | A live `.xlsx` worksheet | Handing a calculation to someone who works in Excel |
| [`BaseRenderer`](base.md) | `base` | A nested Python list | Building your own renderer, debugging |

## Using one

Every renderer is a class in `handcalcs.renderers`. Pass an **instance** to an interface:

```python
from handcalcs import HandCalcs
from handcalcs.renderers import HTMLRenderer

html = HandCalcs(renderer=HTMLRenderer())(source)
```

In Jupyter, choose by **name**:

```python
%hc_default_renderer html
```

Or set the default for each interface in the [configuration](../getting-started/configuration.md):
`default_renderer` for a bare `HandCalcs()`, `jupyter_renderer` for `%%render`.

## The same calculation, five ways

::::{tab-set}

:::{tab-item} Markdown
```{hc-example}
:renderer: markdown
:hide-source:
:setup: from math import sqrt
## Roots
a = 2; b = -7; c_0 = 3
x_1 = (-b + sqrt(b**2 - 4*a*c_0)) / (2*a)  # Larger root
```
:::

:::{tab-item} HTML
```{hc-example}
:renderer: html
:hide-source:
:setup: from math import sqrt
## Roots
a = 2; b = -7; c_0 = 3
x_1 = (-b + sqrt(b**2 - 4*a*c_0)) / (2*a)  # Larger root
```
:::

:::{tab-item} LaTeX
```{hc-example}
:renderer: latex
:hide-source:
:setup: from math import sqrt
## Roots
a = 2; b = -7; c_0 = 3
x_1 = (-b + sqrt(b**2 - 4*a*c_0)) / (2*a)  # Larger root
```
:::

:::{tab-item} Plain text
```{hc-example}
:renderer: plain_text
:hide-source:
:setup: from math import sqrt
## Roots
a = 2; b = -7; c_0 = 3
x_1 = (-b + sqrt(b**2 - 4*a*c_0)) / (2*a)  # Larger root
```
:::

:::{tab-item} Base
```{hc-example}
:renderer: base
:hide-source:
:setup: from math import sqrt
## Roots
a = 2; b = -7; c_0 = 3
x_1 = (-b + sqrt(b**2 - 4*a*c_0)) / (2*a)  # Larger root
```
:::

::::

The source for all five:

```python
## Roots
a = 2; b = -7; c_0 = 3
x_1 = (-b + sqrt(b**2 - 4*a*c_0)) / (2*a)  # Larger root
```

## Going further

- Change how a built-in renderer looks: [Customizing a renderer](../customizing/index.md).
- Write a renderer for a new format: [Building a renderer](../building-renderers/index.md).

```{toctree}
:hidden:

markdown
latex
html
plain-text
excel
base
```
