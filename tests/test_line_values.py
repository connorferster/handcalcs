"""
Each line shows the values it ran with (B2, B3): values are recorded statement
by statement while the source runs (``handcalcs.parsing.line_values``), not
read from the namespace after the whole source ran.
"""
import sys

import pytest

from handcalcs import HandCalcs, handcalc
from handcalcs.parsing import line_values
from handcalcs.parsing.line_values import LineValues, run
from handcalcs.renderers import ASCIIRenderer, LatexRenderer


def ascii(source: str, *args, **kwargs) -> str:
    return HandCalcs(ASCIIRenderer())(source, *args, **kwargs)


@pytest.fixture(params=["monitoring", "settrace"])
def backend(request, monkeypatch):
    """Run a test with sys.monitoring (3.12+) and with the sys.settrace fallback."""
    if request.param == "monitoring" and not hasattr(sys, "monitoring"):
        pytest.skip("sys.monitoring needs Python 3.12+")
    if request.param == "settrace":
        monkeypatch.setattr(line_values, "_free_tool_id", lambda monitoring: None)
    return request.param


# --- recording -----------------------------------------------------------------


def test_statements_by_line():
    source = (
        "a = 1\n"
        "if (a >\n"
        "        0):\n"
        "    b = (a +\n"
        "         1)\n"
        "for i in range(2):\n"
        "    c = i\n"
        "with open(__file__) as f:\n"
        "    d = 1\n"
    )
    values = LineValues(source)
    assert values.statement_of_line == {
        1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 6, 7: 7, 8: 8, 9: 9
    }
    assert values.loop_headers == {6}


def test_before_and_after_each_statement(backend):
    values = run("a = 2\nb = a * 3\na = 10\n", {})
    assert values.before[2] == {"a": 2}
    assert values.after[2] == {"a": 2, "b": 6}
    assert values.after[3] == {"a": 10, "b": 6}


def test_loop_header_keeps_its_starting_values(backend):
    values = run("t = 0\nfor i in range(3):\n    t = t + i\n", {})
    assert values.before[2] == {"t": 0}
    assert values.before[3] == {"t": 1, "i": 2}  # the last pass
    assert values.after[3] == {"t": 3, "i": 2}


def test_only_names_the_source_uses_are_recorded(backend):
    values = run("a = 1\n", {"unrelated": 5})
    assert values.after[1] == {"a": 1}


def test_settrace_restores_an_earlier_trace_function(monkeypatch):
    monkeypatch.setattr(line_values, "_free_tool_id", lambda monitoring: None)

    def earlier(frame, event, arg):
        return None

    previous = sys.gettrace()
    sys.settrace(earlier)
    try:
        run("a = 1\n", {})
        assert sys.gettrace() is earlier
    finally:
        sys.settrace(previous)


@pytest.mark.skipif(not hasattr(sys, "monitoring"), reason="Python 3.12+")
def test_monitoring_tool_is_freed_even_after_an_error():
    with pytest.raises(ZeroDivisionError):
        run("a = 1 / 0\n", {})
    assert all(sys.monitoring.get_tool(tool) != "handcalcs" for tool in range(6))


@pytest.mark.skipif(not hasattr(sys, "monitoring"), reason="Python 3.12+")
def test_falls_back_to_settrace_without_a_free_tool_id(monkeypatch):
    monkeypatch.setattr(sys.monitoring, "get_tool", lambda tool: "taken")
    assert "b = a * 3 = 2 * 3 = 6" in ascii("a = 2\nb = a * 3\na = 10\n")


# --- B3: a reassigned name -------------------------------------------------------


def test_reassigned_name(backend):
    out = ascii("a = 2\nb = a * 3\na = 10\nc = a * 3\n")
    assert out.splitlines()[0] == "a = 2"
    assert "b = a * 3 = 2 * 3 = 6" in out
    assert "c = a * 3 = 10 * 3 = 30" in out


def test_reassigned_name_in_latex():
    out = HandCalcs(LatexRenderer())("a = 2\nb = a * 3\na = 10\n")
    assert "a &= 2" in out
    assert "b &= a \\cdot 3 = 2 \\cdot 3 = 6" in out


def test_self_reference_substitutes_the_value_before(backend):
    assert "a = a * 2 = 2 * 2 = 4" in ascii("a = 2\na = a * 2\n")


def test_loop_body_shows_its_last_pass(backend):
    out = ascii("t = 0\nfor i in range(3):\n    t = t + i\n")
    assert out.splitlines()[0] == "t = 0"
    assert "t = t + i = 1 + 2 = 3" in out


def test_loop_header_shows_the_iterable_it_started_with(backend):
    out = ascii("xs = [1, 2]\nfor x in xs:\n    y = x\nxs = [5]\n")
    assert out.splitlines()[0] == "xs = [1, 2]"
    assert "y = x = 2" in out


def test_supplied_namespace_has_no_line_values():
    # The source does not run, so every line shows the namespace's values.
    out = ascii("a = 2\nb = a * 3\n", {"a": 10, "b": 6}, {})
    assert "b = a * 3 = 10 * 3 = 6" in out


def test_inputs_with_reassignment(backend):
    out = ascii("a = 2\nb = a + 1\na = 0\n", inputs={"a": 7})
    assert "a = 7" in out
    assert "b = a + 1 = 7 + 1 = 8" in out


def test_index_lookup_uses_the_values_before(backend):
    out = ascii("xs = [1, 2]\ny = xs[0] * 10\nxs = [5, 6]\n")
    assert "y = xs[0] * 10 = 1 * 10 = 10" in out


# --- B2: the branch that ran -----------------------------------------------------


def test_branch_whose_test_variable_is_reassigned(backend):
    out = ascii("a = 5\nif a > 3:\n    a = 1\n    b = 2\nelse:\n    b = 3\n")
    assert "Since (a>3) -> (5>3) is True:" in out
    assert "b = 2" in out
    assert "Otherwise" not in out


def test_test_variable_reassigned_after_the_block(backend):
    out = ascii("x = 10\nif x > 5:\n    y = 1\nx = 0\n")
    assert out.splitlines()[0] == "x = 10"
    assert "Since (x>5) -> (10>5) is True:" in out
    assert "No conditions were satisfied" not in out


def test_elif_reached(backend):
    source = "a = 3\nif a > 5:\n    b = 1\nelif a > 2:\n    a = 100\n    b = 2\nelse:\n    b = 3\n"
    out = ascii(source)
    assert "Since (a>2) -> (3>2) is True:" in out
    assert "b = 2" in out


def test_if_inside_a_loop_uses_that_pass(backend):
    source = "t = 0\nfor x in [1, 5]:\n    if x > 2:\n        t = t + x\n"
    out = ascii(source)
    assert "Since (x>2) -> (5>2) is True:" in out
    assert "t = t + x = 0 + 5 = 5" in out


# --- comments ------------------------------------------------------------------


def test_comment_values_follow_the_source(backend):
    source = "n = 1\n# n is {{ n }} here\na = n * 2  # with n = {{ n }}\nn = 2\n# now {{ n }}\n"
    out = ascii(source)
    assert "n is 1 here" in out
    assert "(with n = 1)" in out
    assert "now 2" in out


def test_a_name_not_assigned_yet_is_left_unfilled(backend):
    out = ascii("## Case {{ n }}\nn = 1\nn = 2\n")
    assert "Case {{ n }}" in out


def test_a_name_the_source_does_not_use_is_filled():
    out = ascii("# {{ total }} cases\nn = total\n", {"total": 5, "n": 5}, {})
    assert "5 cases" in out


# --- the decorator -----------------------------------------------------------------


@handcalc(ASCIIRenderer())
def calc_reassigned(a):
    b = a * 3
    a = 10
    if a > 5:
        a = 1
        c = 2
    else:
        c = 3
    return b + c


def test_decorator_reassignment_and_branch(backend):
    value, out = calc_reassigned(2)
    assert value == 8
    assert "b = a * 3 = 2 * 3 = 6" in out
    assert "Since (a>5) -> (10>5) is True:" in out
    assert "Otherwise" not in out


class Beam:
    @handcalc(ASCIIRenderer())
    def moment(self, w):
        M = w * 2
        w = 0
        return M


def test_decorator_method(backend):
    assert "M = w * 2 = 4 * 2 = 8" in Beam().moment(4)[1]


def test_decorator_closure(backend):
    def outer(k):
        @handcalc(ASCIIRenderer())
        def inner(z):
            w = z * k
            z = 0
            return w

        return inner(5)

    assert "w = z * k = 5 * 3 = 15" in outer(3)[1]
