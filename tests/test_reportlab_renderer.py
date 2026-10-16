"""
Tests for ym_handcalcs.ReportLabRenderer, run through the full HandCalcs
pipeline (source -> parser -> HcSequence -> ReportLabRenderer -> complete()).

- Contract: ``complete()`` returns ``{"stylesheet": StyleSheet1, "story": [...]}``
  and every style the story uses is in the stylesheet.
- Golden files (regenerate with ``HANDCALCS_UPDATE_GOLDEN=1 uv run pytest
  tests/test_reportlab_renderer.py`` and review the diff):
  ``reportlab_demo.txt`` is a text dump of the demo story (flowable kind,
  style, depth, markup); ``reportlab_layouts.txt`` is the layout every demo calc
  line chooses at 252 pt and 504 pt (see ``CalcLine``).
- Build tests: the demo builds to a PDF at several frame widths, which catches
  paragraph markup that ReportLab cannot parse.
- Focused tests: escaping, break ranking, collection elision and the overflow
  ladder.

The DejaVu fonts are registered from the system (``ensure_dejavu_registered``),
as ymprint would have done.
"""
import io
import os
import pathlib

import pytest

pytest.importorskip("reportlab")

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import StyleSheet1
from reportlab.platypus import (
    Flowable, HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
)

from handcalcs import HandCalcs
from ym_handcalcs import Fonts, FontFamily, ReportLabRenderer, build_pdf, ensure_dejavu_registered
from ym_handcalcs.breaking import NBSP, elide_collections, ranked_breaks, with_breaks
from ym_handcalcs.flowables import BreakingParagraph, CalcLine, Chip, DepthGuides, ParamGrid

GOLDEN_DIR = pathlib.Path(__file__).parent / "golden"
UPDATE_GOLDEN = os.environ.get("HANDCALCS_UPDATE_GOLDEN") == "1"
WIDTHS = (252, 504)

ensure_dejavu_registered()


def render(source: str, **kwargs) -> dict:
    return HandCalcs(renderer=ReportLabRenderer(**kwargs))(source)


def demo(**kwargs) -> dict:
    return HandCalcs(renderer=ReportLabRenderer(**kwargs)).demo()


def build(story: list, width: float = 252) -> None:
    """Lay ``story`` out in a ``width``-point frame (fills in every CalcLine.layout)."""
    margin = (letter[0] - width) / 2
    doc = SimpleDocTemplate(io.BytesIO(), pagesize=letter, leftMargin=margin, rightMargin=margin)
    doc.build(list(story))


def leaves(story: list, depth: int = 0):
    """``(depth, flowable)`` for every leaf flowable, through groups and depth wrappers."""
    for flowable in story:
        if isinstance(flowable, KeepTogether):
            yield from leaves(flowable._content, depth)
        elif isinstance(flowable, DepthGuides):
            yield from leaves([flowable.content], flowable.depth)
        else:
            yield depth, flowable


def describe(depth: int, flowable: Flowable) -> str:
    pad = "  " * depth
    clean = lambda text: str(text).replace(NBSP, "~")
    if isinstance(flowable, CalcLine):
        comment = f" | {clean(flowable.comment)}" if flowable.comment else ""
        grid = " [-m]" if flowable.forced_grid else ""
        return f"{pad}CalcLine{grid}: {' = '.join(map(clean, flowable.columns))}{comment}"
    if isinstance(flowable, ParamGrid):
        cells = "; ".join(" ".join(clean(part) for part in cell if part) for cell in flowable.cells)
        return f"{pad}ParamGrid(cols={flowable.cols}): {cells}"
    if isinstance(flowable, BreakingParagraph):
        return f"{pad}Header: {clean(flowable.markup)}"
    if isinstance(flowable, Chip):
        return f"{pad}Chip: {clean(flowable.paragraph.text)}"
    if isinstance(flowable, Paragraph):
        return f"{pad}Paragraph[{flowable.style.name}]: {clean(flowable.text)}"
    if isinstance(flowable, HRFlowable):
        return f"{pad}Rule"
    if isinstance(flowable, Spacer):
        return f"{pad}Spacer"
    return f"{pad}{type(flowable).__name__}"


def dump(story: list) -> str:
    return "\n".join(describe(depth, flowable) for depth, flowable in leaves(story)) + "\n"


def layouts(width: float) -> str:
    story = demo()["story"]
    build(story, width)
    lines = [
        f"{flowable.layout:<24} {flowable.columns[0]}"
        for _, flowable in leaves(story) if isinstance(flowable, CalcLine)
    ]
    return f"# frame width {width} pt\n" + "\n".join(lines) + "\n"


def check_golden(name: str, actual: str) -> None:
    path = GOLDEN_DIR / name
    if UPDATE_GOLDEN:
        path.write_text(actual)
    assert path.exists(), f"missing golden file {path}; run with HANDCALCS_UPDATE_GOLDEN=1"
    assert actual == path.read_text()


# -- contract ---------------------------------------------------------------

def test_complete_returns_stylesheet_and_flat_story():
    result = demo()
    assert set(result) == {"stylesheet", "story"}
    assert isinstance(result["stylesheet"], StyleSheet1)
    assert isinstance(result["story"], list)
    assert all(isinstance(flowable, Flowable) for flowable in result["story"])


def test_every_paragraph_style_is_in_the_stylesheet():
    result = demo()
    sheet = result["stylesheet"]
    names = set()
    for _, flowable in leaves(result["story"]):
        if isinstance(flowable, (Paragraph, BreakingParagraph)):
            names.add(flowable.style.name)
        elif isinstance(flowable, CalcLine):
            names.update(style.name for style in flowable.styles.values())
    assert names
    for name in names:
        assert name in sheet, name


def test_stylesheet_has_aliases_and_table_styles():
    sheet = demo()["stylesheet"]
    assert sheet["hc-calc"] is sheet["hcCalc"]
    assert sheet["hcParams"].getCommands()
    assert sheet["hcCalcGrid"].getCommands()


def test_renderer_is_registered_by_name():
    from handcalcs.renderers import get_renderer

    assert get_renderer("reportlab") is ReportLabRenderer


def test_missing_fonts_raise_a_helpful_error():
    fonts = Fonts(sans=FontFamily("NoSuchFont", "NoSuchFont-B", "NoSuchFont-I", "NoSuchFont-BI"))
    with pytest.raises(ValueError, match="ensure_dejavu_registered"):
        ReportLabRenderer(fonts=fonts)


# -- golden -------------------------------------------------------------------

def test_demo_story_matches_golden():
    check_golden("reportlab_demo.txt", dump(demo()["story"]))


def test_demo_layouts_match_golden():
    check_golden("reportlab_layouts.txt", "".join(layouts(width) for width in WIDTHS))


@pytest.mark.parametrize("width", WIDTHS)
def test_no_demo_line_shrinks_or_overflows(width):
    story = demo()["story"]
    build(story, width)
    bad = [
        (flowable.layout, flowable.columns[0])
        for _, flowable in leaves(story)
        if isinstance(flowable, CalcLine) and flowable.layout.startswith(("shrink", "overflow"))
    ]
    assert bad == []


# -- building -------------------------------------------------------------------

@pytest.mark.parametrize("width", [160, 252, 504])
def test_demo_builds(width):
    build(demo()["story"], width)


def test_build_pdf_writes_bookmarks(tmp_path):
    pdf = build_pdf(demo(), tmp_path / "demo.pdf", title="Demo", frame_width=252)
    data = pdf.read_bytes()
    assert data.startswith(b"%PDF")
    assert b"/Outlines" in data


def test_heading_outline_keys_are_unique_across_renders():
    keys = []
    for _ in range(2):
        for _, flowable in leaves(render("## A\n## B\nx = 1")["story"]):
            if hasattr(flowable, "hc_outline"):
                keys.append(flowable.hc_outline[0])
    assert len(keys) == 4 and len(set(keys)) == 4


def test_nested_blocks_carry_their_depth():
    source = "a = 1\nif a > 0:\n    if a < 2:\n        b = a + 1\n"
    found = [(depth, type(flowable).__name__) for depth, flowable in leaves(render(source)["story"])]
    assert found == [(0, "CalcLine"), (0, "BreakingParagraph"), (1, "BreakingParagraph"), (2, "CalcLine")]


# -- escaping -------------------------------------------------------------------

def test_user_text_is_escaped():
    source = (
        "## R&D <notes>\n"
        "# Prose with <angle> & ampersand and `code`\n"
        'label = "a<b & c" # note: x<y & z\n'
    )
    story = render(source)["story"]
    text = dump(story)
    assert "R&amp;D &lt;notes&gt;" in text
    assert "Prose with &lt;angle&gt; &amp; ampersand" in text
    assert "a&lt;b &amp; c" in text
    assert "x&lt;y &amp; z" in text
    build(story)


def test_backticks_in_prose_become_code():
    text = dump(render("# use `math.pi` here\nx = 1")["story"])
    assert '<font name="DejaVuSansMono">math.pi</font>' in text


# -- breaking --------------------------------------------------------------------

def test_breaks_rank_top_level_operators_first():
    markup = "(a + b · c) / (2 · d)"
    assert with_breaks(markup, 0).replace(NBSP, "~") == "(a~+~b~·~c)~/~(2~·~d)"
    assert with_breaks(markup, 2).replace(NBSP, "~") == "(a~+~b~·~c) /~(2~·~d)"
    assert with_breaks(markup, 4).replace(NBSP, "~") == "(a +~b~·~c) /~(2~·~d)"
    assert with_breaks(markup, 5).replace(NBSP, "~") == "(a +~b ·~c) /~(2 ·~d)"


def test_breaks_never_split_tags_or_follow_an_operator():
    markup = '<font color="#123456">x</font> + y'
    ranks = ranked_breaks(markup)
    assert all(markup[idx] == " " for idx in ranks)
    assert list(ranks.values()) == [1, None]


def test_collection_commas_break_after_the_comma():
    assert with_breaks("[1, 2, 3]", 4).replace(NBSP, "~") == "[1, 2, 3]"
    assert with_breaks("[1, 2, 3]", 3).replace(NBSP, "~") == "[1,~2,~3]"


def test_elide_collections():
    long = "[" + ", ".join(str(n) for n in range(20)) + "]"
    assert elide_collections(long) == "[0, 1, 2, …, 17, 18, 19]"
    assert elide_collections("[1, 2, 3]") == "[1, 2, 3]"


# -- the layout ladder -------------------------------------------------------------

def calc_line(columns, comment=None, forced_grid=False, **kwargs):
    return ReportLabRenderer(**kwargs).calc_line(columns, comment, forced_grid)


def test_short_line_stays_on_one_line():
    line = calc_line(["x", "a + b", "1 + 2", "3"])
    line.wrap(400, 1000)
    assert line.layout == "line"


def test_comment_moves_under_a_line_that_fits_without_it():
    comment = '<font color="#6B7785"><i>(a fairly long explanatory comment)</i></font>'
    line = calc_line(["x", "a + b", "1 + 2", "3"], comment)
    line.wrap(110, 1000)
    assert line.layout == "line+comment"


def test_forced_grid_skips_the_one_line_layouts():
    line = calc_line(["x", "a + b", "1 + 2", "3"], forced_grid=True)
    line.wrap(400, 1000)
    assert line.layout == "grid"


def test_hc_m_command_forces_a_grid():
    story = render("a = 1\n# hc: -m\nb = a + 1\n")["story"]
    build(story, 504)
    forced = [f for _, f in leaves(story) if isinstance(f, CalcLine) and f.forced_grid]
    assert len(forced) == 1 and forced[0].layout == "grid"


def test_long_line_wraps_at_top_level_operators():
    sym = " + ".join(f"term{n} · factor{n}" for n in range(8))
    line = calc_line(["x", sym, "1", "2"])
    line.wrap(220, 1000)
    assert line.layout == "grid:break1"


def test_drop_numeric_is_opt_in():
    # The numeric column is one unbreakable token wider than the value column.
    columns = ["x", "a · b", "123456789012345678901234", "1.2e+35"]
    default = calc_line(columns)
    default.wrap(130, 1000)
    assert not default.layout.endswith("no-num")
    dropped = calc_line(columns, drop_numeric_when_narrow=True)
    dropped.wrap(130, 1000)
    assert "no-num" in dropped.layout


def test_unfittable_line_shrinks_then_overflows():
    line = calc_line(["x", "a", "123456789012", "123456789012"])
    line.wrap(95, 1000)
    assert line.layout.startswith("shrink:")
    line.wrap(60, 1000)
    assert line.layout.startswith("overflow:")


def test_short_grid_is_not_split_across_pages():
    line = calc_line(["x", "a + b", "1 + 2", "3"], forced_grid=True)
    line.wrap(400, 1000)
    assert line.split(400, 10) == []


def test_params_grid_steps_down_columns_to_fit():
    story = render("# hc: -h\nalpha_1 = 1 # first\nbeta_2 = 2 # second\ngamma_3 = 3 # third\n")["story"]
    grid = next(f for _, f in leaves(story) if isinstance(f, ParamGrid))
    grid.wrap(500, 1000)
    wide = grid.cols_used
    grid.wrap(150, 1000)
    assert wide == 3 and grid.cols_used == 1
