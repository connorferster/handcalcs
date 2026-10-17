# Python: `HandCalcs`

`HandCalcs` renders calculations from any Python program. Create it with a renderer,
then call it with source code.

```python
from handcalcs import HandCalcs
from handcalcs.renderers import MarkdownRenderer

hc = HandCalcs(renderer=MarkdownRenderer())
markdown = hc("""
## Beam moment
w = 5  # kN/m
L = 6  # m
M = w * L**2 / 8
""")
```

The return value is whatever the renderer produces: a string for the Markdown, LaTeX,
HTML and plain-text renderers, a workbook for the Excel renderer, a nested list for the
base renderer. One `HandCalcs` object can be called any number of times.

## Creating it

`HandCalcs(renderer=None)`
: `renderer` is a renderer **instance**. If it is omitted, the renderer named by the
  `default_renderer` [option](../getting-started/configuration.md) is used (the base
  renderer unless you change it).

The global configuration is copied when the object is created, so set options first.

## Calling it

`hc(source_or_path, supplied_globals=None, supplied_locals=None)`

`source_or_path`
: Either a **string of Python source**, or a **`pathlib.Path`** to a `.py` file.

  ```{important}
  A plain string is always treated as source code, even if it looks like a file name.
  Wrap paths in `pathlib.Path`.
  ```

`supplied_globals`
: Where values come from.
  - If omitted, the source is **run** (with `exec`, in a fresh namespace) and the
    resulting variables are used.
  - If given, the source is **not run**: values are looked up in this dictionary. Use
    this when you have already run the code, or want to render code with values from
    somewhere else.

```python
import pathlib

# Run a file and render it
latex = HandCalcs(LatexRenderer())(pathlib.Path("beam.py"))

# Render with values you already have (the code is not run)
values = {"w": 5, "L": 6, "M": 22.5}
text = HandCalcs(PlainTextRenderer())("M = w * L**2 / 8", values)
```

If a name has no value in `supplied_globals`, it is shown as empty in the substituted
step.

### Inspecting the parsed tree

After a call, `hc.hc_ast` holds the parsed calculation (an `HcSequence`). This is
mostly useful when [building a renderer](../building-renderers/nodes.md).

## The demo

`hc.demo()` renders a built-in example calculation (headings, prose, parameter grids,
long equations and nested conditionals) with the object's renderer:

```python
print(HandCalcs(PlainTextRenderer()).demo())
```

It is a quick way to compare renderers, or to check a renderer you are writing. A
renderer that cannot render the general demo can supply its own source in a
`demo_source` attribute (the Excel renderer does).

## Examples

### Write a LaTeX file

```python
import pathlib
from handcalcs import HandCalcs
from handcalcs.renderers import LatexRenderer

body = HandCalcs(LatexRenderer())(pathlib.Path("calcs/beam.py"))
pathlib.Path("report/beam.tex").write_text(body)
```

The output is a fragment for the body of a document; see
[the LaTeX renderer](../renderers/latex.md) for the packages it needs.

### Serve HTML from a web app

```python
from handcalcs import HandCalcs
from handcalcs.renderers import HTMLRenderer

hc = HandCalcs(HTMLRenderer())

def beam_page(w: float, L: float) -> str:
    return hc("M = w * L**2 / 8", {"w": w, "L": L, "M": w * L**2 / 8})
```

### One calculation per row of a table

```python
source = "M = w * L**2 / 8"
hc = HandCalcs(PlainTextRenderer())
for w, L in [(5, 6), (7.5, 4)]:
    print(hc(source, {"w": w, "L": L, "M": w * L**2 / 8}))
```

## Source

{source}`src/handcalcs/interfaces/object_oriented.py`
