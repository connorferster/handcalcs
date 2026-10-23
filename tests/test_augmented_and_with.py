"""
Augmented assignment (``a += b``, shown as ``a = a + b``) and ``with`` blocks
(shown as their body), from the v2.0rc1 release review's known limitations.
"""
import pytest

from handcalcs import HandCalcs, handcalc
from handcalcs.renderers import ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer

TEXT_RENDERERS = [ASCIIRenderer, HTMLRenderer, LatexRenderer, MarkdownRenderer]


def ascii(source: str) -> str:
    return HandCalcs(ASCIIRenderer())(source)


# -- augmented assignment -----------------------------------------------------


def test_augmented_assignment_shows_the_values_before_and_after():
    lines = ascii("a = 1\nb = 2\na += b\nc = a * 2\n").splitlines()
    assert lines[2] == "a = a + b = 1 + 2 = 3"
    assert lines[3] == "c = a * 2 = 3 * 2 = 6"


@pytest.mark.parametrize(
    "line, expected",
    [
        ("a -= 0.5", "a = a - 0.5 = 3 - 0.5 = 2.5"),
        ("a *= 2", "a = a * 2 = 3 * 2 = 6"),
        ("a /= 2", "a = a / 2 = 3 / 2 = 1.5"),
        ("a //= 2", "a = a // 2 = 3 // 2 = 1"),
        ("a %= 2", "a = a % 2 = 3 % 2 = 1"),
        ("a **= 2", "a = a² = 3² = 9"),
    ],
)
def test_every_augmented_operator(line, expected):
    assert ascii(f"a = 3\n{line}\n").splitlines()[1] == expected


def test_augmented_value_is_bracketed_by_precedence():
    lines = ascii("a = 2\nb = 3\na *= b + 1\na -= b - 1\n").splitlines()
    assert lines[2] == "a = a * (b + 1) = 2 * (3 + 1) = 8"
    assert lines[3] == "a = a - (b - 1) = 8 - (3 - 1) = 6"


def test_augmented_inline_comment_shows_the_new_value():
    assert ascii("a = 1\na += 1  # now {{a}}\n").splitlines()[1] == (
        "a = a + 1 = 1 + 1 = 2 (now 2)"
    )


def test_accumulator_in_a_loop_shows_the_last_pass():
    output = ascii("total = 0\nfor x in [1, 2, 3]:\n    total += x\n")
    assert "total = total + x = 3 + 3 = 6" in output


def test_augmented_assignment_in_a_branch():
    output = ascii("a = 1\nif a > 0:\n    a += 10\n")
    assert "a = a + 10 = 1 + 10 = 11" in output


@pytest.mark.parametrize("renderer", TEXT_RENDERERS)
def test_augmented_assignment_in_every_renderer(renderer):
    output = HandCalcs(renderer())("a = 2\nb = 3\na += b\n")
    assert "5" in output
    assert output.count("3") >= 2  # b's value, and in a's substitution


def test_augmented_assignment_in_word():
    pytest.importorskip("docx")
    from handcalcs.renderers.word import WordRenderer

    xml = HandCalcs(WordRenderer())("a = 2\nb = 3\na += b\n").element.xml
    assert xml.count("<m:oMath>") + xml.count("<m:oMath ") >= 1
    assert ">5<" in xml


def test_augmented_assignment_in_the_decorator():
    @handcalc(ASCIIRenderer())
    def accumulate(a, b):
        total = a
        total += b
        return total

    result, output = accumulate(2, 3)
    assert result == 5
    assert "total = total + b = 2 + 3 = 5" in output


# -- with blocks ----------------------------------------------------------------


WITH_SOURCE = """\
import decimal
a = 2
with decimal.localcontext() as ctx:
    b = a * 3  # inside
    # trailing comment
c = b + 1
"""


def test_with_block_shows_its_body():
    lines = ascii(WITH_SOURCE).splitlines()
    assert "b = a * 3 = 2 * 3 = 6 (inside)" in lines
    assert "trailing comment" in lines
    assert lines[-1] == "c = b + 1 = 6 + 1 = 7"
    assert not any("decimal.localcontext" in line or "ctx" in line for line in lines[1:])


def test_with_block_body_is_not_indented():
    lines = ascii(WITH_SOURCE).splitlines()
    assert any(line.startswith("b = ") for line in lines)


def test_with_block_inside_a_branch():
    source = "import decimal\na = 1\nif a > 0:\n    with decimal.localcontext():\n        b = a + 1\n"
    assert "b = a + 1 = 1 + 1 = 2" in ascii(source)


def test_nested_with_blocks():
    source = (
        "import decimal\na = 1\n"
        "with decimal.localcontext():\n"
        "    with decimal.localcontext():\n"
        "        b = a + 1\n"
    )
    assert ascii(source).splitlines()[-1] == "b = a + 1 = 1 + 1 = 2"


@pytest.mark.parametrize("renderer", TEXT_RENDERERS)
def test_with_block_in_every_renderer(renderer):
    output = HandCalcs(renderer())(WITH_SOURCE)
    assert "localcontext" not in output
    assert "6" in output and "7" in output
