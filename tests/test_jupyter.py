"""
Tests for the Jupyter interface (``%%render``, ``%render`` and ``%hc_default_renderer``), run in
a real IPython ``InteractiveShell``. The interface registers its magics on the
active shell at import, so the module is imported after the shell is created.
"""
import importlib
import sys

import pytest

IPython = pytest.importorskip("IPython")
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output

from handcalcs import config
from handcalcs.renderers import LatexRenderer, MarkdownRenderer

CELL = "a = 2\nb = 3\nif a < b:\n    c = a + b\n"


@pytest.fixture(scope="module")
def shell():
    shell = InteractiveShell.instance()
    sys.modules.pop("handcalcs.interfaces.jupyter", None)
    jupyter = importlib.import_module("handcalcs.interfaces.jupyter")
    yield shell, jupyter
    sys.modules.pop("handcalcs.interfaces.jupyter", None)
    InteractiveShell.clear_instance()


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HANDCALCS_CONFIG", str(tmp_path / "config.json"))
    config.reset_config()
    yield
    config.reset_config()


def render_cell(shell, cell: str = CELL) -> dict:
    """Run ``%%render`` on a cell and return the data of its one display output."""
    with capture_output() as captured:
        shell.run_cell_magic("render", "", cell)
    assert len(captured.outputs) == 1
    return captured.outputs[0].data


def test_render_defaults_to_markdown(shell):
    ip, _ = shell
    data = render_cell(ip)
    assert set(data) >= {"text/markdown"}
    markdown = data["text/markdown"]
    assert "> $$\\begin{aligned} c &= a + b" in markdown
    assert "\\begin{list}" not in markdown
    # The cell still ran in the user namespace.
    assert ip.user_ns["c"] == 5


def test_hc_default_renderer_sets_jupyter_renderer_only(shell):
    ip, _ = shell
    ip.run_line_magic("hc_default_renderer", "latex")
    assert config.get_option("jupyter_renderer") == "latex"
    assert config.get_option("default_renderer") == "base"
    data = render_cell(ip)
    assert "text/latex" in data
    assert "\\begin{list}" in data["text/latex"]


def test_hc_default_renderer_rejects_unknown_name(shell):
    ip, _ = shell
    with pytest.raises(ValueError, match="No renderer named 'ghost'"):
        ip.run_line_magic("hc_default_renderer", "ghost")
    assert config.get_option("jupyter_renderer") == "markdown"


def test_display_class_follows_nearest_builtin_ancestor(shell):
    _, jupyter = shell

    class MyMarkdown(MarkdownRenderer):
        name = "my_markdown_for_display_test"

    class MyLatex(LatexRenderer):
        pass

    assert jupyter.display_class_for(MyMarkdown) is jupyter.Markdown
    assert jupyter.display_class_for(MyLatex) is jupyter.Latex
    assert jupyter.display_class_for(MarkdownRenderer) is jupyter.Markdown


def run_cell(shell, cell: str):
    """Run a cell and return its result and the data of each display output."""
    with capture_output() as captured:
        result = shell.run_cell(cell)
    return result, [output.data for output in captured.outputs]


def test_line_magic_renders_only_its_line(shell):
    ip, _ = shell
    result, outputs = run_cell(ip, "a = 2\nb = 3\n%render c = a * b\nd = c + 1\n")
    assert result.success
    assert len(outputs) == 1
    assert outputs[0]["text/markdown"] == (
        "$$\\begin{aligned} c &= a \\cdot b = 2 \\cdot 3 = 6 \\end{aligned}$$\n"
    )
    # The line ran in the user namespace, and so did the rest of the cell.
    assert ip.user_ns["c"] == 6
    assert ip.user_ns["d"] == 7


def test_line_magic_reads_trailing_comment_command(shell):
    ip, _ = shell
    _, outputs = run_cell(ip, "a = 2\nb = 3\n%render c = a * b  # hc: -f .2f\n")
    assert "= 6.00" in outputs[0]["text/markdown"]


def test_line_magic_in_a_loop_renders_each_pass(shell):
    ip, _ = shell
    _, outputs = run_cell(ip, "b = 3\nfor i in range(2):\n    %render e = i * b\n")
    assert [o["text/markdown"].count("= 0 \\cdot 3") for o in outputs] == [1, 0]
    assert "= 1 \\cdot 3 = 3" in outputs[1]["text/markdown"]


def test_line_magic_uses_jupyter_renderer(shell):
    ip, _ = shell
    ip.run_line_magic("hc_default_renderer", "latex")
    _, outputs = run_cell(ip, "a = 2\n%render c = a + 1\n")
    assert "text/latex" in outputs[0]


def test_line_magic_refuses_function_body(shell):
    ip, jupyter = shell
    with pytest.raises(jupyter.UsageError, match="inside a function"):
        jupyter.render_line("x = 1", {"a": 1})


def test_line_magic_needs_code(shell):
    ip, jupyter = shell
    with pytest.raises(jupyter.UsageError, match="needs a line of code"):
        ip.run_line_magic("render", "  ")
