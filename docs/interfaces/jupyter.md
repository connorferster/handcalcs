# Jupyter: `%%render`

The Jupyter interface renders a notebook cell in place.

```python
import handcalcs
```

Importing handcalcs inside a running IPython kernel registers one cell magic and two
line magics:

| Magic | Does |
|---|---|
| `%%render` | Runs the cell, then displays it as a calculation. |
| `%hc_default_renderer NAME` | Chooses the renderer `%%render` uses for this session. |
| `%hc_format_code CODE` | Sets the default [number format](../getting-started/formatting-numbers.md) for this session. |

## `%%render`

```python
%%render
## Section properties
b = 300  # mm
h = 600  # mm
I_x = b * h**3 / 12
```

What happens:

1. The cell runs in the notebook's namespace, exactly as it would without the magic.
   Variables it defines are available to later cells. Anything the cell prints is
   suppressed.
2. handcalcs parses the cell and renders it with the session's renderer, reading values
   from the notebook namespace.
3. The output is displayed with the IPython display class that matches the renderer.

Anything after `%%render` on the first line is ignored. Formatting is controlled with
[comment commands](../getting-started/comment-commands.md) inside the cell.

```{warning}
If the cell raises an exception, `%%render` displays nothing, and the traceback is not
shown. If a rendered cell comes up empty, remove `%%render` and run it again to see the
error.
```

## Choosing the renderer

`%%render` uses the Markdown renderer by default: Markdown prose with LaTeX math, which
Jupyter typesets with MathJax. To switch:

```python
%hc_default_renderer latex
```

| Name | Displayed as |
|---|---|
| `markdown` (default) | `IPython.display.Markdown` |
| `latex` | `IPython.display.Latex` |
| `html` | `IPython.display.HTML` |
| `plain_text` | `IPython.display.Pretty` |

The setting lasts for the session. To make it permanent, save it to the
[configuration](../getting-started/configuration.md):

```python
handcalcs.set_option("jupyter_renderer", "html")
handcalcs.save_config()
```

`%hc_default_renderer` only changes `%%render`; a bare `HandCalcs()` uses the separate
`default_renderer` option.

### Custom renderers

Any renderer with a `name` can be selected once its class has been defined or imported:

```python
from my_package import MyRenderer   # name = "mine"
%hc_default_renderer mine
```

A custom renderer is displayed with the display class of the built-in renderer it
inherits from: a subclass of `HTMLRenderer` is shown as HTML, a subclass of
`MarkdownRenderer` as Markdown, and so on. See
[Publishing a renderer](../building-renderers/publishing.md).

## Exporting a notebook

To share a notebook of rendered calculations without the code, export it with the
input cells hidden. The [nb-hideinputs](https://github.com/connorferster/nb-hideinputs)
package (`pip install "handcalcs[exporters]"`) adds "no input" HTML, LaTeX and PDF
export options to Jupyter.

## Source

{source}`src/handcalcs/interfaces/jupyter.py`
