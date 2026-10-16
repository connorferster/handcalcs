# ReportLabRenderer implementation plan / session notes

Branch: `features/reportlab_renderer` (cut from `hc2/dev`). This file is the single source of
truth for resuming the ReportLabRenderer work. Keep the checklist and progress log below up to
date.

## Status (2026-10-16, session 2)

The two pending decisions were answered:

1. **Per-line numeric/symbolic drop:** done as new values for the existing `mode` context option:
   `no_num`/`drop_numeric` and `no_sym`/`drop_symbolic`, which can be combined (`mode="no_num no_sym"`). Written
   as `# hc: mode="no_num"` or the flag form `# hc: --mode no_num` (no short letter: `-m` is `--multiline`).
   Inline it applies to that line only; standalone it persists.
   `mode_columns()` in `handcalcs/renderers/base.py` handles them, and every renderer gets them for free.
   The aliases are checked before the old substring matching because they contain `num`/`sym` themselves.
2. **ymprint block converter:** the user will build it later. Focus stays on "getting the guts right".

### Experiment: every calc line in an aligned table (branch `features/reportlab_aligned_calcs`)

User request (2026-10-16): "switch all calc lines to using tables to align around the = signs ... my motivation is
primarily readability". Keep the accent rule on the left of the table.

- `CalcBlock` (flowables.py): `ReportLabRenderer.join_items` merges each run of consecutive calc lines at one depth
  into one table, `target | = | value`, so the first `=` lines up down the run, with one accent rule for the whole run.
- `CalcLine` now emits table rows (`choose(avail_width, id_width)`); its ladder is unchanged, but `line` is a single
  row that must fit unwrapped. A standalone `CalcLine` still wraps/draws itself as a one-line block.
- Target column = widest target, ignoring targets wider than 40% of the frame (`CalcBlock.max_target`); those lines
  use `stack`. Space between lines = `hcCalc.spaceBefore` added to the line's first-row top padding.
- Page breaks: runs of 2–6 lines stay in a `KeepTogether`; longer runs split between lines, never inside one.
- Cost: cell padding takes ~18 pt per row, so a few lines move one rung down the ladder (layout golden: 7 changes).

### Summary of the work so far

The ReportLab renderer is built: Phases 0–7 are done on `features/reportlab_renderer` (pushed 2026-10-16). The full
test suite passes (478 tests after session 2).

- **What you get:** `HandCalcs(renderer=ReportLabRenderer())(source)` returns
  `{"stylesheet": StyleSheet1, "story": [flowables]}`. The code is in `src/ym_handcalcs/`, and `handcalcs` itself
  never imports it.
- **How it looks:** headings in blue with rules underneath; serif comments with `backticks` as code; import chips;
  results bold blue on a light highlight; inline comments grey italic; `if`/`else`/`for` headers in rounded tinted
  boxes with coloured indent guides for nested blocks; parameter grids centred, aligned on `=`, on a rounded
  background.
- **Overflow:** each calc line picks its layout at wrap time (one line → comment underneath → grid aligned on `=` →
  wrap at top-level, then deeper, operators → target on its own row → shorten long collections → shrink to at most 85% → overflow). Demo: 18 of 42 lines need more than one line at 252 pt, 7 of
  42 at 504 pt, none shrink or overflow. Parameter grids drop from 3 columns to 2 to 1 until they fit.
- **Changes from the plan:** break points come from scanning the rendered output (`breaking.py`), not from markers
  in the operator handlers; a "target on its own row" layout was added; mono bold-italic falls back to bold
  (ymprint has no DejaVuSansMono-BoldOblique); matplotlib was briefly added for fonts, then removed.
- **Things to know:** `doc.build(story)` empties the list (`build_pdf` passes a copy; ymprint should too). Dev PDFs
  show italics upright because the system DejaVu has no italic files. Dropping the numeric step is per line only,
  with `# hc: mode="no_num"`; the user ruled out a renderer argument (`drop_numeric_when_narrow` was removed).
- **Preview:** `uv run --with pymupdf python scripts/reportlab_demo_check.py --width 252 --png`.

## Standing instructions from the user (2026-10-15)

> Build a handcalcs renderer for display in ReportLab. It will be based off of the HTML
> renderer and will return a dictionary with the following keys: `'stylesheet'` will be a
> ReportLab Stylesheet (not SimpleStylesheet) that creates a stylesheet appropriate for
> displaying the Python calcs; `'story'` will be a ReportLab Story object that contains all of
> the rendered content. This will, ultimately, be a part of a third-party library and not part
> of handcalcs proper so only add ReportLab as a dev dependency on this branch. [...] Take
> liberty to use ReportLab's native styling options to make it look a little extra special.

- ReportLab is a **dev** dependency only (`[dependency-groups] dev`, added with
  `uv add --dev reportlab`, currently 5.0.1). `handcalcs` itself must never import it.
- Decisions (2026-10-15, answered by the user): package name `ym_handcalcs`. It will be a
  third-party **block module for ymprint**. Ymprint bundles the full DejaVu suite, so assume
  it is available under the standard ReportLab names. `build_pdf` goes in the package as an
  optional helper. Calc-line comments are inline grey italics.
- Git: **commit locally after each phase, never push** (the user pushes). The user asked for a push on 2026-10-16;
  that does not change the default.
- Do not change `HTMLRenderer` output to suit ReportLab. Put ReportLab needs in
  `ReportLabRenderer` overrides. If a genuine bug turns up that affects both renderers, raise
  it with the user instead of silently changing HTML output (same rule as the LaTeX and
  Markdown work).

## Where the code lives (decision)

The renderer will become a third-party library, so it goes in a **sibling package**, not in
`handcalcs.renderers`:

```
src/ym_handcalcs/
    __init__.py      # exports ReportLabRenderer, build_stylesheet, build_pdf
    renderer.py      # ReportLabRenderer(HTMLRenderer) + its registered handlers
    styles.py        # palette, fonts, build_stylesheet() -> StyleSheet1
    flowables.py     # DepthGuides wrapper flowable (indent guides for nested blocks)
    fonts.py         # standard DejaVu font names (+ dev/test-only registration helper)
```

- `src` is already on `sys.path` in the venv (the editable install's `.pth`), so
  `import ym_handcalcs` works in tests and scripts without packaging changes. Flit
  only builds the `handcalcs` module, so the sibling package is never shipped in the
  handcalcs wheel. Lifting it out later means moving one directory.
- `handcalcs/renderers/__init__.py` does **not** import it. Importing
  `ym_handcalcs` registers the renderer under `name = 'reportlab'` in
  `_RENDERER_REGISTRY` (via `BaseRenderer.__init_subclass__`), so
  `HandCalcs(renderer=ReportLabRenderer())` and name lookup both work.
- Jupyter: `display_class_for` falls through to `Pretty` for an unknown name. That is fine
  because ReportLab output is not meant for notebook display. No change to `jupyter.py`.

## Output contract

```python
from handcalcs import HandCalcs
from ym_handcalcs import ReportLabRenderer

result = HandCalcs(renderer=ReportLabRenderer())(source)   # or hc.demo()
result["stylesheet"]  # reportlab.lib.styles.StyleSheet1
result["story"]       # list[reportlab.platypus.Flowable] -- a flat Platypus story

SimpleDocTemplate("calcs.pdf").build(result["story"])
```

- **`stylesheet`**: a fresh `StyleSheet1` (not `getSampleStyleSheet()`), holding every
  `ParagraphStyle` the story uses, plus the named `TableStyle`s. `StyleSheet1.add` accepts
  any object with a `.name`, so `TableStyle`s are stored by setting `.name` on them (verified
  in the Phase 0 spike). Names are prefixed `hc` and have kebab-case aliases, for example
  `hcCalc` / `hc-calc`. The consuming library can use it to style its own surrounding
  content so it matches the calcs (e.g. its own headings in `hcH2`).
- **`story`**: ReportLab has no Story class. A story is a plain `list` of flowables, which is
  what `doc.build()` takes. The list is **flat** (no nested tables for block structure), so
  it splits cleanly across pages. Nesting is drawn by the `DepthGuides` wrapper (see below).
- The story's flowables hold references to the stylesheet's style objects. Editing the
  stylesheet **after** render does not restyle an existing story. Customization goes in
  **before** render: `ReportLabRenderer(stylesheet=..., palette=..., font_family=...,
  base_size=10)`. `build_stylesheet(palette, fonts, base_size)` is public, so callers can
  start from the default and tweak it.

## How it builds on HTMLRenderer

`ReportLabRenderer(HTMLRenderer)`. ReportLab's `Paragraph` mini-markup overlaps a lot with
the inline HTML that `HTMLRenderer` already emits, so most inline rules are inherited as-is:

| Inherited from HTMLRenderer | Works in ReportLab because |
|---|---|
| `swap_greeks` (Unicode Greek) | the DejaVu fonts have the glyphs (Helvetica does not, see Fonts) |
| `swap_subscripts` (`<sub>`) | `<sub>` is native Paragraph markup |
| `swap_special_symbols` (`<sup>*</sup>`, combining marks U+0302/U+0305, prime) | `<sup>` is supported, and DejaVu has the combining marks |
| `swap_py_operators` (`·`, `/`, `<sup>` powers) | same |
| `swap_angle_ops` (`&lt;` `&le;` `&gt;` `&ge;`) | ReportLab resolves these entities (spike verified) |
| `swap_sqrt_symbol` (`√`) | DejaVu glyph |
| `if_block_header` / `for_block_header` text | reused, then wrapped in callout styling |

What gets overridden:

| Hook | HTMLRenderer | ReportLabRenderer |
|---|---|---|
| `complete` | `<div class="handcalcs">` + `<style>` | `{"stylesheet": ss, "story": flowables}` |
| `create_context` | sparse context | same, plus `space=" "`. The stylesheet and fonts live on the renderer instance, not the context |
| `join_item` | returns HTML strings | returns `list[(depth, Flowable)]`, flattened by `join` |
| `heading` | `<hN>` | tagged item turned into a `Paragraph(style=hcH{N})` + optional rule + bookmark anchor |
| `comments_block` | `<p class="hc-comment">` | prose `Paragraph(style=hcComment)`, text **XML-escaped** |
| `import` | `[Python import]: ...` line | monospaced "chip" `Paragraph(style=hcImport)` |
| `calc_line:post` | (none) | marks the result column and the comment for styling (see Visual design) |
| `inline_comment` | plain text | `<font color=muted><i>...</i></font>` |
| `format_param_grid` | `<table class="hc-params">` | returns a `_Grid` marker that `join_item` turns into a `Table` |
| `format_calc_grid` | `<table class="hc-multiline">` | `_Grid` marker that becomes a left-aligned `Table` aligned on `=` |
| `header:else_block` | `Otherwise:` | same text, callout style |
| line-break directive (`"\n"`) | nothing (CSS gap) | `Spacer(1, 0.6 * base_size)` |

### Why handlers return markers, not flowables (key decision)

Handlers run during `render`, when the nesting depth is not known yet. `join_item` knows the
depth. So handlers return light-weight tagged values: a `_Grid(rows, kind)` dataclass for
grids, and a `_Tagged(kind, text)` string subclass for headings, imports and callouts.
`join_item` builds the real flowable with depth-aware indentation and widths. Base-class
code that inspects body items (`render_block_body` checks `isinstance(body[0], str)`, and
`join_item` checks `isinstance(item[-1], list)`) keeps working, because `_Tagged` *is* a
`str` and `_Grid` is neither `str` nor `list`. `join_item` checks for `_Grid` first.

## Edit from user: overflow

Similar with the Latex renderer, there is a possibility of calculation overflow. I have considered using 
ReportLab tables for layout of the calc_blocks. The ReportLab table has features that allow dynamic shrinking of content.
Since I am planning on using this renderer to render content in a US letter 1/2 size frame (half of the page on a US letter doc),
consider solutions for dealing with calculation overflow and line wrapping. This is a tricky problem and I am  open to idea here.

### Overflow: measurements and decisions (2026-10-16)

The demo, measured in DejaVu Sans at 9.5 pt: **21 of 49** lines are wider than a half-width
column (~252 pt), and 3 of 49 are wider than a half-height block (~504 pt). The worst are the
one-line `M_u` (~990 pt), `acc` (~860 pt), `x_1`/`x_2` (~495 pt), the logic rows (400–490 pt)
and the `Since …` headers (~345 pt). At these widths scaling alone is unreadable (`M_u` would
need 0.25), so wrapping and re-layout come first and shrinking is only a capped last resort.

**Decisions (user, 2026-10-16):**

- The frame **varies**: ymprint may place a block in a half-width column or a half-height
  block. So layout is decided at `wrap(availWidth, …)` time by a measuring flowable, not by a
  `frame_width` argument. The same story then fits any frame and still splits across pages.
- An explicit `# hc: -m` always gets the grid (it may still wrap inside cells). Lines without
  the flag choose their layout by measured width.
- Long collections are shortened (first and last `EDGE_ITEMS = 3` around `…`) **only when
  the full collection, wrapped at commas, would still overflow**. Otherwise every item is
  shown.
- Dropping the numeric-substitution step is allowed, but **opt-in only** (see below).

**`CalcLine` flowable and its layout ladder.** The renderer emits a `_CalcLine` marker that
holds the line's columns (target, sym, num, result), its comment, and its `-m` flag.
`join_item` turns it into a `CalcLine(Flowable)`. In `wrap()` it tries these layouts in
order and uses the first whose measured width fits `availWidth`:

1. One line (skipped when `-m` is set).
2. One line with the inline comment moved to its own muted italic line underneath.
3. Grid: `target = sym` / `= num` / `= result` in a `Table` aligned on `=`, the value column
   taking the remaining width. This is "auto `-m`".
4. Grid with **math-aware wrapping** in the value cells. Every space is non-breaking (U+00A0;
   the spike confirmed ReportLab never breaks there) except the break points before
   **top-level** operators (`+`, `−`, `·`, `/`, `and`, `or`, `,` in collections). A
   continuation line starts with its operator and gets a hanging indent.
5. As 4, but break points one nesting level deeper are allowed too, repeated until it fits
   or no deeper level is left. Collections that still overflow are shortened at this step.
6. Optional lossy step: drop the numeric row (only when enabled).
7. Shrink the font, capped at a scale of 0.85.
8. Give up: let it overflow and record it in the overflow report.

Implementation notes:
- Break points come from ReportLab-only overrides of the binary/bool-op handlers. They put
  private-use marker characters before an operator, encoding its nesting depth (for example
  U+E001 for depth 1 and U+E002 for depth 2). At each step `CalcLine` turns the markers up to
  the allowed depth into spaces and the rest into U+00A0, then wraps and checks
  `Paragraph.minWidth()` (which reports any piece wider than the frame). No changes to `base.py`.
- `wrap()` caches the result per `availWidth`. ReportLab calls `wrap` repeatedly, and tables
  and `KeepTogether` call it with trial widths.
- Each `CalcLine` records the step it used (`layout_rung`). The demo check prints an
  overflow/layout report, like the LaTeX overfull-box report. Tests snapshot the chosen step
  for every demo line at **252 pt and 504 pt**, and assert that no line reaches step 8
  except a set of known lines.
- Other overflow sources, fixed in the renderer:
  - The params grid steps down from `param_cols` (3 → 2 → 1) until it fits. This is
    measured in the grid flowable's `wrap()`.
  - `Since … is True:` / `Iterating over …` headers wrap at `→` and at top-level `and`/`or`
    (same marker scheme; headers are plain `Paragraph`s, so no ladder is needed).
  - Nested blocks need no extra handling. `DepthGuides` passes the reduced `availWidth` on
    to the wrapped `CalcLine`, so deeper lines re-layout automatically.
- **Dropping the numeric row (step 6)**: *superseded 2026-10-16.* The renderer argument
  `drop_numeric_when_narrow` and the ladder step were removed at the user's request ("this should
  not be something that can be set upon instantiation"). The layout ladder never drops content;
  the author drops the numeric row per line with `# hc: mode="no_num"` / `--mode no_num`.

### Escaping

ReportLab's paragraph parser rejects stray `&` and some `<` sequences. A bare `a < b`
happened to parse in the spike, but `a<b` and `R&D` will not. Escape (`xml.sax.saxutils.escape`)
**user prose only**: comment lines, heading text, string constants, import module names and
docstring `ExprLine`s. Generated markup (`<sub>`, entities) must not be escaped. Note:
`HTMLRenderer` has the same latent issue with comments that contain `<`/`&`. Report it to the
user rather than fixing it there.

## Fonts

Decision: ymprint ships the full DejaVu suite and registers it under the **standard names**,
so the renderer assumes those names exist. There is no discovery and no Helvetica/Symbol
fallback.

| Role | Regular | Bold | Oblique/Italic | Bold oblique |
|---|---|---|---|---|
| Math/calc lines (sans) | `DejaVuSans` | `DejaVuSans-Bold` | `DejaVuSans-Oblique` | `DejaVuSans-BoldOblique` |
| Comment prose (serif) | `DejaVuSerif` | `DejaVuSerif-Bold` | `DejaVuSerif-Italic` | `DejaVuSerif-BoldItalic` |
| Imports (mono) | `DejaVuSansMono` | `DejaVuSansMono-Bold` | `DejaVuSansMono-Oblique` | `DejaVuSansMono-BoldOblique` |

- The names are defaults in a `Fonts` dataclass that the caller can override
  (`ReportLabRenderer(fonts=Fonts(...))`) in case ymprint's names differ.
- `<b>`/`<i>` inside paragraphs need `registerFontFamily` mappings. The renderer calls
  `registerFontFamily` for the three families only if no mapping exists yet. This is
  idempotent and does not register any TTFs.
- `fonts.ensure_dejavu_registered()` is a **dev/test-only** helper. If a name is not
  registered, it registers the face from the system TTFs (`/usr/share/fonts/truetype/dejavu`
  in this sandbox, and the Phase 0 spike confirmed the glyph coverage). The demo script and
  the tests call it. The renderer never does. Inside ymprint, the fonts are already there.
- Why DejaVu is required: the built-in Helvetica has no Greek, `√` or `≤`, and ReportLab's
  bundled Vera has no Greek (spike verified).

## Visual design ("a little extra special")

Native ReportLab styling only. No images, all vector. One palette dataclass (overridable):

| Token | Default | Used for |
|---|---|---|
| `ink` | `#1F2933` | body text |
| `muted` | `#6B7785` | inline comments, imports, "no condition satisfied" notes |
| `accent` | `#1D4E89` (deep engineering blue) | headings, result values, rules |
| `accent_soft` | `#E8EFF8` | callout and param-grid backgrounds |
| `guide` | cycling `#9DB4D3`, `#B9A6D9`, `#9FCFB8` | nested-block depth guides |
| `rule` | `#C9D2DC` | hairlines |

Elements:

- **Headings**: H1 is 20 pt bold accent, followed by a 1.5 pt accent `HRFlowable`. H2 is 14 pt
  with a 0.5 pt hairline. H3 is 11.5 pt bold ink. Every heading carries
  `<a name="hc-h-N"/>` plus `keepWithNext=1`. Downstream doc templates can turn the anchors
  into PDF outline bookmarks. The demo helper below does this.
- **Comment prose**: DejaVu **Serif**, 10 pt, justified, with comfortable leading. The serif
  prose against sans-serif math reads like a hand-written calc sheet with notes.
- **Calc lines**: DejaVu Sans with a hanging indent (`leftIndent=2em`, `firstLineIndent=-2em`)
  so long substitutions wrap under the expression, not under the target. The **result**
  column is bold in `accent` on a faint `accent_soft` highlight
  (`<font backColor=...>`, spike verified). The inline comment follows after an em space in
  `muted` italic.
- **Imports**: small DejaVu Sans Mono "chip" in `muted` on a light grey `backColor` with
  `borderRadius=3`, `borderPadding=2` (both verified). Visible, but quiet.
- **Params grid**: `Table` aligned on `=` (id right, `=` centered, value left, spacer column
  between groups), centered on the page, `accent_soft` background with `ROUNDEDCORNERS`
  (verified), hairline `rule` above and below, and alternating row tint for grids with more
  than two rows. With `# hc: -h`, the comment column is muted italic.
- **Multi-line calc**: left-aligned `Table` aligned on `=`, with a 1 pt `accent` `LINEBEFORE`
  bar so it reads as one unit. The result row is bold accent, like single-line results.
- **Block headers** (`Since (...) → (...) is True:`, `Otherwise:`, `Iterating over ...`): a
  callout. The `Paragraph` has `accent_soft` `backColor`, `borderRadius`, a small `accent`
  left marker glyph (`▸`), and `keepWithNext=1`, so a header never strands at the bottom of a
  page. `->` becomes `→` only in this renderer (via the overridden header handlers).
- **Nested bodies**: indent by `indent = 1.4em` per level, with **indent guides**. Each body
  flowable is wrapped in `DepthGuides(flowable, depth, colors)`, which delegates
  `wrap`/`split`/`draw` and draws one thin vertical line per enclosing level in the left
  margin. Each guide extends through the flowable's `spaceBefore`, so consecutive guides
  join into continuous lines. This looks like a code editor's indent guides, and because the
  story stays flat it keeps page splitting intact. Nested `Table`s would make deep blocks
  unsplittable. Fallback if `DepthGuides` proves fiddly: plain `Indenter` without guides.
- **Grouping**: a calc group (`calcs_block`) gets `KeepTogether` when it is 6 lines or fewer,
  so short groups don't split across pages.

## Phases (checklist)

- [x] **Phase 0: Setup and spikes.** Branch `features/reportlab_renderer`. `uv add --dev reportlab`
  (5.0.1, also pulls pillow). Verified: `StyleSheet1` accepts a named `TableStyle`; Paragraph
  markup accepts `<sub>`, `<sup>`, `&le;`/`&ge;`/`&nbsp;`, `<font backColor>`,
  `<span backColor>`, `<a name>`; `ParagraphStyle(borderRadius=...)`; `ROUNDEDCORNERS`;
  DejaVu glyph coverage.
- [x] **Phase 1: Skeleton.** Package layout, `fonts.py`, palette, `build_stylesheet()`,
  `ReportLabRenderer.complete()` returning the dict, with `join` producing plain
  `Paragraph`s for everything (no styling yet). Add
  `scripts/reportlab_demo_check.py`: builds `reportlab_demo.pdf` from `hc.demo()` with
  `SimpleDocTemplate`, and with `--png` rasterizes pages via
  `uv run --with pymupdf` so Claude can eyeball them (no poppler/ghostscript in the sandbox).
  Add `reportlab_demo.pdf` and `reportlab_demo_build/` to `.gitignore`.
- [x] **Phase 2: Lines.** Headings, comment prose with escaping, imports, calc lines (hanging
  indent, result highlight, inline comments), expression lines, line-break spacers, flat
  blocks.
- [x] **Phase 3: Blocks.** Callout headers for if/elif/else/for/function blocks,
  `DepthGuides` flowable, `keepWithNext`, the "No conditions were satisfied" note.
- [x] **Phase 4: Grids.** `_Grid` marker, params `Table` (both `;` and `# hc: -h` forms),
  multi-line calc `Table`.
- [x] **Phase 5: Overflow.** `_CalcLine` marker and `CalcLine` flowable with the layout
  ladder (steps 1–8 above), depth-tagged break markers in the operator handlers, shortening
  collections only on overflow, `drop_numeric_when_narrow`, params-grid column step-down,
  wrapping of block headers, and the overflow/layout report in the demo script. Check by eye
  at 252 pt and 504 pt (the demo script takes `--width`).
- [x] **Phase 6: Polish.** `KeepTogether` grouping, the optional
  `build_pdf(result, path, title=...)` helper (page footer with page numbers, outline
  bookmarks from heading anchors via `afterFlowable`). The helper is for the demo and
  downstream convenience. The renderer itself only returns the dict.
- [x] **Phase 7: Tests.** `tests/test_reportlab_renderer.py` with
  `pytest.importorskip("reportlab")`:
  - contract: dict keys, `StyleSheet1` type, every style the story uses is in the
    stylesheet, the story is a flat list of `Flowable`s;
  - the demo builds to an in-memory PDF without error (catches any Paragraph markup that
    fails to parse);
  - escaping: comments with `<`, `&`, `>` survive;
  - golden file `tests/golden/reportlab_demo.txt`: a textual dump of the story (flowable
    class, style name, depth, text or cell grid), regenerated with
    `HANDCALCS_UPDATE_GOLDEN=1` like the LaTeX and Markdown goldens. Do not golden the PDF
    bytes, which contain timestamps and IDs.
  - overflow: snapshot the layout step of every demo calc line at 252 pt and 504 pt, and
    check the known-overflow set (like `KNOWN_OVERFULL` in the LaTeX tests).

## How to check progress

```bash
uv run python scripts/reportlab_demo_check.py            # writes reportlab_demo.pdf
uv run python scripts/reportlab_demo_check.py --width 252   # frame width in pt (default: half-width column)
uv run --with pymupdf python scripts/reportlab_demo_check.py --png   # + page PNGs to inspect
uv run pytest tests/test_reportlab_renderer.py           # golden: HANDCALCS_UPDATE_GOLDEN=1
```

Ad-hoc probe:
`uv run python -c "from handcalcs import HandCalcs; from ym_handcalcs import ReportLabRenderer; r = HandCalcs(renderer=ReportLabRenderer())('x = 1'); print(r['story'])"`

## Resolved questions (2026-10-15)

1. Package name: `ym_handcalcs` (a ymprint block module).
2. Fonts: ymprint bundles DejaVu under the standard names, so assume they exist. No
   discovery and no fallback.
3. `build_pdf`: in the package, optional.
4. Calc-line comments: inline grey italics.
5. Git: commit locally after each phase. The user pushes.
6. Overflow (2026-10-16): the frame varies, so layout is measured at wrap time. `-m` forces
   the grid. Collections are shortened only on overflow. Dropping the numeric row is
   opt-in. See "Overflow: measurements and decisions".

## Progress log

- 2026-10-15: Branch created from `hc2/dev`. ReportLab 5.0.1 added as a dev dependency
  (`uv.lock` is gitignored, so only `pyproject.toml` changes). Feasibility spikes done
  (Phase 0). This plan written.
- 2026-10-15: The user answered the open questions (see above). Plan updated: package
  `ym_handcalcs`, DejaVu assumed under the standard names, commit locally only.
- 2026-10-16: The user added the overflow section. Overflow options were discussed and
  decided (see "Overflow: measurements and decisions"). Added Phase 5 (Overflow); Polish and
  Tests are now Phases 6 and 7.
- 2026-10-16: **Phase 1 done.** `src/ym_handcalcs/` has `fonts.py` (`Fonts` with the standard DejaVu names,
  `register_families` leaves existing mappings alone, the dev-only `ensure_dejavu_registered`), `styles.py` (`Palette`,
  `Metrics`, `build_stylesheet`), `markers.py` (`Tagged`, `CalcComponents`, `Grid`) and `renderer.py`. The demo
  builds (68 flowables). Findings:
  - ymprint (at `~/ymprint`) bundles DejaVu, but **DejaVuSansMono has no BoldOblique**, so `Fonts.mono.bold_italic`
    defaults to `DejaVuSansMono-Bold`. ymprint's `register_fonts` also sets the family mappings itself.
  - This sandbox's system DejaVu has no italic faces. The dev helper registers the regular face under the missing
    names, so dev PDFs show italics upright. matplotlib was briefly added for its fonts and then removed, to keep
    ReportLab as the only new dev dependency.
  - `doc.build(story)` **consumes** the list. The demo script passes a copy. Note this for ymprint integration.
  - ymprint block converters have the signature `convert(block_key, block_value, context) -> list[Flowable]` and scale
    with `blockstyles.block_scale(context)`. The future block converter maps that scale onto `base_size`.
- 2026-10-16: **Phase 2 done.** H1 and H2 get accent and hairline rules. Every heading paragraph carries
  `hc_outline = (key, text, level)` for bookmarks; keys come from a process-wide counter, so they stay unique when
  several calc blocks share one document. Prose is serif with `backtick` spans in mono. Imports use a `Chip` flowable
  (rounded background as wide as the text). Calc lines use a hanging indent and `autoLeading="max"`. The result is bold
  accent on a highlight (only when the line has a substitution). Comments are muted italic. Escaped: headings, comment
  lines, inline comments, string constants and docstrings. The "No conditions were satisfied" text becomes a note.
  Base-level oddities seen (not ReportLab-specific, left alone): comparison operators have no spaces around them
  (`temp<temp_max`), and `acc.append(value) = acc.append(11.31)`.
- 2026-10-16: **Phase 3 done.** `DepthGuides(content, depth, indent, colors)` indents a leaf flowable, draws one guide
  per enclosing level (through spaceBefore/After so guides join), and delegates `split`. `join_item` wraps leaves
  only: nested results come back wrapped in `_Placed` so they are never wrapped twice. Headers are callouts with a `▸`
  marker and accent keywords (`Since … → … is True:`, `Otherwise:`, `Iterating over each … in …:`), and
  `keepWithNext` keeps a header with its first body line.
- 2026-10-16: **Phase 4 done.** `ParamGrid` and `CalcGrid` build their `Table` in `wrap()` (so they know the frame
  width). `ParamGrid` is centred, aligned on `=`, rounded `accent_soft` background, zebra rows above 2 rows, and steps
  down from `param_cols` to 1 until it fits. That Phase 5 item is done early: the demo's `-h` grid drops to 2
  columns at 252 pt. `CalcGrid` (`-m`) has an accent bar; the value column takes the remaining width and wraps;
  the result row is highlighted. Inline comments are styled once in `render_inline_comment`, so calc lines, `-m`
  grids and params grids match. The grid splits the result from the comment on `comment_open`. Gotchas:
  `VALIGN BASELINE` is invalid for flowable cells (TOP is used); `Flowable.__init__` sets `hAlign` on the instance.
  Seen at 252 pt, for Phase 5: wrapping breaks at any space, sub/superscripts collide across wrapped lines
  (`autoLeading="max"` does not cover sub descent), and wrapped callout headers need a hanging indent.
- 2026-10-16: **Phase 5 done.** It differs from the plan in three ways:
  - **No marker characters in the operator handlers.** `breaking.py` scans the *rendered* markup instead: brackets
    give the depth, the token after a space gives the operator class (0 relations/`and`/`or`/`→`/words, 1 `+ −` and
    commas, 2 `· / // %`), and rank = depth·3 + class. A space after an operator is never a break, so continuation
    lines start with the operator. Tags are skipped. This needs no handler changes.
  - A **`stack`** layout (target on its own row, then `= …` rows) runs after the `grid` steps, for targets too
    wide to share a row (`acc.append(value_computed)` at depth 2 in a 252 pt frame).
  - The fit check wraps each cell and compares every line with its own available width (`fits_width`).
    `minWidth()` ignored the hanging indent.
  Gotcha: ReportLab's default `splitLongWords=1` chops a too-long non-breaking run mid-token, so everything seemed
  to fit. All math styles set `splitLongWords=0`; prose keeps the default.
  Other pieces: `CalcLine` caches its layout per width, keeps grids of 4 rows or fewer whole (no page split), and
  tables are `hAlign="LEFT"` (split parts used to be centred). `BreakingParagraph` draws the header callout
  background itself so the hanging indent stays inside the box. Leading is 1.55 for calc lines and headers, so
  sub/superscripts no longer collide. `drop_numeric_when_narrow` is a renderer argument.
  Demo layout report: 252 pt has 42 calc lines, 18 not on one line, 0 shrink/overflow. 504 pt has 7 not on one
  line, 0 shrink/overflow.
- 2026-10-16: **Phase 6 done.**
  - A headerless group of 2–6 lines is wrapped in `KeepTogether` (`keep_together_max`).
  - `pdf.py` adds `HandcalcsDocTemplate` and `build_pdf(result, path, title=, frame_width=)`: bookmarks from
    `hc_outline` (levels clamped so the outline never skips a level), a footer with the title and page number, and a
    centred narrower frame for previews. The demo script uses it.
  - ReportLab-only: comparison operators are spaced (`a < b`), `!=` renders as `≠`, and `breaking` treats them as
    relations.
- 2026-10-16: **Phase 7 done.** `tests/test_reportlab_renderer.py` has 30 tests:
  - contract and stylesheet coverage, name registration, the missing-font error;
  - golden files `tests/golden/reportlab_demo.txt` (story dump) and `reportlab_layouts.txt` (layout per calc line at
    252 and 504 pt), regenerated with `HANDCALCS_UPDATE_GOLDEN=1`;
  - no shrink/overflow in the demo at either width (`KNOWN_OVERFULL` equivalent: an empty set);
  - builds at 160, 252 and 504 pt, and `build_pdf` writes bookmarks;
  - escaping, break ranking, elision, and every rung of the ladder (including `drop_numeric_when_narrow`);
  - params grid step-down and the short-grid no-split rule.
  The full suite passes: 465 passed, 2 skipped.

## Open items (after Phase 7)

- **ymprint block converter** (not started; the user will build it later): `convert(block_key, block_value, context)` that renders a source string
  or `.py` path with `ReportLabRenderer(base_size=<body size × block_scale(context)>)` and returns the story. Needs
  the user's call on the block key (e.g. `_handcalcs`) and on where the module lives.
- ~~Per-line `# hc:` flag for dropping the numeric row~~: done as `mode="no_num"` / `mode="no_sym"` (see Status).
- Base-level oddities seen in every renderer (left alone): string values render without quotes (`steel`), and
  `acc.append(x) = acc.append(11.31)`.
- `HTMLRenderer` does not escape `<`/`&` in comments (latent; ReportLab escapes its own).
- Dev PDFs show italics upright, because the system DejaVu has no italic faces. Inside ymprint the real italics are
  used.
