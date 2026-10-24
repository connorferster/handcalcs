# Installation

handcalcs is a pure-Python package on PyPI. These docs are for handcalcs 2.0, which is
a release candidate for now, so ask for it by version (a plain `pip install handcalcs`
installs 1.x):

```console
$ pip install "handcalcs>=2.0.0rc1"
```

or, with [uv](https://docs.astral.sh/uv/):

```console
$ uv add "handcalcs>=2.0.0rc1"
```

## Optional extras

| Extra | Install | Adds |
|---|---|---|
| `excel` | `pip install "handcalcs[excel]"` | [XlsxWriter](https://xlsxwriter.readthedocs.io/), needed by the [Excel renderer](../renderers/excel.md) to write `.xlsx` files |
| `word` | `pip install "handcalcs[word]"` | [python-docx](https://python-docx.readthedocs.io/), needed by the [Word renderer](../renderers/word.md) to write `.docx` files |
| `exporters` | `pip install "handcalcs[exporters]"` | [nb-hideinputs](https://github.com/connorferster/nb-hideinputs), Jupyter export options that hide input cells |
| `doc` | `pip install "handcalcs[doc]"` | Sphinx and the theme used to build these docs |

## Using handcalcs in Jupyter

handcalcs does not install Jupyter itself. Install JupyterLab (or Notebook) in the same
environment:

```console
$ pip install "handcalcs>=2.0.0rc1" jupyterlab
```

Then, in a notebook, `import handcalcs` registers the `%%render` cell magic. See
[the Jupyter interface](../interfaces/jupyter.md).

Jupyter typesets the default Markdown output with MathJax, so no LaTeX installation is
needed to *see* rendered calculations. You only need a LaTeX distribution if you export
the notebook to PDF through LaTeX, or compile the output of the
[LaTeX renderer](../renderers/latex.md) yourself.

## Checking the installation

```python
>>> from handcalcs import HandCalcs
>>> from handcalcs.renderers import ASCIIRenderer
>>> print(HandCalcs(ASCIIRenderer()).demo()[:120])
```

`demo()` renders a built-in example calculation with whichever renderer you give it,
which is also a quick way to compare renderers.

**Next:** [How handcalcs reads your code](how-it-works.md).
