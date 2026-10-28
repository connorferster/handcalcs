# Comment commands

A comment starting with `hc:` is a command. On its own line it applies to every following
line; at the end of a line it applies to that line. See
[the guide](../getting-started/comment-commands.md) for examples.

## Flags

| Flag | Long forms | Context field | Value | Effect |
|---|---|---|---|---|
| `-f CODE` | `--format-code` | `format_code` | a format code | Number format |
| `-m` | `--multiline`, `--mult` | `multiline` | flag | Break calculations over several lines |
| `-p` | `--param-line` | `param_line` | flag | Show *target = result* only |
| `-g` | `--grid`, `--params-block`, `--params` | (opens a grid) | flag | Grid of the following assignments, with comments |
| `-c N` | `--param-cols`, `--param_cols` | `param_cols` | integer | Columns in parameter grids (default 3) |
| `-b` | `--line-break` | (one-shot) | flag | Vertical space |
| | `--check` | `check` | flag | A boolean result is shown as a pass/fail mark (`CHECK_MARKS`) |
| | `--pagebreak`, `--page-break` | (one-shot) | flag | Page break (see below) |
| `-i` | `--ignore` | `ignore` | flag | Leave lines out of the output |
| `-w` | `--if-winner-only`, `--winner` | `if_winner_only` | flag | Accepted; no effect in 2.0 |

Source: {src}`handcalcs.parsing.commands`.

### Page breaks

`# hc: --pagebreak` on its own line breaks the page before the next line; at the end of
a line it breaks after that line. It is one-shot and never carried forward. It does
nothing at the end of a block header (`if ...:`) or inside a `;` parameter line.

| Renderer | Output (class attribute `PAGE_BREAK`) |
|---|---|
| ASCII | a line holding a form feed (`\f`) |
| LaTeX | `\newpage` |
| Markdown | `<div style="break-after: page;"></div>` (takes effect when printed or converted through HTML) |
| HTML | `<div class="hc-page-break" style="break-after: page;"></div>` |
| Word | a page break |
| Excel | a horizontal print page break after the row |

A custom renderer receives the break as the item `handcalcs.renderers.base.PAGE_BREAK`
(`"\f"`) in `join_item`.

## Assignment form

`# hc: name = value[; name = value ...]` sets context fields directly. The text is run as
Python; if that fails, it is parsed as flags.

| Field | Values |
|---|---|
| `format_code` | a format code string |
| `mode` | `"full"`, or a string containing any of `ass`, `sym`, `num`, `res` |
| `multiline`, `param_line`, `ignore` | `True` / `False` |
| `param_cols` | integer |
| `assign` | the symbol between steps (default `"="`) |
| `subscripts` | `"comma"` or `"nested"` |
| `symbols` | a dict of name → display spec, e.g. `{"N_plRd": "N_{pl,Rd}"}` |
| `greek_prefixes` | `True` / `False` |
| `check` | `True` / `False` |
| any other name | stored on the context for custom renderers |
