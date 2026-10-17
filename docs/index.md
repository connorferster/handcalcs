# handcalcs

**Python calculations, written out the way you would write them by hand.**

handcalcs turns ordinary Python calculation code into a formatted calculation: the
symbolic formula, then the formula with every value substituted in, then the result.
Because the substitution step is shown, anyone can check the calculation by hand.

```{hc-example}
:renderer: markdown
:setup: from math import sqrt
a = 2.5  # Side a, in m
b = 4.0  # Side b, in m
c = sqrt(a**2 + b**2)  # Hypotenuse
```

The same parsed calculation can be sent to different **renderers**: Markdown and LaTeX for
Jupyter and documents, HTML for web pages, plain text for terminals and logs, and a live
Excel worksheet. You can restyle the built-in renderers or write your own.

## Where do you want to go?

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} {octicon}`rocket` Get started
:link: getting-started/index
:link-type: doc

Install handcalcs and render your first calculation in Jupyter or a Python script.
:::

:::{grid-item-card} {octicon}`paintbrush` Use a renderer
:link: renderers/index
:link-type: doc

Markdown, LaTeX, HTML, plain text or Excel: what each produces and when to use it.
:::

:::{grid-item-card} {octicon}`plug` Pick an interface
:link: interfaces/index
:link-type: doc

The `%%render` cell magic, the `HandCalcs` object, or the `@handcalc` decorator.
:::

:::{grid-item-card} {octicon}`tools` Customize a renderer
:link: customizing/index
:link-type: doc

Add colors to the HTML output, change Markdown and LaTeX tokens, add symbols.
:::

:::{grid-item-card} {octicon}`package` Build a renderer
:link: building-renderers/index
:link-type: doc

How rendering works, the methods you override, and worked examples.
:::

:::{grid-item-card} {octicon}`code` Work on handcalcs
:link: developers/index
:link-type: doc

Set up a development environment, find your way around the source, run the tests.
:::
::::

Looking for a specific function, option or `# hc:` command? See the
[reference](reference/index.md).

```{toctree}
:hidden:
:maxdepth: 2

getting-started/index
interfaces/index
renderers/index
customizing/index
building-renderers/index
developers/index
reference/index
```
