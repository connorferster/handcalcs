# HTML renderer

`HTMLRenderer` produces a self-contained HTML fragment: a `<div class="handcalcs">` with
its own small, scoped stylesheet. It needs no math engine, so it works in any web page,
email or app.

```python
from handcalcs.renderers import HTMLRenderer
```

```{hc-example}
:renderer: html
:setup: from math import sqrt
## Bolt group
# Shear is shared equally between the bolts.
n = 4  # bolts
V_f = 120  # kN
V_b = V_f / n
f = 1; g = 2; h = 4
if V_b <= 40:
    status = "OK"
```

## A fuller example

Headings and prose, a parameter grid, a long equation broken with `-m`, a governing
branch, and a pass/fail check, all in one calculation:

```{hc-example}
:renderer: html
:setup: from math import pi, sqrt
## Steel beam
# Lateral-torsional buckling resistance of a simply supported span.
# hc: -g -c 3
E = 200000     # MPa
G = 77000      # MPa
L = 6000       # mm
I_y = 160e6    # mm⁴
J = 133e3      # mm⁴
C_w = 200e9    # mm⁶
### Elastic critical moment
M_u = pi / L * sqrt(E * I_y * G * J + (pi * E / L)**2 * I_y * C_w)  # hc: -m
M_p = 285e6    # N mm
if M_u > 0.67 * M_p:
    M_r = 1.15 * 0.9 * M_p * (1 - 0.28 * M_p / M_u)  # hc: -m
else:
    M_r = 0.9 * M_u
M_f = 210e6    # N mm
M_f <= M_r     # hc: --check
```

## Using the output

Insert the string anywhere in a page. It inherits the page's font and color, and its
styles never override yours (see [Styling the HTML output](../customizing/html-styling.md)).

```python
from handcalcs import HandCalcs
from handcalcs.renderers import HTMLRenderer

fragment = HandCalcs(HTMLRenderer())(source)
page = f"<html><body><main>{fragment}</main></body></html>"
```

For a page of its own, give a `destination`. The file is a complete HTML page
(`<!DOCTYPE html>`, a `<head>` with the character set and a title, the calculation in
the `<body>`), from the renderer's `preamble` and `postamble`:

```python
HandCalcs(HTMLRenderer())(source, destination="beam.html")
```

In Jupyter, `%hc_default_renderer html` displays it with `IPython.display.HTML`.

## Output structure

```html
<div class="handcalcs">
  <style>/* scoped rules */</style>
  <h1>Bolt group</h1>
  <p class="hc-comment">Shear is shared equally between the bolts.</p>
  <div class="hc-line">n = 4 (bolts)</div>
  <table class="hc-params">...</table>
  <div class="hc-block">
    <div class="hc-header">Since ... is True:</div>
    <div class="hc-body">
      <div class="hc-line">status = "OK"</div>
    </div>
  </div>
</div>
```

| Class | Element |
|---|---|
| `handcalcs` | The container. Holds the CSS custom properties. |
| `hc-line` | One rendered line (a calculation, parameter or import). |
| `hc-comment` | A paragraph of comment lines. |
| `hc-block`, `hc-header`, `hc-body` | An `if`/`for` block: its header line and its indented body. |
| `hc-params` | A parameter grid (a `<table>`); cells are `hc-param-id`, `hc-param-eq`, `hc-param-val`, `hc-param-comment`, with `hc-param-gap` spacers. |
| `hc-multiline` | Added to the table of a `# hc: -m` calculation. |
| `hc-pre` | Pre-formatted text (whitespace kept). |

Headings are `<h1>` (for `##`) to `<h6>`. The headings and text sizes come from the host
page.

## Conventions

- Names: Greek letters as Unicode characters; `_` makes a `<sub>` subscript, and further
  subscripts follow after a comma (`N<sub>pl,Rd</sub>`; nested with the `subscripts`
  option); `__` is a space, `___` a literal underscore. `hat`, `bar`, `dot`, `ddot`,
  `prime` and `star` add a hat, an overbar, a dot, two dots, a prime or a superscript `*` to
  the part before them. All of this is one `name:sym` rule, `swap_identifier`. See
  [naming variables](../getting-started/writing-calculations.md#naming-variables).
- Operators: `*` → `·`, `**` → `<sup>`, `sqrt` → `√`, `<=` → `≤`.
- Numbers use the format code as-is (`1.2e+05` stays as written). Strings are shown in
  curly quotes and HTML-escaped.

## Source

{source}`src/handcalcs/renderers/html.py`
