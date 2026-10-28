# Showing and hiding steps

Recipes for choosing what appears: which steps of a calculation, which lines, and how
long equations are broken. The commands are all listed in
[Comment commands](../getting-started/comment-commands.md).

## Show only the result of a line

*Asked in {issue}`183`.*

`-p` shows *target = result* and skips the formula and the substitution. It suits values
whose formula adds nothing, like a section property taken from a table or a unit
conversion:

```{hc-example}
b = 300                    # mm
h = 600                    # mm
A = b * h                  # hc: -p
I_x = b * h**3 / 12
```

## Show only formulas, or only results, for a whole section

*Asked in {issue}`89` and {issue}`183`.*

The `mode` field picks the steps. `"ass sym"` shows formulas, as in a design guide:

```{hc-example}
w = 5
L = 6
# hc: mode = "ass sym"
M = w * L**2 / 8
V = w * L / 2
```

`"ass res"` shows results, as in a summary table:

```{hc-example}
w = 5
L = 6
# hc: mode = "ass res"
M = w * L**2 / 8
V = w * L / 2
```

Switch back with `# hc: mode = "full"`. For every calculation in a session:
`handcalcs.set_option("mode", "ass res")`.

## Hide a line

*Asked in {issue}`106` and {issue}`226`.*

`-i` at the end of a line runs it but leaves it out of the output:

```{hc-example}
L_mm = 6000
L = L_mm / 1000            # hc: -i
w = 5
M = w * L**2 / 8
```

On its own line, `# hc: -i` hides every line after it (headings, comments and blocks
too), and `# hc: -s` shows them again:

```{hc-example}
# hc: -i
a_raw = [3.1, 2.9, 3.0]
a = sum(a_raw) / len(a_raw)
# hc: -s
b = 2 * a
```

`-s` at the end of a line shows that one line of a hidden section.

An `if` or `for` block is shown or hidden whole, by the setting where it starts.

## Show or hide a section on a condition

*Asked in {issue}`343`.*

End `-i` or `-s` with a Python expression to decide from the calculation's values.
`# hc: -s M_f > 0` shows what follows when `M_f > 0` and hides it otherwise, so a load
case without moment skips its flexure check:

```{hc-example}
w = 0
L = 6
M_f = w * L**2 / 8
# hc: -s M_f > 0
## Flexure
Z_req = M_f / 350
# hc: -s
R = w * L / 2
```

`# hc: -i A_s < A_req` is the opposite: it hides when the expression is true. The
expression uses the values at the comment, from the lines above it. At the end of a
line, it uses the values after that line ran:

```{hc-example}
a = 2
b = a - 2                  # hc: -i b == 0
c = a + 1                  # hc: -i c == 0
```

The expression is the rest of the comment, so other flags go before it:
`# hc: -f .2f -s M_f > 0`.

## Show only what you mark

*Asked in {issue}`343`.*

To start from nothing and show only chosen lines, begin with `# hc: -i` and mark what
to show with `-s`:

```{hc-example}
# hc: -i
b = 300
h = 600
A = b * h
I_x = b * h**3 / 12        # hc: -s
```

To do this for every calculation, without the first line, turn on the
`hidden_by_default` [option](../getting-started/configuration.md):
`handcalcs.set_option("hidden_by_default", True)`. For one decorated function, pass it
in the render context: `@handcalc(render_context={"hidden_by_default": True})`.

## Hide import lines

Imports are shown as a line of code. To leave one out, end it with `# hc: -i`:

```{hc-example}
from math import sqrt  # hc: -i
a = 3
b = 4
c = sqrt(a**2 + b**2)
```

To never show imports, register a handler on your renderer that renders nothing for
`import` nodes:

```{literalinclude} ../_examples/hide_imports.py
:language: python
```

```{hc-example}
:renderer-file: _examples/hide_imports.py
:renderer-class: make_renderer
from math import sqrt
a = 3
b = 4
c = sqrt(a**2 + b**2)
```

## Lay out inputs in a grid

A row of short parameter assignments takes up a lot of vertical space. Separate them with
`;` to put them on one row:

```{hc-example}
b = 300; h = 600; c = 40
```

or put `# hc: -g` above a group of assignments to lay them out in a grid, `-c N`
columns wide, with their comments:

```{hc-example}
# hc: -g -c 2
f_c = 30     # Concrete strength, MPa
f_y = 400    # Rebar yield, MPa
b = 300      # Width, mm
d = 540      # Effective depth, mm
```

## Break a long equation over several lines

*Asked in {issue}`199`, {issue}`181`, {issue}`149` and {issue}`259`.*

`-m` puts each step (formula, substitution, result) on its own line:

```{hc-example}
:setup: from math import pi, sqrt
E = 200000; I_y = 160e6; G = 77e3; J = 133e3; C_w = 200e9; L = 6000
M_u = pi / L * sqrt(E * I_y * G * J + (pi * E / L)**2 * I_y * C_w)  # hc: -m
```

A formula that is still too wide can be broken where you break it in the source. A
line continuation, either `\` or an open bracket, starts a new row in the output:

```{hc-example}
a = 2; b = 3; c = 4
y = (a + b)**2 \
    + 3 * a * c \
    - b / c
```

There is no automatic wrapping: you decide where a long formula breaks.

## Render one line in a notebook

*Asked in {issue}`179`.*

In Jupyter, `%render` (one `%`) runs and renders a single line, so a cell of ordinary
code can show just the equation that matters:

```python
b = 300
h = 600
%render I_x = b * h**3 / 12
```

See [`%render`](../interfaces/jupyter.md#render-one-line).

## Show the result of an expression

*Asked in {issue}`54`.*

A line that is only an expression (no `=`) is shown with its result, like a calculator:

```{hc-example}
x = 3
2 * x + 1
x**2 > 5
```

handcalcs evaluates such a line again to find its result, but only when that is safe:
arithmetic, built-ins, and `math` and numpy functions. A call to your own function is
never run twice, so it is shown without a result (`f(a) = f(2)`). To show its result,
assign it: `y = f(a)`.

## Add space between parts

`# hc: -b` on its own line adds vertical space, to separate groups of results:

```{hc-example}
a = 2
b = 3
# hc: -b
c = a * b
```

**Next:** [Checks and decisions](checks.md).
