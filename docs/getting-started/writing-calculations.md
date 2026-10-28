# Writing calculations

A handcalcs calculation is ordinary Python plus comments. This page covers the pieces you
use to turn a block of code into a readable calculation. The examples use the Markdown
renderer (the Jupyter default); every built-in renderer supports the same features.

## Headings and prose

A comment starting with `##` is a heading. `##` is the top level, `###` the next, and so
on. Other comment lines are prose; consecutive comment lines join into one paragraph.

```{hc-example}
## Beam design
### Loads
# The beam carries a uniformly distributed load from the floor above.
# Self-weight is included in w.
w = 12.5  # kN/m
```

## Naming variables

A variable's name is typeset as a math symbol, so name variables the way you'd write them
on paper:

| You write | Shown as | Rule |
|---|---|---|
| `I_y` | *I*<sub>y</sub> | `_` starts a subscript |
| `N_pl_Rd` | N<sub>pl,Rd</sub> | each further `_` adds a subscript, separated by a comma |
| `sigma_max`, `Gamma` | σ<sub>max</sub>, Γ | a Greek letter's name becomes the letter (`lamb` or `lambda_` for λ) |
| `ΔH`, `σ_R` | ΔH, σ<sub>R</sub> | Unicode Greek letters work too |
| `DeltaH`, `gammaM0`, `alpha2` | ΔH, γM0, α2 | a Greek name followed by an uppercase letter or a digit |
| `x_hat`, `x_bar`, `V_dot`, `x_ddot` | x̂, x̄, V̇, ẍ | accents over the part before them |
| `x̄`, `ŷ_2`, `σ̂` | x̄, ŷ<sub>2</sub>, σ̂ | Unicode letters with a combining accent (hat, bar, dot, double dot) |
| `f_prime_c`, `M_star` | f′<sub>c</sub>, M<sup>*</sup> | a prime, a superscript `*` |
| `Annual__Rate` | Annual Rate | `__` is a space |
| `a___b` | a_b | `___` is a literal underscore |

A lowercase continuation never splits off a Greek letter: `metal`, `beta` and `Pin` stay
as they are. A subscript of more than one letter is set upright.

```{hc-example}
N_pl_Rd = 1250  # kN
gammaM0 = 1.0
DeltaT = 35  # K
f_prime_c = 30  # MPa
```

### Nested subscripts

handcalcs v1 nested each further subscript (`x_a_b` → x<sub>a<sub>b</sub></sub>). To get
that back, set the `subscripts` option to `"nested"`, either for the rest of the calculation
with a comment command or for the session with `set_option`:

```{hc-example}
# hc: subscripts = "nested"
x_a_b = 2
```

```python
import handcalcs
handcalcs.set_option("subscripts", "nested")
```

### Display symbols

When a name can't express the symbol you want, map the variable to a display spec with
the `symbols` option. The spec uses a small TeX-like syntax that every renderer
understands:

```{hc-example}
# hc: symbols = {"N_plRd": "N_{pl,Rd}", "V_flow": "dot(V)", "dH": "ΔH^{*}"}
N_plRd = 1250  # kN
V_flow = 2.5  # m³/s
dH = 4.2  # kJ
```

| Spec | Meaning |
|---|---|
| `N_{pl,Rd}` | subscripts in braces, separated by commas; `N_Rd` takes the run after `_` |
| `M^{*}`, `x^2` | superscripts, the same way |
| `x_{a_{b}}` | a subscript with its own subscript |
| `Delta H`, `ΔH`, `sigma_{c}` | spaces separate words; Greek names or Unicode letters |
| `hat(x)`, `bar(x)_{m}`, `dot(V)`, `ddot(x)` | an accent over the base |
| `f'_c` | a prime |

Set `symbols` for the whole session with `handcalcs.set_option("symbols", {...})`. A spec
that can't be parsed raises an error that says where.

## Indexing

An index or key lookup shows the element it looks up in the substitution. A name indexed
by integers, short strings or other names is set with the index as a subscript, the way a
hand calculation numbers its values:

```{hc-example}
M_Ed = [90, 120, 140]  # kNm, load cases
loads = {"dead": 5.0, "live": 3.0}  # kN/m
i = 2
eta = M_Ed[i] / 150
w = 1.25 * loads["dead"] + 1.5 * loads["live"]
```

Each index follows the name's own subscripts (`M_Ed[i]` → M<sub>Ed,i</sub>), and
`A[i, j]` gives A<sub>i,j</sub>. Other lookups, such as slices (`xs[1:3]`) and indexes
that are expressions (`xs[i + 1]`), are shown in brackets. The ASCII renderer always uses
brackets.

handcalcs finds the element without running any code again: the index must be a literal,
a name or an attribute (or a slice or tuple of those), and the container a list, tuple,
string, dict, numpy array, pandas object or units-library quantity. Otherwise the
substitution shows the lookup with its index substituted (`xs[2 + 1]`), followed by the
result. To show every lookup in brackets, see [the recipe](../customizing/symbols-and-functions.md#indexes-in-brackets).

## Several targets

Tuple unpacking and chained assignment are shown as written, with their values:

```{hc-example}
:renderer: ascii
x = [3.0, 4.0]
a, b = x
c = d = a * b
```

## Inline comments

A comment at the end of a line is shown next to that line. Use it for units, sources or
short notes:

```{hc-example}
L = 6000  # Span, in mm (drawing S-201)
E = 200000  # MPa
```

## Values inside comments

Comments (headings, prose and inline comments) are [Jinja](https://jinja.palletsprojects.com/)
templates. Put a variable name in `{{ }}` to insert its value, and use Jinja filters to
format it:

```{hc-example}
:renderer: ascii
F = 12.3456
# The applied force is {{ F|round(1) }} kN.
check = F < 15  # F = {{ "%.2f"|format(F) }} kN, below the 15 kN limit
```

```{note}
Values in `{{ }}` are inserted as they are, without the
[number format](formatting-numbers.md). Use a Jinja filter such as `round` or `format`
to control them.
```

## Parameter grids

Long lists of inputs take up a lot of vertical space. Put several assignments on one line,
separated by `;`, and they are laid out as a grid, three per row:

```{hc-example}
b = 200; d = 450; c_c = 40; f_c = 30; f_y = 400
```

To keep inline comments, use a `# hc: -g` command instead. The assignments that follow
go into the grid, each with its comment, until a blank line, a comment line or a
statement that is not an assignment. Each cell shows only *target = result*:

```{hc-example}
# hc: -g
b = 200  # mm
d = 450  # mm
f_c = 30  # MPa
f_y = 400  # MPa
```

Change the number of columns with `# hc: -c N`:

```{hc-example}
# hc: -c 2
b = 200; d = 450; f_c = 30; f_y = 400
```

```{note}
A standalone command such as `# hc: -c 2` stays in effect for the rest of the
calculation. See [scope](comment-commands.md#scope).
```

## Long equations

A long expression is broken at the same places as your source code. Continue the line
with a `\`, before or after an operator, and each continued piece starts a new row,
indented under the expression above, in both the symbolic and the substituted step:

```{hc-example}
:renderer: ascii
a = 1.5
b = 2.25
c = 3.125
total = a * b \
    + b * c \
    + a * c
```

Only breaks between the terms of the expression itself are kept. A break inside brackets
or a fraction can't be, so that calculation is shown on one line. Brackets around the
*whole* expression show only the result, as for any [bracketed expression](how-it-works.md#skipping-the-substitution).

Code formatters such as black and ruff wrap a long right-hand side in brackets on their
own, so after formatting the line shows only its result. To keep the steps, shorten the
line, break it with `\` as above, or leave the calculation out of formatting
(`# fmt: off` / `# fmt: on` around it).

To break between the steps of a calculation (symbolic, substituted, result) instead, use
[`# hc: -m`](comment-commands.md).

## Expressions

A line that is only an expression, such as `2 * a`, shows its result:

```{hc-example}
:renderer: ascii
a = 3
2 * a + 1
```

An expression that calls a function or has a side effect isn't evaluated again, so it is
shown without a result.

## Conditionals

`if` / `elif` / `else` blocks show the condition that was true, first symbolically and
then with values, followed by the lines in that branch. Branches that did not run are not
shown, so the output reads as the reasoning that applies to *these* inputs:

```{hc-example}
:setup: from math import sqrt
b_t = 8.5
F_y = 350
if b_t <= 145 / sqrt(F_y):
    section_class = 1
elif b_t <= 170 / sqrt(F_y):
    section_class = 2
else:
    section_class = 3
```

Blocks can be nested; each level is indented.

## Loops

A `for` loop is shown as a line describing the iteration, followed by its body. The body
is shown once, with the values of the **last** pass through the loop:

```{hc-example}
:renderer: ascii
total = 0
for load in (1.2, 3.4, 5.6):
    factored = 1.25 * load
```

To show a calculation for every case in a table of inputs, render one representative
case, or call a renderer once per case from a script (see
[the object-oriented interface](../interfaces/object-oriented.md)).

## Spacing

`# hc: -b` inserts a blank line (vertical space) at that point:

```{hc-example}
:renderer: ascii
a = 2
# hc: -b
b = a * 3
```

## Hiding a line

Some lines are needed for the calculation but are not interesting to the reader, such as
setting up a unit system. Add `# hc: -i` to run the line but leave it out of the output:

```{hc-example}
:renderer: ascii
a = 2
scale = 1000  # hc: -i
b = a * scale
```

**Next:** [Comment commands](comment-commands.md) lists every command.
