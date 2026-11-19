# SymPy

Recipes for calculations that start as algebra in [SymPy](https://www.sympy.org).
SymPy shows its own expressions as maths; handcalcs takes over when the algebra is done
and the numbers go in.

## Calculate with an expression from SymPy

Work out the expression symbolically, in a cell you don't render or at the top of the
script:

```python
import sympy as sp
from math import sqrt

w, L, x = sp.symbols("w L x")
M_x = sp.integrate(sp.integrate(-w, x) + w * L / 2, x)   # bending moment along a beam
M_mid = M_x.subs(x, L / 2)                               # w*L**2/8
```

Then give the symbols values and mark the line that uses the expression with
`# hc: -y`:

```{hc-example}
:setup: import sympy as sp; w, L, x = sp.symbols("w L x"); M_mid = sp.integrate(sp.integrate(-w, x) + w * L / 2, x).subs(x, L / 2)
w = 5
L = 6
M = M_mid  # hc: -y
M_f = 1.5 * M
```

The line runs as `M = w*L**2/8`: the expression `M_mid` holds is written into the line
just before it runs, with the values `w` and `L` have at that moment. So `M` holds a
number, and every later line calculates with it. `M_mid` itself is left unchanged.

The line must be *name = name*, where the right-hand name holds a SymPy expression, an
equation (`sp.Eq(R, w * L / 2)`, whose right-hand side is used) or a one-item list of
solutions (`sp.solve(...)`).

On its own line, `# hc: -y` applies to every following *name = name* line whose
right-hand name holds a SymPy expression, until `# hc: sympy = False`:

```python
# hc: -y
M = M_mid
V = V_end
# hc: sympy = False
```

```{note}
Giving a symbol a number replaces the SymPy symbol of that name. Finish the symbolic
work, with every `integrate`, `solve` and `subs`, before the line that gives it a
value; a SymPy step after it calculates with the number instead.
```

## Functions and constants

The expression is written with the names of the functions it uses (`sqrt`, `sin`,
`exp`, `log`, `atan2`, ...) and of `pi`, `e` and `inf`. Import them from `math`
(`from math import sqrt, pi`) to show them as `√` and `π`, or `import math` to use
them as `math.sqrt` and `math.pi`. SymPy's `Abs`, `Max` and `Min` become Python's
`abs`, `max` and `min`.

An expression that still holds something unevaluated, like an `Integral` or a
`Piecewise`, is an error: evaluate it with SymPy first (`.doit()`), or split it into
lines.

## In a function

`@handcalc` substitutes too. The expression is looked up when the function is called,
in its arguments and then the module's variables, so it can also be passed in:

```python
@handcalc()
def midspan_moment(w, L):
    M = M_mid  # hc: -y
    return M

@handcalc()
def moment(expr, w, L):
    M = expr  # hc: -y
    return M

moment(M_mid, w=5, L=6)
```

The symbols are the function's parameters (or variables assigned before the line).
A function defined inside another function, using its variables, can't be rewritten.

## In a notebook

In a `%%render` cell the expression comes from an earlier cell or from the same one.
The cell runs a statement at a time so that each `# hc: -y` line is rewritten just
before it runs. `-y` can't be combined with `%%render inputs=...` (or
`HandCalcs(..., inputs=...)`), and needs handcalcs to run the code, so not with
`supplied_globals`.
