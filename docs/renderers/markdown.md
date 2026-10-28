# Markdown renderer

`MarkdownRenderer` produces Markdown text with LaTeX math in `$$` delimiters. It is the
default for `%%render` in Jupyter, and works anywhere Markdown is shown with MathJax or
KaTeX.

```python
from handcalcs.renderers import MarkdownRenderer
```

```{hc-example}
:renderer: markdown
:setup: from math import sqrt
## Bolt group
# Shear is shared equally between the bolts.
n = 4  # bolts
V_f = 120  # kN
V_b = V_f / n
if V_b <= 40:
    status = "OK"
```

The raw output:

```{hc-example}
:renderer: markdown
:hide-source:
:output: code
:output-language: markdown
:setup: from math import sqrt
## Bolt group
# Shear is shared equally between the bolts.
n = 4  # bolts
V_f = 120  # kN
V_b = V_f / n
if V_b <= 40:
    status = "OK"
```

## A fuller example

Headings and prose, a parameter grid, a long equation broken with `-m`, a governing
branch, and a pass/fail check, all in one calculation:

```{hc-example}
:renderer: markdown
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

## Where it works

- **Jupyter** (Lab, Notebook, VS Code): `%%render` displays it with `IPython.display.Markdown`.
- **MyST / Sphinx** with the `dollarmath` and `amsmath` extensions, and **Quarto**.
- **GitHub** and other sites that render `$$` math with MathJax or KaTeX.

## Output structure

| Source | Markdown |
|---|---|
| `## Heading` | `# Heading` (one `#` fewer than the source) |
| Comment lines | A paragraph |
| `import ...` | A code span |
| A run of calculation lines | One `$$\begin{aligned} ... \end{aligned}$$` on a **single line** |
| A parameter grid | Its own `aligned` group |
| `# hc: -b` | An `&nbsp;` spacer paragraph |
| `if` / `for` body | A blockquote, one `>` per nesting level |

The math is the same as the [LaTeX renderer](latex.md)'s (Greek letters, subscripts,
fractions, `\sqrt`), with two changes for MathJax and KaTeX: `<` and `>` are written as
`\lt` and `\gt` (a raw `<` can be mistaken for an HTML tag), and text inside math
(comments, strings) is wrapped in `\text{}`.

Each math group is kept on one physical line because Jupyter extracts math from the raw
text *before* parsing the Markdown; a group spread over several `>`-quoted lines would
carry the `>` characters into the LaTeX.

## Customizing

`MarkdownRenderer` subclasses `LatexRenderer` and is controlled by the same class
attributes (`MATH_OPEN`, `ROW_SEP`, `BLOCK_PREFIX`, `LINE_BREAK`, `OPERATOR_SYMBOLS`, ...).
See [LaTeX and Markdown tokens](../customizing/latex-markdown-tokens.md).

## Source

{source}`src/handcalcs/renderers/markdown.py`
