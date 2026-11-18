"""
A param line (``w = 5``) keeps its value in a mode without the result column,
e.g. ``ass sym`` (v1's ``%%render symbolic``): it showed only ``w``.
"""

import pytest

from handcalcs import HandCalcs
from handcalcs.renderers import ASCIIRenderer

SOURCE = "w = 5\nL = 6\nM = w * L**2 / 8\n"


def render(mode: str) -> list[str]:
    source = f'# hc: mode = "{mode}"\n{SOURCE}'
    namespace: dict = {}
    exec(source, namespace)
    return HandCalcs(ASCIIRenderer()).render_run(source, namespace).splitlines()


@pytest.mark.parametrize(
    "mode, expected",
    [
        ("ass sym", ["w = 5", "L = 6", "M = w * L² / 8"]),
        ("ass num", ["w = 5", "L = 6", "M = 5 * 6² / 8"]),
        ("sym", ["5", "6", "w * L² / 8"]),
        ("ass res", ["w = 5", "L = 6", "M = 22.5"]),
        # Only the targets: no value column to show.
        ("ass", ["w", "L", "M"]),
    ],
)
def test_param_lines_keep_their_value(mode, expected):
    assert [line for line in render(mode) if line] == expected
