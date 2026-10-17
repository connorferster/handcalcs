# Comment commands

A comment that starts with `hc:` is a **command**: it changes how lines are rendered and
is not shown itself. Commands work in every interface and every built-in renderer.

```python
x = a / b  # hc: -f .2f        <- applies to this line only
# hc: -f .3g                   <- applies to every following line
```

## The commands

| Command | Long form | Effect |
|---|---|---|
| `-f CODE` | `--format-code CODE` | Number format code, e.g. `.2f`, `.3e`, `.4g`. See [Formatting numbers](formatting-numbers.md). |
| `-m` | `--multiline` | Break a calculation over several lines, aligned on `=`, for long equations. |
| `-p` | `--param-line` | Show only *target = result*, hiding the symbolic and substituted steps. |
| `-h` | `--params` | Start a [parameter grid](writing-calculations.md#parameter-grids) of the following assignments, keeping their comments. |
| `-c N` | `--param-cols N` | Number of columns in parameter grids (default 3). |
| `-b` | `--line-break` | Insert vertical space here. |
| `-i` | `--ignore` | Run the line but leave it out of the output. |

Flags can be combined: `# hc: -m -f .2f`.

`-w` (`--if-winner-only`) is accepted but has no effect yet.

## Scope

Where you put a command decides how long it lasts:

- **At the end of a line** (`x = a / b  # hc: -f .2f`), it applies to that line only.
  A line can carry a command *or* a normal comment, not both.
- **On its own line** (`# hc: -f .2f`), it applies to **every following line** until
  another command changes it. The exceptions are `-b`, which inserts space once, and
  `-h`, which applies to the grid directly below it.

```{hc-example}
a = 2
b = 3
x = a / b  # hc: -f .2f
y = a / b
# hc: -f .1f
z = a / b
w = b / a
```

```{warning}
A standalone `# hc: -i` hides **everything after it**. To hide a single line, put
`# hc: -i` at the end of that line.
```

### Turning a setting off again

The flags can only switch a setting *on*. To switch one back off, or to set a value, use
the assignment form described next: `# hc: multiline = False`, `# hc: param_line = False`,
`# hc: format_code = ".5g"`.

## The assignment form

Instead of flags, a command can be one or more Python assignments:

```python
# hc: format_code = ".2f"
# hc: param_cols = 2
x = a / b  # hc: multiline = True
```

Each assignment sets a field on the **render context**, the settings object the
renderer reads. The flags are shorthands for these fields:

| Flag | Context field |
|---|---|
| `-f` | `format_code` |
| `-m` | `multiline` |
| `-p` | `param_line` |
| `-c` | `param_cols` |
| `-i` | `ignore` |

Any other name is allowed too, and is passed to the renderer. A
[customized](../customizing/render-context.md) or [custom](../building-renderers/render-context.md)
renderer can read its own fields this way, for example `# hc: highlight = True`.

```{note}
The assignment form is executed as Python, so only use it in code you trust (which is
already true of any code you render, because handcalcs runs it).
```

## Choosing which steps appear: `mode`

The `mode` field picks the steps of a calculation that are shown. The default, `"full"`,
shows them all. Otherwise give a string containing any of:

| Word | Step |
|---|---|
| `ass` | the assignment target (`c`) |
| `sym` | the symbolic formula (`2 a + b/3`) |
| `num` | the formula with values substituted |
| `res` | the result |

For example, to show formulas only (symbolically, as v1's `symbolic` override did):

```{hc-example}
a = 2
b = 3
# hc: mode = "ass sym"
c = 2*a + b/3
d = a**2 + b**2
```

## Examples

### A long equation

```{hc-example}
:setup: from math import pi, sqrt
omega_2 = 1.0; L = 6000; E = 200000; I_y = 160e6; G = 77e3; J = 133e3; C_w = 200e9
M_u = omega_2 * pi / L * sqrt(E * I_y * G * J + (pi * E / L)**2 * I_y * C_w)  # hc: -m
```

### Results only

```{hc-example}
a = 2
b = 3
c = a**2 + b**2  # hc: -p
```

See the [comment command reference](../reference/comment-commands.md) for a compact table.
