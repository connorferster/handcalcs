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
INPUT_CELL = "a = 2\nb = 3\nc = a + b\n"


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


def test_bare_expression_shows_its_result(shell):
    # #54: a cell (or a %render line) that is just an expression shows its result.
    ip, _ = shell
    assert render_cell(ip, "2 + 2\n")["text/markdown"] == (
        "$$\\begin{aligned} 2 + 2 &= 4 \\end{aligned}$$\n"
    )
    _, outputs = run_cell(ip, "a = 2\n%render a * 3\n")
    assert "a \\cdot 3 &= 2 \\cdot 3 = 6" in outputs[0]["text/markdown"]


def render_cell_with(shell, line: str, cell: str) -> dict:
    """Run ``%%render <line>`` on a cell and return the data of its one display output."""
    with capture_output() as captured:
        shell.run_cell_magic("render", line, cell)
    assert len(captured.outputs) == 1
    return captured.outputs[0].data


def test_render_with_inputs(shell):
    ip, _ = shell
    ip.user_ns["case"] = {"a": 7}
    markdown = render_cell_with(ip, "inputs=case", INPUT_CELL)["text/markdown"]
    assert "a &= 7" in markdown
    assert "c &= a + b = 7 + 3 = 10" in markdown
    assert ip.user_ns["c"] == 10


def test_render_with_inputs_expression_and_options(shell):
    ip, _ = shell
    ip.user_ns["cases"] = [{"a": 1}, {"a": 4, "unused": 0}]
    markdown = render_cell_with(ip, "inputs=cases[1], strict=False", INPUT_CELL)[
        "text/markdown"
    ]
    assert "c &= a + b = 4 + 3 = 7" in markdown
    markdown = render_cell_with(
        ip, "inputs={'b': 5}, allow_computed=True", "a = 2\nb = a * 3\nc = a + b\n"
    )["text/markdown"]
    assert "c &= a + b = 2 + 5 = 7" in markdown


def test_render_with_quantity_input(shell):
    ip, _ = shell
    pint = pytest.importorskip("pint")
    ip.user_ns["case"] = {"L": pint.UnitRegistry().Quantity(8000, "mm")}
    cell = "import pint\nureg = pint.UnitRegistry()\nm = ureg.m\nL = 6 * m\nA = L**2\n"
    markdown = render_cell_with(ip, "inputs=case", cell)["text/markdown"]
    assert "L &= 8" in markdown
    assert ip.user_ns["A"].magnitude == 64
    assert "__hc_input__" not in ip.user_ns


def test_render_with_inputs_errors(shell):
    ip, jupyter = shell
    ip.user_ns["case"] = {"z": 1}
    with pytest.raises(KeyError, match="'z'"):
        ip.run_cell_magic("render", "inputs=case", CELL)
    with pytest.raises(jupyter.UsageError, match="does not take 'input'"):
        ip.run_cell_magic("render", "input=case", CELL)
    with pytest.raises(jupyter.UsageError, match="needs inputs="):
        ip.run_cell_magic("render", "strict=False", CELL)
    with pytest.raises(jupyter.UsageError, match="must be a dict"):
        ip.run_cell_magic("render", "inputs=[1]", CELL)
    with pytest.raises(jupyter.UsageError, match="keyword arguments"):
        ip.run_cell_magic("render", "inputs=case strict=False", CELL)


def test_render_ignores_words_without_arguments(shell):
    # v1 options such as `%%render params` are ignored, as before.
    ip, _ = shell
    with capture_output() as captured:
        ip.run_cell_magic("render", "params", CELL)
    assert "c &= a + b" in captured.outputs[0].data["text/markdown"]
