# The parser

The parser turns source code and a namespace into the node tree described in
[Nodes](../building-renderers/nodes.md). Entry point:
{src}`HcSequence.from_source <handcalcs.parsing.sequence.HcSequence.from_source>`.

## `AST_Parser`

{src}`AST_Parser <handcalcs.parsing.ast_parser.AST_Parser>` is a dataclass holding the
namespace (`globals`) and some parse state. Calling it with source:

1. **Classifies comments** ({src}`_classify_comments <handcalcs.parsing.ast_parser.AST_Parser._classify_comments>`).
   Using `tokenize`, it records every *standalone* comment (one on a line with no code)
   by line number, and every blank line. Inline comments are not collected here.
2. **Parses** the source with [`pfst`](https://pypi.org/project/pfst/) (imported as
   `ast`). pfst produces standard `ast` nodes that also keep their formatting, which is
   how the parser reads a statement's trailing comment (`node.f.get_line_comment()`).
3. **Walks the tree** with
   {src}`ast_parse <handcalcs.parsing.ast_parser.AST_Parser.ast_parse>`, one `isinstance`
   branch per supported `ast` node type, each returning a handcalcs node.

### Bodies and comments

A statement list (the module, an `if` branch, a loop body) goes through
{src}`_parse_body <handcalcs.parsing.ast_parser.AST_Parser._parse_body>`, which:

- inserts the standalone comments that come before each statement
  ({src}`_flush_comment_lines <handcalcs.parsing.ast_parser.AST_Parser._flush_comment_lines>`),
  each becoming a `Heading`, `CommentCommand` or `CommentLine`
  ({src}`_make_comment_line <handcalcs.parsing.ast_parser.AST_Parser._make_comment_line>`);
- gathers `;`-separated assignments that share a line into a `ParamsBlock`;
- after a `# hc: -g` command, gathers the following assignments into a `ParamsBlock`
  with comments, stopping at a blank line, a comment or a non-assignment.

Because comments are attached *before* the next statement, a comment after the last
statement of a body has no statement to attach to.

### Values

A `Name` gets its value from `self.globals`; an `Attribute` looks up its namespace and
then the attribute.

While the source runs, {src}`LineValues <handcalcs.parsing.line_values.LineValues>`
records a {src}`StatementValues <handcalcs.parsing.line_values.StatementValues>`
(`before`, `after`) for each statement, keyed by the statement's first line (for a
statement in a loop, during the last pass). It watches the line events of the source's
own frames only: `sys.monitoring` on Python 3.12+ (so library code runs untraced),
`sys.settrace` on 3.11. A new statement starting is the one moment anything is recorded:
one snapshot is both the `after` of the statement that ended and the `before` of the one
that starts. Only names the source assigns can change while it runs, so a snapshot holds
only those that the two statements use (plus names in `{{ }}` in comments). Values are
not copied. With the `line_values` option off, the source runs with a single `exec` and
nothing is recorded.

The parser switches `self.globals` as it goes: before parsing a statement, to the values
from just before it ran (an expression's operands, an `if` test, a loop's iterable);
before parsing an assignment's targets, to the values from just after it. A statement
with no recorded values (a branch that did not run, or a namespace supplied without
running the source) uses the namespace after the run.

### Unsupported syntax

An `ast` node with no branch in `ast_parse` becomes `NoValue()` and renders as nothing
(or `HcNotImplemented` when `show_notimplemented` is set). This is why function
definitions, `while` loops and `try` blocks silently disappear.

Two statements are rewritten instead. An `ast.AugAssign` (`a += b`) becomes a `CalcLine`
for `a = a + b`: its right side is parsed with the values from before the line, its target
with the values after. `_parse_body` replaces an `ast.With` (or `ast.AsyncWith`) with the
nodes of its body.

### Comment commands

{src}`CommentCommand.from_raw_comment <handcalcs.parsing.line_nodes.CommentCommand.from_raw_comment>`
(standalone) and
{src}`InlineCommand.from_raw_comment <handcalcs.parsing.inline_nodes.InlineCommand.from_raw_comment>`
(inline) first try the text as Python assignments
({src}`parse_kwargs <handcalcs.parsing.comment_parser.parse_kwargs>`, which `exec`s it);
if that fails with a `SyntaxError` or `NameError`, they parse it as flags with the
{src}`argparse parser <handcalcs.parsing.commands>`. Either way the result is a dict
stored on `commands`.

## Post-parse passes

{src}`HcSequence.from_source <handcalcs.parsing.sequence.HcSequence.from_source>` then
runs three passes over the tree:

| Pass | Does |
|---|---|
| {src}`convert_if_tree <handcalcs.parsing.sequence.convert_if_tree>` | Python's AST nests `elif` as an `if` inside `orelse`. This flattens each chain into an `ElifBlock` whose `lines` are the `IfBlock`s and an optional `ElseBlock`. |
| {src}`group_lines <handcalcs.parsing.sequence.group_lines>` | Wraps runs of consecutive calc/expr lines in a `CalcsBlock`, and of comment lines in a `CommentsBlock`, recursively. Headings, commands, imports and blocks end a run. |
| `set_levels` | Sets `level` on every node to its nesting depth. Flat blocks (`ElifBlock`, `ParamsBlock`, `CalcsBlock`, `CommentsBlock`) don't add a level. |

## Which branch ran

An `IfBlock` records `is_true`: whether its test was true, evaluated with the values from
just before the `if` ran (see [Values](#values)). The base `elif_block` handler renders only the first true branch
(or the `else`), which is how the output shows only the reasoning that applies.
