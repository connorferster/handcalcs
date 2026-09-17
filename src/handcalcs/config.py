"""
Global, user-editable configuration for handcalcs.

A designer can permanently change a small number of handcalcs defaults so that a
bare ``HandCalcs()`` behaves the way they prefer. The configuration is a JSON file
stored in the per-user config location for the operating system (resolved by
``platformdirs``), e.g. ``~/.config/handcalcs/config.json`` on Linux.

Two base options are recognised:

- ``default_renderer``: the ``name`` of the renderer a bare ``HandCalcs()`` uses.
- ``format_code``: the default float format code used for all values, unless a
  comment command (e.g. ``# hc: -f .3g``) overrides it for a line/block.

In addition, arbitrary extra fields may be set. These are ignored by the base
renderer but are threaded onto the render context when rendering, so a custom
renderer can read session-dependent settings a designer has configured.

Typical use::

    import handcalcs
    handcalcs.set_option("format_code", ".2f")
    handcalcs.save_config()   # make it the permanent default
"""

import json
import os
import pathlib
import warnings
from copy import deepcopy
from typing import Any

import platformdirs

# Built-in defaults. These mirror the implicit v2 defaults: a bare HandCalcs() uses
# the 'base' renderer and RenderContext's format_code defaults to '.5g'.
DEFAULTS: dict[str, Any] = {
    "default_renderer": "base",
    "format_code": ".5g",
}

# The base options whose value type is validated by set_option (both strings).
# Any other option name is accepted with any value so that custom renderers can
# store arbitrary session-dependent settings.
_BASE_OPTION_TYPES: dict[str, type] = {
    "default_renderer": str,
    "format_code": str,
}

# Environment variable that overrides the config file location (used by tests and
# power users who want a project-local config).
_CONFIG_ENV_VAR = "HANDCALCS_CONFIG"


def config_path() -> pathlib.Path:
    """
    Return the path to the config JSON file.

    Honors the ``HANDCALCS_CONFIG`` environment variable if set; otherwise resolves
    the per-user config directory via ``platformdirs``.
    """
    override = os.environ.get(_CONFIG_ENV_VAR)
    if override:
        return pathlib.Path(override)
    config_dir = platformdirs.user_config_dir("handcalcs", appauthor=False)
    return pathlib.Path(config_dir) / "config.json"


def _load_config() -> dict[str, Any]:
    """
    Return the built-in defaults overlaid with any values found in the config file.

    A missing file is normal (the defaults are used). A malformed file warns and
    falls back to the defaults rather than crashing on import.
    """
    config = deepcopy(DEFAULTS)
    path = config_path()
    if not path.exists():
        return config
    try:
        with open(path, "r") as config_file:
            file_data = json.load(config_file)
        if isinstance(file_data, dict):
            config.update(file_data)
        else:
            warnings.warn(
                f"handcalcs config file at {path} did not contain a JSON object; "
                "using default configuration."
            )
    except (json.JSONDecodeError, OSError) as e:
        warnings.warn(
            f"Could not read handcalcs config file at {path} ({e}); "
            "using default configuration."
        )
    return config


# Loaded once at import, like handcalcs v1.
_config: dict[str, Any] = _load_config()


def get_config() -> dict[str, Any]:
    """Return a copy of the current in-memory configuration."""
    return deepcopy(_config)


def get_option(option: str, default: Any = None) -> Any:
    """Return the value of ``option`` in the current configuration."""
    return _config.get(option, default)


def set_option(option: str, value: Any) -> None:
    # __doc__ is assigned below, built from DEFAULTS (mirrors handcalcs v1).
    if option in _BASE_OPTION_TYPES and not isinstance(value, _BASE_OPTION_TYPES[option]):
        raise ValueError(
            f"Option '{option}' must be set with a value of type "
            f"{_BASE_OPTION_TYPES[option].__name__}, not {type(value).__name__}."
        )
    _config[option] = value


def reset_option(option: str) -> None:
    """
    Reset ``option`` to its built-in default, or remove it if it is a custom field.

    This affects the in-memory configuration only; call ``save_config`` to persist.
    """
    if option in DEFAULTS:
        _config[option] = deepcopy(DEFAULTS[option])
    else:
        _config.pop(option, None)


def reset_config() -> None:
    """Reset the entire in-memory configuration to the built-in defaults."""
    global _config
    _config = deepcopy(DEFAULTS)


def save_config() -> None:
    """
    Persist the current in-memory configuration to disk.

    The saved configuration becomes the new default, loaded automatically the next
    time handcalcs is imported. The config directory is created if necessary.
    """
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as config_file:
        json.dump(_config, config_file, indent=4)
        config_file.truncate()


def _build_options_doc() -> str:
    lines = []
    for key, value in DEFAULTS.items():
        lines.append(f"{key}: {type(value).__name__} (default = {value!r})")
    return (
        "The following base options are recognised (arbitrary extra options may "
        "also be set for use by custom renderers):\n\t" + "\n\t".join(lines)
    )


set_option.__doc__ = f"""
    Set the value of ``option`` to ``value`` in the global configuration.

    This affects the in-memory configuration only; call ``save_config`` to make the
    change permanent. Base options are type-checked; any other option name is
    accepted with any value, so custom renderers can store their own settings.

    {_build_options_doc()}
    """
