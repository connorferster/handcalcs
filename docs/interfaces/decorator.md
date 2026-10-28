# Functions: `@handcalc`

The `@handcalc` decorator turns a calculation function into one that returns both its
result and its rendered calculation.

```python
from handcalcs import handcalc
from handcalcs.renderers import MarkdownRenderer

@handcalc(MarkdownRenderer())
def moment(w, L):
    M = w * L**2 / 8  # Simply supported, uniform load
    return M

value, markdown = moment(5, 6)
# value == 22.5
```

The function runs normally. handcalcs captures the values of its local variables (with
[innerscope](https://github.com/eriknw/innerscope)), then renders the function body with
those values.

## Signature

`handcalc(renderer=None, render_context=None, destination=None)`

`renderer`
: A renderer **instance**. If it is omitted, the renderer named by the
  `default_renderer` [option](../getting-started/configuration.md) is used (the ASCII
  renderer unless you change it), as for `HandCalcs`. `@handcalc()` and a bare
  `@handcalc` both work.

`render_context`
: A dictionary of [render context](../customizing/render-context.md) fields for every
  call, for example `{"format_code": ".2f"}`. These override the global
  [configuration](../getting-started/configuration.md).

`destination`
: A file path (a string or a `pathlib.Path`). If given, every call writes the render to
  that file, as [`HandCalcs`](object-oriented.md#writing-a-file) does, and returns its
  `Path` in place of the render. Each call overwrites the file; to keep one file per
  call, call `HandCalcs` in a loop with your own file names.

The decorated function returns a tuple `(return_value, rendered)`. The type of
`rendered` depends on the renderer, as for [`HandCalcs`](object-oriented.md).

## What is rendered

The body of the function (its lines between the `def` line and the `return`), with the
values from that call. Arguments, local variables, closure variables and globals can all
be used. [Comment commands](../getting-started/comment-commands.md) work as usual.
An early `return` ends the rendered calculation where the function returned: the lines
after it did not run, so they are not shown.

```python
from math import sqrt

@handcalc(MarkdownRenderer(), render_context={"format_code": ".3g"})
def shear_capacity(b_w, d, f_c):
    ## Concrete shear resistance
    phi_c = 0.65
    beta = 0.18
    V_c = phi_c * beta * sqrt(f_c) * b_w * d / 1000  # kN
    return V_c
```

## Using it in Jupyter

The decorator returns the rendered output; it does not display it. Display it with the
class that matches the renderer:

```python
from IPython.display import Markdown, display

value, markdown = shear_capacity(300, 540, 30)
display(Markdown(markdown))
```

## Source

{source}`src/handcalcs/interfaces/decorator.py`
