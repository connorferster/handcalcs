# LaTeX and Markdown tokens

`LatexRenderer` builds its output from a set of **tokens**: class attributes holding the
strings it wraps math groups, paragraphs and blocks in. `MarkdownRenderer` is a subclass
of `LatexRenderer` that overrides some of them. Change a token by overriding it in your
own subclass.

## The tokens

| Attribute | `LatexRenderer` | `MarkdownRenderer` | Wraps or separates |
|---|---|---|---|
| `MATH_OPEN` | `\noindent$\displaystyle` + newline + `\begin{aligned}[t]` | `$$\begin{aligned}` | The start of a math group |
| `MATH_CLOSE` | `\end{aligned}$` | `\end{aligned}$$` | The end of a math group |
| `ROW_SEP` | ` \\` + newline | ` \\ ` | Rows within a group |
| `MATH_SKIP` | `\medskip` | (empty) | Before and after each group |
| `PARAGRAPH` | `\noindent ` | (empty) | The start of each prose paragraph |
| `LINE_BREAK` | `\medskip` | `&nbsp;` | A `# hc: -b` break |
| `BLOCK_OPEN`, `BLOCK_CLOSE` | a `list` environment | not used | Around an `if`/`for` body |
| `BLOCK_PREFIX` | not used | `>` | Each line of an `if`/`for` body (blockquote) |
| `HEADINGS` | `section*`, `subsection*`, `subsubsection*`, `paragraph*` | not used (`#` headings) | Headings by level |
| `COMMENT_OPEN`, `COMMENT_CLOSE` | `\quad\text{(`, `)}` | inherited | Around an inline comment |
| `OPERATOR_SYMBOLS` | `{"mult_op": "\\cdot", ...}` | adds `\lt`, `\gt` | The symbol for each operator node type |
| `MATH_FUNCS` | `{"sin": "\\sin", ...}` | inherited | Function names typeset as operators |

The values are in {source}`src/handcalcs/renderers/latex.py` and
{source}`src/handcalcs/renderers/markdown.py`.

```{important}
The Markdown renderer keeps each math group on **one physical line**. If you override
`ROW_SEP` or `MATH_OPEN` in a Markdown subclass, don't add newlines; Jupyter would carry
the blockquote `>` markers of an `if` body into the math.
```

## Example: centred LaTeX displays with `\times`

```{literalinclude} ../_examples/latex_display.py
:language: python
```

```{hc-example}
:renderer-file: _examples/latex_display.py
:renderer-class: DisplayLatexRenderer
:output-language: latex
a = 2
b = a * 3
```

## Example: colors in Markdown math

MathJax and KaTeX both support `\color{name}{...}`, so a Markdown renderer can color parts
of the math. This subclass colors calculated results and inline comments:

```{literalinclude} ../_examples/markdown_colors.py
:language: python
```

```{hc-example}
:renderer-file: _examples/markdown_colors.py
:renderer-class: ColorMarkdownRenderer
:output: markdown
w = 5  # kN/m
L = 6  # m
M = w * L**2 / 8  # kN m
```

Two details in this example come from how the LaTeX layout works:

- The result is found as the part after the last `=` of the line (the context's
  `assign`), the same way as in the [HTML example](html-styling.md#option-3-add-your-own-markup).
- The LaTeX layout recognises an inline comment by its `COMMENT_OPEN` prefix, and moves
  the comment of a long calculation onto its own row. Because `color_comment` changes how
  comments start, the subclass sets `COMMENT_OPEN` to match. If you change
  `COMMENT_COLOR` in a further subclass, set `COMMENT_OPEN` again.

## Example: a different heading scheme in LaTeX

```python
class ChapterLatexRenderer(LatexRenderer):
    HEADINGS = ("chapter*", "section*", "subsection*", "subsubsection*")
```

**Next:** [Symbols and functions](symbols-and-functions.md).
