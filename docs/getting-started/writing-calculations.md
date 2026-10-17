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
:renderer: plain_text
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

To keep inline comments, use a `# hc: -h` command instead. The assignments that follow
go into the grid, each with its comment, until a blank line, a comment line or a
statement that is not an assignment. Each cell shows only *target = result*:

```{hc-example}
# hc: -h
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

A `for` loop is shown as a line describing the iteration, followed by its body. Because
values are captured after the code runs, the body shows the values from the **last**
iteration:

```{hc-example}
:renderer: plain_text
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
:renderer: plain_text
a = 2
# hc: -b
b = a * 3
```

## Hiding a line

Some lines are needed for the calculation but are not interesting to the reader, such as
setting up a unit system. Add `# hc: -i` to run the line but leave it out of the output:

```{hc-example}
:renderer: plain_text
a = 2
scale = 1000  # hc: -i
b = a * scale
```

**Next:** [Comment commands](comment-commands.md) lists every command.
