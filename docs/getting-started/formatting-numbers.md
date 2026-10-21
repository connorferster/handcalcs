# Formatting numbers

Every number handcalcs shows goes through a Python
[format code](https://docs.python.org/3/library/string.html#format-specification-mini-language),
the part after the colon in `f"{value:.2f}"`. The default is `.5g`: up to five
significant figures, switching to scientific notation for very large or small values.
An integer keeps all its digits under a `g` format code (`E = 200000`, not `2e+05`);
a code such as `.2f` or `.3e` applies to integers too.

```{hc-example}
:renderer: ascii
a = 1234.56789
b = 0.000012345
c = a * b
```

## Common format codes

| Code | Meaning | `1234.56789` becomes |
|---|---|---|
| `.5g` | 5 significant figures (default) | `1234.6` |
| `.3g` | 3 significant figures | `1.23e+03` |
| `.2f` | 2 decimal places | `1234.57` |
| `.0f` | no decimals | `1235` |
| `.3e` | scientific, 3 decimals | `1.235e+03` |
| `,.1f` | thousands separator, 1 decimal | `1,234.6` |

The LaTeX and Markdown renderers typeset scientific notation as
1.235 × 10<sup>3</sup> rather than `1.235e+03`. The same value with four codes:

```{hc-example}
x = 1234.56789 * 1         # hc: -f .5g
x_3g = 1234.56789 * 1      # hc: -f .3g
x_2f = 1234.56789 * 1      # hc: -f .2f
x_3e = 1234.56789 * 1      # hc: -f .3e
```

Numbers you type inside a formula keep their digits as written (`1234.56789` above);
the format code applies to calculated values and to the values of parameters.

## Where to set it

From the narrowest scope to the widest:

**One line**: a command at the end of the line.

```{hc-example}
a = 2.0
b = 1 / 3
c = a * b  # hc: -f .2f
d = a * b
```

**The rest of the calculation**: a command on its own line.

```{hc-example}
a = 2.0
b = 1 / 3
# hc: -f .3e
c = a * b
d = c / 7
```

**Every calculation in the session**: the `format_code` option.

```python
import handcalcs
handcalcs.set_option("format_code", ".3g")
```

**Every session, permanently**: set the option, then save it.

```python
handcalcs.set_option("format_code", ".3g")
handcalcs.save_config()
```

In Jupyter there is also a line magic for the session setting:

```python
%hc_format_code .3g
```

See [Configuration](configuration.md) for how saved options are stored and reset.

## Values that are not plain numbers

- `True` and `False` are shown as words, not as `1` and `0`.
- Dates and times are shown in their usual `str()` form.
- Collections (`list`, `tuple`, `set`, `dict`) format each element; long ones are
  shortened with an ellipsis.

```{hc-example}
:setup: import datetime
ok = 3 > 2
today = datetime.date(2026, 10, 20)
xs = [1 / 3, 2 / 3, 1.0]           # hc: -f .2f
long_list = list(range(20))
```

- Any other object is formatted with the format code if it supports one (as
  [forallpeople](units.md) quantities do); otherwise its `str()` is shown. An object
  whose `str()` looks like `<MyObject at 0x...>` will be shown that way, so give your
  own classes a readable `__str__` or `__format__`.

**Next:** [Configuration](configuration.md).
