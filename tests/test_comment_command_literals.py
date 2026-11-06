"""
Comment commands are parsed, never run. A kwarg command (``# hc: multiline =
False``) takes literal values only, and a flag (``# hc: -s``) is always read as a
flag, even when the same text is a valid Python expression.

forallpeople's ``si.environment(..., top_level=True)`` puts its units in
``builtins``: with ``s`` (seconds) and ``m`` (metres) there, ``-s`` and ``-m``
used to run as expressions (negative one second) and be ignored, silently.
"""

import builtins

import pytest

from handcalcs import HandCalcs, ASCIIRenderer
from handcalcs.parsing.commands import CommentCommandError
from handcalcs.parsing.comment_parser import parse_kwargs
from handcalcs.parsing.line_nodes import CommentCommand
from handcalcs.parsing.inline_nodes import InlineCommand


class Unit:
    """Stands in for a forallpeople unit: something that can be negated."""

    def __neg__(self):
        return self


@pytest.fixture
def units_in_builtins(monkeypatch):
    for name in ("s", "m", "g", "h", "b", "p", "c", "i", "w", "f"):
        monkeypatch.setattr(builtins, name, Unit(), raising=False)


def render(source: str) -> str:
    return HandCalcs(ASCIIRenderer())(source)


SHOW_AFTER_HIDE = "x = 1\n# hc: -i\ny = 2\n# hc: -s\nz = x + y\n"
LONG = "a = 2\nb = 3\nc = a * b + a / b - a ** 2  # hc: -m\n"


def test_show_after_hide(units_in_builtins):
    assert render(SHOW_AFTER_HIDE) == "x = 1\nz = x + y = 1 + 2 = 3\n"


def test_inline_multiline(units_in_builtins):
    assert render(LONG).splitlines()[-3:] == [
        "c = a * b + a / b - a²",
        "  = 2 * 3 + 2 / 3 - 2²",
        "  = 2.6667",
    ]


def test_standalone_multiline(units_in_builtins):
    rendered = render("a = 2\n# hc: -m\nc = a * 3 + 4\n")
    assert rendered.splitlines()[-3:] == ["c = a * 3 + 4", "  = 2 * 3 + 4", "  = 10"]


@pytest.mark.parametrize(
    "flag, key, expected",
    [
        ("-s", "ignore", False),
        ("-i", "ignore", True),
        ("-m", "multiline", True),
        ("-g", "params_block", True),
        ("-h", "params_block", True),
        ("-b", "line_break", True),
        ("-p", "param_line", True),
    ],
)
def test_every_short_flag_is_a_flag(units_in_builtins, flag, key, expected):
    assert CommentCommand.from_raw_comment(f"# hc: {flag}").commands[key] is expected
    assert InlineCommand.from_raw_comment(f"hc: {flag}").commands[key] is expected


@pytest.mark.parametrize(
    "comment, expected",
    [
        ("hc: multiline = False", {"multiline": False}),
        ('hc: format_code = ".2f"', {"format_code": ".2f"}),
        ('hc: mode = "ass sym"', {"mode": "ass sym"}),
        ("hc: param_cols = 3", {"param_cols": 3}),
        ("hc: a = b = -1.5", {"a": -1.5, "b": -1.5}),
        ('hc: multiline = True; format_code = ".3f"', {"multiline": True, "format_code": ".3f"}),
        ("hc: check = None", {"check": None}),
    ],
)
def test_kwarg_literals(comment, expected):
    assert parse_kwargs(comment) == expected


@pytest.mark.parametrize(
    "comment",
    ["hc: -s", "hc: -m", "hc: --show", "hc: -s M_f > 0", "hc: -f .2f", "hc: m", "hc:"],
)
def test_not_kwarg_style_is_a_syntax_error(units_in_builtins, comment):
    # The callers read a SyntaxError as "not kwarg-style" and use the flag parser.
    with pytest.raises(SyntaxError):
        parse_kwargs(comment)


@pytest.mark.parametrize(
    "comment",
    [
        "hc: format_code = fc",
        'hc: format_code = "." + "2f"',
        "hc: x = __import__('os').getcwd()",
    ],
)
def test_non_literal_value_is_an_error(comment):
    with pytest.raises(CommentCommandError, match="must be a literal"):
        parse_kwargs(comment)


def test_kwarg_comment_is_not_run(monkeypatch):
    calls = []
    monkeypatch.setattr(builtins, "record", calls.append, raising=False)
    with pytest.raises(CommentCommandError):
        parse_kwargs("hc: x = record(1)")
    assert calls == []
