# Get started

This page gets you from nothing to a rendered calculation in a couple of minutes. The
other pages in this section explain each feature in depth.

## 1. Install

```console
$ pip install handcalcs
```

For Excel output, install the extra: `pip install "handcalcs[excel]"`. See
[Installation](installation.md) for `uv`, Jupyter setup and the other extras.

## 2. Render a calculation

::::{tab-set}

:::{tab-item} In Jupyter
Import handcalcs once, at the top of the notebook:

```python
import handcalcs
```

Then start any cell with `%%render`. The cell runs as normal Python, and handcalcs
displays it as a calculation:

```python
%%render
a = 2
b = 3
c = 2*a + b/3
```
:::

:::{tab-item} In a Python script
Create a `HandCalcs` object with a renderer and call it with your source code:

```python
from handcalcs import HandCalcs
from handcalcs.renderers import PlainTextRenderer

calc = HandCalcs(renderer=PlainTextRenderer())
print(calc("""
a = 2
b = 3
c = 2*a + b/3
"""))
```
:::

::::

Either way, each line is shown as the **symbolic** formula, the formula with the values
**substituted**, and the **result**:

```{hc-example}
:hide-source:
a = 2
b = 3
c = 2*a + b/3
```

Lines that only assign a number (`a = 2`) are shown as just the value. Calculations show
every step.

## 3. Add explanation

Comments become part of the output. A `##` comment is a heading, a plain comment line is
a paragraph, and a comment at the end of a line is shown next to that line:

```{hc-example}
:setup: from math import sqrt
## Hypotenuse of a right triangle
# Both sides are measured from the site drawings.
a = 2.5  # Side a, in m
b = 4.0  # Side b, in m
c = sqrt(a**2 + b**2)
```

## 4. Control the formatting

A comment that starts with `hc:` is a **command**. It changes how the line (or the
following lines) are rendered. For example, `-f` sets the number format:

```{hc-example}
a = 2.123456
b = 3.987654
c = a * b  # hc: -f .2f
```

[Comment commands](comment-commands.md) lists them all.

## Go deeper

::::{grid} 1 2 2 2
:gutter: 2

:::{grid-item-card} How handcalcs reads your code
:link: how-it-works
:link-type: doc
What each kind of line becomes, and what is not rendered.
:::

:::{grid-item-card} Writing calculations
:link: writing-calculations
:link-type: doc
Headings, prose, inline comments, parameter grids, conditionals and loops.
:::

:::{grid-item-card} Comment commands
:link: comment-commands
:link-type: doc
`# hc:` commands for number formats, long equations, grids and spacing.
:::

:::{grid-item-card} Formatting numbers
:link: formatting-numbers
:link-type: doc
Format codes, and setting them per line, per section or for the whole session.
:::

:::{grid-item-card} Configuration
:link: configuration
:link-type: doc
Save your preferred defaults: format code, default renderers, custom settings.
:::

:::{grid-item-card} Units
:link: units
:link-type: doc
Calculations with forallpeople or pint quantities.
:::

:::{grid-item-card} Gotchas
:link: gotchas
:link-type: doc
Out-of-order cells, unsupported code, and responsibility for results.
:::

:::{grid-item-card} Coming from handcalcs v1
:link: migrating-from-v1
:link-type: doc
What changed in v2 and how to update your notebooks.
:::
::::

**Next:** choose where your output goes with a [renderer](../renderers/index.md), or
choose how you call handcalcs with an [interface](../interfaces/index.md).

```{toctree}
:hidden:

installation
how-it-works
writing-calculations
comment-commands
formatting-numbers
configuration
units
gotchas
migrating-from-v1
```
