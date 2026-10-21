# Gotchas

## Objects changed in place

Each line shows the values its variables had when that line ran, even if a name is
assigned again later. Values are not copied, though: an object that is changed in place
afterwards (`xs.append(4)`, `arr[0] = 5` on a numpy array) shows its final contents on
every line. Make a new object instead (`xs = xs + [4]`), or give each quantity its own
name.

## Jupyter cells can run out of order

In a notebook, `%%render` reads values from the notebook's namespace. If you run cells
out of order, or re-use a name in a later cell, a rendered cell can show values that
are beautifully formatted and **wrong**. Before you rely on a notebook, restart the
kernel and run all cells from the top.

## Not all Python is rendered

handcalcs renders arithmetic, function calls, comparisons, conditional expressions,
conditionals and loops. It leaves out function and class definitions, `while` loops,
`with` blocks, augmented assignments and `print()` calls. See
[What is not rendered](how-it-works.md#what-is-not-rendered).

## Floor division and modulo

`//` and `%` are rendered (LaTeX shows `//` with floor brackets), but readers may not
recognise them in a hand calculation. Consider `floor(a / b)` for clarity.

## Responsibility for results

handcalcs is free, open-source software provided without warranty. If you use it for
work that may become a legal document, such as engineering design calculations, **you**
are responsible for checking that the results are what you expect. The point of showing
the substitution is to make that check easy.
