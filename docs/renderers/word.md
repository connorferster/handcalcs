# Word renderer

The `WordRenderer` turns a calculation into a **Word document (.docx)** whose equations
are native Word equations, the kind Word's own equation editor makes. Click into any
value or symbol in Word to edit it. Fonts and sizes come from the document's styles, so
every equation matches the text around it.

## Installing

The renderer builds documents with [python-docx](https://python-docx.readthedocs.io), an
optional dependency:

```console
$ pip install "handcalcs[word]"
```

## Usage

```python
from handcalcs import HandCalcs
from handcalcs.renderers import WordRenderer

source = '''
## Roots of a quadratic
from math import sqrt
a = 2; b = -7; c_0 = 3
x_1 = (-b + sqrt(b**2 - 4*a*c_0)) / (2*a)  # larger root
'''

HandCalcs(WordRenderer())(source, destination="quadratic.docx")
```

With `destination=`, the document is saved there and its `Path` is returned. Without it,
the renderer returns a python-docx
[`Document`](https://python-docx.readthedocs.io/en/latest/api/document.html): call
`document.save(path)` yourself, or keep adding to it with python-docx first. The
renderer's `filepath=` option saves every render it makes, wherever it is called from.

This works from a plain `.py` script or any Python program, with no Jupyter or export
step. Pass a `pathlib.Path` to render a whole file:
`HandCalcs(WordRenderer())(Path("calc.py"), destination="calc.docx")`.

## Layout

| handcalcs | Word |
|---|---|
| a run of calc lines | one equation, flush left, its rows aligned on the first `=` |
| a params line (`b = 300; d = 500`) | a borderless table, one equation per cell, so the grid keeps its columns |
| `## Heading` | a paragraph in the `Heading 1` style (`###` → `Heading 2`, and so on) |
| comment lines | a text paragraph |
| an import | the import's source in the `HC Code` style |
| `if`/`for`/function headers | a text paragraph with the condition as an inline equation: "Since (*a* > 1) → (2 > 1) is True:" |
| a nested block | indented 0.5" per level |
| an inline comment | normal text after the equation; on its own row when the line shows substitutions |
| a `-m` calc or a line continuation (`\`) | extra rows in the same aligned equation |

Names follow the shared [naming rules](../getting-started/writing-calculations.md#naming-variables):
subscripts, Greek letters, accents and the `symbols` option look the same as in the other
renderers. A single letter is italic, as in print; a word (`max`, `Rd`) is upright and
stays one run, so you can edit it as one word in Word.

## Choosing a layout for Google Docs and LibreOffice

Word aligns the rows of a calc on their `=` signs with an **equation array**. Google Docs
and LibreOffice don't show equation arrays properly: Google Docs runs the rows together
on one line, and LibreOffice draws the alignment marks as stray symbols. For a document
headed there, use the `"lines"` layout. Each row becomes an equation of its own (no `=`
alignment), and rows that continue the one above are indented a little:

```python
WordRenderer(filepath="calc.docx", layout="lines")
```

| `layout` | Looks right in | Rows |
|---|---|---|
| `"aligned"` (default) | Word | one equation per run of calcs, aligned on `=` |
| `"lines"` | Word, Google Docs, LibreOffice | one equation per row, not aligned |

A comment command changes the layout for the calcs that follow it:

```python
# hc: layout = "lines"
```

## Templates and reports

**A company template.** `template=` starts each document from a `.docx`. Its styles, page
setup, headers and footers and any content already in it (a title block, say) are kept,
and the calculation is added after that content:

```python
WordRenderer(template="company.docx", filepath="beam.docx")
```

**Several calcs in one report.** `document=` appends to a python-docx `Document` you
already have, so one report can hold many calculations with your own text between them:

```python
import docx
from handcalcs import HandCalcs
from handcalcs.renderers import WordRenderer

report = docx.Document("company.docx")
report.add_heading("Beam design", level=1)
calc = HandCalcs(renderer=WordRenderer(document=report))
calc(beam_source)
report.add_paragraph("The column carries the beam reaction.")
calc(column_source)
report.save("report.docx")
```

Give `template=` or `document=`, not both.

### Styles

The renderer uses the document's `Normal` and `Heading 1`-`Heading 9` styles, and adds
two of its own when the document doesn't define them:

| Style | Kind | Used for | Default |
|---|---|---|---|
| `HC Math` | paragraph, based on `Normal` | paragraphs holding equations | 6 pt before and after a group, none between its rows |
| `HC Code` | character | imports | Consolas |

To restyle them, define styles with these names in your template. Equations take their
paragraph's font size, so a larger `HC Math` gives larger equations. If a template has
no `Heading N` style, that heading becomes a bold paragraph and handcalcs warns you.

## Options

```python
WordRenderer(
    filepath=None,      # also save every render here
    layout="aligned",   # or "lines"
    template=None,      # a .docx to start each document from
    document=None,      # a python-docx Document to append to
)
```

An unknown layout or a missing template raises an error when the renderer is created.

## Comment commands

| command | effect in Word |
|---|---|
| `-f CODE` | formats calculated values, as in every renderer |
| `-m` | puts the symbolic, numeric and result columns on rows of their own |
| `-b` | inserts an empty paragraph |
| `-i` | leaves the line out |
| `-h`, `;` | a params table |
| `layout = "lines"` | one equation per row for the calcs that follow |

## Units

[pint](https://pint.readthedocs.io) and
[forallpeople](https://github.com/connorferster/forallpeople) values show their number as
math and their unit as text: 2.8125 kN·m. The number takes the format code. A pint unit
is written in the registry's format, so set `ureg.formatter.default_format = "~P"` for
short unit symbols (`mm²` rather than `millimeter ** 2`).

## In Jupyter

`%%render` has no Word display, so the Word renderer isn't a `jupyter_renderer`. To make
a document from a notebook, put the calculation in a Python cell:

```python
document = HandCalcs(renderer=WordRenderer(filepath="calc.docx"))(source)
```

To convert rendered Markdown instead, pandoc turns the
[Markdown renderer](markdown.md)'s output into Word equations too:

```console
$ pandoc calc.md -o calc.docx
```

pandoc centres every equation, splits upright words into single letters and flattens
params grids into one row, so the Word renderer gives a closer match to handcalcs'
layout.

## Notes

- An equation row can't break across lines, so a list or tuple longer than 10 items
  shows its first and last 3 items around "…". Use a line continuation (`\`) to break
  a long equation yourself.
- `HandCalcs(renderer=WordRenderer()).demo()` renders the general handcalcs demo as a
  document.

## Source

- {source}`src/handcalcs/renderers/word/renderer.py`: the renderer, its options and the tree walk
- {source}`src/handcalcs/renderers/word/handlers.py`: node handlers that return OMML fragments
- {source}`src/handcalcs/renderers/word/omml.py`: builders for Office Math Markup (OMML)
- {source}`src/handcalcs/renderers/word/document.py`: writing paragraphs, equations and tables

The Word renderer's handlers return OMML strings, Word's math markup, the way the
LaTeX renderer's return LaTeX, so the base renderer's line machinery works on them
unchanged. Only `complete()` builds the document. See
[Example: a non-text renderer](../building-renderers/example-json.md).
