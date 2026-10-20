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

The same calculation can go to different **renderers**: Markdown and LaTeX for Jupyter and documents, HTML for web pages, ASCII text for terminals and logs, a live, formula-based Excel worksheet and Word documents. You can restyle the built-in renderers or write your own.

**[Read the documentation](https://handcalcs.structuralpython.com/)**: getting started, every renderer, a cookbook of
recipes, and how to customize or write a renderer.

> ### Engineers who use handcalcs
> Did you know that you can _link_ your handcalcs Jupyter notebooks together so that the result of one notebook is available as an input for the next?
>
> [Opt in here](https://www.structuralpython.com/handcalcs-the-chaining-technique) to see how you can use the [Chaining Technique](https://www.structuralpython.com/handcalcs-the-chaining-technique) to build entire engineering automations from your handcalcs notebooks.

## Example

```python
from math import sqrt   # hc: -i
## Hypotenuse of a right triangle
# Both sides are measured from the site drawings.
a = 2.5  # Side a, in m
b = 4.0  # Side b, in m
c = sqrt(a**2 + b**2)
```

In Jupyter this is typeset as maths. With the ASCII renderer it reads:

```text
==============================
Hypotenuse of a right triangle
==============================

Both sides are measured from the site drawings.
a = 2.5 (Side a, in m)
b = 4 (Side b, in m)
c = √(a² + b²) = √(2.5² + 4²) = 4.717
```

## Installing

```console
pip install handcalcs
```

handcalcs needs Python 3.11 or newer. Extras add the Excel and Word renderers
(`handcalcs[excel]`, `handcalcs[word]`) and Jupyter export options
(`handcalcs[exporters]`). See [Installation](https://handcalcs.structuralpython.com/getting-started/installation.html).

## Quick start

In Jupyter, import handcalcs once, then start any cell with `%%render`:

```python
import handcalcs
```

```python
%%render
a = 2
b = 3
c = 2*a + b/3
```

From a script, render a string or a `.py` file with any renderer:

```python
import pathlib
from handcalcs import HandCalcs
from handcalcs.renderers import LatexRenderer

latex = HandCalcs(LatexRenderer())(pathlib.Path("beam.py"))
```

On a function, `@handcalc(renderer)` returns the result and the rendered calculation.

## Renderers

Markdown (the Jupyter default), LaTeX, HTML, ASCII text, a live formula-based Excel
workbook, and Word documents with native equations. Subclass one to change its look, or
write your own. See [Renderers](https://handcalcs.structuralpython.com/renderers/index.html).

## Upgrading from handcalcs 1.x

handcalcs 2 is a rewrite around a parsed node tree and pluggable renderers. Most notebooks
need only a few changes: `import handcalcs` instead of `import handcalcs.render`, and
`# hc:` comment commands instead of `%%render` arguments. See
[Coming from handcalcs v1](https://handcalcs.structuralpython.com/getting-started/migrating-from-v1.html).

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
