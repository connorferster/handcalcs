# Node types

Every node `type` string the parser produces, with its class. A renderer registers
handlers and rules under these strings. The [Nodes](../building-renderers/nodes.md)
page explains what each node represents.

| `type` | Class | Attributes |
|---|---|---|
| `calc_line` | {src}`CalcLine <handcalcs.parsing.line_nodes.CalcLine>` | `assigns`, `expression_tree`, `comment`, `pars_nesting` |
| `expr_line` | {src}`ExprLine <handcalcs.parsing.line_nodes.ExprLine>` | `expression_tree`, `comment`, `return_expr`, `pars_nesting` |
| `comment_line` | {src}`CommentLine <handcalcs.parsing.line_nodes.CommentLine>` | `content` |
| `heading` | {src}`Heading <handcalcs.parsing.line_nodes.Heading>` | `content`, `heading_level` |
| `comment_command` | {src}`CommentCommand <handcalcs.parsing.line_nodes.CommentCommand>` | `commands` |
| `import` | {src}`Import <handcalcs.parsing.line_nodes.Import>` | `import_from`, `names`, `import_from_module`, `import_from_level` |
| `params_block` | {src}`ParamsBlock <handcalcs.parsing.block_nodes.ParamsBlock>` | `lines`, `with_comments` |
| `comments_block` | {src}`CommentsBlock <handcalcs.parsing.block_nodes.CommentsBlock>` | `lines` |
| `calcs_block` | {src}`CalcsBlock <handcalcs.parsing.block_nodes.CalcsBlock>` | `lines` |
| `for_block` | {src}`ForBlock <handcalcs.parsing.block_nodes.ForBlock>` | `lines`, `assigns`, `iterator` |
| `if_block` | {src}`IfBlock <handcalcs.parsing.block_nodes.IfBlock>` | `lines`, `test`, `orelse`, `is_true` |
| `else_block` | {src}`ElseBlock <handcalcs.parsing.block_nodes.ElseBlock>` | `lines` |
| `elif_block` | {src}`ElifBlock <handcalcs.parsing.block_nodes.ElifBlock>` | `lines` |
| `name` | {src}`Name <handcalcs.parsing.nodes.Name>` | `identifier`, `value` |
| `constant` | {src}`Constant <handcalcs.parsing.nodes.Constant>` | `value` |
| `attribute` | {src}`Attribute <handcalcs.parsing.nodes.Attribute>` | `namespace`, `identifier`, `value` |
| `list` | {src}`List <handcalcs.parsing.nodes.List>` | `elems` |
| `tuple` | {src}`Tuple <handcalcs.parsing.nodes.Tuple>` | `elems` |
| `set` | {src}`Set <handcalcs.parsing.nodes.Set>` | `elems` |
| `dictionary` | {src}`Dictionary <handcalcs.parsing.nodes.Dictionary>` | `keys`, `values` |
| `subscript` | {src}`Subscript <handcalcs.parsing.nodes.Subscript>` | `container`, `index`, `labels`, `value` |
| `slice` | {src}`Slice <handcalcs.parsing.nodes.Slice>` | `lower`, `upper`, `step` |
| `function_call` | {src}`FunctionCall <handcalcs.parsing.inline_nodes.FunctionCall>` | `namespace`, `function_name`, `args` |
| `keyword` | {src}`Keyword <handcalcs.parsing.inline_nodes.Keyword>` | `arg`, `value` |
| `compare` | {src}`Compare <handcalcs.parsing.inline_nodes.Compare>` | `comparison` |
| `if_exp` | {src}`IfExp <handcalcs.parsing.inline_nodes.IfExp>` | `test`, `body`, `orelse`, `is_true` |
| `inline_comment` | {src}`InlineComment <handcalcs.parsing.inline_nodes.InlineComment>` | `content` |
| `inline_command` | {src}`InlineCommand <handcalcs.parsing.inline_nodes.InlineCommand>` | `content`, `commands` |
| `comprehension` | {src}`Comprehension <handcalcs.parsing.inline_nodes.Comprehension>` | `assigns`, `iterator`, `is_async` |
| `comprehension_chain` | {src}`ComprehensionChain <handcalcs.parsing.inline_nodes.ComprehensionChain>` | `comp_type`, `assign`, `key`, `value`, `comprehensions` |
| `pow_op` | {src}`PowOp <handcalcs.parsing.operator_nodes.PowOp>` | `left`, `right`, `symbol` |
| `div_op` | {src}`DivOp <handcalcs.parsing.operator_nodes.DivOp>` | `left`, `right`, `symbol` |
| `floor_op` | {src}`FloorOp <handcalcs.parsing.operator_nodes.FloorOp>` | `left`, `right`, `symbol` |
| `modulo_op` | {src}`ModuloOp <handcalcs.parsing.operator_nodes.ModuloOp>` | `left`, `right`, `symbol` |
| `mult_op` | {src}`MultOp <handcalcs.parsing.operator_nodes.MultOp>` | `left`, `right`, `symbol` |
| `mat_mult_op` | {src}`MatMultOp <handcalcs.parsing.operator_nodes.MatMultOp>` | `left`, `right`, `symbol` |
| `add_op` | {src}`AddOp <handcalcs.parsing.operator_nodes.AddOp>` | `left`, `right`, `symbol` |
| `sub_op` | {src}`SubOp <handcalcs.parsing.operator_nodes.SubOp>` | `left`, `right`, `symbol` |
| `unary_op` | {src}`HcUnaryOp <handcalcs.parsing.operator_nodes.HcUnaryOp>` | `operand`, `symbol` |
| `eq_op` | {src}`EqOp <handcalcs.parsing.operator_nodes.EqOp>` | `symbol` |
| `neq_op` | {src}`NeqOp <handcalcs.parsing.operator_nodes.NeqOp>` | `symbol` |
| `gt_op` | {src}`GtOp <handcalcs.parsing.operator_nodes.GtOp>` | `symbol` |
| `gte_op` | {src}`GtEOp <handcalcs.parsing.operator_nodes.GtEOp>` | `symbol` |
| `lt_op` | {src}`LtOp <handcalcs.parsing.operator_nodes.LtOp>` | `symbol` |
| `lte_op` | {src}`LtEOp <handcalcs.parsing.operator_nodes.LtEOp>` | `symbol` |
| `is_op` | {src}`IsOp <handcalcs.parsing.operator_nodes.IsOp>` | `symbol` |
| `is_not_op` | {src}`IsNotOp <handcalcs.parsing.operator_nodes.IsNotOp>` | `symbol` |
| `in_op` | {src}`InOp <handcalcs.parsing.operator_nodes.InOp>` | `symbol` |
| `not_in_op` | {src}`NotInOp <handcalcs.parsing.operator_nodes.NotInOp>` | `symbol` |
| `and_op` | {src}`AndOp <handcalcs.parsing.operator_nodes.AndOp>` | `values`, `symbol` |
| `or_op` | {src}`OrOp <handcalcs.parsing.operator_nodes.OrOp>` | `values`, `symbol` |
| `no_value` | {src}`NoValue <handcalcs.parsing.null_values.NoValue>` | (none) |
| `not_implemented` | {src}`HcNotImplemented <handcalcs.parsing.null_values.HcNotImplemented>` | `node_name` |
| `root` | {src}`HcSequence <handcalcs.parsing.sequence.HcSequence>` | `sequence`, `hc_globals`, `hc_locals` |

All line nodes also have `level`, `pre` and `post`; all block nodes have `level`,
`header_pre`, `header_post`, `body_pre` and `body_post`; operators have `pre` and `post`.
