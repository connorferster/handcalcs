# Reports and documents

Recipes for getting calculations into a deliverable: a PDF, a Word file, a web page or a
Quarto report, with equation numbers, a title block and your colors.

## Write a calculation straight to a file

*Asked in {issue}`177`, {issue}`138`, {issue}`128` and {issue}`203`.*

You don't need Jupyter or a notebook export. `HandCalcs` renders a `.py` file (or a
string) with any renderer, and the result is a string you can save:

```python
import pathlib
from handcalcs import HandCalcs
from handcalcs.renderers import LatexRenderer, HTMLRenderer, MarkdownRenderer

calc = pathlib.Path("calcs/beam.py")
pathlib.Path("report/beam.tex").write_text(HandCalcs(LatexRenderer())(calc))
pathlib.Path("report/beam.html").write_text(HandCalcs(HTMLRenderer())(calc))
pathlib.Path("report/beam.md").write_text(HandCalcs(MarkdownRenderer())(calc))
```

The HTML output is self-contained: it needs no MathJax or other JavaScript.
See [Python: `HandCalcs`](../interfaces/object-oriented.md).

## A PDF through LaTeX

Write the LaTeX output to a file and `\input` it into your report. It needs only the
`amsmath` package:

```latex
\documentclass{article}
\usepackage{amsmath}
\begin{document}
\input{beam.tex}
\end{document}
```

See [LaTeX renderer](../renderers/latex.md#using-the-output).

## A Word document

*Asked in {issue}`222` and {issue}`228`.*

The Word renderer writes a `.docx` file with native, editable Word equations:

```python
import pathlib
from handcalcs import HandCalcs
from handcalcs.renderers import WordRenderer

HandCalcs(WordRenderer(filepath="beam.docx"))(pathlib.Path("calcs/beam.py"))
```

Install it with `pip install "handcalcs[word]"`. It can add to an existing document
(`document=`) or start from your company template (`template="company.docx"`). See
[Word renderer](../renderers/word.md).

## A Quarto or MyST report

The Markdown output works in Quarto (`.qmd`) and MyST documents as it is. Render a
calculation in a code cell with `%%render`, or write the Markdown to a file and include
it. See [Where it works](../renderers/markdown.md#where-it-works).

## Share a notebook without the code

To share a notebook without the code cells, export it with nbconvert's `--no-input`
option:

```bash
jupyter nbconvert --to html --no-input calcs.ipynb
jupyter nbconvert --to pdf --no-input calcs.ipynb
```

`pip install "handcalcs[exporters]"` also adds "no input" export options to Jupyter's
menus. See [Exporting a notebook](../interfaces/jupyter.md#exporting-a-notebook).

## Start a new page

*Asked in {issue}`233`.*

`# hc: --pagebreak` starts a new page in printed and exported output: `\newpage` in
LaTeX, a CSS page break in HTML and Markdown, a real page break in Word and a print page
break in Excel. On its own line it breaks before the next line; at the end of a line it
breaks after it:

```python
## Loads
w = 5            # kN/m
L = 6            # m
# hc: --pagebreak
## Design
M = w * L**2 / 8
V = w * L / 2    # hc: --pagebreak
```

See [Page breaks](../reference/comment-commands.md#page-breaks).

## Number the equations

*Asked in {issue}`218` and {issue}`200`.*

A `calc_line:post` rule can append a number to each calculation. This one reads two
context fields: `eq_numbers = True` numbers every calculated line in order, and
`label = "..."` at the end of a line gives that line its own label:

```{literalinclude} ../_examples/equation_numbers.py
:language: python
```

```{hc-example}
:renderer-file: _examples/equation_numbers.py
:renderer-class: NumberedMarkdownRenderer
# hc: eq_numbers = True
w = 5                     # kN/m
L = 6                     # m
M = w * L**2 / 8          # kN m
V = w * L / 2             # kN
R_A = V                   # hc: label = "B.1"
```

The number is placed in the math as `\qquad (n)`, so it works in Jupyter, KaTeX and
LaTeX alike. For LaTeX cross-references, emit `\tag{...}\label{...}` instead and use an
`align` environment in your own subclass.

## A title block on every calculation

*Asked in {issue}`137`.*

Override `complete()`, which assembles the final output, and add a header built from
context fields. Set the fields once per session with `handcalcs.set_option("project",
"Footbridge")`, or per calculation with a comment command:

```{literalinclude} ../_examples/title_block.py
:language: python
```

```{hc-example}
:renderer-file: _examples/title_block.py
:renderer-class: TitleMarkdownRenderer
# hc: project = "Footbridge"; calc_by = "CF"; date = "2026-10-20"
w = 5                     # kN/m
L = 6                     # m
M = w * L**2 / 8          # kN m
```

`TitleLatexRenderer` writes the same block as a `tabular` for LaTeX output.

## Left-aligned or centred equations

*Asked in {issue}`201`, {issue}`186`, {issue}`133`, {issue}`116` and {issue}`91`.*

The LaTeX renderer sets its math flush left. To centre it instead, override the math
delimiters:

```{literalinclude} ../_examples/latex_display.py
:language: python
```

The Markdown renderer's `$$...$$` blocks are placed by your notebook or site; Jupyter
centres them. The HTML renderer is always flush left.

## Colors

*Asked in {issue}`293`.*

- HTML: [Styling the HTML output](../customizing/html-styling.md), including a theme
  with dark mode and highlighted results.
- Markdown and LaTeX: [Colors in Markdown math](../customizing/latex-markdown-tokens.md#example-colors-in-markdown-math).

## Wrap the whole output

Override `complete()`, call the parent's, and add to the result. For example, a framed
LaTeX box:

```python
class FramedLatexRenderer(LatexRenderer):
    def complete(self, tree, base_context):
        body = super().complete(tree, base_context)
        return "\\begin{framed}\n" + body + "\\end{framed}\n"
```

**Next:** [Apps and workflows](workflows.md).
