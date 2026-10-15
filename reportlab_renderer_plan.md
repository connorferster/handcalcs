# ReportLabRenderer implementation plan / session notes

Branch: `features/reportlab_renderer` (cut from `hc2/dev`). This file is the single source of
truth for resuming the ReportLabRenderer work. Keep the checklist and progress log below up to
date.

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
- Git: **commit locally after each phase, never push** (the user pushes).
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
- [ ] **Phase 1: Skeleton.** Package layout, `fonts.py`, palette, `build_stylesheet()`,
  `ReportLabRenderer.complete()` returning the dict, with `join` producing plain
  `Paragraph`s for everything (no styling yet). Add
  `scripts/reportlab_demo_check.py`: builds `reportlab_demo.pdf` from `hc.demo()` with
  `SimpleDocTemplate`, and with `--png` rasterizes pages via
  `uv run --with pymupdf` so Claude can eyeball them (no poppler/ghostscript in the sandbox).
  Add `reportlab_demo.pdf` and `reportlab_demo_build/` to `.gitignore`.
- [ ] **Phase 2: Lines.** Headings, comment prose with escaping, imports, calc lines (hanging
  indent, result highlight, inline comments), expression lines, line-break spacers, flat
  blocks.
- [ ] **Phase 3: Blocks.** Callout headers for if/elif/else/for/function blocks,
  `DepthGuides` flowable, `keepWithNext`, the "No conditions were satisfied" note.
- [ ] **Phase 4: Grids.** `_Grid` marker, params `Table` (both `;` and `# hc: -h` forms),
  multi-line calc `Table`.
- [ ] **Phase 5: Polish.** `KeepTogether` grouping, the optional
  `build_pdf(result, path, title=...)` helper (page footer with page numbers, outline
  bookmarks from heading anchors via `afterFlowable`). The helper is for the demo and
  downstream convenience. The renderer itself only returns the dict.
- [ ] **Phase 6: Tests.** `tests/test_reportlab_renderer.py` with
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

## How to check progress

```bash
uv run python scripts/reportlab_demo_check.py            # writes reportlab_demo.pdf
uv run --with pymupdf python scripts/reportlab_demo_check.py --png   # + page PNGs to inspect
uv run pytest tests/test_reportlab_renderer.py           # once Phase 6 exists
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

## Progress log

- 2026-10-15: Branch created from `hc2/dev`. ReportLab 5.0.1 added as a dev dependency
  (`uv.lock` is gitignored, so only `pyproject.toml` changes). Feasibility spikes done
  (Phase 0). This plan written.
- 2026-10-15: The user answered the open questions (see above). Plan updated: package
  `ym_handcalcs`, DejaVu assumed under the standard names, commit locally only.
