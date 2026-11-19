# Units

Recipes for calculations with units. handcalcs shows whatever value your code produces,
so the units library does the arithmetic and formats the units. The background is in
[Units](../getting-started/units.md).

## Calculate with forallpeople

Load an environment once, in a cell you don't render, then write units as you would on
paper:

```python
import forallpeople as si
si.environment("structural", top_level=True)
```

```{hc-example}
:setup: import forallpeople as si; si.environment("structural", top_level=True)
# hc: -u
L = 6 * m
w = 5 * kN / m
M = w * L**2 / 8
```

An input such as `6 * m` has nothing worth substituting: without help it renders as
`L = 6 · m = 6 · 1 m = 6 m`. `# hc: -u` shows each line that is a number times units as
*name = value*, and leaves the lines that calculate, like `M`, with every step. On its
own line it lasts until `# hc: units = False`; at the end of a line it applies to that
line. To use it everywhere, set it once: `handcalcs.set_option("units", True)`.

A line counts as a number times units when it has exactly one number, multiplying units:
`5 * kN`, `-12 * kN`, `4.5 * kN / m`, `300 * mm**2`. A name only counts as a unit if it
is one (`kN`), not a variable that holds one (`F = 1 * kN`, then `R = 3 * F`), so `R`
keeps its steps. In symbolic-only [mode](../getting-started/comment-commands.md), which
hides values, lines are left as they are.

For a single line, two other ways give the same result:

- wrap the right-hand side in parentheses: `L = (6 * m)`;
- end the line with the param-line flag: `w = 5 * kN / m  # hc: -p`.

See [Show only the result of a line](showing-and-hiding.md#show-only-the-result-of-a-line).

Units are set upright, and a substituted quantity raised to a power is bracketed.

## Calculate with pint

*Asked in {issue}`203` and {issue}`245`.*

Choose pint's short, pretty unit format when you create the registry:

```python
import pint
ureg = pint.UnitRegistry()
ureg.formatter.default_format = "~P"
```

```{hc-example}
:setup: import pint; ureg = pint.UnitRegistry(); ureg.formatter.default_format = "~P"
# hc: -u
L = 6 * ureg.m
w = 5 * ureg.kN / ureg.m
M = w * L**2 / 8
```

The LaTeX and Markdown renderers typeset pint units in math, abbreviated when the
registry's default format contains `~`; the HTML and ASCII renderers use the
registry's text format (`22.5 kN⋅m` with `~P`).

Outside Jupyter, `HandCalcs(renderer)(source, globals())` renders the same code from a
script. See [Python: `HandCalcs`](../interfaces/object-oriented.md).

## Show a result in specific units

*Asked in {issue}`100` and {issue}`226`.*

Convert with the library's own method. A conversion can be chained onto a whole
expression, or put on its own line with `-p` to show only the converted value:

```{hc-example}
:setup: import pint; ureg = pint.UnitRegistry(); ureg.formatter.default_format = "~P"
w = (5 * ureg.kN / ureg.m)
L = 6000 * ureg.mm  # hc: -p
M = (w * L**2 / 8).to("kN*m")
M_Nmm = M.to("N*mm")  # hc: -p
```

## Set the precision of a quantity

`-f` applies to quantities from both libraries:

```{hc-example}
:setup: import forallpeople as si; si.environment("structural", top_level=True)
w = (5.25 * kN / m)
L = 7.3 * m  # hc: -p
M = w * L**2 / 8  # hc: -f .2f
```

## Keep the unit setup out of the output

Set up the units in a cell you don't render, or end each setup line with `# hc: -i`:

```{hc-example}
import forallpeople as si               # hc: -i
si.environment("structural", top_level=True)  # hc: -i
L = (6 * si.m)
```

## Values with a tolerance, or their own LaTeX

*Asked in {issue}`340`.*

A value that is not a quantity but has its own `_repr_latex_`, such as a
[worstcase](https://github.com/amosborne/worstcase) parameter, is shown with that LaTeX
by the LaTeX and Markdown renderers. It is bracketed in a substitution when it has more
than one term:

```{literalinclude} ../_examples/tolerance.py
:language: python
```

```{hc-example}
:setup: from tolerance import Tolerance; x = Tolerance(1, 0.1)
y = x * 2
```

The format code does not apply to such a value: it is shown exactly as its
`_repr_latex_` writes it. The other renderers show its text (its `__format__`).

## Units in Excel

The [Excel renderer](../renderers/excel.md) turns pint and forallpeople quantities into
unit columns and SI-scaled formulas, so the workbook stays live.

**Next:** [Reports and documents](documents.md).
