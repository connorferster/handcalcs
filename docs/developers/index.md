# Developer's guide

This section is for working on handcalcs itself: fixing a bug, adding a feature, adding a
renderer to the package, or improving these docs.

## Set up in five minutes

handcalcs uses [uv](https://docs.astral.sh/uv/) for its environment.

```console
$ git clone https://github.com/connorferster/handcalcs.git
$ cd handcalcs
$ uv sync                 # creates .venv with the package (editable) and dev tools
$ uv run pytest           # the whole suite runs in a few seconds
```

Build the docs:

```console
$ uv run --extra doc sphinx-build -b html docs docs/_build/html
```

Open `docs/_build/html/index.html`.

## The shape of the code

```text
src/handcalcs/
    __init__.py          public API: HandCalcs, handcalc, set_option, ...
    config.py            global configuration
    interfaces/          HandCalcs, @handcalc, %%render
    parsing/             source -> tree of nodes
    renderers/           tree -> output (base.py is the core)
tests/                   pytest suite; tests/golden holds golden files
docs/                    these docs (Sphinx + MyST)
scripts/                 demo and check scripts (LaTeX compile, Markdown, Excel)
```

Two packages do almost all the work: **`parsing`** builds the node tree, and
**`renderers/base.py`** defines how a tree is rendered. Every built-in renderer is a
subclass that registers handlers and rules; the
[renderer-building guide](../building-renderers/index.md) describes that API and applies
equally to the built-in renderers.

## Go deeper

::::{grid} 1 2 2 2
:gutter: 2

:::{grid-item-card} Repository layout
:link: repository-layout
:link-type: doc
Every module, what it does, with links to the source.
:::

:::{grid-item-card} The parser
:link: parsing
:link-type: doc
From `ast` to handcalcs nodes: comments, commands, blocks and values.
:::

:::{grid-item-card} Rendering internals
:link: rendering-internals
:link-type: doc
`base.py` walkthrough: dispatch, precedence and parentheses, calc lines.
:::

:::{grid-item-card} Adding a node type
:link: adding-a-node-type
:link-type: doc
Supporting new Python syntax, end to end.
:::

:::{grid-item-card} Tests
:link: testing
:link-type: doc
Suite layout, fixtures, golden files.
:::

:::{grid-item-card} Documentation
:link: documentation
:link-type: doc
Building the docs, the `hc-example` directive and the `src` role.
:::

:::{grid-item-card} Releasing
:link: releasing
:link-type: doc
Versioning, CI and publishing to PyPI.
:::
::::

## Conventions

- Code is formatted with [black](https://black.readthedocs.io/); CI checks
  `uv run black src --check`.
- Renderer branches are merged into `hc2/dev` during the v2 cycle; open pull requests
  against it.
- Handlers and rules are module-level functions registered with decorators, named
  `render_<type>` for handlers and for what they do for rules (`swap_greeks`,
  `toggle_param_line`). Their docstrings say what they render and why; keep that up.

```{toctree}
:hidden:

repository-layout
parsing
rendering-internals
adding-a-node-type
testing
documentation
releasing
```
