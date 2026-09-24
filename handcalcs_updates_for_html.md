# handcalcs implementation changes for the HTML renderer (Alternative C)

This documents the changes made to the handcalcs rendering pipeline to implement
**Alternative C** from `HTML_alternatives.md`: a semantic nested-`<div>` structure
whose vertical rhythm and indentation are owned entirely by one scoped stylesheet,
sharpened with contemporary CSS (flex-column `gap`, `:where()` zero-specificity
scoping, logical properties, custom-property knobs, tabular numerals, dark mode).

Branch: `sub/html_alternatives`.

## Summary

**All changes are confined to `src/handcalcs/renderers/html.py`.** No change was
required to `base.py`, `plaintext.py`, or `latex.py` — the plain-text and any other
renderers are untouched, and the shared `BaseRenderer.join` / `_join_item` logic is
left intact for them. This confirms the assessment's premise that Alternative C is
implementable without editing the shared pipeline.

The HTML renderer now emits, for the demo:

```html
<div class="handcalcs">
  <style>/* scoped rules, once */</style>
  <h1>HandCalcs v2.0 Demo</h1>
  <p class="hc-comment">…prose paragraph…</p>
  <div class="hc-line">a = 5.25</div>
  <div class="hc-block">
    <div class="hc-header">Since (…) is True:</div>
    <div class="hc-body">
      <div class="hc-line">class_section = 3</div>
    </div>
  </div>
</div>
```

## Changes to `src/handcalcs/renderers/html.py`

### 1. Scoped stylesheet + single wrapper (`HTMLRenderer.STYLE`, `complete`)
- Added a class-level `STYLE` string holding the whole scoped stylesheet.
- `complete()` now wraps the joined body once in
  `<div class="handcalcs"><style>…</style>{body}</div>`, injecting the stylesheet a
  single time at the top.
- The stylesheet owns **all** spacing/indentation via two custom-property knobs:
  - `--hc-gap` (inter-line spacing, applied through flex-column `gap`, so there is
    no margin-collapse/doubling to reason about and no per-line `<br>`);
  - `--hc-indent` (block indentation via `padding-inline-start`, a logical property
    that stays correct under RTL / vertical writing modes).
  - Every rule is scoped with `:where(…)` so it contributes **zero specificity** and
    a host page's own styles always win over the renderer defaults.
  - `font-variant-numeric: tabular-nums` aligns stacked numbers in columns.
  - A `@media (prefers-color-scheme: dark)` block adapts to notebook dark themes.

### 2. Structural indentation, not `&nbsp;` (`create_context`)
- Dropped the `indent='&nbsp;&nbsp;&nbsp;&nbsp;'` override. Indentation is now
  structural (nested `.hc-body` + `padding-inline-start`), so no `&nbsp;` text prefix
  is injected into the render context. This removes the stray `&nbsp;`-prefixed block
  tags (e.g. `&nbsp;×8<p>`) seen in the old output.

### 3. New `_join_item` override (nested `<div>` emission)
- `HTMLRenderer` now overrides only `_join_item`; it reuses the inherited `join` /
  `_join_items` (which call `self._join_item`). The dispatch mirrors
  `BaseRenderer._join_item` exactly — same master-list shapes — but the emitted
  markup is nested `<div>`s instead of indent-prefixed, `\n`-terminated lines:
  - **bare string** → passes through untouched if it is already block-level HTML
    (a heading, a prose `<p>`); a multi-line plain string (a params grid) becomes
    `<div class="hc-line hc-params">…</div>` (whitespace preserved); any other plain
    text becomes `<div class="hc-line">…</div>`.
  - **`[header, body]` with a non-empty header** → `hc-block` wrapping an `hc-header`
    line and an indented `hc-body`; nesting recurses, so nested if/for blocks nest
    structurally.
  - **headerless (flat) block** (a `CommentsBlock`/`CalcsBlock` group) → its body
    emitted directly at the current level, no wrapper.
  - **all-string list** (a calc line, an import) → one `hc-line` joined by a space.
  - Falsy items and one-shot line-break directives emit nothing — the CSS `gap`
    owns vertical rhythm — so no stray blank lines / empty elements.
- `depth` is retained in the signature for parity with the base method but is unused:
  indentation comes from CSS nesting, not a depth-scaled text prefix.

### 4. Params grid as preserved-whitespace block (`format_param_grid` override)
- `format_param_grid` now calls `super().format_param_grid(...)` (reusing the base
  plain-text column layout) and wraps the result in `<div class="hc-params">`, whose
  `white-space: pre` preserves the column alignment HTML would otherwise collapse.
  This also makes the params grid render consistently with the rest of the output
  (previously it was an un-wrapped bare line, unlike calc/comment groups).

### 5. Handler cleanups (drop the `<br>`/`<p>`-margin scaffolding)
- `render_heading`: no longer appends a trailing `\n`; a heading is block-level HTML
  that `join` passes through as a flex child (the container `gap` supplies spacing).
- `render_comments_block`: a run of consecutive comment lines is true prose, so it
  now renders as a **single** flowing `<p class="hc-comment">` (its lines joined by a
  space), rather than the old `[header], [['<p>'], …, ['</p>']]` tuple. An all-empty
  block (e.g. only `# hc:` commands) returns `''` and emits nothing — this removes the
  empty, margin-bearing `<p></p>` the old code produced for an ignored/`-i` line.
- `calcs_block`: the HTML-specific override was **removed**; the renderer now inherits
  the base handler (a clean headerless `[header, body]` group). Each calc line becomes
  one `hc-line`, with spacing from the stylesheet `gap` — no per-line `<br>`, no
  wrapping `<p>`. An ignored line renders to `''` and is skipped (no empty element).
- `if_block_header` / `for_block_header`: dropped the trailing `<br>`; the `hc-header`
  div supplies the break structurally.
- Removed the now-unused `render_block_body` import.

## What was NOT required

- **No `base.py` change.** `BaseRenderer.join` / `_join_item` and every base node
  handler are untouched; the HTML renderer only overrides `_join_item`,
  `format_param_grid`, `complete`, and `create_context`, plus its own registered
  swap rules. Plain-text output is byte-for-byte unaffected.
- **No new parallel formatting helpers.** The block handlers reuse the existing
  render path (inherited base `calcs_block`, `super().format_param_grid`), rather
  than introducing new formatting functions.

## Verification

- `HandCalcs(renderer=HTMLRenderer()).demo()` now emits: a single `.handcalcs`
  wrapper with one `<style>`; no empty `<p></p>`; no `&nbsp;`-prefixed block tags;
  no `<br>`; if/for bodies sitting directly under their headers with one consistent
  gap; nested if/for blocks nested structurally. (Asserted programmatically.)
- Full test suite: **identical** pass/fail set before and after this change
  (`18 failed, 216 passed, 9 errors`). Those failures/errors are **pre-existing** and
  live entirely in the base/plaintext/parser/demo pipeline (several paths return the
  master list instead of a joined string, and unrelated superscript/division cases) —
  none are in the HTML renderer and none are introduced by this work. This matches
  the assessment's "expect ~10 pre-existing failures unrelated to this work".

## Notes / follow-ups (out of scope here)

- The pre-existing base/plaintext/demo test failures/errors are unrelated to Option C
  and remain to be addressed separately.
- The uncommitted WIP that was on `features/html_renderer` (renamed demo variables in
  `demo.py`, a one-line tweak to the old `calcs_block`) was **stashed** on that branch
  (`git stash` entry: "WIP demo.py + html.py before Option C") before this branch was
  created; it is not part of this implementation.
- MathJax/KaTeX typesetting of the math (instead of hand-built `<sup>`/`<sub>`) remains
  a larger, separate architectural decision, as flagged in `HTML_alternatives.md`.
