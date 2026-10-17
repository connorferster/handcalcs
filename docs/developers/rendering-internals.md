# Rendering internals

{src}`handcalcs.renderers.base` holds the rendering engine and the base handler for every
node type. The public side of it is documented in the
[renderer-building guide](../building-renderers/index.md); this page covers the parts you
meet when changing the engine or the base handlers.

## Dispatch

- {src}`BaseRenderer.render <handcalcs.renderers.base.BaseRenderer.render>` sends the
  root to `render_root` and everything else to `render_node`.
- {src}`render_node <handcalcs.renderers.base.BaseRenderer.render_node>` wraps a raw
  Python value (anything without a `type` attribute) in a node with
  {src}`_reify <handcalcs.renderers.base._reify>` first. That is how a `Name`'s value
  is formatted by the `constant` handler, and how a list value becomes a `List` node whose
  elements are each formatted.
- Registration is routed by
  {src}`_route_registration <handcalcs.renderers.base.BaseRenderer._route_registration>`;
  the tables are copied per subclass in `__init_subclass__` and per instance in
  `__init__`.
- The registry of renderer names is `_RENDERER_REGISTRY`, filled in `__init_subclass__`.
  `BaseRenderer` registers itself explicitly at the end of the module, since
  `__init_subclass__` doesn't run for the class that defines it.

## Calculation lines

{src}`render_calcline <handcalcs.renderers.base.render_calcline>` is the most involved
handler. In order:

1. Render the comment first (an inline command replaces the line context).
2. If `ignore` is set, reset the line context and return `""`.
3. Build the columns allowed by `mode`: assignment targets (`sym`), symbolic expression
   (`sym`), numeric expression (`num`), result (targets in `num`). A param line skips the
   two expression columns.
4. Drop any column equal to the one before it, so `q = y` doesn't read `q = y = 3 = 3`.
5. If `multiline` is set and there is something to break, build `[id, "=", value]` rows
   and return `format_calc_grid(rows)`.
6. Otherwise interleave the columns with `context.assign`, append the comment, reset the
   line context and return the list of parts.

Whether a line is a parameter is decided before this by the `calc_line:pre` rule
{src}`toggle_param_line <handcalcs.renderers.base.toggle_param_line>`: a scalar literal, a
negated literal or a collection of literals, or a right-hand side wrapped in parentheses
(`pars_nesting`).

## Precedence and parentheses

The parser does not keep source parentheses; the renderer adds them where precedence
needs them. {src}`infix_binop <handcalcs.renderers.base.infix_binop>` compares each
operand's precedence with the operator's (`OP_PRECEDENCE`):

- a left operand that binds looser is wrapped;
- a right operand that binds looser, or equally for a non-commutative operator (`a - (b -
  c)`), is wrapped;
- an operand that renders with a leading sign is wrapped (`7·(-3)`), as is a signed base
  of a power (`(-2)²`).

{src}`infix_boolop <handcalcs.renderers.base.infix_boolop>` and
{src}`render_unary_op <handcalcs.renderers.base.render_unary_op>` follow the same table;
unary operators sit between multiplication and power (`UNARY_PRECEDENCE = 2.5`).
Renderers that draw some operators structurally (LaTeX fractions) override those handlers
and skip the parentheses that the structure makes unnecessary.

## Blocks

{src}`render_block_body <handcalcs.renderers.base.render_block_body>` renders every block
as `[header, body]`: the header from `render_header` (the `header:{type}` handler) wrapped
in the node's `header_pre`/`header_post`, and the body with `body_pre`/`body_post` added
as first and last items. The LaTeX renderer uses `body_pre`/`body_post` as sentinels to
mark a math group ({src}`calcs_block_pre_post <handcalcs.renderers.latex.calcs_block_pre_post>`).

{src}`render_elifblock <handcalcs.renderers.base.render_elifblock>` renders only the true
branch.

## Comments and Jinja

The `pre` rule {src}`interpolate_jinja_strings <handcalcs.renderers.base.interpolate_jinja_strings>`
renders the content of headings, comment lines and inline comments as a Jinja template
against `context.global_ns`. It uses `DebugUndefined`, so an unknown name is left as
`{{ name }}` instead of raising.

## Joining

{src}`join_item <handcalcs.renderers.base.BaseRenderer.join_item>` documents the three
tree shapes; the built-in renderers' `join_item` overrides each start from the same
dispatch. Keep the shapes stable: every renderer depends on them.
