<p>
  <a href="https://github.com/connorferster/handcalcs/actions/workflows/python-pytest.yml"><img src="https://github.com/connorferster/handcalcs/actions/workflows/python-pytest.yml/badge.svg" alt="Tests"></a>
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black">
  <img src="https://img.shields.io/pypi/v/handcalcs" alt="PyPI version">
  <img src="https://img.shields.io/pypi/pyversions/handcalcs" alt="Python versions">
  <img src="https://img.shields.io/github/license/connorferster/handcalcs" alt="License">
  <img src="https://static.pepy.tech/badge/handcalcs" alt="Downloads">
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/connorferster/handcalcs/main/docs/images/handcalcs.jpg" alt="handcalcs cover art"><br>
  Cover art by <a href="https://www.copperkettlegameworks.ca/">Joshua Hoiberg</a>
</p>

<h1 align="center">handcalcs:<br>Python calculations,<br>as though you wrote them by hand.</h1>

`handcalcs` turns ordinary Python calculation code into a formatted calculation: the symbolic formula, then the formula with every value **substituted in**, then the result. Because the substitution step is shown, anyone can check the calculation by hand.

The same calculation can go to different **renderers**: Markdown and LaTeX for Jupyter and documents, HTML for web pages, plain text for terminals and logs, and a live, formula-based Excel worksheet. You can restyle the built-in renderers or write your own.

<!-- TODO: link the hosted v2 documentation here once hosting is set up. -->

> ### Engineers who use handcalcs
> Did you know that you can _link_ your handcalcs Jupyter notebooks together so that the result of one notebook is available as an input for the next?
>
> [Opt in here](https://www.structuralpython.com/handcalcs-the-chaining-technique) to see how you can use the [Chaining Technique](https://www.structuralpython.com/handcalcs-the-chaining-technique) to build entire engineering automations from your handcalcs notebooks.

## Example

```python
from math import sqrt
## Hypotenuse of a right triangle
# Both sides are measured from the site drawings.
a = 2.5  # Side a, in m
b = 4.0  # Side b, in m
c = sqrt(a**2 + b**2)
```

In Jupyter this is typeset as maths. With the plain-text renderer it reads:

```text
[Python import]: from math import sqrt
# Hypotenuse of a right triangle
Both sides are measured from the site drawings.
a = 2.5 (Side a, in m)
b = 4 (Side b, in m)
c = √(a² + b²) = √(2.5² + 4²) = 4.717
```

## Installing

```console
pip install handcalcs
```

handcalcs needs Python 3.11 or newer. Optional extras:

| Extra | Install | Adds |
|---|---|---|
| `excel` | `pip install "handcalcs[excel]"` | XlsxWriter, for the Excel renderer |
| `exporters` | `pip install "handcalcs[exporters]"` | nb-hideinputs, Jupyter export options that hide input cells |

handcalcs does not install Jupyter itself: `pip install handcalcs jupyterlab`.

## Three ways to use it

### 1. In Jupyter: the `%%render` cell magic

Import handcalcs once, then start any cell with `%%render`. The cell runs as normal Python, and handcalcs displays it as a calculation (Markdown with LaTeX maths by default):

```python
import handcalcs
```

```python
%%render
a = 2
b = 3
c = 2*a + b/3
```

Switch the output format for the session with `%hc_default_renderer latex` (or `html`, `plain_text`, `markdown`).

### 2. In a script: the `HandCalcs` object

```python
import pathlib
from handcalcs import HandCalcs
from handcalcs.renderers import LatexRenderer

calc = HandCalcs(renderer=LatexRenderer())
latex = calc("a = 2\nb = 3\nc = 2*a + b/3")   # a source string...
latex = calc(pathlib.Path("beam.py"))         # ...or a .py file
```

`HandCalcs(renderer).demo()` renders a built-in example, a quick way to compare renderers.

### 3. On a function: the `@handcalc` decorator

```python
from handcalcs import handcalc
from handcalcs.renderers import PlainTextRenderer

@handcalc(PlainTextRenderer())
def moment(w, L):
    M = w * L**2 / 8  # kN m
    return M

value, rendered = moment(5, 6)
# value == 22.5
# rendered == "M = w * L² / 8 = 5 * 6² / 8 = 22.5 (kN m)\n"
```

The function runs normally and returns `(return_value, rendered)`. Its body is rendered with the values from that call.

## Renderers

| Renderer | Name | Output |
|---|---|---|
| `MarkdownRenderer` | `markdown` | Markdown prose with LaTeX maths; the `%%render` default |
| `LatexRenderer` | `latex` | A LaTeX fragment for your own documents |
| `HTMLRenderer` | `html` | A self-contained, themeable HTML fragment (`HTMLRenderer(theme_color="#0B5F66")`) |
| `PlainTextRenderer` | `plain_text` | Unicode text for terminals and logs |
| `ExcelRenderer` | `excel` | A live `.xlsx` worksheet: every calculation is a real Excel formula, with named cells, units and `IF` formulas for conditionals |
| `BaseRenderer` | `base` | The raw render tree, the starting point for your own renderer |

All of them live in `handcalcs.renderers`. Subclass one to change its look, or subclass `BaseRenderer` to write a new output format.

## Writing calculations

- **Comments are part of the output.** A `##` comment is a heading, a plain comment line is a paragraph, and a comment at the end of a line is shown next to that line. `{{ name }}` in a comment inserts a value.
- **Parameter lines** (`a = 2`) show just the value. Put several on one line with `;` to get a compact grid.
- **`if`/`elif`/`else` and `for` blocks** render the branch that ran, with its condition.
- **Units:** [forallpeople](https://github.com/connorferster/forallpeople) and [pint](https://pint.readthedocs.io) quantities render with their units.

### Comment commands

A comment starting with `hc:` is a command. At the end of a line it applies to that line; on its own line it applies to every line after it.

| Command | Effect |
|---|---|
| `# hc: -f .2f` | Number format (any Python format code) |
| `# hc: -m` | Break a long calculation over several lines |
| `# hc: -p` | Show *target = result* only |
| `# hc: -h` | Show the following assignments as a grid |
| `# hc: -c 2` | Columns in parameter grids (default 3) |
| `# hc: -b` | Add vertical space |
| `# hc: -i` | Leave lines out of the output |
| `# hc: --mode no_num` | Leave out the numeric substitution (`no_sym` leaves out the symbolic formula) |

### Configuration

```python
import handcalcs
handcalcs.set_option("format_code", ".3g")   # this session
handcalcs.save_config()                      # ...and from now on
```

The options are `format_code`, `default_renderer` (used by a bare `HandCalcs()`) and `jupyter_renderer` (used by `%%render`).

## Upgrading from handcalcs 1.x

handcalcs 2 is a rewrite around a parsed node tree and pluggable renderers. Most notebooks need only a few changes:

| 1.x | 2.0 |
|---|---|
| `import handcalcs.render` | `import handcalcs` |
| `%%tex` | `%hc_default_renderer latex`, then `%%render` |
| `%%render 2` (precision) | `# hc: -f .2f` |
| `%%render params` | `;`-separated parameter lines, or `# hc: -h` |
| `%%render long` / `short` | `# hc: -m` / the default |
| `%%render symbolic` | `# hc: mode = "ass sym"` |
| `@handcalc(override=..., precision=...)` | `@handcalc(renderer, render_context={"format_code": ".2f"})` |
| `set_option("display_precision", 3)` | `set_option("format_code", ".3f")` |
| `%%render sympy` | not available in 2.0 |

The v1 global options (`latex_block_start`, `custom_symbols`, `greek_exclusions`, ...) are now renderer attributes and rules. A v1 `config.json` is not read.

## Gotchas

Jupyter cells can run out of order. handcalcs looks up values in the notebook's namespace, so if you re-use variable names, a cell run out of order can render a **beautiful but completely incorrect** calculation. Run your notebook top to bottom before you rely on it.

**If you use handcalcs for any kind of reporting that may become a legal document (e.g. design engineering calculations), it is up to YOU to ensure that the results are what you expect them to be. handcalcs is free and open-source software, and the author(s) are not responsible for incorrect calculations that result from its use.**

That said, the whole point of showing the substitution is to make calculations easy to check by hand.

## YouTube tutorials

These cover handcalcs 1.x; the ideas carry over.

- [Getting Started with handcalcs (assumes zero Python knowledge)](https://www.youtube.com/watch?v=ZNFhLCWqA_g)
- [Engineering Calculations: handcalcs-on-Jupyter vs. Excel](https://www.youtube.com/watch?v=n9Uzy3Eb-XI)

## License

Apache 2.0. See [LICENSE](https://github.com/connorferster/handcalcs/blob/main/LICENSE).
