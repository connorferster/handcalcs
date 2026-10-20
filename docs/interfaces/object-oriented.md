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

`hc(source_or_path, supplied_globals=None, supplied_locals=None, *, inputs=None, strict=True, allow_computed=False)`

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
step. The exception is a name used in an `if` condition: the condition is evaluated to
decide which branch to show, so a missing name raises `NameError`.

`inputs`, `strict`, `allow_computed`
: Render the source with different given values. See
  [Rendering many input sets](#rendering-many-input-sets). `inputs` cannot be combined
  with `supplied_globals`.

### Inspecting the parsed tree

After a call, `hc.hc_ast` holds the parsed calculation (an `HcSequence`). This is
mostly useful when [building a renderer](../building-renderers/nodes.md).

## Rendering many input sets

Write a calculation once, as an ordinary script with sample values, then render it
with different inputs, one document per input set:

```python
import json
import pathlib
from handcalcs import HandCalcs
from handcalcs.renderers import LatexRenderer

hc = HandCalcs(LatexRenderer())
for case in json.loads(pathlib.Path("beams.json").read_text()):  # [{"w": 6.2, "L": 8}, ...]
    doc = hc(pathlib.Path("beam.py"), inputs=case)
```

In a notebook, [`%%render inputs=case`](jupyter.md#rendering-with-inputs) does the same
for a cell. A [`@handcalc`](decorator.md) function needs nothing extra: its parameters
are already its inputs.

`beam.py` stays a normal script that runs and renders on its own:

```python
import forallpeople as si
si.environment("structural")
from forallpeople import *

w = 5 * kN/m  # load
L = 6 * m
M = w * L**2 / 8
```

With `inputs={"w": 7.5, "L": 8}`, the first assignment of each input name is given
the input value and the script is then run and rendered as usual, so everything
computed from the inputs is recomputed:

```text
w = 7.5 * kN / m = 7.5 * 1 kN / 1 m = 7.5 kN/m (load)
L = 8 * m = 8 * 1 m = 8 m
M = w * L² / 8 = 7.5 kN/m * 8 m² / 8 = 60 kN·m
```

**Units are kept.** When the input is a number and the script assigns a number times
units (`L = 6 * m`), only the number is replaced, so the line becomes `L = 8 * m`. Any
other input replaces the whole right-hand side.

**Which assignment is bound.** The first top-level `name = value` assignment of each
input name, including one statement of an `a = 1; b = 2` line. Later reassignments
still run. A name assigned only inside a block or function, by `+=`, or by unpacking
cannot be bound and raises `ValueError`.

**Input values** are usually what JSON holds: numbers, strings, `True`/`False`, `None`,
and lists and dicts of these. They are written into the script as typed. Numbers of
other types, such as `numpy.float64` from a pandas row, are written as plain numbers.

**Quantities** are converted to the units of their line. With
`inputs={"w": 6200 * ureg.N / ureg.m}`, the line `w = 4.5 * kN / m` runs and renders as
`w = 6.2 * kN / m`, so the document keeps the script's units. A quantity whose units
do not convert (a length for a load) raises `ValueError`. pint quantities from another
`UnitRegistry` are converted into the script's registry.

**Other objects**, such as arrays, sections or a quantity on a line with no units
(`A = 100`), are assigned as they are and shown as the line's value. Keep pint
quantities on such lines in the script's registry, since pint cannot calculate with
quantities from two registries.

### Checks

`strict=True`
: An input the script never assigns raises `KeyError`, which catches misspelled names.
  With `strict=False` such inputs are ignored, so one input file can serve several
  scripts.

`allow_computed=False`
: An input for a computed line (`M = w * L**2 / 8`) raises `ValueError`, so a
  calculation is not replaced by accident. With `allow_computed=True` the line is
  replaced by the input value.

### Finding a script's inputs

`find_inputs` lists the names whose first assignment is a literal or a number times
units, with their values in the script (the number only, for a value with units). Use
it as a template for an input file:

```python
from handcalcs import find_inputs

find_inputs(pathlib.Path("beam.py"))  # {'w': 5, 'L': 6}
```

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
source = """
w = 5
L = 6
M = w * L**2 / 8
"""
hc = HandCalcs(PlainTextRenderer())
for w, L in [(5, 6), (7.5, 4)]:
    print(hc(source, inputs={"w": w, "L": L}))
```

## Source

{source}`src/handcalcs/interfaces/object_oriented.py`
