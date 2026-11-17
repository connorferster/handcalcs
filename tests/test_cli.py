"""
The command line interface, ``python -m handcalcs`` (handcalcs/__main__.py).
"""

import subprocess
import sys
import zipfile

import pytest

from handcalcs import config
from handcalcs.__main__ import literal, main
from handcalcs.renderers.base import _RENDERER_REGISTRY

SOURCE = """\
## Beam
w = 4.5
L = 6.0
M = w * L**2 / 8
"""


@pytest.fixture
def script(tmp_path):
    path = tmp_path / "beam.py"
    path.write_text(SOURCE, encoding="utf-8")
    return path


def sheet_names(path) -> str:
    return zipfile.ZipFile(path).read("xl/workbook.xml").decode("utf-8")


def test_no_arguments_prints_help(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: handcalcs")
    assert "--output" in out and "--sheet-name" in out


def test_prints_text_by_default(script, capsys):
    assert main([str(script)]) == 0
    assert capsys.readouterr().out == (
        "====\nBeam\n====\n\nw = 4.5\nL = 6\nM = w * L² / 8 = 4.5 * 6² / 8 = 20.25\n"
    )


def test_renderer_and_output(script, tmp_path, capsys):
    output = tmp_path / "beam.xlsx"
    assert main([str(script), "--renderer", "excel", "--output", str(output)]) == 0
    assert output.is_file()
    assert capsys.readouterr().err == f"Wrote {output}\n"


def test_renderer_from_extension(script, tmp_path):
    output = tmp_path / "beam.tex"
    main([str(script), "-o", str(output), "-q"])
    assert output.read_text(encoding="utf-8").startswith("\\documentclass")


def test_unknown_extension_needs_renderer(script, tmp_path, capsys):
    with pytest.raises(SystemExit) as exit_info:
        main([str(script), "-o", str(tmp_path / "beam.pdf")])
    assert exit_info.value.code == 2
    assert "--renderer" in capsys.readouterr().err


@pytest.mark.parametrize(
    "arguments",
    [
        ["--sheet-name", "Loads", "{script}", "-o", "{out}"],
        ["{script}", "-o", "{out}", "--sheet-name", "Loads"],
        ["{script}", "--sheet-name=Loads", "-o", "{out}"],
    ],
)
def test_renderer_options_anywhere(arguments, script, tmp_path):
    output = tmp_path / "beam.xlsx"
    filled = [a.format(script=script, out=output) for a in arguments]
    assert main(filled + ["-q"]) == 0
    assert 'name="Loads"' in sheet_names(output)


def test_option_values_are_literals(script, tmp_path):
    output = tmp_path / "beam.xlsx"
    main([str(script), "-o", str(output), "-q", "--value-format", '{"bold": False}'])
    assert output.is_file()


def test_unknown_renderer_option(script, capsys):
    with pytest.raises(SystemExit):
        main([str(script), "-r", "latex", "--sheet-name", "x"])
    err = capsys.readouterr().err
    assert "no option --sheet-name" in err and "--format-code" in err


def test_invalid_option_value(script, tmp_path, capsys):
    with pytest.raises(SystemExit):
        main([str(script), "-o", str(tmp_path / "b.xlsx"), "--sheet-name", "a/b"])
    assert "'excel' renderer: sheet_name" in capsys.readouterr().err


def test_handcalcs_options_apply_to_one_run(script, capsys):
    before = config.get_config()
    main([str(script), "--format-code", ".2f"])
    assert "L = 6.00" in capsys.readouterr().out
    assert config.get_config() == before


def test_flag_alone_is_true(script, capsys):
    main([str(script), "--hidden-by-default"])
    assert capsys.readouterr().out == ""
    assert config.get_option("hidden_by_default") is False


def test_file_renderer_needs_output(script, capsys):
    with pytest.raises(SystemExit):
        main([str(script), "-r", "word"])
    assert "--output" in capsys.readouterr().err


def test_unknown_renderer(script, capsys):
    with pytest.raises(SystemExit):
        main([str(script), "-r", "pdf"])
    assert "no renderer named 'pdf'" in capsys.readouterr().err


def test_missing_source(capsys):
    with pytest.raises(SystemExit):
        main(["missing.py"])
    assert "no such file" in capsys.readouterr().err


def test_list_renderers(capsys):
    assert main(["--list-renderers"]) == 0
    out = capsys.readouterr().out
    for name in ("ascii", "excel", "html", "latex", "markdown", "word"):
        assert f"\n  {name}" in out
    assert "--filepath" not in out and "--document" not in out


def test_import_registers_custom_renderer(script, tmp_path, monkeypatch, capsys):
    (tmp_path / "shout.py").write_text(
        "from handcalcs.renderers import ASCIIRenderer\n"
        "class Shout(ASCIIRenderer):\n"
        "    name = 'shout_test'\n"
        "    def complete(self, tree, base_context):\n"
        "        return super().complete(tree, base_context).upper()\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        main([str(script), "--import", "shout", "-r", "shout_test"])
    finally:
        _RENDERER_REGISTRY.pop("shout_test", None)
        sys.modules.pop("shout", None)
    assert "W = 4.5" in capsys.readouterr().out


def test_script_directory_is_importable(tmp_path, capsys):
    (tmp_path / "loads_cli_test.py").write_text("w = 2.5\n", encoding="utf-8")
    script = tmp_path / "calc.py"
    script.write_text("from loads_cli_test import w\nM = w * 2\n", encoding="utf-8")
    main([str(script)])
    assert "M = w * 2 = 2.5 * 2 = 5" in capsys.readouterr().out
    assert str(tmp_path) not in sys.path


@pytest.mark.parametrize(
    "text, value",
    [("3", 3), ("True", True), ("#1d4ed8", "#1d4ed8"), ("Beam", "Beam"), (".2f", ".2f")],
)
def test_literal(text, value):
    assert literal(text) == value


def test_python_dash_m(script):
    result = subprocess.run(
        [sys.executable, "-m", "handcalcs", str(script), "-r", "markdown"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.startswith("# Beam")
