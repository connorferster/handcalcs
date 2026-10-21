# Repository layout

## `src/handcalcs`

| Module | Contents |
|---|---|
| {src}`handcalcs` | The public API: `HandCalcs`, `handcalc`, the config functions, `BaseRenderer`, `get_renderer`. Imports the Jupyter interface when IPython is available. |
| {src}`handcalcs.config` | Global options: defaults, `set_option`/`save_config`, the config file location (`platformdirs`, `HANDCALCS_CONFIG`). |

### `interfaces/`

| Module | Contents |
|---|---|
| {src}`handcalcs.interfaces.object_oriented` | `HandCalcs`: read source or a path, run it, parse, render, complete; `demo()`. |
| {src}`handcalcs.interfaces.decorator` | `@handcalc`: run the function with innerscope, parse its source, render. |
| {src}`handcalcs.interfaces.jupyter` | `%%render`, `%hc_default_renderer`, `%hc_format_code`; the display class for each renderer. Only importable inside IPython. |

### `parsing/`

| Module | Contents |
|---|---|
| {src}`handcalcs.parsing.line_values` | Records each statement's values while the source runs. |
| {src}`handcalcs.parsing.ast_parser` | `AST_Parser`: Python `ast` → handcalcs nodes, comment classification, parameter grids. The largest module. |
| {src}`handcalcs.parsing.sequence` | `HcSequence` (the root) and the post-parse passes: `convert_if_tree`, `group_lines`, `set_levels`. |
| {src}`handcalcs.parsing.nodes` | Value nodes: `Name`, `Attribute`, `Constant`, collections. |
| {src}`handcalcs.parsing.line_nodes` | `CalcLine`, `ExprLine`, `CommentLine`, `Heading`, `CommentCommand`, `Import`. |
| {src}`handcalcs.parsing.block_nodes` | `IfBlock`, `ElifBlock`, `ElseBlock`, `ForBlock`, `ParamsBlock`, `CalcsBlock`, `CommentsBlock`. |
| {src}`handcalcs.parsing.inline_nodes` | `FunctionCall`, `Keyword`, `Compare`, `InlineComment`, `InlineCommand`, comprehensions. |
| {src}`handcalcs.parsing.operator_nodes` | Binary, unary, comparison and boolean operators. |
| {src}`handcalcs.parsing.comment_parser` | Is a comment a heading, a command? Splitting and executing command text. |
| {src}`handcalcs.parsing.commands` | The `argparse` parser for `# hc:` flags. |
| {src}`handcalcs.parsing.null_values` | `NoValue`, `HcNotImplemented`. |

### `renderers/`

| Module | Contents |
|---|---|
| {src}`handcalcs.renderers.base` | `RenderContext`, `BaseRenderContext`, the registry, `BaseRenderer` and every base handler and rule. The core of the package. |
| {src}`handcalcs.renderers.identifiers` | Identifier parsing shared by every renderer: the Greek table, `parse_identifier` (→ `Symbol` tree), `parse_spec` for the `symbols` option, `identifier_options`. |
| {src}`handcalcs.renderers.ascii` | `ASCIIRenderer`. |
| {src}`handcalcs.renderers.latex` | `LatexRenderer`, `latex_identifier`, `latex_prose`, the symbol tables. |
| {src}`handcalcs.renderers.markdown` | `MarkdownRenderer` (subclass of `LatexRenderer`). |
| {src}`handcalcs.renderers.html` | `HTMLRenderer` and its stylesheet. |
| {src}`handcalcs.renderers.excel` | `ExcelRenderer`, split into `renderer`, `formulas`, `names`, `rows`, `conditionals`, `units`, `writer`, `symbolic`, `rich_text`, `number_formats`, `evaluate`, `compat`, `options`. |
| {src}`handcalcs.renderers.demo` | The source rendered by `HandCalcs.demo()`. |

## Elsewhere

| Path | Contents |
|---|---|
| `tests/` | The pytest suite (see [Tests](testing.md)). |
| `tests/golden/` | Golden output files for the LaTeX and Markdown renderers. |
| `scripts/` | `latex_demo_check.py` (compile the demo with pdflatex, report overfull boxes), `markdown_demo_check.py`, `excel_demo.py`. |
| `docs/` | These docs. `_ext/` holds the local Sphinx extensions, `_examples/` the example renderers the docs run. |
| `.github/workflows/` | CI: tests on Linux/macOS/Windows × Python 3.11–3.14; publish to PyPI on release. |
