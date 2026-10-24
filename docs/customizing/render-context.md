# Settings and the render context

While it renders, a renderer reads its settings from a **render context**: a simple
object whose attributes are the settings. Changing a context field is the lightest way
to change the output, and needs no subclass.

## Fields the built-in renderers read

| Field | Default | Meaning |
|---|---|---|
| `format_code` | `".5g"` | [Number format](../getting-started/formatting-numbers.md). |
| `mode` | `"full"` | Which steps to show: `"full"`, or any of `ass`, `sym`, `num`, `res` (see [mode](../getting-started/comment-commands.md#choosing-which-steps-appear-mode)). |
| `assign` | `"="` | The symbol between the steps of a calculation. |
| `multiline` | `False` | Break calculations over several lines (`# hc: -m`). |
| `param_line` | `False` | Show *target = result* only (`# hc: -p`). |
| `param_cols` | `3` | Columns in a parameter grid (`# hc: -c`). |
| `ignore` | `False` | Leave lines out of the output (`# hc: -i`). |
| `space` | `" "` | The separator between the parts of a line. |
| `newline` | `"\n"` | The line separator. |
| `indent` | `"    "` | One level of indentation for block bodies. |
| `lpar`, `rpar` | `"("`, `")"` | Parentheses added for operator precedence and around comments. |
| `subscripts` | `"comma"` | `"comma"` (`N_pl_Rd` → N<sub>pl,Rd</sub>) or `"nested"` (v1's x<sub>a<sub>b</sub></sub>). See [naming variables](../getting-started/writing-calculations.md#naming-variables). |
| `symbols` | `{}` | Display specs for names, e.g. `{"N_plRd": "N_{pl,Rd}"}`. See [display symbols](../getting-started/writing-calculations.md#display-symbols). |
| `greek_prefixes` | `True` | Split a Greek name before an uppercase letter or digit (`DeltaH` → ΔH). |
| `max_items` | `10` | A list, tuple, set or dict with more items shows only its first and last `edge_items`, around an ellipsis. `0` shows every item. |
| `edge_items` | `3` | The items kept at each end of a shortened collection. |

The LaTeX and Markdown renderers set `space`, `newline`, `indent`, `lpar` and `rpar`
themselves (for example `lpar` is `\left(`). The HTML renderer ignores `indent`; its
indentation comes from CSS.

Two more fields are set by the interface: `global_ns`, the namespace the values come
from (used for `{{ }}` in comments), and, during rendering, `current_mode` (`"sym"` or
`"num"`). See [the render context](../building-renderers/render-context.md) in the
renderer-building guide for how the context works internally.

## Four ways to set a field

**For every render in the session** (or permanently, with `save_config()`):

```python
import handcalcs
handcalcs.set_option("assign", ":=")
```

**For part of one calculation**, with the assignment form of a comment command. It
applies to every line after it:

```{hc-example}
:renderer: ascii
a = 2
b = 3
# hc: assign = ":="
c = a + b
d = c * 2
```

**For one line**, at the end of that line. Note that `format_code` applies to the
substituted values as well as the result:

```{hc-example}
:renderer: ascii
a = 85
b = 110
c = a / b  # hc: format_code = ".2f"
d = a / b
```

**For every call of a decorated function**:

```python
@handcalc(ASCIIRenderer(), render_context={"format_code": ".2f"})
def calc(a, b): ...
```

```{caution}
In handcalcs 2.0, setting `space`, `newline`, `indent`, `lpar` or `rpar` with
`set_option` makes the LaTeX and Markdown renderers raise a `TypeError`, because they
set those fields themselves. Change them in a subclass's `create_context` instead (see
{ref}`overridable methods <create-context>`).
```

## Your own fields

Any name can be used. The built-in renderers ignore names they don't use, and a rule
you write can read them from the context. This makes a rule switchable from a comment.
This renderer marks lines with a note given by a `flag` field:

```{literalinclude} ../_examples/flag_lines.py
:language: python
```

```{hc-example}
:renderer-file: _examples/flag_lines.py
:renderer-class: FlagASCIIRenderer
M_f = 85; M_r = 110; V_f = 40; V_r = 35
u_M = M_f / M_r
u_V = V_f / V_r  # hc: flag = "governs"
# hc: flag = "check later"
u_T = 0.4 * u_V
```

Read optional fields with `getattr(context, name, default)`, since a field only exists
once something has set it. A field set at the end of a line is in
`base_context.current` while the line's parts render, but is reset before the line's
`post` rules run; a `post` rule reads it from `node.comment.commands`, as above.

**Next:** [Styling the HTML output](html-styling.md).
