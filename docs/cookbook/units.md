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
L = 6 * m
w = 5 * kN / m
M = w * L**2 / 8
```

Units are set upright, and a substituted quantity raised to a power is bracketed. A bare
unit in a formula (the `m` in `6 * m`) shows an empty substituted value in 2.0; the
result is correct.

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
w = 5 * ureg.kN / ureg.m
L = 6000 * ureg.mm
M = (w * L**2 / 8).to("kN*m")
M_Nmm = M.to("N*mm")  # hc: -p
```

## Set the precision of a quantity

`-f` applies to quantities from both libraries:

```{hc-example}
:setup: import forallpeople as si; si.environment("structural", top_level=True)
w = 5.25 * kN / m
L = 7.3 * m
M = w * L**2 / 8  # hc: -f .2f
```

## Keep the unit setup out of the output

Set up the units in a cell you don't render, or end each setup line with `# hc: -i`:

```{hc-example}
import forallpeople as si               # hc: -i
si.environment("structural", top_level=True)  # hc: -i
L = 6 * si.m
```

## Units in Excel

The [Excel renderer](../renderers/excel.md) turns pint and forallpeople quantities into
unit columns and SI-scaled formulas, so the workbook stays live.

**Next:** [Reports and documents](documents.md).
