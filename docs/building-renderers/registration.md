# Handlers and rules

A renderer's behaviour is a set of functions stored in three tables, filled by
`register`. This page covers what you can register, the function signatures, and the
order things run in.

## Registering

```python
@MyRenderer.register("calc_line")        # a handler
def render_calc_line(renderer, node, base_context): ...

@MyRenderer.register("name:sym")         # a rule
def swap_names(renderer, node, base_context): ...
```

`register` is a class method. A function can be registered several times by stacking
decorators. To change a single instance instead, use `renderer.register_handler(classifier,
function)` (see [Customizing one instance](../customizing/per-instance-handlers.md)).

Source: {src}`BaseRenderer.register <handcalcs.renderers.base.BaseRenderer.register>` and
{src}`_route_registration <handcalcs.renderers.base.BaseRenderer._route_registration>`.

## Classifiers

The string you register under is a **classifier**. Its form picks the table:

| Classifier | Registers | Signature | Returns |
|---|---|---|---|
| `"{type}"` | the **handler** for that node type (replaces any inherited one) | `(renderer, node, base_context)` | the rendered piece |
| `"{type}:pre"` | a rule run before the handler, in any mode | `(renderer, node, base_context)` | the node (changed or replaced) |
| `"{type}:sym"` | a rule run before the handler when `current_mode == "sym"` | `(renderer, node, base_context)` | the node |
| `"{type}:num"` | a rule run before the handler when `current_mode == "num"` | `(renderer, node, base_context)` | the node |
| `"{type}:post"` | a rule run on the handler's result | `(renderer, rendered, node, base_context)` | the rendered piece |
| `"header:{type}"` | the header line of a block node | `(renderer, node, base_context)` | a string (`""` for no header) |
| `"root:pre"`, `"root:post"` | an item added at the start or end of the render tree | `(renderer, root, base_context)` | an item for the tree |

`{type}` is a node's `type` string (`calc_line`, `name`, `div_op`, ... see [Nodes](nodes.md)).
Anything else raises `NotImplementedError` when you register it.

```{important}
Rules **must return** the node (or, for `post`, the rendered piece). A rule that forgets
to `return node` replaces the node with `None`.
```

## Handlers

A handler renders one node and returns its piece of the [render tree](output-tree.md).
For a node with children, it renders them by calling `renderer.render(child,
base_context)`, which goes back through the rules and handlers for the child's type:

```python
@MyRenderer.register("div_op")
def render_div(renderer, node, base_context):
    top = renderer.render(node.left, base_context)
    bottom = renderer.render(node.right, base_context)
    return f"{top} ÷ {bottom}"
```

Every type the parser can produce has a handler on `BaseRenderer`, so a subclass only
registers handlers for the types it renders differently. If a node reaches
`render_node` with no handler, it raises `NotImplementedError` naming the type.

## Rules

Rules adjust rendering without rewriting a handler. They are the right tool when the
handler's logic is fine but a detail differs:

- **`pre`** changes the node before rendering in both modes: operator symbols, function
  names, delimiters (`node.pre`, `node.post`).
- **`sym`** and **`num`** change the node for one mode only. The built-in renderers
  translate variable names in `name:sym` rules, because a name's identifier only shows in
  the symbolic step (the numeric step shows its value).
- **`post`** changes the result: wrap it in markup, add a class, color it.

A rule can also read or set [context](render-context.md) fields, as the built-in
`calc_line:pre` rule does to decide whether a line is a parameter
({src}`toggle_param_line <handcalcs.renderers.base.toggle_param_line>`).

### Rules see each node twice

A calculation renders its right-hand side once in `sym` mode and once in `num` mode, so
`pre` and `post` rules on the nodes inside it run **twice on the same node object**.
Make rules idempotent: set a value (`node.symbol = "×"`) rather than build on the current
one (`node.symbol += "×"`), and look things up by `node.type` rather than by the current
symbol. The built-in rules follow this pattern; see
{src}`swap_operator_symbols <handcalcs.renderers.latex.swap_operator_symbols>`.

## Order of execution

For each node, {src}`render_node <handcalcs.renderers.base.BaseRenderer.render_node>` runs:

1. `{type}:pre` rules
2. `{type}:sym` or `{type}:num` rules (by `current_mode`; neither when it is unset)
3. the `{type}` handler
4. `{type}:post` rules

Within a category, rules run in **registration order**, and a subclass's rule list starts
as a copy of its parent's. So **a subclass's rules run after its parent's** for the same
classifier. To run before an inherited `sym` rule, register a `pre` rule instead (the
technique used in [Symbols and functions](../customizing/symbols-and-functions.md)).

## Inheritance

Each subclass gets its own copies of the three tables when it is defined
({src}`__init_subclass__ <handcalcs.renderers.base.BaseRenderer.__init_subclass__>`), so
registering on a subclass never changes its parent. Each instance copies its class's
tables when it is created.

This means:

- Register on your class **before** creating instances.
- To remove an inherited rule, remove it from your class's table:
  `MyRenderer.rule_handlers["name"]["sym"].remove(parent_rule)`.
- To call the parent's handler from yours, look it up on the parent class:

  ```python
  @MyRenderer.register("constant")
  def render_constant(renderer, node, base_context):
      text = LatexRenderer.node_handlers["constant"](renderer, node, base_context)
      return f"\\mathbf{{{text}}}"
  ```

  (A `post` rule does the same job more simply; use this when you need to choose
  whether to call the parent at all. The Markdown renderer does this for strings,
  {src}`render_constant <handcalcs.renderers.markdown.render_constant>`.)

## The tables

| Class attribute | Instance attribute | Holds |
|---|---|---|
| `node_handlers` | `_handlers` | `{type: handler}` |
| `header_handlers` | `_header_handlers` | `{type: header handler}` |
| `rule_handlers` | `_rule_handlers` | `{type: {"pre"/"sym"/"num"/"post": [rule, ...]}}` |

**Next:** [The render context](render-context.md).
