# Architecture

This page follows one call, `HandCalcs(renderer)(source)`, from source code to output.
Each step links to the code that does it.

## 1. Run the code

If no namespace is supplied, the interface runs the source with `exec` and keeps the
resulting globals ({src}`HandCalcs.__call__ <handcalcs.interfaces.object_oriented.HandCalcs.__call__>`).
In Jupyter the notebook has already run the cell, and the decorator runs the function
with innerscope. Either way the result is a dictionary of values.

## 2. Parse into nodes

{src}`HcSequence.from_source <handcalcs.parsing.sequence.HcSequence.from_source>` turns
the source into a tree:

1. {src}`AST_Parser <handcalcs.parsing.ast_parser.AST_Parser>` walks Python's `ast` and
   builds handcalcs **nodes**: dataclasses such as `CalcLine`, `Name` and `DivOp`. Every
   `Name` is given its value from the namespace. Comments are classified as headings,
   comment lines, inline comments or commands
   ({src}`comment_parser <handcalcs.parsing.comment_parser>`), and `# hc:` flags are parsed
   with {src}`argparse <handcalcs.parsing.commands>`.
2. {src}`convert_if_tree <handcalcs.parsing.sequence.convert_if_tree>` turns each
   `if`/`elif`/`else` chain into an `ElifBlock` of `IfBlock`s (and an `ElseBlock`).
3. {src}`group_lines <handcalcs.parsing.sequence.group_lines>` gathers consecutive
   calculation lines into a `CalcsBlock` and consecutive comment lines into a
   `CommentsBlock`, so a renderer can treat a run of lines as one group (one LaTeX
   `aligned` environment, one HTML paragraph).
4. `set_levels` records each node's nesting depth on its `level` attribute.

The root of the tree is an `HcSequence` whose `sequence` holds the top-level nodes. See
[Nodes](nodes.md) for every node type.

## 3. Create the render context

`renderer.create_context(**settings)` builds a
{src}`BaseRenderContext <handcalcs.renderers.base.BaseRenderContext>` from the global
configuration (and, for `HandCalcs`, a `global_ns` field holding the namespace). It has a
**global** layer, for settings that persist, and a **line** layer, for settings that apply
to the current line only. See [The render context](render-context.md).

## 4. Render each node

`renderer.render(root, context)` calls
{src}`render_root <handcalcs.renderers.base.BaseRenderer.render_root>`, which renders each
top-level node with
{src}`render_node <handcalcs.renderers.base.BaseRenderer.render_node>`. For one node,
`render_node`:

1. runs the node type's `pre` rules (each may return a changed node);
2. runs its `sym` or `num` rules, depending on `context.current_mode`;
3. calls the node type's **handler**, which returns the rendered piece, and usually calls
   `renderer.render(child, context)` for the node's children;
4. runs its `post` rules on the rendered piece.

Handlers and rules are looked up by the node's `type` string in tables that
[`register`](registration.md) fills. A calculation line is rendered twice per
sub-expression: once with `current_mode = "sym"` (names as symbols) and once with
`"num"` (names as values), by {src}`render_calcline <handcalcs.renderers.base.render_calcline>`.

The result is the **render tree**, a nested list mirroring the node tree. With the
built-in handlers, a line becomes a list of strings and a block becomes
`[header, body]`; see [The render tree](output-tree.md).

## 5. Complete

`renderer.complete(tree, context)` produces the final output. Text renderers call
{src}`join <handcalcs.renderers.base.BaseRenderer.join>`, which walks the tree with
{src}`join_item <handcalcs.renderers.base.BaseRenderer.join_item>` and inserts spaces,
newlines and indentation. Handlers deliberately leave all of that out, so each renderer
decides its own layout in one place.

`BaseRenderer.complete` returns the tree unchanged; that is what you see from the
[base renderer](../renderers/base.md).

## Where the code lives

| Step | Module |
|---|---|
| Interfaces | {src}`handcalcs.interfaces.object_oriented`, {src}`handcalcs.interfaces.jupyter`, {src}`handcalcs.interfaces.decorator` |
| Parsing | {src}`handcalcs.parsing.ast_parser`, {src}`handcalcs.parsing.sequence` |
| Nodes | {src}`handcalcs.parsing.nodes`, {src}`handcalcs.parsing.line_nodes`, {src}`handcalcs.parsing.block_nodes`, {src}`handcalcs.parsing.inline_nodes`, {src}`handcalcs.parsing.operator_nodes` |
| Rendering core | {src}`handcalcs.renderers.base` |
| Built-in renderers | {src}`handcalcs.renderers.plaintext`, {src}`handcalcs.renderers.latex`, {src}`handcalcs.renderers.markdown`, {src}`handcalcs.renderers.html`, {src}`handcalcs.renderers.excel` |
| Configuration | {src}`handcalcs.config` |

**Next:** [Nodes](nodes.md).
