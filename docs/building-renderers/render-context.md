# The render context

Every handler and rule receives `base_context`, a
{src}`BaseRenderContext <handcalcs.renderers.base.BaseRenderContext>`. It carries the
settings for the render, and lets handlers pass information to each other.

## Two layers

`base_context.global_context`
: A {src}`RenderContext <handcalcs.renderers.base.RenderContext>` built by
  `create_context` from the configuration. Settings here last for the rest of the render.
  A standalone comment command (`# hc: -f .2f` on its own line) writes here.

`base_context.line_context`
: A sparse `RenderContext` holding only the overrides for the **current line**. An inline
  command (`x = a / b  # hc: -f .2f`) writes here, and the line handlers reset it to
  empty when the line is finished.

`base_context.current`
: The two layers merged, line over global, as a **new** `RenderContext`. Read settings
  from it.

```python
def my_rule(renderer, node, base_context):
    context = base_context.current
    if context.format_code == ".2f": ...
```

```{warning}
`base_context.current` is a fresh copy each time. **Writing to it has no effect.** To set
a value, write to `base_context.line_context` (for this line) or
`base_context.global_context` (for the rest of the render).
```

A `RenderContext` is a plain object: fields are attributes, and any keyword given to it
becomes one. Read fields that may be missing with `getattr(context, "name", default)`.

## `current_mode`

The handlers for lines set `current_mode` on the line context before rendering an
expression:

- `"sym"`: render names as **symbols** (their identifiers);
- `"num"`: render names as **values**.

{src}`render_calcline <handcalcs.renderers.base.render_calcline>` renders the assignment
targets and the expression in `sym` mode, then the expression and the targets again in
`num` mode, collecting the columns. The `name` handler reads `current_mode` to decide what
to show, and `render_node` uses it to choose between `sym` and `num` rules.

If you write a handler for a line or block that renders expressions, set `current_mode`
before rendering them, as the built-in ones do:

```python
base_context.line_context.current_mode = "sym"
symbolic = "".join(renderer.render(n, base_context) for n in node.expression_tree)
```

## Fields

The fields the built-in renderers use are listed in
[Settings and the render context](../customizing/render-context.md#fields-the-built-in-renderers-read).
In addition:

| Field | Set by | Meaning |
|---|---|---|
| `global_ns` | `HandCalcs` | The namespace values came from (used for `{{ }}` in comments) |
| `current_mode` | line handlers | `"sym"` or `"num"` (see above) |
| `param_line` | the `calc_line:pre` rule | This line is a parameter: show *target = value* |
| `line_break` | `# hc: -b` | (consumed by `render_comment_command`; never stored) |

## How comment commands reach the context

1. The parser stores a command's settings as a dict on `CommentCommand.commands` (a
   standalone command) or `InlineCommand.commands` (at the end of a line). Flags become
   their long names (`-f` → `format_code`); the assignment form keeps your names.
2. {src}`render_comment_command <handcalcs.renderers.base.render_comment_command>` copies
   a standalone command's settings onto the **global** context.
3. {src}`render_inline_command <handcalcs.renderers.base.render_inline_command>` replaces
   the **line** context with the inline command's settings. A calculation line renders
   its comment first, so the settings apply to the rest of that line.

So your own fields work the same way: `# hc: highlight = True` sets `highlight` on the
global context, and a rule reads `getattr(base_context.current, "highlight", False)`.

## Setting defaults in `create_context`

Override `create_context` to give your renderer its own defaults, while still letting the
configuration override them:

```python
class MyRenderer(BaseRenderer):
    def create_context(self, **kwargs):
        settings = {"indent": "  ", "assign": ":="} | kwargs
        return BaseRenderContext(RenderContext(**settings), RenderContext.sparse())
```

(`BaseRenderContext` and `RenderContext` are in `handcalcs.renderers.base`.) Merging
with `|` like this avoids the `TypeError` the built-in LaTeX renderer raises when a
configured field collides with one it sets itself.

## Keeping state for a render

The global context is created fresh for each render, so it is a safe place to keep state
that handlers share during one render: counters, a table of names, collected footnotes.
The Excel renderer keeps its formula builder and symbol table there
({src}`excel_state <handcalcs.renderers.excel.renderer.excel_state>`). Use a name that won't
collide with a setting:

```python
def counter(base_context):
    gc = base_context.global_context
    gc._equation_number = getattr(gc, "_equation_number", 0) + 1
    return gc._equation_number
```

**Next:** [Overridable methods](overridable-methods.md).
