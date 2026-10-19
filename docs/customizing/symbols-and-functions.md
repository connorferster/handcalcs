# Symbols and functions

Every built-in renderer translates names, operators and function calls as it renders
them: `alpha` becomes α, `sqrt` a radical. You can add your own translations.

## Display symbols for names

Most notation needs no code: name the variable as described in
[naming variables](../getting-started/writing-calculations.md#naming-variables)
(`N_pl_Rd`, `DeltaH`, `V_dot`, `M_star`), or give it a display spec with the `symbols`
option, which every built-in renderer reads:

```python
import handcalcs
handcalcs.set_option("symbols", {"N_plRd": "N_{pl,Rd}", "V_flow": "dot(V)"})
```

## Subscript style and Greek prefixes in a renderer

Two class attributes set a renderer's defaults; the `subscripts` and `greek_prefixes`
context fields still override them:

```python
from handcalcs.renderers import LatexRenderer

class V1StyleLatexRenderer(LatexRenderer):
    SUBSCRIPT_STYLE = "nested"   # x_a_b -> x_{a_{b}} (default "comma": x_{a,b})
    GREEK_PREFIXES = False       # keep DeltaH as \mathrm{DeltaH} (default True: \Delta H)
```

## Custom symbols with a rule

For markup the spec syntax can't express, a rule registered as `name:pre` runs on every
variable name before the renderer's own translation. Replace the identifier with the
symbol you want:

```{literalinclude} ../_examples/custom_symbols.py
:language: python
```

```{hc-example}
:renderer-file: _examples/custom_symbols.py
:renderer-class: SymbolMarkdownRenderer
:setup: ceil_to = round
u_t = 2.5
F_cal = u_t * 3
M_r = ceil_to(F_cal)
```

Why `pre` and not `sym`? The LaTeX family translates names in a `name:sym` rule
(`latex_identifier`), and a subclass's rules run **after** the inherited ones. A
`pre` rule runs first, and `latex_identifier` leaves anything that is no longer a Python
identifier (it contains a backslash, a brace, ...) alone. See
[rule order](../building-renderers/registration.md#order-of-execution).

The same rule works for the HTML and plain-text renderers, using HTML markup or Unicode
in the replacement: `{"u_t": "ũ"}`. The HTML renderer also leaves markup such as
`u&#771;` alone.

## Function names

The LaTeX and Markdown renderers look function names up in `MATH_FUNCS`. Extend it in a
subclass, as `SymbolMarkdownRenderer` above does for `ceil_to`. A function that is not
in the table is shown by name in `\operatorname{...}`.

For other renderers, register a `function_call:pre` rule and change the function name's
`identifier` (shown in the symbolic step) and `value` (shown in the substituted step):

```python
@MyHTMLRenderer.register("function_call:pre")
def swap_ln(renderer, node, base_context):
    if node.function_name.identifier == "log":
        node.function_name.identifier = "ln"
        node.function_name.value = "ln"
    return node
```

## Operator symbols

The LaTeX and Markdown renderers look operator symbols up in `OPERATOR_SYMBOLS`, keyed
by node type:

```python
class TimesMarkdownRenderer(MarkdownRenderer):
    OPERATOR_SYMBOLS = MarkdownRenderer.OPERATOR_SYMBOLS | {"mult_op": "\\times"}
```

The node types are `add_op`, `sub_op`, `mult_op`, `div_op`, `floor_op`, `modulo_op`,
`pow_op`, the comparisons `lt_op`, `gt_op`, `lte_op`, `gte_op`, `eq_op`, `neq_op`, `in_op`,
`not_in_op`, `is_op`, `is_not_op`, and the boolean `and_op`, `or_op`. In the HTML and
plain-text renderers, set `node.symbol` in a `{type}:pre` rule (as the built-in
`swap_py_operators` rules do).

## Turning off a built-in translation

A subclass inherits its parent's rules. To stop, for example, Greek letter translation in
the plain-text renderer, remove the rule from the subclass's rule list:

```python
from handcalcs.renderers import PlainTextRenderer
from handcalcs.renderers.plaintext import swap_greeks

class NoGreekTextRenderer(PlainTextRenderer):
    pass

NoGreekTextRenderer.rule_handlers["name"]["sym"].remove(swap_greeks)
```

Each subclass gets its own copy of the rule lists, so this doesn't affect
`PlainTextRenderer` itself. In the HTML renderer, one rule, `swap_identifier` in
`handcalcs.renderers.html`, does all the name typesetting (Greek letters, subscripts,
accents); the LaTeX family's is `swap_identifier` in `handcalcs.renderers.latex`.

**Next:** [Customizing one instance](per-instance-handlers.md).
