# Units

handcalcs renders whatever values your code produces, so quantities from a units library
work like numbers: the substituted step and the result show the value with its unit.
[forallpeople](https://github.com/connorferster/forallpeople) (designed alongside
handcalcs) and [pint](https://pint.readthedocs.io/) are both used this way.

## forallpeople

Load an environment with `top_level=True` so the unit names (`m`, `kN`, ...) are
available directly:

```python
import forallpeople as si
si.environment("structural", top_level=True)
```

Then, in a separate rendered cell:

```python
%%render
L = 6 * m
w = 5 * kN / m
M = w * L**2 / 8
```

The result is shown as `22.5 kN·m`. forallpeople quantities accept format codes, so
[`# hc: -f`](formatting-numbers.md) works on them.

## pint

```python
import pint
ureg = pint.UnitRegistry()
ureg.formatter.default_format = "~P"   # short, pretty unit symbols
```

```python
%%render
L = 6 * ureg.m
w = 5 * ureg.kN / ureg.m
M = w * L**2 / 8
```

## Tips

- **Set up the units in a cell you don't render**, or hide the setup lines with
  `# hc: -i` at the end of each line. The setup code is not part of the calculation.
- Unit-aware values are formatted by the units library. Whether the format code
  applies depends on the library's `__format__` support.
- The [Excel renderer](../renderers/excel.md) converts pint and forallpeople
  quantities into unit columns and SI-scaled formulas.

```{admonition} Known limitations in 2.0
:class: caution
- With forallpeople, a bare unit in a formula (the `m` in `6 * m`) shows an empty
  substituted value (`6 * m = 6 *  = 6 m`). The result is correct.
- Calling a method on a parenthesized expression, such as `(w * L**2 / 8).to("kN*m")`,
  is not parsed. Assign the expression first, then convert it on the next line.
```

**Next:** [Gotchas](gotchas.md).
