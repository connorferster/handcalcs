# Adding a node type

Supporting a new piece of Python syntax touches the parser, the base renderer and,
usually, each built-in renderer. This page walks through the steps with a real example:
conditional expressions (`x = a if test else b`), the `IfExp` node. The snippets are
simplified; each step links to the code it describes.

## 1. Define the node

Add a dataclass next to its relatives. An expression goes in
{src}`handcalcs.parsing.inline_nodes`; a statement in {src}`handcalcs.parsing.line_nodes`;
a compound statement in {src}`handcalcs.parsing.block_nodes`.

```python
@dataclass
class IfExp(HcInlineNode):
    test: Any = None
    body: Any = None
    orelse: Any = None
    is_true: Optional[bool] = None
    type: str = "if_exp"
```

The `type` string is the name renderers register against: lowercase snake case, unique.
The real node is {src}`IfExp <handcalcs.parsing.inline_nodes.IfExp>`.

## 2. Parse it

Add a branch to
{src}`AST_Parser.ast_parse <handcalcs.parsing.ast_parser.AST_Parser.ast_parse>`. Recurse
into children with `self.ast_parse`, and capture whatever runtime information the
renderer needs at this point, since the namespace is only available here:

```python
elif isinstance(node, ast.IfExp):
    val = IfExp(
        test=self.ast_parse(node.test),
        body=self.ast_parse(node.body),
        orelse=self.ast_parse(node.orelse),
        is_true=self._evaluate_test(node.test),
    )
```

Add a parser test in `tests/test_parser.py` that checks the node tree for a few sources.

## 3. Render it in `BaseRenderer`

Register a handler in {src}`handcalcs.renderers.base`, so every renderer can render the
node, even if plainly:

```python
@BaseRenderer.register("if_exp")
def render_if_exp(renderer, node, base_context):
    if_kw, else_kw = renderer.IF_EXP_KEYWORDS
    body = renderer.render(node.body, base_context)
    test = renderer.render(node.test, base_context)
    orelse = renderer.render(node.orelse, base_context)
    return f"{body}{if_kw}{test}{else_kw}{orelse}"
```

The real handler, {src}`render_if_exp <handcalcs.renderers.base.render_if_exp>`, also
parenthesizes a nested conditional expression. The keywords come from a class attribute,
`IF_EXP_KEYWORDS` (`(" if ", " else ")` on `BaseRenderer`), so a renderer can change
them without a new handler.

Check whether the new node interacts with existing logic: precedence (`OP_PRECEDENCE`),
param-line detection (`is_literal_expr`), the duplicate-column check in
`render_calcline`. Add node-level tests in the style of `tests/test_render_nodes.py`,
using the `renderer` and `make_context` fixtures from `tests/conftest.py`.

## 4. Render it in each built-in renderer

Decide how each format should show it, and register a handler or rule:

- `ASCIIRenderer`: often the base handler is enough.
- `LatexRenderer` (and so `MarkdownRenderer`): math notation. For `IfExp`, the LaTeX
  renderer only overrides `IF_EXP_KEYWORDS` with upright `\mathrm{if}` and `\mathrm{else}`.
- `HTMLRenderer`: HTML markup.
- `ExcelRenderer`: an Excel formula (`IfExp` becomes `IF(...)`, see
  {src}`handcalcs.renderers.excel.formulas`), or add it to the incompatible list so it
  raises `ExcelRendererIncompatibleError` with a clear message.

## 5. Update the golden files and docs

If the demo uses the new syntax, regenerate the golden files (see [Tests](testing.md)).
Add the node to [Nodes](../building-renderers/nodes.md) and the
[node type reference](../reference/node-types.md), and describe the feature in
[How handcalcs reads your code](../getting-started/how-it-works.md).
