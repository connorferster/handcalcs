# Configuration

handcalcs has a small global configuration. Change it for the current session with
`set_option`, and make the change permanent with `save_config`.

```python
import handcalcs

handcalcs.set_option("format_code", ".3g")   # this session
handcalcs.save_config()                      # and every session after
```

## Options

| Option | Default | Used by |
|---|---|---|
| `format_code` | `".5g"` | Every renderer: the default [number format](formatting-numbers.md). |
| `default_renderer` | `"base"` | `HandCalcs()` with no renderer argument. The name of a [renderer](../renderers/index.md). |
| `jupyter_renderer` | `"markdown"` | The `%%render` cell magic. Also set by `%hc_default_renderer`. |

Renderer names are `base`, `plain_text`, `latex`, `markdown`, `html` and `excel`, plus the
name of any custom renderer that has been imported.

### Custom options

Any other option name is accepted, with any value:

```python
handcalcs.set_option("highlight_results", True)
```

Every option except `default_renderer` and `jupyter_renderer` is copied onto the
**render context** of every render. Built-in renderers ignore names they don't know; a
[custom renderer](../building-renderers/render-context.md) can read them. This is how a
renderer gets settings that differ per user or per project.

## Functions

All of these are available from the top-level `handcalcs` package.

`set_option(option, value)`
: Set an option for the current session. The three built-in options must be strings.

`get_option(option, default=None)`
: The current value of an option.

`get_config()`
: A copy of the whole configuration, as a `dict`.

`reset_option(option)`
: Restore a built-in option to its default, or remove a custom option. Session only.

`reset_config()`
: Restore every option to the defaults. Session only.

`save_config()`
: Write the current configuration to the config file, so it loads automatically next
  time handcalcs is imported.

```{important}
The configuration is read **when handcalcs is imported**, and each `HandCalcs` object
copies it **when it is created**. Set options before creating the `HandCalcs` objects
that should use them.
```

## The config file

`save_config()` writes JSON to the per-user config directory for your operating system:

| OS | Location |
|---|---|
| Linux | `~/.config/handcalcs/hc_config.json` |
| macOS | `~/Library/Application Support/handcalcs/hc_config.json` |
| Windows | `%LOCALAPPDATA%\handcalcs\hc_config.json` |

To use a different file, for example one per project, set the `HANDCALCS_CONFIG`
environment variable to its path before importing handcalcs.

A missing file is normal (the defaults are used). A file that cannot be read produces a
warning and the defaults.

**Next:** [Units](units.md).
