# Checks and decisions

Design calculations end in a decision: does the member pass? Recipes for showing the
check, the governing case, and a verdict in words.

## Mark a check as pass or fail

*Asked in {issue}`251` and {issue}`195`.*

`--check` at the end of a comparison replaces its `True`/`False` result with a green ✓
or a red ✗:

```{hc-example}
M_Ed = 120        # kN m
M_Rd = 150        # kN m
eta = M_Ed / M_Rd
ok = eta <= 1.0   # hc: --check
```

A bare comparison works too, and a failing check is marked as clearly:

```{hc-example}
V_Ed = 210        # kN
V_Rd = 180        # kN
V_Ed <= V_Rd      # hc: --check
```

On its own line, `# hc: --check` marks every boolean result after it, until
`# hc: check = False`. Lines that aren't comparisons are unaffected:

```{hc-example}
:renderer: html
# hc: --check
f_y = 355
f_u = 510
f_u / f_y >= 1.1
f_y <= 460
```

The marks come from each renderer's `CHECK_MARKS` class attribute, a `(pass, fail)`
pair that includes the gap before the mark. For example, words instead of symbols:

```python
class WordyMarkdownRenderer(MarkdownRenderer):
    CHECK_MARKS = ("\\quad\\text{OK}", "\\quad\\text{NOT OK}")
```

In a LaTeX document, the default marks need the `amssymb` and `xcolor` packages. The
HTML renderer colors them with the `hc-pass` and `hc-fail` classes, and the Excel
renderer keeps the live `TRUE`/`FALSE` formula with green or red formatting.

## Write the verdict in a comment

*Asked in {issue}`195` and {issue}`251`.*

Comments can contain Jinja expressions in `{{ }}`. They are evaluated with the
calculation's values, so a sentence can state the outcome:

```{hc-example}
M_Ed = 120  # kN m
M_Rd = 150  # kN m
eta = M_Ed / M_Rd
# Utilisation is {{ "%.0f" % (eta * 100) }} %, so the section {{ "passes" if eta <= 1 else "fails" }}.
```

Inline comments work the same way:

```{hc-example}
eta = 0.83  # {{ "OK" if eta <= 1 else "NOT OK" }}
```

## Pick a value with a conditional expression

A one-line `if`/`else` keeps a simple choice on one line, and the substitution shows
which branch the values pick:

```{hc-example}
t = 18           # mm
f_y = 355 if t <= 16 else 345
```

## Show the comparison as True or False

Without `--check`, a comparison on its own line is shown with its result. Assign it to
keep the result for later:

```{hc-example}
M_Ed = 120
M_Rd = 150
M_Ed <= M_Rd
passes = M_Ed / M_Rd <= 1.0
```

## Show only the governing branch

*Asked in {issue}`251` and {issue}`191`.*

An `if`/`elif`/`else` block shows the test that was true and the lines that ran under
it. The other branches are left out, so the output reads as the governing case:

```{hc-example}
eta = 0.97
if eta <= 0.9:
    verdict = "Pass"
elif eta <= 1.0:
    verdict = "Pass, close to the limit"
else:
    verdict = "Fail"
```

Calculations inside the branch are rendered too, so a code clause with two cases can be
written as it reads:

```{hc-example}
:setup: from math import sqrt
lamb = 0.6
if lamb <= 0.2:
    chi = 1.0
else:
    phi = 0.5 * (1 + 0.34 * (lamb - 0.2) + lamb**2)
    chi = 1 / (phi + sqrt(phi**2 - lamb**2))
```

## Check several load cases at once

A `for` loop's body shows the values of its **last** iteration only, so it can't show a
check per case. Put the cases in a list instead, and let `max` pick the governing one:

```{hc-example}
M_Rd = 150
M_Ed = [90, 120, 140]
eta = [M / M_Rd for M in M_Ed]  # hc: -f .2f
eta_max = max(eta)              # hc: -f .2f
```

## Run the same check for many designs

To render one calculation for each row of a table of inputs, see
[Rendering many input sets](../interfaces/object-oriented.md#rendering-many-input-sets).

**Next:** [Symbols and notation](symbols.md).
