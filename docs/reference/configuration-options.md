# Configuration options

| Option | Type | Default | Used by |
|---|---|---|---|
| `format_code` | `str` | `".5g"` | every renderer (via the render context) |
| `default_renderer` | `str` | `"base"` | `HandCalcs()` with no renderer |
| `jupyter_renderer` | `str` | `"markdown"` | `%%render` (also set by `%hc_default_renderer`) |
| `subscripts` | `str` | the renderer's (`"comma"`) | the built-in renderers: `"comma"` or `"nested"` subscripts |
| `symbols` | `dict` | (none) | the built-in renderers: display specs for names |
| `greek_prefixes` | `bool` | the renderer's (`True`) | the built-in renderers: `DeltaH` → ΔH |
| `hidden_by_default` | `bool` | `False` | every renderer: start hidden, as after `# hc: -i` |
| any other name | any | (none) | copied onto the render context of every render |

The three base options (`format_code`, `default_renderer`, `jupyter_renderer`) must be
strings. `subscripts`, `symbols` and `greek_prefixes` are ordinary context fields: they
are copied onto the render context like any other name, and the built-in renderers read
them (an invalid `subscripts` value raises `ValueError` when rendering). `default_renderer` and `jupyter_renderer` are
not copied onto the render context.

## Files and environment

| | |
|---|---|
| Config file | `hc_config.json` in the per-user config directory (`platformdirs.user_config_dir("handcalcs")`) |
| Override | `HANDCALCS_CONFIG=/path/to/file.json` |
| Loaded | once, when `handcalcs` is imported |
| Copied | by each `HandCalcs` object when it is created, and by `@handcalc` when it decorates |

Source: {src}`handcalcs.config`. Guide: [Configuration](../getting-started/configuration.md).
