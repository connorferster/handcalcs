# How handcalcs reads your code

handcalcs renders *arithmetic calculations written in Python*. It is not a general
Python-to-math converter. This page explains what happens to your code and what each kind
of line turns into.

## What happens when you render

1. **Your code runs** as ordinary Python (in the notebook, or with `exec` for a
   script). While it runs, handcalcs records the values of its variables just before
   and just after each statement.
2. **handcalcs parses the source**, statement by statement, into a tree of nodes.
   Each variable in the tree is paired with the value it had on that line: a
   calculation substitutes the values its operands had when it ran, and its result is
   the value it produced.
3. **A renderer turns the tree into output**: the symbolic form uses the variable
   names, the numeric form uses their values.

So a name can be reassigned: each line shows the value it had there, and an `if` shows
the branch that ran with the values its test was evaluated with:

```{hc-example}
:renderer: ascii
a = 2
b = a * 3
a = a + 8
if a > 5:
    a = 1
    c = b + a
```

## Kinds of line

### Calculations

An assignment whose right-hand side uses variables, operators or function calls is a
**calculation**. It is shown as *target = symbolic = substituted = result*:

```{hc-example}
:renderer: ascii
a = 2
b = 3
c = 2*a + b/3
```

When two steps would read the same (for example `q = b`), the duplicate is dropped.

### Parameters

An assignment of a plain number, a negative number or a collection of literals
(`[1, 2, 3]`) is a **parameter**. It is shown as *target = value*:

```{hc-example}
:renderer: ascii
L = 6.0
loads = [1.2, 3.4, 5.6]
```

Several parameters on one line, separated by `;`, are laid out as a
[parameter grid](writing-calculations.md#parameter-grids).

### Augmented assignment

`a += b` is shown as `a = a + b`, with the value `a` had before the line on the right
and its new value as the result. The same goes for `-=`, `*=`, `/=`, `//=`, `%=` and
`**=`:

```{hc-example}
:renderer: ascii
total = 1.5
extra = 0.25
total += 2 * extra
```

### Skipping the substitution

Wrap the right-hand side in parentheses to show only *target = result*. This is useful
for intermediate values that are not the focus of the calculation:

```{hc-example}
:renderer: ascii
a = 2
b = 3
d = (a**2 + b**2)
e = a**2 + b**2
```

### Expressions

A bare expression (no assignment) is shown like a calculation without a target: its
symbolic and substituted forms, then its result. A call to your own function is not
run again, so it has no result; see
[Show the result of an expression](../cookbook/showing-and-hiding.md#show-the-result-of-an-expression).

```{hc-example}
:renderer: ascii
a = 2
b = 3
a + b
```

### Conditional expressions

A conditional expression is shown with its keywords, and the substitution shows which
branch the values pick:

```{hc-example}
a = 2
b = 10 if a > 0 else -10
```

### Comments, headings and imports

| Source | Becomes |
|---|---|
| `## Title`, `### Subtitle`, ... | A heading. `##` is the top level; each extra `#` goes one level down. |
| `# Some text` on its own line | A paragraph of prose. Consecutive comment lines join into one paragraph. |
| `x = 1  # note` | The note, shown next to the line. |
| `# hc: ...` | A [comment command](comment-commands.md). It is not shown. |
| `import math` | The import, shown as code (renderer dependent). |

### Blocks

| Source | Becomes |
|---|---|
| `if` / `elif` / `else` | The condition that was true, symbolically and with values, followed by that branch's lines. Branches that did not run are not shown. |
| `for` | A line describing the loop, followed by its body. The body shows the values of the **last** pass through the loop. |
| `with` | Its body, as if it were not inside the `with`. The `with` line itself is not shown. |

See [Writing calculations](writing-calculations.md#conditionals) for examples.

## What is not rendered

- Function and class definitions, `while` loops and `try` blocks are not shown. Run
  them in a cell or script section that you don't render, then render the calculation
  that uses the result.
- `print(...)` calls are skipped, so a script can print progress without it showing up.
  A comment line above one is kept.

## Function names and symbols

Renderers translate names as they render them. In the ASCII, HTML, LaTeX and
Markdown renderers:

- Greek letter names (`alpha`, `beta`, `Gamma`, ...) become Greek letters; a lowercase
  name gives a lowercase letter, a capitalized name an uppercase letter.
- `_` starts a subscript: `I_y` becomes *I*<sub>y</sub>; each further `_` adds a subscript
  after a comma (`N_pl_Rd` → N<sub>pl,Rd</sub>). (The ASCII renderer keeps the
  underscore.) See [naming variables](writing-calculations.md#naming-variables) for Greek
  letters joined to other letters, accents and display symbols.
- `sqrt(...)` becomes a radical; `**` becomes a superscript; `/` becomes a fraction in
  LaTeX and Markdown.
- Other function calls are shown by name, with their arguments.

```{hc-example}
:setup: from math import sqrt, sin, radians
alpha = 30
L_span = 6.0
F_y = 350
d = L_span * sin(radians(alpha)) / sqrt(F_y)
```

Each renderer page lists its exact translations; [Customizing](../customizing/index.md)
shows how to add your own.

**Next:** [Writing calculations](writing-calculations.md).
