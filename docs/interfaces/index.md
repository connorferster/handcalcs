# Interfaces

An **interface** is how you hand code to handcalcs. All three use the same parser and
the same [renderers](../renderers/index.md); they differ in where the code and its
values come from.

| Interface | You write | Values come from | Returns | Best for |
|---|---|---|---|---|
| [`%%render`](jupyter.md) | a Jupyter cell | the notebook namespace | displays the output | notebooks |
| [`HandCalcs`](object-oriented.md) | a string or a `.py` file | running the code, or a namespace you pass | the rendered output | scripts, reports, web apps, tests |
| [`@handcalc`](decorator.md) | a function | the function's call | `(return value, rendered output)` | reusable calculations |

## In 30 seconds

::::{tab-set}

:::{tab-item} Jupyter
```python
import handcalcs
```
```python
%%render
a = 2
b = 3
c = 2*a + b/3
```
:::

:::{tab-item} HandCalcs
```python
from handcalcs import HandCalcs
from handcalcs.renderers import LatexRenderer

hc = HandCalcs(renderer=LatexRenderer())
latex = hc("a = 2\nb = 3\nc = 2*a + b/3\n")
```
:::

:::{tab-item} @handcalc
```python
from handcalcs import handcalc
from handcalcs.renderers import HTMLRenderer

@handcalc(HTMLRenderer())
def moment(w, L):
    M = w * L**2 / 8
    return M

value, html = moment(5, 6)
```
:::

::::

## Which one?

- Working in a **notebook**: use `%%render`. Change its output format with
  `%hc_default_renderer`.
- Generating output **from a program** (a report, a web page, a batch of PDFs): use
  `HandCalcs`. It is the most direct interface and the one the others are built on.
- Wrapping a calculation you **call repeatedly** with different inputs: use
  `@handcalc`, which returns the result for your program and the rendered calculation
  for your report.

```{toctree}
:hidden:

jupyter
object-oriented
decorator
```
