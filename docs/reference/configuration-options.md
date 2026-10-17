# Configuration options

| Option | Type | Default | Used by |
|---|---|---|---|
| `format_code` | `str` | `".5g"` | every renderer (via the render context) |
| `default_renderer` | `str` | `"base"` | `HandCalcs()` with no renderer |
| `jupyter_renderer` | `str` | `"markdown"` | `%%render` (also set by `%hc_default_renderer`) |
| any other name | any | (none) | copied onto the render context of every render |

The three built-in options must be strings. `default_renderer` and `jupyter_renderer` are
not copied onto the render context.

## Files and environment

| | |
|---|---|
| Config file | `hc_config.json` in the per-user config directory (`platformdirs.user_config_dir("handcalcs")`) |
| Override | `HANDCALCS_CONFIG=/path/to/file.json` |
| Loaded | once, when `handcalcs` is imported |
| Copied | by each `HandCalcs` object when it is created, and by `@handcalc` when it decorates |

Source: {src}`handcalcs.config`. Guide: [Configuration](../getting-started/configuration.md).
