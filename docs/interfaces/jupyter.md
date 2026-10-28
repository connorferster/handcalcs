# Jupyter: `%%render`

The Jupyter interface renders a notebook cell in place.

```python
import handcalcs
```

Importing handcalcs inside a running IPython kernel registers the `render` magic (as a cell
magic and a line magic) and two settings magics:

| Magic | Does |
|---|---|
| `%%render` | Runs the cell, then displays it as a calculation. |
| `%%render inputs=case` | Runs and displays the cell with the values in `case` ([inputs](#rendering-with-inputs)). |
| `%render LINE` | Runs one line, then displays it as a calculation. |
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
   suppressed. If the cell raises an error, the error is shown as usual and nothing
   is rendered.
2. handcalcs parses the cell and renders it with the session's renderer, reading values
   from the notebook namespace.
3. The output is displayed with the IPython display class that matches the renderer.

Formatting is controlled with [comment commands](../getting-started/comment-commands.md)
inside the cell. The first line takes only the [inputs](#rendering-with-inputs) arguments;
words without `=` after `%%render` (such as v1's `params`) are ignored.

```{warning}
If the cell raises an exception, `%%render` displays nothing, and the traceback is not
shown. If a rendered cell comes up empty, remove `%%render` and run it again to see the
error.
```

## Rendering with inputs

`%%render inputs=case` renders the cell with the values in the dict `case` in place of
the values the cell assigns them, the same way as
[`HandCalcs(..., inputs=...)`](object-oriented.md#rendering-many-input-sets) does for
a script:

```python
case = {"w": 6.2, "L": 8}
```

```python
%%render inputs=case
w = 4.5 * kN / m
L = 6 * m
M_f = w * L**2 / 8
```

This runs and renders as `w = 6.2 kN/m`, `L = 8 m`, and `M_f` is computed from them. A
number keeps the cell's units; a quantity is converted to them. Later cells see the
values the cell computed with the inputs.

The arguments are keyword arguments, separated by commas, and are evaluated in the
notebook's namespace, so any expression works: `%%render inputs=cases[2], strict=False`.

| Argument | Does |
|---|---|
| `inputs` | A dict of names and values. Required for `strict` and `allow_computed`. |
| `strict=False` | Ignore inputs the cell never assigns, instead of raising a `KeyError`. |
| `allow_computed=True` | Let an input replace a computed line (`b = 2 * a`), instead of raising a `ValueError`. |
| `destination="calc.tex"` | Write the render to this file instead of displaying it (see below). |

A misspelled input name or an input on a computed line raises its error before the
cell runs, so its traceback is shown. A quantity whose units don't match the line's
raises while the cell runs, so, as the warning above says, nothing is displayed.

## Writing a file

`%%render destination="calc.tex"` runs the cell and writes the render to the file, as
[`HandCalcs(..., destination=...)`](object-oriented.md#writing-a-file) does, instead of
displaying it. The cell shows the file's path. The file type follows the
[Jupyter renderer](#choosing-the-renderer): set it to `latex` for a `.tex` file, `word`
for a `.docx` file. It combines with inputs:
`%%render inputs=case, destination="case_1.tex"`.

## `%render`: one line

`%render` runs the rest of its line in the notebook's namespace and renders just that
line. Use it for the one equation that matters in a cell of ordinary code:

```python
b = 300
h = 600
%render I_x = b * h**3 / 12
print(I_x)
```

The line can carry an inline comment or comment command
(`%render M = w * L**2 / 8  # hc: -f .1f`). `%render` with no code is an error, and so is
`%render` inside a function, because the line would run in the notebook's namespace
instead of the function's; use [`@handcalc`](decorator.md) there.

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
| `ascii` | `IPython.display.Pretty` |

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
