# Coming from handcalcs v1

handcalcs v2 is a rewrite. The parser now builds a tree of nodes, and separate
**renderers** turn that tree into Markdown, LaTeX, HTML, plain text or Excel. Most
notebooks need only a few changes.

## Quick reference

| v1 | v2 |
|---|---|
| `import handcalcs.render` | `import handcalcs` |
| `%%render` | `%%render` (now shows Markdown with LaTeX math by default) |
| `%%tex` | `%hc_default_renderer latex`, then `%%render`; or `HandCalcs(LatexRenderer())` |
| `%%render 2` (precision) | `# hc: -f .2f` (any [format code](formatting-numbers.md)) |
| `%%render params` | `;` [parameter grids](writing-calculations.md#parameter-grids), or `# hc: -h`; `# hc: -p` for one line |
| `%%render long` | `# hc: -m` |
| `%%render short` | the default (or `# hc: multiline = False`) |
| `%%render symbolic` | `# hc: mode = "ass sym"` (see [mode](comment-commands.md#choosing-which-steps-appear-mode)) |
| `%%render sympy` | not available in 2.0 |
| `from handcalcs.decorator import handcalc` | `from handcalcs import handcalc` |
| `@handcalc(override=..., precision=..., ...)` | `@handcalc(renderer, render_context={...})` (see [the decorator](../interfaces/decorator.md)) |
| `handcalcs.set_option("display_precision", 3)` | `handcalcs.set_option("format_code", ".3f")` |
| `latex_block_start`, `line_break`, `math_environment_start`, ... options | renderer class attributes (see [LaTeX and Markdown tokens](../customizing/latex-markdown-tokens.md)) |
| `custom_symbols` option | a renderer rule (see [Symbols and functions](../customizing/symbols-and-functions.md)) |
| `greek_exclusions`, `underscore_subscripts` options | a renderer subclass (see [Customizing](../customizing/index.md)) |

## What's new

- **Renderers.** Choose the output format, restyle it, or
  [write your own](../building-renderers/index.md).
- **A Python interface.** `HandCalcs(renderer)(source)` renders a string or a `.py`
  file outside Jupyter (see [the object-oriented interface](../interfaces/object-oriented.md)).
- **Comment commands.** `# hc:` commands work per line or per section, instead of one
  override per cell.
- **Headings and prose.** `##` comments become headings and comment lines become
  paragraphs, so a single cell can hold a whole documented calculation.
- **Jinja in comments.** `{{ name }}` inserts a value into a comment.
- **Nested conditionals** and `for` loops.
- **Excel output** with live formulas (see [the Excel renderer](../renderers/excel.md)).

## Global options that were removed

The v1 options `decimal_separator`, `latex_block_start`, `latex_block_end`,
`math_environment_start`, `math_environment_end`, `line_break`,
`use_scientific_notation`, `display_precision`, `underscore_subscripts`,
`greek_exclusions`, `param_columns`, `preferred_string_formatter` and `custom_symbols`
no longer exist. v2 has three options (`format_code`, `default_renderer`,
`jupyter_renderer`) plus any [custom options](configuration.md#custom-options); the rest
is controlled by the renderer.

An old `config.json` from v1 is not read; v2 stores its configuration in a new location
(see [Configuration](configuration.md#the-config-file)).
