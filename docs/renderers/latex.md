# LaTeX renderer

`LatexRenderer` produces a LaTeX fragment to paste into the body of a `.tex` document.

```python
from handcalcs.renderers import LatexRenderer
```

```{hc-example}
:renderer: latex
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
:renderer: latex
:setup: from math import pi, sqrt
## Steel beam
# Lateral-torsional buckling resistance of a simply supported span.
# hc: -h -c 3
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

To get a document you can compile straight away, give a `destination`:

```python
HandCalcs(LatexRenderer())(pathlib.Path("calcs/bolts.py"), destination="bolts.tex")
```

The file is the output wrapped in the renderer's `preamble` and `postamble`: an
`article` that loads the packages below. Change them on the renderer for your own
document class (see [Writing a file](../interfaces/object-oriented.md#writing-a-file)).

Without a `destination`, the output is a fragment for the body of a document. It needs
the `amsmath` package, plus `amssymb` and `xcolor` for the marks of
[`--check`](../cookbook/checks.md) lines. A minimal document:

```latex
\documentclass{article}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{xcolor}
\begin{document}
% paste or \input the handcalcs output here
\end{document}
```

A common pattern is to write each calculation to its own file and `\input` it:

```python
import pathlib
from handcalcs import HandCalcs
from handcalcs.renderers import LatexRenderer

tex = HandCalcs(LatexRenderer())(pathlib.Path("calcs/bolts.py"))
pathlib.Path("report/bolts.tex").write_text(tex)
```

```latex
\input{bolts.tex}
```

In Jupyter, `%hc_default_renderer latex` displays the output with
`IPython.display.Latex`, which renders the math but not the text-mode commands
(`\section*`, `\noindent`, `\medskip`). Use the [Markdown renderer](markdown.md) for
notebooks.

## Output structure

| Source | LaTeX |
|---|---|
| `##`, `###`, `####`, `#####` headings | `\section*`, `\subsection*`, `\subsubsection*`, `\paragraph*` |
| Comment lines | A `\noindent` paragraph (LaTeX special characters escaped) |
| A run of calculation lines | One flush-left `aligned` group, aligned on the first `=` of each row, with `\medskip` before and after |
| Parameter grid | An `aligned` group with one column pair per cell |
| `# hc: -b` | `\medskip` |
| `if` / `for` body | Indented with a `list` environment |

## Math conventions

- Names: Greek letter names become Greek letters (`alpha` → $\alpha$, `Gamma` → $\Gamma$;
  `lamb` or `lambda_` gives $\lambda$ since `lambda` is a Python keyword), and so do
  Unicode letters (`ΔH` → $\Delta H$, which also compiles under pdflatex) and a Greek name
  before an uppercase letter or digit (`DeltaH` → $\Delta H$). `_` starts a subscript and
  each further `_` adds one after a comma (`N_pl_Rd` → $N_{\mathrm{pl,Rd}}$); neighbouring
  upright words share one `\mathrm{}`. Multi-letter words are set upright
  (`class_section` → $\mathrm{class}_{\mathrm{section}}$). `__` is a space and `___` a
  literal underscore. `hat`, `bar`, `dot`, `ddot`, `prime` and `star` decorate the part
  before them (`x_hat` → $\hat{x}$, `M_star` → $M^{*}$). See
  [naming variables](../getting-started/writing-calculations.md#naming-variables).
- Operators: `*` → $\cdot$, `/` → a fraction, `**` → a superscript, `//` → a fraction in
  floor brackets, `%` → $\bmod$, `<=` → $\le$.
- Functions: `sqrt` → a radical; `floor`, `ceil` → brackets; `sin`, `cos`, `exp` and the
  other trigonometric and hyperbolic functions → their operators; any other function by
  its name, upright (`\operatorname`).
- Numbers: scientific notation is written as $\times 10^{n}$; `inf` → $\infty$.
- Collections longer than 10 items show their first and last three items around
  $\ldots$.

## Customizing

The document structure is set by class attributes (`MATH_OPEN`, `MATH_CLOSE`,
`HEADINGS`, `BLOCK_OPEN`, `COMMENT_OPEN`, ...) and the symbol tables `OPERATOR_SYMBOLS` and
`MATH_FUNCS`. Change them in a subclass; see
[LaTeX and Markdown tokens](../customizing/latex-markdown-tokens.md).

## Source

{source}`src/handcalcs/renderers/latex.py`
