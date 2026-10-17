# Symbols and functions

Every built-in renderer translates names, operators and function calls as it renders
them: `alpha` becomes α, `sqrt` a radical. You can add your own translations.

## Custom symbols for names

A rule registered as `name:pre` runs on every variable name before the renderer's own
translation. Replace the identifier with the symbol you want:

```{literalinclude} ../_examples/custom_symbols.py
:language: python
```

```{hc-example}
:renderer-file: _examples/custom_symbols.py
:renderer-class: SymbolMarkdownRenderer
:setup: ceil_to = round
V_dot = 2.5
N_star = V_dot * 3
M_r = ceil_to(N_star)
```

Why `pre` and not `sym`? The LaTeX family translates names in a `name:sym` rule
(`latex_identifier`), and a subclass's rules run **after** the inherited ones. A
`pre` rule runs first, and `latex_identifier` leaves a name that already contains LaTeX
(a backslash or a brace) alone. See
[rule order](../building-renderers/registration.md#order-of-execution).

The same rule works for the HTML and plain-text renderers, using HTML markup or Unicode
in the replacement: `{"V_dot": "V&#775;"}` for HTML, `{"V_dot": "V̇"}` for plain text.

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
`PlainTextRenderer` itself.

**Next:** [Customizing one instance](per-instance-handlers.md).
