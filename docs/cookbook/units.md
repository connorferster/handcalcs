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

```python
%%render
L = 6 * m
w = 5 * kN / m
M = w * L**2 / 8
```

The result is `22.5 kN·m`.

## Calculate with pint

*Asked in {issue}`203` and {issue}`245`.*

Choose pint's short, pretty unit format when you create the registry:

```python
import pint
ureg = pint.UnitRegistry()
ureg.formatter.default_format = "~P"
```

```python
%%render
L = 6 * ureg.m
w = 5 * ureg.kN / ureg.m
M = w * L**2 / 8
```

Outside Jupyter, `HandCalcs(renderer)(source, globals())` renders the same code from a
script. See [Python: `HandCalcs`](../interfaces/object-oriented.md).

## Show a result in specific units

*Asked in {issue}`100` and {issue}`226`.*

Convert with the library's own method. A conversion can be chained onto a whole
expression:

```python
M = (w * L**2 / 8).to("kN*m")        # pint
M_kNm = M.to("kN*m")                 # or on a line of its own
```

To show only the converted value, hide the conversion step with `-p`:

```python
M_kNm = M.to("kN*m")  # hc: -p
```

## Set the precision of a quantity

`-f` applies to forallpeople quantities, which accept format codes:

```python
M = w * L**2 / 8  # hc: -f .1f
```

## Keep the unit setup out of the output

Set up the units in a cell you don't render (in Jupyter), or before the source string
you pass to `HandCalcs` (in a script). The rendered cell then starts with the
calculation itself.

## Units in Excel

The [Excel renderer](../renderers/excel.md) turns pint and forallpeople quantities into
unit columns and SI-scaled formulas, so the workbook stays live.

**Next:** [Reports and documents](documents.md).
