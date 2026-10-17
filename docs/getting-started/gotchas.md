# Gotchas

## Values are taken after the code runs

handcalcs runs your code first and then looks up each variable's value. If a name is
assigned more than once, every line shows the **final** value, so the substitution
can disagree with the formula:

```{hc-example}
:renderer: plain_text
a = 2
b = a * 3
a = 10
```

Use a new name for each quantity (`a_1`, `a_2`, or names that describe them).

## Jupyter cells can run out of order

In a notebook, `%%render` reads values from the notebook's namespace. If you run cells
out of order, or re-use a name in a later cell, a rendered cell can show values that
are beautifully formatted and **wrong**. Before you rely on a notebook, restart the
kernel and run all cells from the top.

## Not all Python is rendered

handcalcs renders arithmetic, function calls, comparisons, conditionals and loops. It
leaves out function and class definitions, `while` loops, `with` blocks and augmented
assignments, and does not support conditional expressions (`a if test else b`). See
[What is not rendered](how-it-works.md#what-is-not-rendered).

## Floor division and modulo

`//` and `%` are rendered (LaTeX shows `//` with floor brackets), but readers may not
recognise them in a hand calculation. Consider `floor(a / b)` for clarity.

## Responsibility for results

handcalcs is free, open-source software provided without warranty. If you use it for
work that may become a legal document, such as engineering design calculations, **you**
are responsible for checking that the results are what you expect. The point of showing
the substitution is to make that check easy.
