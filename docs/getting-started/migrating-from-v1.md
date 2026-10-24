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
| `custom_symbols` option | the `symbols` option with renderer-neutral specs (see [display symbols](writing-calculations.md#display-symbols)), or a renderer rule for raw markup. A `symbols` key matches a whole variable name, not part of one: `{"star": "^*"}` no longer changes `Mstar_1`, so give each name its own entry (`{"Mstar_1": "M^{*}_{1}"}`) |
| `custom_brackets` option | not available in 2.0. Index the value instead (`x[1]` is shown as x<sub>1</sub>, see [indexing](writing-calculations.md#indexing)), or give the name a `symbols` entry |
| `greek_exclusions`, `underscore_subscripts` options | the `greek_prefixes`/`subscripts` settings, or a renderer subclass (see [Customizing](../customizing/index.md)) |

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
- **Better names.** Comma subscripts (`N_pl_Rd` → N<sub>pl,Rd</sub>), Greek letters joined
  to other letters (`DeltaH` → ΔH), accents (`V_dot` → V̇) and display specs (the
  `symbols` option). See [naming variables](writing-calculations.md#naming-variables).
- **Long equations** break where the source line continues with `\`, and a bare
  expression line shows its result (see [writing calculations](writing-calculations.md)).
- **`%render`**, a line magic that runs and renders one line (see
  [Jupyter](../interfaces/jupyter.md)).
- **Checks and page breaks.** `# hc: --check` marks a comparison ✓ or ✗, and
  `# hc: --pagebreak` starts a new page in exported output (see the
  [cookbook](../cookbook/index.md)).
- **More Python.** Conditional expressions (`a if test else b`), methods on expressions
  (`(a * b).to("mm")`), `cbrt`, `factorial` and infinity.
- **Text output** for terminals and logs from `ASCIIRenderer` (`ascii`), with underlined
  headings and `=` signs lined up (see [the ASCII renderer](../renderers/ascii.md)). If
  you tried a 2.0 pre-release, this is the renderer that was called `PlainTextRenderer`
  (`plain_text`).
- **Word output** with native equations (see [the Word renderer](../renderers/word.md)).
- **Many input sets.** Render one script for a table of inputs with
  `HandCalcs(...)(path, inputs=...)` or `%%render inputs=case`.

## Converting a cell

A v1 cell with cell-wide overrides:

```python
%%render params 2
b = 300
h = 600
```

```python
%%render long 2
I_x = b * h**3 / 12
S_x = I_x / (h / 2)
```

becomes one v2 cell, with each setting where it applies:

```{hc-example}
## Section properties
# hc: -f .2f
b = 300; h = 600
I_x = b * h**3 / 12   # hc: -m
S_x = I_x / (h / 2)
```

The heading and the `;` grid replace a separate `params` cell, and `-m` applies to the
one long line rather than the whole cell.

## Names that render differently

| v1 | v2 | To get the v1 output |
|---|---|---|
| `x_a_b` → x<sub>a<sub>b</sub></sub> (nested) | x<sub>a,b</sub> (comma) | `handcalcs.set_option("subscripts", "nested")` |
| `PiD`, `phiM`, `eta2`, `chi2` shown as words | ΠD, φM, η2, χ2: a Greek name before an uppercase letter or digit is a letter | `set_option("greek_prefixes", False)`, or `# hc: greek_prefixes = False` |
| `x_hat`, `p_bar`, `V_dot`, `M_star` as subscripts | accents and `*` | a `symbols` entry, e.g. `{"p_bar": "p_{bar}"}` |
| `ΔH` (Unicode) failed under pdflatex | `\Delta H` | — |

## Global options that were removed

The v1 options `decimal_separator`, `latex_block_start`, `latex_block_end`,
`math_environment_start`, `math_environment_end`, `line_break`,
`use_scientific_notation`, `display_precision`, `underscore_subscripts`,
`greek_exclusions`, `param_columns`, `preferred_string_formatter`, `custom_symbols` and
`custom_brackets` no longer exist. v2 has four options (`format_code`, `default_renderer`,
`jupyter_renderer`, `line_values`) plus any [custom options](configuration.md#custom-options); the rest
is controlled by the renderer.

An old `config.json` from v1 is not read; v2 stores its configuration in a new location
(see [Configuration](configuration.md#the-config-file)).
