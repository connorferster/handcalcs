# Apps and workflows

Recipes for using handcalcs beyond a notebook: scripts, reusable calculation functions,
parametric studies and web or desktop apps.

## Render from a plain Python script

*Asked in {issue}`203`.*

`HandCalcs` works anywhere Python runs. Give it the source and the namespace to take
values from:

```python
from handcalcs import HandCalcs
from handcalcs.renderers import ASCIIRenderer

source = """
w = 5
L = 6
M = w * L**2 / 8
"""
namespace = {}
exec(source, namespace)
print(HandCalcs(ASCIIRenderer())(source, namespace))
```

Pass a `pathlib.Path` instead of a string and handcalcs runs the file for you:
`HandCalcs(renderer)(Path("beam.py"))`.

## Turn a calculation function into a rendered one

*Asked in {issue}`107` and {issue}`173`.*

`@handcalc` makes a function return its result and its rendered calculation:

```python
from handcalcs import handcalc
from handcalcs.renderers import MarkdownRenderer

@handcalc(MarkdownRenderer())
def moment(w, L):
    M = w * L**2 / 8
    return M

value, markdown = moment(5, 6)
```

A function you already have, in a module you don't want to change, can be wrapped when
you call it: `value, markdown = handcalc(MarkdownRenderer())(beams.moment)(5, 6)`.
See [Functions: `@handcalc`](../interfaces/decorator.md).

## Run one calculation for many designs

Write the calculation once as a script with sample values. Then render it for each row
of a table of inputs. Every line computed from an input is recomputed:

```python
import csv
import pathlib
from handcalcs import HandCalcs, find_inputs
from handcalcs.renderers import LatexRenderer

calc = pathlib.Path("beam.py")
print(find_inputs(calc))            # {'w': 5, 'L': 6}: the names you can set

hc = HandCalcs(LatexRenderer())
with open("beams.csv") as f:        # columns: mark, w, L
    for row in csv.DictReader(f):
        case = {"w": float(row["w"]), "L": float(row["L"])}
        pathlib.Path(f"out/{row['mark']}.tex").write_text(hc(calc, inputs=case))
```

Units in the script are kept: with `L = 6 * m` in the script, `inputs={"L": 8}` renders
`L = 8 * m`. In a notebook, `%%render inputs=case` does the same for a cell. See
[Rendering many input sets](../interfaces/object-oriented.md#rendering-many-input-sets).

## Rendered calculations in a web app

*Asked in {issue}`167`.*

The HTML renderer returns a self-contained fragment (its own `<style>`, no JavaScript),
so any web framework can return it.

::::{tab-set}

:::{tab-item} Flask
```python
from flask import Flask, request
from handcalcs import HandCalcs
from handcalcs.renderers import HTMLRenderer

app = Flask(__name__)
hc = HandCalcs(HTMLRenderer())
SOURCE = "M = w * L**2 / 8"

@app.get("/beam")
def beam():
    w = float(request.args["w"]); L = float(request.args["L"])
    return hc(SOURCE, {"w": w, "L": L, "M": w * L**2 / 8})
```
:::

:::{tab-item} Django
```python
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.shortcuts import render
from handcalcs import HandCalcs
from handcalcs.renderers import HTMLRenderer

hc = HandCalcs(HTMLRenderer())

def beam(request):
    w = float(request.GET["w"]); L = float(request.GET["L"])
    calc = hc("M = w * L**2 / 8", {"w": w, "L": L, "M": w * L**2 / 8})
    return render(request, "beam.html", {"calc": mark_safe(calc)})
```
In the template: `{{ calc }}`.
:::

:::{tab-item} Streamlit
```python
import streamlit as st
from handcalcs import HandCalcs
from handcalcs.renderers import MarkdownRenderer

w = st.number_input("w (kN/m)", value=5.0)
L = st.number_input("L (m)", value=6.0)
M = w * L**2 / 8
st.markdown(HandCalcs(MarkdownRenderer())("M = w * L**2 / 8", {"w": w, "L": L, "M": M}))
```
Streamlit typesets the `$$` math with KaTeX.
:::

::::

Only render source you wrote. `HandCalcs` runs a `Path` it is given, so never pass it
code or file paths from a web request.

## Rendered calculations in a desktop app

*Asked in {issue}`98`.*

The HTML output needs no JavaScript, so Qt's rich-text widgets can show it:

```python
from PySide6.QtWidgets import QApplication, QTextBrowser
from handcalcs import HandCalcs
from handcalcs.renderers import HTMLRenderer

app = QApplication([])
view = QTextBrowser()
view.setHtml(HandCalcs(HTMLRenderer())("M = w * L**2 / 8", {"w": 5, "L": 6, "M": 22.5}))
view.show()
app.exec()
```

`QTextBrowser` supports only a subset of CSS; `QWebEngineView` shows the output exactly
as a browser does.

## A live Excel workbook

The [Excel renderer](../renderers/excel.md) writes the calculation as formulas, so
changing an input cell recalculates the sheet:

```python
import pathlib
from handcalcs import HandCalcs
from handcalcs.renderers import ExcelRenderer

HandCalcs(ExcelRenderer(filepath="beam.xlsx"))(pathlib.Path("beam.py"))
```

**Back to:** [the cookbook](index.md).
