# Nodes

The parser turns source code into a tree of **nodes**. Each node is a dataclass with a
`type` string; the renderer dispatches on that string, so `type` is the name you
register handlers under.

## What a tree looks like

```python
>>> from handcalcs.parsing.sequence import HcSequence
>>> tree = HcSequence.from_source("a = 2\nb = a * 3  # note\n", hc_globals={"a": 2, "b": 6}, hc_locals={})
>>> tree.sequence
deque([CalcsBlock(lines=deque([
    CalcLine(assigns=deque([Name(identifier='a', value=2)]),
             expression_tree=deque([Constant(value=2)]),
             comment=None),
    CalcLine(assigns=deque([Name(identifier='b', value=6)]),
             expression_tree=deque([MultOp(left=Name(identifier='a', value=2),
                                           right=Constant(value=3),
                                           symbol='*')]),
             comment=InlineComment(content='note')),
]))])
```

(Abbreviated: fields at their defaults are left out.) After a call, `HandCalcs.hc_ast`
holds the tree it rendered, so you can inspect the tree for any source.

## Node types

The tables below list every node type, its class and the attributes a handler typically
reads. All classes live in `handcalcs.parsing`.

### Lines

Defined in {src}`handcalcs.parsing.line_nodes`. Every line node has `level` (nesting
depth) and `pre`/`post` strings.

| `type` | Class | Attributes | Source |
|---|---|---|---|
| `calc_line` | `CalcLine` | `assigns` (targets), `expression_tree` (the right-hand side), `comment` (`InlineComment`, `InlineCommand` or `None`), `pars_nesting` (wrapped in parentheses) | `x = a + b` |
| `expr_line` | `ExprLine` | `expression_tree`, `comment`, `return_expr` | `a + b`, `print(x)` |
| `comment_line` | `CommentLine` | `content` | `# prose` |
| `heading` | `Heading` | `content`, `heading_level` (1 for `##`) | `## Title` |
| `comment_command` | `CommentCommand` | `commands` (dict of settings) | `# hc: -f .2f` |
| `import` | `Import` | `names` (`Name`s; `value` holds an `as` alias), `import_from`, `import_from_module`, `import_from_level` | `import math` |

### Blocks

Defined in {src}`handcalcs.parsing.block_nodes`. Every block has `lines` (its children),
`level`, and four strings the built-in block handler wraps around its output:
`header_pre`, `header_post`, `body_pre`, `body_post`.

| `type` | Class | Attributes | Made from |
|---|---|---|---|
| `calcs_block` | `CalcsBlock` | `lines` | consecutive calc/expr lines (by `group_lines`) |
| `comments_block` | `CommentsBlock` | `lines` | consecutive comment lines |
| `params_block` | `ParamsBlock` | `lines`, `with_comments` | `;` lines, or `# hc: -h` |
| `elif_block` | `ElifBlock` | `lines`: the `IfBlock`s of the chain, then an optional `ElseBlock` | an `if` statement |
| `if_block` | `IfBlock` | `test`, `lines`, `is_true` (did this branch run) | one `if`/`elif` branch |
| `else_block` | `ElseBlock` | `lines` | the `else` branch |
| `for_block` | `ForBlock` | `assigns` (loop variables), `iterator`, `lines` | a `for` loop |
| `function_block` | `FunctionBlock` | `function_name`, `params`, `lines` | a function definition (not rendered in 2.0) |

### Expressions

Defined in {src}`handcalcs.parsing.nodes`, {src}`handcalcs.parsing.inline_nodes` and
{src}`handcalcs.parsing.operator_nodes`.

| `type` | Class | Attributes |
|---|---|---|
| `name` | `Name` | `identifier`, `value` (`NoValue()` if none was captured) |
| `attribute` | `Attribute` | `namespace` (e.g. `"math"`), `identifier`, `value` |
| `constant` | `Constant` | `value` |
| `list`, `tuple`, `set` | `List`, `Tuple`, `Set` | `elems` |
| `dictionary` | `Dictionary` | `keys`, `values` |
| `subscript` | `Subscript` | `container` (a node), `index` (one node per dimension), `labels` (each index as `(text, is_name)` when the container is a name and every index is an integer, a short string or a name, else `None`), `value` (the element, or `NoValue()`) |
| `slice` | `Slice` | `lower`, `upper`, `step` (nodes, or `None` for a missing part) |
| `function_call` | `FunctionCall` | `function_name` (a `Name`), `namespace`, `args`, `pre`/`post` (the argument delimiters) |
| `keyword` | `Keyword` | `arg` (`None` for `**mapping`), `value` |
| `compare` | `Compare` | `comparison`: operands and comparison operators, in order |
| `if_exp` | `IfExp` | `test`, `body`, `orelse`, `is_true` (the test's value, or `None`) |
| `comprehension_chain` | `ComprehensionChain` | `comp_type` (`list`, `set`, `dict`, `generator`), `assign`, `key`, `value`, `comprehensions` |
| `comprehension` | `Comprehension` | `assigns`, `iterator`, `is_async` |
| `inline_comment` | `InlineComment` | `content` |
| `inline_command` | `InlineCommand` | `content`, `commands` |
| `no_value` | `NoValue` | (none) |

### Operators

Every operator has `symbol` (initially the Python symbol) and `pre`/`post` strings, which
the built-in handlers place around the rendered operation.

| `type` | Class | Attributes |
|---|---|---|
| `add_op`, `sub_op`, `mult_op`, `mat_mult_op`, `div_op`, `floor_op`, `modulo_op`, `pow_op` | `AddOp`, ... (`HcBinOp`) | `left`, `right` |
| `unary_op` | `HcUnaryOp` | `operand`, `symbol` (`-`, `+`, `not`, `~`) |
| `and_op`, `or_op` | `AndOp`, `OrOp` (`HcBoolOp`) | `values` |
| `lt_op`, `gt_op`, `lte_op`, `gte_op`, `eq_op`, `neq_op`, `is_op`, `is_not_op`, `in_op`, `not_in_op` | `LtOp`, ... (`HcCompOp`) | `symbol` only; they sit inside a `Compare` |

### The root

The root is an {src}`HcSequence <handcalcs.parsing.sequence.HcSequence>` with
`type = "root"` and the top-level nodes in `sequence`. `render_root` handles it; it is
not dispatched to a handler, but you can register `root:pre` and `root:post` rules to add
items at the start and end of the output.

## Values

A `Name` (or `Attribute`) carries its value in `value`. A value can be any Python object;
the built-in `name` handler renders it in numeric mode by turning it into a `Constant`
(or a collection node) and rendering that, so the `constant` handler is where values are
formatted.

`NoValue()` marks a name without a value (not in the namespace). It renders as an empty
string.

**Next:** [Handlers and rules](registration.md).
