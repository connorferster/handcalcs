# HTML renderer: grouping, line-spacing & indentation — assessment and alternatives

Assessment of the extra vertical whitespace around `IfBlock`/`ForBlock` contents in the
`HTMLRenderer` (`src/handcalcs/renderers/html.py`) demo output, with three implementation
alternatives (A/B/C) and a recommendation. **This document is an assessment only — no code has
been changed.**

Diagnosis was confirmed by running the demo
(`HandCalcs(renderer=HTMLRenderer()).demo()`) and reading `html.py`, `base.py` `join`, and
`demo.py`.

---

## Root cause

The renderer mixes **three different spacing mechanisms at once**, and they stack:

1. **Literal `\n` newlines** inserted by the shared `BaseRenderer.join` / `_join_item`
   (`base.py:296-350`). In HTML these collapse to a single space — *harmless*, but misleading:
   the base `join` model is designed for whitespace-significant plain text, not HTML.
2. **`<br>` tags** — appended to every calc line (`html.py:98-99`) and to the `if`/`for` block
   headers (`html.py:109`, `html.py:119`).
3. **`<p>` browser default margins** — `render_comments_block` / `render_calcs_block`
   (`html.py:89-101`) wrap every grouped body in `<p>…</p>`, and browsers give `<p>` a default
   `margin: 1em 0` (~16px top *and* bottom).

Because line-grouping recurses into block bodies (`parsing/sequence.py`), **an `IfBlock`/`ForBlock`
body is itself a nested `CalcsBlock`**, so its contents are always wrapped in a `<p>`. The result:

```
Since (...) is True:<br>      <- header's <br> forces a break
    <p>                        <- then <p> top margin adds ANOTHER ~1em gap
    class_section = 3
    </p>                       <- <p> bottom margin adds ~1em below
```

That doubled gap (header `<br>` + `<p>` top margin) above the body, plus the `<p>` bottom margin, is
exactly the "extra vertical space around IfBlock/ForBlock contents" you're seeing.

### Secondary defects confirmed in the live output

- **Empty `<p></p>` paragraph.** The ignored line `acc = [] # hc: -i` yields an empty `CalcsBlock`
  still wrapped in `<p>…</p>`, rendering a blank, margin-bearing paragraph. Empty bodies must not be
  wrapped. (`html.py:95-101`)
- **`&nbsp;`-indented block tags.** Indentation is `indent='&nbsp;&nbsp;&nbsp;&nbsp;'`
  (`html.py:63`) applied by `join` as a text prefix — but it is applied to the *block-level* `<p>`
  and `</p>` tags too (e.g. `&nbsp;×8<p>`). Leading `&nbsp;` before a block element is meaningless
  and produces stray inline runs. Indentation should be structural, not text-prefixed.
- **Fragile tuple construction.** `para_body = [block_body[0]], [...]` (`html.py:92`, `html.py:100`)
  builds a *tuple* whose first element is a list, so `join` only treats it as a "headerless flat
  block" by accident (`base.py:345`). It works, but it's brittle and hard to read.
- **Inconsistent wrapping.** Imports (`[Python import]: …`) and the params grid
  (`f = 1    g = 2    h = 4`) render as bare lines with no `<p>`, unlike calc/comment groups — so
  vertical rhythm is uneven across line types.

The deeper issue: **HTML is not whitespace-significant, but the HTML renderer reuses the base
`join()` whose whole model (indent = text prefix, newline = `\n`, space = separator) assumes it is.**
Indentation and vertical rhythm in HTML belong in structure + CSS, not in interleaved `<br>`/`\n`/
`<p>`.

---

## The alternatives at a glance

| | Approach | Diff size | Fixes root cause? | Single tuning point? |
|---|---|---|---|---|
| **A** | Minimal patch, keep current `<br>`+`<p>` structure | Smallest | No (masks it) | Partial |
| **B** | Inline `style="margin:0"` on each `<p>`, no wrapper | Small | No (masks it) | No |
| **C** | Semantic nested `<div>`s + one scoped stylesheet | Larger | **Yes** | **Yes (CSS)** |

- **Alternative A — minimal patch, keep current structure.** Add a scoped `<style>` wrapper that
  zeroes `<p>` margins (`.handcalcs p{margin:.2em 0}`), remove the redundant `<br>` on if/for
  headers, skip empty `<p></p>`, and set `indent=''`. Smallest diff; keeps the `<br>`+`<p>` model so
  vertical rhythm stays slightly coupled and fragile.
- **Alternative B — inline styles, no wrapper.** Same fixes as A but emit `style="margin:0"` on each
  `<p>` instead of a stylesheet (works even where a wrapping element/CSS can't be added, e.g. some
  email/paste targets). Verbose output; no single tuning point.
- **Alternative C — semantic nested divs + scoped CSS (recommended, detailed below).**

**Recommendation: C.** It fixes the root cause rather than masking it and centralizes all spacing.
A is a reasonable stopgap if you want a one-commit fix before the larger refactor.

---

## Recommended approach: semantic nested elements + one scoped stylesheet ("Alternative C")

Stop mixing `\n` / `<br>` / `<p>`-margins. Emit a **clean nested structure** where every line is a
block-level element and nesting expresses indentation, then let **one small scoped stylesheet**
own all vertical rhythm and indentation. This is the standard way to render nested structured
content in HTML and gives you a single place to tune spacing.

### Output shape

```html
<div class="handcalcs">
  <style> /* scoped rules, emitted once */ </style>
  <h1>HandCalcs v2.0 Demo</h1>
  <div class="hc-line">a = 5.25</div>
  <div class="hc-block">
    <div class="hc-header">Since (…) is True:</div>
    <div class="hc-body">
      <div class="hc-line">class_section = 3</div>
    </div>
  </div>
</div>
```

### Scoped CSS (owns ALL spacing/indentation, one place to tune)

```css
.handcalcs .hc-line   { margin: 0; line-height: 1.6; }
.handcalcs .hc-body   { padding-left: 1.5em; }   /* indentation = structure, not &nbsp; */
.handcalcs .hc-header { margin: 0; }
.handcalcs p          { margin: 0.4em 0; }        /* if <p> is kept for prose, tame its margin */
```

### Implementation

1. **Override `join` in `HTMLRenderer`** (it already overrides `complete`, which calls
   `self.join`). Walk the same master-list shapes the base `join` understands
   (bare string / all-string list / `[header, body]` block) but emit nested `<div>`s instead of
   indent-prefixed `\n`-terminated lines:
   - bare string → `<div class="hc-line">{s}</div>` (headings/imports pass through as-is)
   - all-string list → `<div class="hc-line">{context.space.join(item)}</div>`
   - `[header, body]` with a non-empty header → `hc-block` > (`hc-header` + `hc-body`)
   - headerless/flat block (comments/calcs group) → just its lines (no wrapper, no `<p>`)
   Reuse the exact branch logic in `base.py:_join_item` (`base.py:320-350`) as the template so
   dispatch stays identical — only the emitted markup changes. This keeps `base.join` untouched for
   the plaintext renderers (reuse existing render handlers rather than adding parallel ones).
2. **Wrap once + inject the stylesheet** in `complete` (`html.py:57-58`): return
   `f'<div class="handcalcs"><style>…</style>{body}</div>'`. Emit `<style>` once at the top.
3. **Drop the `<br>`/`<p>` scaffolding** from the block handlers:
   - `render_comments_block` / `render_calcs_block` (`html.py:89-101`): stop wrapping in `<p>` and
     stop appending `<br>`; return the plain grouped body and let the new `join` + CSS handle it.
     Keep the multi-line `<p>` prose wrap **only** for true comment paragraphs if you prefer
     paragraph semantics there.
   - `if_block_header` / `for_block_header` (`html.py:103-119`): remove the trailing `<br>`; the
     `hc-header` div supplies the break.
4. **Skip empty bodies** so an ignored/`-i` line never emits an empty element.
5. **Set `indent=''`** (or remove the override) in `create_context` (`html.py:61-65`) — indentation
   now comes from `.hc-body { padding-left }`, not `&nbsp;`.

### Why this is the right altitude

- One knob (CSS) controls vertical rhythm and indentation; no more stacking `<br>` + margins.
- Indentation is structural, so it survives copy/paste, screen readers, and reflow.
- Output degrades gracefully without the stylesheet (still correctly nested, just unstyled).
- No change to `base.py` or the plaintext/latex renderers.

---

## Modern-CSS specifics to fold into the scoped stylesheet

These sharpen Alternative C and are worth adopting as part of it:

- **Zero-specificity scoping with `:where()`** — e.g. `.handcalcs :where(.hc-line){…}`. `:where()`
  contributes zero specificity, so a host page's own styles always win over the renderer's defaults.
- **Flex-column grouping owns the gap.** Give `.hc-body` (and the top-level container)
  `display:flex; flex-direction:column; gap: var(--hc-gap)`. A single `gap` then owns *all*
  inter-line spacing — no per-line `<br>`, and no margin-collapse/doubling to reason about.
- **Logical properties + custom properties as the single tuning point.** Use `margin-block` and
  `padding-inline-start` (instead of `padding-left`) so it stays correct under RTL/vertical writing
  modes, and expose `--hc-gap` and `--hc-indent` as the two knobs everything else references.
- **`font-variant-numeric: tabular-nums`** on lines so stacked numbers align in columns.
- **Optional dark mode** via `@media (prefers-color-scheme: dark)` for notebook dark themes.

Illustrative:

```css
.handcalcs {
  --hc-gap: 0.35em;
  --hc-indent: 1.5em;
  font-variant-numeric: tabular-nums;
}
.handcalcs :where(.hc-body) {
  display: flex;
  flex-direction: column;
  gap: var(--hc-gap);
  padding-inline-start: var(--hc-indent);
}
.handcalcs :where(.hc-line, .hc-header) { margin-block: 0; }

@media (prefers-color-scheme: dark) {
  .handcalcs { color: #e6e6e6; }
}
```

### Longer-term note (out of scope for this fix)

MathJax/KaTeX could typeset the math instead of the hand-built `<sup>`/`<sub>` markup. That is a
bigger architectural call and is **not** premised on any existing LaTeX renderer — note that
`renderers/latex.py` is currently a misnamed copy of the plaintext renderer, so there is no real
LaTeX output to reuse today. Flagged here only so it isn't lost.

---

## If/when you apply Alternative C: files to modify

- `src/handcalcs/renderers/html.py`
  - `create_context` (`html.py:61-65`) — drop/neutralize the `&nbsp;` indent.
  - `complete` (`html.py:57-58`) — wrap in `<div class="handcalcs">` + inject `<style>`.
  - **new** `join` override on `HTMLRenderer` — emit nested `hc-line`/`hc-block`/`hc-header`/
    `hc-body` markup (mirror `base.py:_join_item` branch logic).
  - `render_comments_block` / `render_calcs_block` (`html.py:89-101`) — remove `<p>`/`<br>`
    scaffolding, skip empty bodies, drop the fragile tuple construction.
  - `if_block_header` / `for_block_header` (`html.py:103-119`) — remove trailing `<br>`.
- No changes to `src/handcalcs/renderers/base.py`, `plaintext.py`, or `latex.py`.

## Verification checklist

1. `./.venv/bin/python -c "from handcalcs.handcalcs import HandCalcs; from handcalcs.renderers.html import HTMLRenderer; print(HandCalcs(renderer=HTMLRenderer()).demo())"`
   — confirm: no empty `<p></p>`; no `&nbsp;`-prefixed block tags; if/for bodies sit directly under
   their headers with a single consistent gap.
2. Save the output to an `.html` file and open in a browser (or a Jupyter `display(HTML(...))` cell)
   to eyeball the vertical rhythm around nested if/for blocks.
3. Run the existing renderer tests: `./.venv/bin/python -m pytest tests/ -k "html or base or renderer"`.
   Expect ~10 pre-existing failures unrelated to this work; confirm no *new* failures.
4. Compare against the plaintext renderer output to confirm `base.join` behavior is unchanged.
