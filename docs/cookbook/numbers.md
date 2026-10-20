# Numbers

Recipes for how values are shown: precision, scientific and engineering notation, and
floating-point noise. The guide behind them is
[Formatting numbers](../getting-started/formatting-numbers.md).

## Set the precision of one variable

*Asked in {issue}`182` and {issue}`164`.*

Put a format command at the end of the line. It applies to that line only:

```{hc-example}
A = 1 / 3              # hc: -f .2f
B = 2 / 3              # hc: -f .4f
C = A + B              # hc: -f .1f
```

## Set the precision for part of a calculation

A command on its own line applies to every line after it, until another command
changes it:

```{hc-example}
a = 10 / 3
# hc: -f .2f
b = a * 2
c = b / 7
# hc: -f .5g
d = c * 1000
```

To change the default for a whole session, use `handcalcs.set_option("format_code",
".3g")` or, in Jupyter, `%hc_format_code .3g`.

## Show large and small numbers in scientific notation

*Asked in {issue}`171` and {issue}`121`.*

The default format, `.5g`, already switches to scientific notation for very large or
small values. To always use it, choose an `e` format:

```{hc-example}
E = 200000.0           # hc: -f .2e
I = 8.3e7 / 1e12       # hc: -f .3e
EI = E * I             # hc: -f .3e
```

To keep plain decimals instead, use an `f` format such as `# hc: -f .4f`.

## Show small values instead of zero

*Asked in {issue}`230`.*

Fixed-point formats round small values away (`0.0001` with `.2f` is `0.00`). The
default `.5g` keeps five significant figures whatever the magnitude:

```{hc-example}
k = 0.00012345
k2 = k * 3
```

## Drop trailing zeros

*Asked in {issue}`221`.*

The `g` formats drop trailing zeros; the `f` formats keep them:

```{hc-example}
a = 2.5                # hc: -f .3g
b = a * 2              # hc: -f .3g
c = a * 2              # hc: -f .3f
```

## Thousands separators

```{hc-example}
P = 1234567.891        # hc: -f ,.1f
Q = P * 2              # hc: -f ,.0f
```

## Engineering notation (exponents in multiples of three)

*Asked in {issue}`202` and {issue}`121`.*

Python's format codes can't fix the exponent to a multiple of three, but a renderer can.
This subclass replaces the `constant` handler, which formats every calculated value,
and reads two new [context fields](../customizing/render-context.md) that you set with
comment commands:

- `format_code = "eng4"`: engineering notation with four significant figures;
- `zero_tol = 1e-9`: show anything smaller than the tolerance as `0` (see the next recipe).

```{literalinclude} ../_examples/engineering_notation.py
:language: python
```

```{hc-example}
:renderer-file: _examples/engineering_notation.py
:renderer-class: EngMarkdownRenderer
# hc: format_code = "eng4"
P = 1826000.0 * 100
E = 200000.0 / 3
f = 0.000123 * 4
```

Use `EngLatexRenderer` for LaTeX output. In Jupyter, both are available by name once
the module is imported: `%hc_default_renderer eng_markdown`.

## Snap floating-point noise to zero

*Asked in {issue}`109`.*

`0.1 + 0.2 - 0.3` is `5.55e-17` in floating point. The renderer above also reads a
`zero_tol` field:

```{hc-example}
:renderer-file: _examples/engineering_notation.py
:renderer-class: EngMarkdownRenderer
# hc: zero_tol = 1e-9
x = 0.1 + 0.2 - 0.3
y = 0.1 + 0.2
```

Only the display changes: `x` is still `5.55e-17` in Python.

## Show text values

*Asked in {issue}`157`.*

Strings are shown in quotes, so a calculation can carry a material grade or a
decision:

```{hc-example}
grade = "S355"
f_y = 355  # MPa
```

**Next:** [Showing and hiding steps](showing-and-hiding.md).
