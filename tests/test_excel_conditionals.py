"""
Tests for if/elif/else trees -> one nested-IF formula row per variable.
"""
import pytest

from handcalcs import HandCalcs
from handcalcs.renderers.excel import ExcelRenderer, ExcelRendererIncompatibleError
from handcalcs.renderers.excel.rich_text import plain_text
from handcalcs.renderers.excel.rows import CalcRow

SECTION_CLASS = '''h_w = 500; t_w = 10; F_y = 350
if h_w / t_w <= 1100 / F_y**0.5:
    cls = 1
elif h_w / t_w <= 1700 / F_y**0.5:
    cls = 2
else:
    cls = 4
'''


def rows(source: str) -> list:
    return HandCalcs(renderer=ExcelRenderer())(source).rows


def calc(source: str) -> dict:
    """Calc rows keyed by Excel name."""
    return {row.name: row for row in rows(source) if isinstance(row, CalcRow)}


def test_elif_tree_is_a_nested_if():
    (cls,) = calc(SECTION_CLASS).values()
    assert cls.name == "cls"
    assert cls.formula == "=IF(h_w/t_w<=1100/F_y^0.5,1,IF(h_w/t_w<=1700/F_y^0.5,2,4))"
    assert cls.cached == 1


@pytest.mark.parametrize("h_w, expected", [(500, 1), (800, 2), (1200, 4)])
def test_cached_value_follows_the_taken_branch(h_w, expected):
    source = SECTION_CLASS.replace("h_w = 500", f"h_w = {h_w}")
    assert calc(source)["cls"].cached == expected


def test_piecewise_symbolic_column():
    (cls,) = calc(SECTION_CLASS).values()
    assert plain_text(cls.symbolic).split("\n") == [
        "1,  if hw / tw ≤ 1100 / Fy0.5",
        "2,  if hw / tw ≤ 1700 / Fy0.5",
        "4,  otherwise",
    ]


def test_one_row_per_variable_in_first_appearance_order():
    source = "g = 1\nif g > 0:\n    a = 1\n    b = a * 2\nelse:\n    b = 5\n    a = 3\n"
    a, b = (row for row in rows(source) if isinstance(row, CalcRow))
    assert (a.name, b.name) == ("a", "b")
    assert a.formula == "=IF(g>0,1,3)"
    # b reads a after it is assigned on the same branch: a's own row.
    assert b.formula == "=IF(g>0,a*2,5)"
    assert (a.cached, b.cached) == (1, 2)


def test_reads_before_an_assignment_see_the_previous_version():
    source = "a = 1\nif a > 0:\n    b = a\n    a = 5\n    d = a\nelse:\n    b = 0\n    d = 0\n"
    rows_ = calc(source)
    assert rows_["b"].formula == "=IF(a>0,a,0)"
    assert rows_["a_2"].formula == "=IF(a>0,5,a)"
    assert rows_["d"].formula == "=IF(a>0,a_2,0)"
    assert (rows_["b"].cached, rows_["a_2"].cached, rows_["d"].cached) == (1, 5, 5)


def test_tests_see_the_values_before_the_tree():
    source = "x = 2\nif x > 1:\n    x = 0\n    y = 1\nelse:\n    y = 2\nz = x + y\n"
    rows_ = calc(source)
    assert rows_["x_2"].formula == "=IF(x>1,0,x)"
    assert rows_["y"].formula == "=IF(x>1,1,2)"
    assert rows_["z"].formula == "=x_2+y"
    assert rows_["z"].cached == 1


def test_missing_branch_falls_back_to_the_previous_version():
    source = "k = 7\ng = 1\nif g > 5:\n    k = 1\n"
    k = calc(source)["k_2"]
    assert k.formula == "=IF(g>5,1,k)"
    assert k.cached == 7
    assert plain_text(k.symbolic).split("\n") == ["1,  if g > 5", "k,  otherwise"]


def test_missing_branch_without_previous_version_is_na():
    source = "g = 1\nif g > 5:\n    m = 1\nelif g > 2:\n    pass\n"
    m = calc(source.replace("    pass\n", "    n = 2\n"))["m"]
    assert m.formula == "=IF(g>5,1,IF(g>2,NA(),NA()))"
    assert m.cached is None
    assert plain_text(m.symbolic).endswith("#N/A,  otherwise")


def test_nested_if_else_inside_an_elif_branch():
    source = (
        "t = 10\nq = 40\nk = 0\n"
        "if q < 30:\n    k = 1\n"
        "elif q < 50:\n    if t > 5:\n        k = 3\n    else:\n        k = 4\n"
        "else:\n    k = 9\n"
    )
    k = calc(source)["k_2"]
    assert k.formula == "=IF(q<30,1,IF(q<50,IF(t>5,3,4),9))"
    assert k.cached == 3
    assert plain_text(k.symbolic).split("\n") == [
        "1,  if q < 30",
        "3,  if q < 50 and t > 5",
        "4,  if q < 50",
        "9,  otherwise",
    ]


def test_direct_assignment_then_nested_override_in_one_branch():
    source = "g = 1\nd = 0\nif g > 0:\n    w = 1\n    if d > 0:\n        w = 2\nelse:\n    w = 3\n"
    assert calc(source)["w"].formula == "=IF(g>0,IF(d>0,2,1),3)"


def test_comments_and_commands_in_branches_are_allowed():
    source = "g = 1\nif g > 0:\n    # explain\n    # hc: -f .2f\n    a = 1  # first case\nelse:\n    a = 2\n"
    a = calc(source)["a"]
    assert a.formula == "=IF(g>0,1,2)"
    assert a.comment == "first case"


def test_later_rows_use_the_conditional_values():
    source = SECTION_CLASS + "q = cls * 10\n"
    q = calc(source)["q"]
    assert q.formula == "=cls*10"
    assert q.cached == 10


def test_boolean_tests():
    source = "a = 1\nb = 2\nif a > 0 and b > 1:\n    g = 1\nelse:\n    g = 0\n"
    assert calc(source)["g"].formula == "=IF(AND(a>0,b>1),1,0)"


@pytest.mark.parametrize("body, match", [
    ("    a = 1\n    a = 2\n", "more than once"),
    ("    for i in range(2):\n        a = i\n", "for loops|has no Excel equivalent"),
    ("    abs(g)\n", "has no Excel equivalent"),
    ("    a, b = 1, 2\n", "single-name"),
])
def test_incompatible_branches_raise(body, match):
    source = f"g = 1\nif g > 0:\n{body}else:\n    a = 0\n"
    with pytest.raises(ExcelRendererIncompatibleError, match=match):
        rows(source)


def test_unknown_name_in_a_branch_raises_with_target():
    # zz has a value (supplied globals) but is never assigned on the sheet.
    source = "g = 1\nif g > 0:\n    a = zz\nelse:\n    a = 0\n"
    renderer = ExcelRenderer()
    with pytest.raises(ExcelRendererIncompatibleError, match="'zz'.*'a'"):
        HandCalcs(renderer=renderer)(source, supplied_globals={"g": 1, "zz": 3, "a": 3})


def test_recalculation_matches_python(tmp_path):
    pytest.importorskip("formulas")
    from scripts.excel_demo import recalculation_problems
    source = (
        SECTION_CLASS.replace("h_w = 500", "h_w = 800")
        + "k = 0\nif cls == 2:\n    if t_w > 5:\n        k = 3\n    else:\n        k = 4\n"
        + "z = cls + k\n"
    )
    result = HandCalcs(renderer=ExcelRenderer())(source)
    path = result.save(tmp_path / "cond.xlsx")
    assert recalculation_problems(path, result.rows) == []
