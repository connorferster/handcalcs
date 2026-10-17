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

**For part of one calculation**, with the assignment form of a comment command:

```python
# hc: assign = ":="
x = a + b
```

**For one line**:

```python
x = a + b  # hc: format_code = ".2f"
```

**For every call of a decorated function**:

```python
@handcalc(PlainTextRenderer(), render_context={"format_code": ".2f"})
def calc(a, b): ...
```

```{hc-example}
:renderer: plain_text
a = 2
b = 3
# hc: assign = ":="
c = a + b
```

```{caution}
In handcalcs 2.0, setting `space`, `newline`, `indent`, `lpar` or `rpar` with
`set_option` makes the LaTeX and Markdown renderers raise a `TypeError`, because they
set those fields themselves. Change them in a subclass's `create_context` instead (see
[overridable methods](../building-renderers/overridable-methods.md#create-context)).
```

## Your own fields

Any name can be used. The built-in renderers ignore names they don't use, and a rule
you write can read them from the context. This makes a rule switchable from a comment:

```python
# hc: highlight = True
```

```python
def highlight_result(renderer, rendered, node, base_context):
    if not getattr(base_context.current, "highlight", False):
        return rendered
    ...
```

Read optional fields with `getattr(context, name, default)`, since a field only exists
once something has set it.

**Next:** [Styling the HTML output](html-styling.md).
