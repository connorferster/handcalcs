"""
Tests for the global user configuration feature (``handcalcs.config``) and the
renderer name registry it relies on.

The config file location is redirected to a temp path via the ``HANDCALCS_CONFIG``
environment variable so these tests never touch the real per-user config.
"""
import json

import pytest

from handcalcs import config
from handcalcs import HandCalcs
from handcalcs.renderers import BaseRenderer, PlainTextRenderer, get_renderer


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Redirect the config file to a temp path and reset in-memory state."""
    path = tmp_path / "config.json"
    monkeypatch.setenv("HANDCALCS_CONFIG", str(path))
    config.reset_config()
    yield path
    config.reset_config()


# --- defaults & getters -----------------------------------------------------

def test_defaults_present_when_no_file(isolated_config):
    assert config.get_option("default_renderer") == "base"
    assert config.get_option("format_code") == ".5g"
    # Nothing is written to disk until save_config() is called.
    assert not isolated_config.exists()


def test_get_config_returns_copy(isolated_config):
    cfg = config.get_config()
    cfg["format_code"] = "mutated"
    assert config.get_option("format_code") == ".5g"


# --- set_option -------------------------------------------------------------

def test_set_known_and_arbitrary_options(isolated_config):
    config.set_option("format_code", ".2f")
    assert config.get_option("format_code") == ".2f"
    # An arbitrary custom field (for a custom renderer) is accepted.
    config.set_option("my_custom_setting", 42)
    assert config.get_option("my_custom_setting") == 42


def test_set_option_type_guard_on_base_option(isolated_config):
    with pytest.raises(ValueError):
        config.set_option("format_code", 5)
    with pytest.raises(ValueError):
        config.set_option("default_renderer", 123)


# --- save / load round trip -------------------------------------------------

def test_save_and_reload_round_trip(isolated_config):
    config.set_option("format_code", ".1f")
    config.set_option("custom_field", "hello")
    config.save_config()

    assert isolated_config.exists()
    on_disk = json.loads(isolated_config.read_text())
    assert on_disk["format_code"] == ".1f"
    assert on_disk["custom_field"] == "hello"

    # A fresh load from disk reflects the saved values.
    reloaded = config._load_config()
    assert reloaded["format_code"] == ".1f"
    assert reloaded["custom_field"] == "hello"


def test_reset_option(isolated_config):
    config.set_option("format_code", ".1f")
    config.set_option("custom_field", "x")
    config.reset_option("format_code")
    config.reset_option("custom_field")
    assert config.get_option("format_code") == ".5g"
    assert config.get_option("custom_field") is None


# --- renderer registry ------------------------------------------------------

def test_registry_resolves_builtins():
    assert get_renderer("base") is BaseRenderer
    assert get_renderer("plain_text") is PlainTextRenderer
    assert get_renderer("does_not_exist") is None


def test_subclass_auto_registers():
    class ConfigTestAutoRenderer(BaseRenderer):
        name = "config_test_auto"

    assert get_renderer("config_test_auto") is ConfigTestAutoRenderer


# --- HandCalcs default renderer selection -----------------------------------

def test_bare_handcalcs_uses_configured_default_renderer(isolated_config):
    class ConfigTestDefaultRenderer(BaseRenderer):
        name = "config_test_default"

    config.set_option("default_renderer", "config_test_default")
    assert isinstance(HandCalcs().renderer, ConfigTestDefaultRenderer)


def test_unknown_default_renderer_warns_and_falls_back(isolated_config):
    config.set_option("default_renderer", "ghost_renderer_xyz")
    with pytest.warns(UserWarning):
        hc = HandCalcs()
    assert type(hc.renderer) is BaseRenderer


def test_explicit_renderer_ignores_default_renderer_option(isolated_config):
    config.set_option("default_renderer", "ghost_renderer_xyz")
    # Passing a renderer explicitly must not trigger the default lookup/warning.
    hc = HandCalcs(BaseRenderer())
    assert type(hc.renderer) is BaseRenderer


# --- end-to-end context threading -------------------------------------------

def test_config_format_code_applies_to_output(isolated_config):
    config.set_option("format_code", ".2f")
    out = HandCalcs()("x = 5.259323\n")
    assert "5.26" in out


def test_inline_command_overrides_config_format(isolated_config):
    config.set_option("format_code", ".2f")
    out = HandCalcs()("x = 5.259323 # hc: -f .4g\n")
    # The per-line -f wins for this line.
    assert "5.259" in out
    assert "5.26" not in out


def test_custom_setting_reaches_render_context(isolated_config):
    config.set_option("my_custom_setting", 99)
    hc = HandCalcs()
    ctx = hc.renderer.create_context(**hc._context_settings)
    assert ctx.current.my_custom_setting == 99
    # 'default_renderer' is not threaded onto the context.
    assert not hasattr(ctx.current, "default_renderer")
