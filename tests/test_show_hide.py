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
