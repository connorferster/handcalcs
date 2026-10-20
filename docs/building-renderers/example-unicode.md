# Example: a Unicode renderer

**Technique: rules only.** This renderer improves the plain-text output with Unicode
subscripts, a centred dot for multiplication and proper comparison signs. It changes no
handlers and no layout; it inherits everything from `ASCIIRenderer` and adds four
rules.

## The code

```{literalinclude} ../_examples/unicode_renderer.py
:language: python
```

## The result

```{hc-example}
:renderer-file: _examples/unicode_renderer.py
:renderer-class: UnicodeRenderer
:setup: from math import sqrt
## Web check
x_1 = 51.7
alpha_max = x_1 * 2
F_y = 350
if x_1 <= 1100 / sqrt(F_y):
    web_class = 1
```

## How it works

**`unicode_subscripts`** is a `name:sym` rule, because a name's identifier only appears
in the symbolic step. It runs after the inherited `swap_greeks` rule (a subclass's rules
run after its parent's), so `alpha_max` has already become `α_max` when it sees it.
Unicode has no subscript form for some letters (`y`, `w`, `b`, ...), so the rule leaves a
name alone unless every character can be converted, which is why `F_y` keeps its
underscore.

**`centred_dot`** and **`comparison_signs`** are `pre` rules, because operators appear in
both the symbolic and the numeric step. They set `node.symbol` from fixed values, so
running twice on the same node (once per step) is harmless. See
[Rules see each node twice](registration.md#rules-see-each-node-twice).

The comparison signs include their own spaces because the `compare` handler joins its
parts with no separator (`a<b`).

## Try it

- Register a `pow_op:pre` rule that turns `**` with a non-number exponent into `^`.
- Add a `name:sym` rule that turns a trailing `_prime` into `′`.

**Next:** [Example: a reStructuredText renderer](example-restructuredtext.md).
