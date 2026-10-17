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
| `-h` | `--params-block`, `--params` | (opens a grid) | flag | Grid of the following assignments, with comments |
| `-c N` | `--param-cols`, `--param_cols` | `param_cols` | integer | Columns in parameter grids (default 3) |
| `-b` | `--line-break` | (one-shot) | flag | Vertical space |
| `-i` | `--ignore` | `ignore` | flag | Leave lines out of the output |
| `-w` | `--if-winner-only`, `--winner` | `if_winner_only` | flag | Accepted; no effect in 2.0 |

Source: {src}`handcalcs.parsing.commands`.

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
| any other name | stored on the context for custom renderers |
