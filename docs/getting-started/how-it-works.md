# How handcalcs reads your code

handcalcs renders *arithmetic calculations written in Python*. It is not a general
Python-to-math converter. This page explains what happens to your code and what each kind
of line turns into.

## What happens when you render

1. **Your code runs** as ordinary Python (in the notebook, or with `exec` for a
   script), producing a namespace of variable values.
2. **handcalcs parses the source**, statement by statement, into a tree of nodes.
   Each variable in the tree is paired with its value from the namespace.
3. **A renderer turns the tree into output**: the symbolic form uses the variable
   names, the numeric form uses their values.

```{important}
Values are looked up **after the code has run**. If a name is assigned twice, every line
shows its *final* value. Give each quantity its own name (see [Gotchas](gotchas.md)).
```

## Kinds of line

### Calculations

An assignment whose right-hand side uses variables, operators or function calls is a
**calculation**. It is shown as *target = symbolic = substituted = result*:

```{hc-example}
:renderer: plain_text
a = 2
b = 3
c = 2*a + b/3
```

When two steps would read the same (for example `q = b`), the duplicate is dropped.

### Parameters

An assignment of a plain number, a negative number or a collection of literals
(`[1, 2, 3]`) is a **parameter**. It is shown as *target = value*:

```{hc-example}
:renderer: plain_text
L = 6.0
loads = [1.2, 3.4, 5.6]
```

Several parameters on one line, separated by `;`, are laid out as a
[parameter grid](writing-calculations.md#parameter-grids).

### Skipping the substitution

Wrap the right-hand side in parentheses to show only *target = result*. This is useful
for intermediate values that are not the focus of the calculation:

```{hc-example}
:renderer: plain_text
a = 2
b = 3
d = (a**2 + b**2)
e = a**2 + b**2
```

### Expressions

A bare expression (no assignment) is shown like a calculation without a target: its
symbolic and substituted forms, then its result:

```{hc-example}
:renderer: plain_text
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
| `for` | A line describing the loop, followed by its body. The body shows the values from the **last** iteration. |

See [Writing calculations](writing-calculations.md#conditionals) for examples.

## What is not rendered

- Function and class definitions, `while` loops, `with` blocks and augmented
  assignments (`a += 1`) are not shown. Run them in a cell or script section that you
  don't render, then render the calculation that uses the result.
- `print(...)` calls are skipped, so a script can print progress without it showing up.
  A comment line above one is kept.
- Generator expressions (`sum(x**2 for x in xs)`) are not rendered. Use a list
  comprehension instead: `sum([x**2 for x in xs])`.

## Function names and symbols

Renderers translate names as they render them. In the plain-text, HTML, LaTeX and
Markdown renderers:

- Greek letter names (`alpha`, `beta`, `Gamma`, ...) become Greek letters; a lowercase
  name gives a lowercase letter, a capitalized name an uppercase letter.
- `_` starts a subscript: `I_y` becomes *I*<sub>y</sub>; each further `_` adds a subscript
  after a comma (`N_pl_Rd` → N<sub>pl,Rd</sub>). (The plain-text renderer keeps the
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
