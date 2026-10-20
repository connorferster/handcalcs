# Symbols and notation

Recipes for making variable names, functions and operators look the way they do in your
code of practice or textbook. The background is in
[Naming variables](../getting-started/writing-calculations.md#naming-variables) and
[Symbols and functions](../customizing/symbols-and-functions.md).

## Eurocode-style subscripts

*Asked in {issue}`101`.*

Each further underscore adds a comma-separated subscript, and a subscript of more than
one letter is set upright:

```{hc-example}
N_pl_Rd = 1250   # kN
M_c_Rd = 410     # kN m
sigma_x_Ed = 185 # MPa
```

For v1-style nested subscripts (x<sub>a<sub>b</sub></sub>), use `# hc: subscripts = "nested"`.

## Greek letters joined to text

*Asked in {issue}`117`.*

A Greek name followed by an uppercase letter or a digit is split off, so `DeltaH` and
`gammaM0` read as written on paper. Unicode letters work too:

```{hc-example}
DeltaH = 4.2     # kJ
gamma_M0 = 1.0
gammaM1 = 1.1
ΔT = 35          # K
```

`lamb` or `lambda_` gives λ (`lambda` is a Python keyword). To turn the prefix split
off, use `# hc: greek_prefixes = False`.

## Accents, primes and stars

*Asked in {issue}`132`.*

```{hc-example}
V_dot = 2.5      # m³/s
x_bar = 12.0
f_prime_c = 30   # MPa
M_star = 85      # kN m
```

## Any symbol for any name

*Asked in {issue}`101` and {issue}`132`.*

When a Python name can't spell the symbol, map it to a display spec with the `symbols`
field. The spec syntax is the same in every renderer:

```{hc-example}
# hc: symbols = {"N_plRd": "N_{pl,Rd}", "V_flow": "dot(V)", "dH": "ΔH^{*}"}
N_plRd = 1250
V_flow = 2.5
dH = 4.2
```

Set it for a session with `handcalcs.set_option("symbols", {...})`.

## Raw LaTeX for a symbol

For markup the spec syntax can't express (`\tilde{u}`, `\mathcal{F}`), register a
`name:pre` rule. See
[Custom symbols with a rule](../customizing/symbols-and-functions.md#custom-symbols-with-a-rule).

## Keep a name as text

*Asked in {issue}`90`.*

Greek names become letters. To keep some names as upright text, replace their
identifier in a `name:pre` rule:

```{literalinclude} ../_examples/notation.py
:language: python
:pyobject: UprightMarkdownRenderer
```

```{literalinclude} ../_examples/notation.py
:language: python
:pyobject: keep_upright
```

```{hc-example}
:renderer-file: _examples/notation.py
:renderer-class: UprightMarkdownRenderer
psi = 14.7
A = 3.5
F = psi * A
beta = 0.8
```

## No subscripts at all

*Asked in {issue}`97`.*

`___` (three underscores) is a literal underscore. A `name:pre` rule can apply that to
every name:

```{literalinclude} ../_examples/notation.py
:language: python
:pyobject: literal_underscores
```

```{hc-example}
:renderer-file: _examples/notation.py
:renderer-class: NoSubscriptMarkdownRenderer
load_case_1 = 3
M_max = load_case_1 * 2
```

## Sigma for sum, and your own function names

*Asked in {issue}`169` and {issue}`194`.*

The LaTeX and Markdown renderers look function names up in `MATH_FUNCS`. Add entries in
a subclass. A function that isn't in the table is shown by its name:

```{literalinclude} ../_examples/notation.py
:language: python
:pyobject: SigmaMarkdownRenderer
```

```{hc-example}
:renderer-file: _examples/notation.py
:renderer-class: SigmaMarkdownRenderer
:setup: interp_table = lambda x: 0.8
loads = [1.5, 2.0, 3.5]
P = sum(loads)
k = interp_table(2.5)
```

The same table gives `ln` for `log`: `MATH_FUNCS | {"log": "\\ln"}`.

## Times sign for multiplication

*Asked in {issue}`163`.*

```{literalinclude} ../_examples/notation.py
:language: python
:pyobject: TimesMarkdownRenderer
```

```{hc-example}
:renderer-file: _examples/notation.py
:renderer-class: TimesMarkdownRenderer
a = 2
b = 3
c = a * b
```

Each operator has a key: `add_op`, `sub_op`, `mult_op`, `div_op`, `pow_op`, the
comparisons and more. See [Operator symbols](../customizing/symbols-and-functions.md#operator-symbols).

## Cube roots, factorials and infinity

*Asked in {issue}`225`, {issue}`96` and {issue}`166`.*

`cbrt` is typeset as a cube root, `factorial` as `n!`, and an infinite value as ∞:

```{hc-example}
:setup: from math import cbrt, factorial
V = 27.0
a = cbrt(V)
n = 4
ways = factorial(n)
more = factorial(n + 1)
limit = float('inf')
```

`math.cbrt` needs Python 3.11 or later. `np.cbrt` works too.

## Functions from `math` and numpy

*Asked in {issue}`127` and {issue}`99`.*

Common functions are typeset as operators and radicals. `min` and `max` show their
arguments:

```{hc-example}
:setup: from math import sqrt, sin, cos, pi, log
a = sqrt(16)
b = sin(pi / 6) + cos(0)
c = log(10)
d = max(a, b, c)
```

`np.sqrt`, `np.sin` and the other numpy functions are typeset the same way.

## `:=` (or anything else) between the steps

```python
handcalcs.set_option("assign", ":=")   # ASCII and HTML renderers
```

The LaTeX and Markdown renderers also read `assign`, but it ends up inside math, so give
it LaTeX: `handcalcs.set_option("assign", "\\coloneqq")` (needs the `mathtools`
package in LaTeX documents).

## A narrower indent in ASCII output

```python
handcalcs.set_option("indent", "  ")
```

This works for the ASCII and base renderers; see the
[caution](../customizing/render-context.md#four-ways-to-set-a-field) for LaTeX and Markdown.

**Next:** [Units](units.md).
