"""
Showing and hiding parts of a calculation: ``# hc: -i`` (hide) and ``# hc: -s``
(show), standalone (a region) or inline (one line), each optionally conditional
(``# hc: -s M_f > 0``).
"""

import pytest

from handcalcs import ASCIIRenderer, HandCalcs
from handcalcs.parsing.commands import parse_commands, resolve_condition


def flags(comment: str) -> dict:
    """The flags ``# hc: <comment>`` gives (the ones left unset are None)."""
    commands = parse_commands(f"hc: {comment}", comment.split())
    return {key: value for key, value in commands.items() if value is not None}


# --- Parsing the flags ---


@pytest.mark.parametrize(
    "comment, expected",
    [
        ("-i", {"ignore": True}),
        ("--ignore", {"ignore": True}),
        ("-s", {"ignore": False}),
        ("--show", {"ignore": False}),
        ("-f .2f", {"format_code": ".2f"}),
        ("-i -m", {"ignore": True, "multiline": True}),
    ],
)
def test_show_hide_flags(comment, expected):
    assert flags(comment) == expected


@pytest.mark.parametrize(
    "comment, expected",
    [
        ("-i A_s < A_req", {"ignore": True, "condition": "A_s < A_req"}),
        ("-s M_f > 0", {"ignore": False, "condition": "M_f > 0"}),
        ("--show not ok", {"ignore": False, "condition": "not ok"}),
        # The condition is the rest of the comment: '-5' is not read as a flag.
        ("-s M_f > -5", {"ignore": False, "condition": "M_f > -5"}),
        (
            "-f .2f -i M_f == 0",
            {"format_code": ".2f", "ignore": True, "condition": "M_f == 0"},
        ),
    ],
)
def test_conditional_flag_keeps_the_condition(comment, expected):
    assert flags(comment) == expected


@pytest.mark.parametrize(
    "comment, value, ignore",
    [
        ("-i x", True, True),
        ("-i x", False, False),
        ("-s x", True, False),
        ("-s x", False, True),
    ],
)
def test_resolve_condition(comment, value, ignore):
    # A false condition does the opposite of its flag.
    resolved = resolve_condition(flags(comment), lambda condition: value)
    assert resolved == {"ignore": ignore}


def test_resolve_condition_without_one_is_unchanged():
    assert resolve_condition({"ignore": True}, lambda condition: 1 / 0) == {
        "ignore": True
    }


# --- A command changes only the settings it names ---


def render(source: str) -> str:
    return HandCalcs(ASCIIRenderer())(source)


def test_a_later_command_does_not_reset_ignore():
    out = render("a = 1\n# hc: -i\nb = 2\n# hc: -f .3f\nc = 3.0\n")
    assert out == "a = 1\n"


def test_a_later_command_does_not_reset_multiline():
    source = "a = 1\nb = 2\n# hc: -m\nc = a + b\n# hc: -f .3f\nd = a + b\n"
    out = render(source)
    assert out == (
        "a = 1\nb = 2\n"
        "c = a + b\n  = 1 + 2\n  = 3\n"
        "d = a + b\n  = 1.000 + 2.000\n  = 3.000\n"
    )


def test_an_inline_command_does_not_show_a_hidden_line():
    out = render("a = 1\n# hc: -i\nb = 2 # hc: -f .3f\n")
    assert out == "a = 1\n"


def test_show_ends_a_hidden_region():
    out = render("a = 1\n# hc: -i\nb = 2\n# hc: -s\nc = 3\n")
    assert out == "a = 1\nc = 3\n"


# --- Conditions ---


def test_standalone_condition_true_shows():
    out = render("a = 1\n# hc: -i\nM_f = 5\n# hc: -s M_f > 0\nb = 2\n")
    assert out == "a = 1\nb = 2\n"


def test_standalone_condition_false_hides():
    # A false condition does the opposite of its flag.
    out = render("M_f = 0\n# hc: -s M_f > 0\nb = 2\n# hc: -s\nc = 3\n")
    # (ASCII right-aligns the names of a group of lines.)
    assert out == "M_f = 0\n  c = 3\n"


def test_standalone_ignore_condition():
    source = "A_s = 300\nA_req = 400\n# hc: -i A_s < A_req\nb = 2\n"
    assert render(source) == "  A_s = 300\nA_req = 400\n"
    source = "A_s = 500\nA_req = 400\n# hc: -i A_s < A_req\nb = 2\n"
    assert render(source) == "  A_s = 500\nA_req = 400\n    b = 2\n"


def test_standalone_condition_uses_the_values_at_the_comment():
    # M_f is 0 at the comment and only later 5: the section is hidden.
    out = render("M_f = 0\n# hc: -s M_f > 0\nb = 2\n# hc: -s\nM_f = 5\n")
    assert out == "M_f = 0\nM_f = 5\n"


def test_inline_condition_uses_the_line_result():
    out = render("a = 2\nb = a - 2 # hc: -i b == 0\nc = a + 1 # hc: -i c == 0\n")
    assert out == "a = 2\nc = a + 1 = 2 + 1 = 3\n"


def test_inline_condition_shows_a_line_in_a_hidden_region():
    out = render("# hc: -i\na = 2\nb = a * 3 # hc: -s b > 5\nc = 1 # hc: -s c > 5\n")
    assert out == "b = a * 3 = 2 * 3 = 6\n"


def test_condition_without_line_values_uses_the_final_values():
    import handcalcs

    handcalcs.set_option("line_values", False)
    try:
        # Without the recorded values, M_f is its value after the run (5) on
        # every line, so the condition is true.
        out = render("M_f = 0\n# hc: -s M_f > 0\nb = 2\n# hc: -s\nM_f = 5\n")
    finally:
        handcalcs.reset_option("line_values")
    assert out == "M_f = 5\n  b = 2\nM_f = 5\n"


def test_condition_error_names_the_condition():
    from handcalcs.parsing.commands import CommentCommandError

    with pytest.raises(CommentCommandError, match=r"'M_x > 0'.*NameError"):
        render("a = 1\n# hc: -s M_x > 0\nb = 2\n")


def test_condition_in_a_decorated_function():
    from handcalcs import handcalc

    @handcalc(ASCIIRenderer())
    def check(M_f):
        a = 1
        # hc: -s M_f > 0
        b = M_f * 2
        return b

    assert check(3) == (6, "a = 1\nb = M_f * 2 = 3 * 2 = 6\n")
    assert check(0) == (0, "a = 1\n")


# --- Hiding in every renderer (BaseRenderer.render_node) ---

HIDDEN_REGION = """
aaa = 2
# hc: -i
## Zebra heading
# Zebra comment
www = aaa + 1
xxx = 1; yyy = 2
# hc: -g
zzz = 3
if www > 2:
    vvv = www * 2
import statistics
statistics.mean([1, 2])
# hc: -s
ddd = 4
"""


def rendered_text(renderer_name: str, source: str) -> str:
    """The text of a render, from any of the renderers producing a document."""
    from handcalcs.renderers import get_renderer

    rendered = HandCalcs(get_renderer(renderer_name)())(source)
    if isinstance(rendered, str):
        return rendered
    return "".join(rendered.element.body.itertext())  # a Word document


@pytest.mark.parametrize(
    "renderer_name", ["ascii", "latex", "markdown", "html", "word"]
)
def test_a_hidden_region_hides_every_kind_of_line(renderer_name):
    text = rendered_text(renderer_name, HIDDEN_REGION)
    for hidden in ["Zebra", "www", "xxx", "yyy", "zzz", "vvv", "Since", "statistics"]:
        assert hidden not in text
    assert "aaa" in text and "ddd" in text


def test_a_hidden_params_grid_leaves_no_empty_grid():
    shown = render("a = 1\n")
    assert render("a = 1\n# hc: -i\nx = 1; y = 2\n") == shown
    assert render("a = 1\n# hc: -i\n# hc: -g\nx = 1\ny = 2\n") == shown


def test_a_hidden_line_in_a_params_grid_is_left_out():
    out = render("x = 1; y = 2 # hc: -i\nz = 3\n")
    assert "y" not in out and "x = 1" in out


def test_an_inline_show_reveals_one_line_of_a_hidden_region():
    out = render("# hc: -i\na = 1\nb = 2 # hc: -s\nc = 3\n")
    assert out == "b = 2\n"


def test_a_hidden_block_is_hidden_whole():
    # The -s in the body does not reveal it, but applies after the block.
    source = "a = 3\n# hc: -i\nif a > 2:\n    b = 1\n    # hc: -s\n    c = 2\nd = 4\n"
    assert render(source) == "a = 3\nd = 4\n"


def test_a_command_in_a_hidden_block_still_applies_after_it():
    source = (
        "a = 3\n# hc: -i\nif a > 2:\n    # hc: -f .3f\n    b = 1.0\n# hc: -s\nd = 4.0\n"
    )
    assert render(source) == "a = 3\nd = 4.000\n"


def test_excel_keeps_a_hidden_region_as_hidden_rows():
    from handcalcs.renderers.excel import ExcelRenderer
    from handcalcs.renderers.excel.rows import CalcRow, ParamRow

    source = "a = 2\n# hc: -i\n## Hidden\n# note\nb = a * 2\n# hc: -s\nd = b + 1\n"
    rows = HandCalcs(renderer=ExcelRenderer())(source).rows
    assert [type(row) for row in rows] == [ParamRow, CalcRow, CalcRow]
    a, b, d = rows
    assert b.hidden and not a.hidden and not d.hidden
    assert d.formula == "=b+1"


# --- The 'hidden_by_default' option (#343) ---


@pytest.fixture
def hidden_by_default(tmp_path, monkeypatch):
    import handcalcs

    monkeypatch.setenv("HANDCALCS_CONFIG", str(tmp_path / "hc_config.json"))
    handcalcs.reset_config()
    handcalcs.set_option("hidden_by_default", True)
    yield
    handcalcs.reset_config()


def test_hidden_by_default_shows_only_what_show_shows(hidden_by_default):
    source = "## Inputs\na = 1\nb = 2 # hc: -s\n# hc: -s\nc = a + b\n# hc: -i\nd = 4\n"
    assert render(source) == "b = 2\nc = a + b = 1 + 2 = 3\n"


def test_hidden_by_default_with_a_condition(hidden_by_default):
    source = "M_f = {}\n# hc: -s M_f > 0\nb = M_f * 2\n"
    assert render(source.format(5)) == "b = M_f * 2 = 5 * 2 = 10\n"
    assert render(source.format(0)) == ""


def test_hidden_by_default_option_is_validated():
    import handcalcs

    with pytest.raises((TypeError, ValueError)):
        handcalcs.set_option("hidden_by_default", "yes")


def test_hidden_by_default_in_a_decorator_render_context():
    from handcalcs import handcalc

    @handcalc(ASCIIRenderer(), render_context={"hidden_by_default": True})
    def calc(a):
        b = a * 2
        c = b + 1  # hc: -s
        return c

    assert calc(1) == (3, "c = b + 1 = 2 + 1 = 3\n")
