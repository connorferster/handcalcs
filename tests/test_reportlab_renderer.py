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
from ym_handcalcs.flowables import BreakingParagraph, CalcBlock, CalcLine, Chip, DepthGuides, ParamGrid

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
        elif isinstance(flowable, CalcBlock):
            yield from leaves(flowable.lines, depth)
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
    line.wrap(130, 1000)
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


def test_layout_never_drops_the_numeric_row():
    # The numeric column is one unbreakable token wider than the value column;
    # the line shrinks or overflows rather than losing it. Dropping it is a
    # per-line author choice (`# hc: mode="no_num"`), not a renderer setting.
    columns = ["x", "a · b", "123456789012345678901234", "1.2e+35"]
    line = calc_line(columns)
    line.wrap(130, 1000)
    assert "no-num" not in line.layout
    assert len(line.columns) == 4
    with pytest.raises(TypeError):
        ReportLabRenderer(drop_numeric_when_narrow=True)


def test_mode_no_num_drops_the_numeric_row():
    story = render("a = 2\nb = 3\nc = a + b  # hc: mode='no_num'\n")["story"]
    calc_lines = [f for _, f in leaves(story) if isinstance(f, CalcLine)]
    assert len(calc_lines[-1].columns) == 3


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


# --- CalcBlock: runs of calc lines aligned on "=" ----------------------------

def blocks(story: list) -> list[CalcBlock]:
    found = []
    for flowable in story:
        while isinstance(flowable, DepthGuides):
            flowable = flowable.content
        if isinstance(flowable, KeepTogether):
            found.extend(blocks(flowable._content))
        elif isinstance(flowable, CalcBlock):
            found.append(flowable)
    return found


def test_consecutive_calc_lines_form_one_block():
    story = render("a = 1\nlong_name = 2\nc = a + long_name\n")["story"]
    (block,) = blocks(story)
    assert len(block.lines) == 3


def test_block_lines_share_the_target_column():
    story = render("a = 1\nlong_name = 2\nc = a + long_name\n")["story"]
    (block,) = blocks(story)
    table = block.build_table(300)
    widest = max(line.target_width() for line in block.lines)
    assert table._argW[0] == widest
    assert all(line.layout == "line" for line in block.lines)


def test_a_very_wide_target_stacks_instead_of_widening_the_column():
    source = "a = 1\n" + "b" * 30 + " = a + 1\nc = a + 2\n"
    (block,) = blocks(render(source)["story"])
    table = block.build_table(252)
    assert table._argW[0] < 252 * CalcBlock.max_target
    assert block.lines[1].layout == "stack"


def test_nested_calc_lines_form_their_own_block():
    source = "x = 1\nif x > 0:\n    y = x + 1\n    z = y + 1\nw = 2\n"
    story = render(source)["story"]
    depths = [(depth, len(f.lines)) for depth, f in block_leaves(story)]
    assert (1, 2) in depths


def block_leaves(story: list, depth: int = 0):
    for flowable in story:
        if isinstance(flowable, KeepTogether):
            yield from block_leaves(flowable._content, depth)
        elif isinstance(flowable, DepthGuides):
            yield from block_leaves([flowable.content], flowable.depth)
        elif isinstance(flowable, CalcBlock):
            yield depth, flowable


def test_long_block_splits_between_lines():
    source = "".join(f"v{n} = {n}\n" for n in range(12))
    (block,) = blocks(render(source)["story"])
    _, height = block.wrap(252, 1000)
    parts = block.split(252, height / 3)
    assert len(parts) == 2 and all(isinstance(p, CalcBlock) for p in parts)
    assert sum(len(p.lines) for p in parts) == 12
    assert 1 <= len(parts[0].lines) < 12


def test_split_never_returns_the_whole_block():
    source = "".join(f"v{n} = {n}\n" for n in range(12))
    (block,) = blocks(render(source)["story"])
    _, height = block.wrap(252, 1000)
    parts = block.split(252, height + 5)
    assert parts and len(parts[0].lines) < 12


def test_rule_marks_only_multirow_lines():
    source = "a = 1\nb = 2\nc = a + b  # hc: -m\nd = a * b\n"
    (block,) = blocks(render(source)["story"])
    block.wrap(400, 1000)
    rows = [len(line.choose(400, block.id_width(400))[1]) for line in block.lines]
    starts = [sum(rows[:i]) for i in range(len(rows))]
    assert [first for first, _, _ in block._ruled] == [starts[2]]
    assert not any(c[0] == "LINEBEFORE" for c in block._table._linecmds)
