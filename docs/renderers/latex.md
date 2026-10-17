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

## Using the output

The fragment needs the `amsmath` package. A minimal document:

```latex
\documentclass{article}
\usepackage{amsmath}
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
  `lamb` gives $\lambda$ since `lambda` is a Python keyword). `_` starts a subscript and
  each further `_` nests another level. Multi-letter words are set upright
  (`class_section` → $\mathrm{class}_{\mathrm{section}}$). `__` is a space and `___` a
  literal underscore.
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
