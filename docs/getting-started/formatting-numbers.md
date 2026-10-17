# Formatting numbers

Every number handcalcs shows goes through a Python
[format code](https://docs.python.org/3/library/string.html#format-specification-mini-language),
the part after the colon in `f"{value:.2f}"`. The default is `.5g`: up to five
significant figures, switching to scientific notation for very large or small values.

```{hc-example}
:renderer: plain_text
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
1.235 × 10<sup>3</sup> rather than `1.235e+03`.

## Where to set it

From the narrowest scope to the widest:

**One line**: a command at the end of the line.

```python
c = a * b  # hc: -f .2f
```

**The rest of the calculation**: a command on its own line.

```python
# hc: -f .3e
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
- Collections (`list`, `tuple`, `set`, `dict`) format each element.
- Any other object is formatted with the format code if it supports one (as
  [forallpeople](units.md) quantities do); otherwise its `str()` is shown. An object
  whose `str()` looks like `<MyObject at 0x...>` will be shown that way, so give your
  own classes a readable `__str__` or `__format__`.

**Next:** [Configuration](configuration.md).
