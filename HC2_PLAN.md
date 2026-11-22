# handcalcs v2.0.0 release plan

Reviewed 2026-11-22 against `main` at `52a6482` (rc5 + #385 + #386).

## Status (2026-11-22)

Everything below that can be done in code has a PR. Merge order: #387 (this file),
#388–#392 in any order, then **#393 last**, after main is merged into it. The
changelog entries conflict, so I fold them in after each merge.

| PR | What | Plan § |
|---|---|---|
| #388 | `# ##` headings; `-b` ≈ one blank line in every renderer (HTML had none) | 1.1, 1.2 |
| #389 | Word: split/reflow/shrink long equations | 1.3 |
| #390 | Line magics and `!` in a `%%render` cell | 3 |
| #391 | CI `katex` job (pinned, sha-checked KaTeX) | 3 |
| #392 | Drop `exporters` (nb-hideinputs broken on nbconvert 7.17; use `--no-input`); remove v1 images and `vis_pyproject.toml` | 3 |
| #393 | Version 2.0.0, Production/Stable, `HC_SOURCE_REF`, README/install text, `handcalcs<2` note, `jupyter_display` removed in 3.0, 2.0.0 changelog | 2 |
| ym-handcalcs #16 | `-b` = one leading | 1.2 |

Not done (needs you): open the Word demo in Word to check #389 by eye; test in Colab
(#190); at release, set the changelog date, tag `v2.0.0`, publish, and close #369 and #365;
then the §5 downstream steps.

## Verdict

Nearly ready. The code, CI and packaging are in good shape. What's left is the three
items from the old `todos.md` (§1; one of them is a real HTML bug), the release paperwork and a few
loose ends.

- Tests: 2506 passed and 15 skipped locally. With forallpeople 4.0 and `formulas`
  installed, 2529 passed and 2 skipped.
- CI on `main`: all 15 jobs green (lint, package, the 12-job OS × Python matrix,
  `forallpeople-4`).
- Wheel and sdist build cleanly and contain only `src/`, README and LICENSE. There
  are no TODO/FIXME markers in `src/`.
- Open PRs: none. Open issues: 4 (see §4).

## Unreleased since rc5 (already in the changelog)

- #386: LaTeX keeps long equations within the line width (row splitting, grid
  reflow, `\hcfit` scaling; needs `graphicx` in the preamble).
- #385: pint quantities of numpy arrays render as arrays with units (#384).

## 1. Must do: the old `todos.md` items

All three are still open (probed on `52a6482`).

1. **`# ##` / `#  ##` headings.** Today these come out as plain comment text, and
   consecutive ones run together into one paragraph (`Heading A Heading B`) in every
   renderer. Treat them as `###` (a heading one level down).
2. **`# hc: -b` spacing is inconsistent:**
   - LaTeX emits three `\medskip`s in a row (the block's trailing skip, then
     `LINE_BREAK`, then the next block's leading skip).
   - Markdown emits an `&nbsp;` paragraph.
   - **HTML: `-b` does nothing**, either standalone or inline. `html.py` never reads
     `line_break`. This is a bug, not only a sizing issue.
   - ASCII emits a blank line and Excel a blank row (both fine).

   Target: one blank line's worth of space in every renderer, and add a
   `FEATURE_CASES` entry so ym-handcalcs picks it up.
3. **Word overflow.** The Word renderer has no width handling. Port the logic from
   #386: estimate each row's width, split substitutions one step per line (as `-m`
   does) and reflow `-g` grids into fewer columns. OMML can't scale like `\hcfit`,
   so a row that is still too wide needs a fallback: a smaller font for that
   paragraph, or leave it.

## 2. Release mechanics (the checklist in `docs/developers/releasing.md`, plus)

- `pyproject.toml`: `version = "2.0.0"`. Change the classifier from
  `Development Status :: 4 - Beta` to `5 - Production/Stable`.
- `uv.lock`: update the handcalcs version by hand (the old local uv).
- `docs/conf.py`: `HC_SOURCE_REF = "v2.0.0"`.
- **Changelog:** add a 2.0.0 section that summarises rc1–rc5 for people coming from
  1.x, and drop the "plain `pip install` installs 1.x" wording. Put the behaviour
  changes in that summary: a lone line ending in `;` is a one-cell grid row, and
  `-c` no longer reshapes `;` lines.
- **README:** remove the "v2.0.0 Pre-release out now!" block (it also has a typo,
  "uodated") and the rc install lines (`==2.0.0rc5`, `--pre`, `>=2.0.0rc5`), plus
  the "is a release candidate" paragraph. The README is the PyPI page.
- `docs/getting-started/installation.md`: three `>=2.0.0rc5` lines become plain
  `pip install handcalcs`.
- **v1 users get v2 on their next upgrade.** The migration page never says how to
  stay on 1.x. Add `pip install "handcalcs<2"` there, and to the README and the
  release notes.

## 3. Other things to watch

- **KaTeX check never runs in CI.** `test_markdown_renderer.py:161` needs
  `HANDCALCS_KATEX_JS`/mini-racer. No workflow sets it, so the check that Markdown
  output is valid KaTeX is skipped everywhere. Either wire it up or accept that.
- **Known bug:** a line magic inside a `%%render` cell doesn't render. Fix it, or
  document it as a limitation.
- **Colab (#190):** v2 is still untested in Colab. A 5-minute check before release
  would let you close the issue or document a workaround.
- **`pfst>=0.3.2,<0.4`:** this is the parser and it's 0.x. If pfst 0.4 ships after
  2.0, handcalcs blocks it until there is a patch release. Keep an eye on it.
- **`jupyter_display=` deprecation:** decide when it is removed (2.1 or 3.0), and
  say so in the warning or the changelog.
- **`exporters` extra:** nb-hideinputs 0.2.0 was last released 2024-06. Check that
  it still works with current nbconvert, or drop the extra.
- **Repo hygiene:**
  - `vis_pyproject.toml` is tracked: a stray `uv init` stub (`handcalcs 0.1.0`).
    Delete it.
  - The 61 `docs/images/*` v1 images are deleted in the working tree but not
    committed. Nothing references them, so commit the deletion.
  - Untracked local leftovers to delete: `word_renderer/` (spike),
    `Untitled*.ipynb`, `quadratic.xlsx`.

## 4. GitHub at release time

- Close **#369** (`@handcalc(display=)`, shipped in rc5) and **#365** (`--boxed`,
  shipped in rc5).
- **#190** Colab: see §3. **#50** showcase: keep open.

## 5. Downstream, after the release

- ym-handcalcs: pin `handcalcs>=2.0.0`, regenerate the demo golden and release.
  Then ymprint: bump its pins.
- handcalcs-migrate: still not on PyPI (PR #2 waits on PyPI/Bunny setup). It's the
  main help for v1 users, so ideally publish it with 2.0.0 and link it from the
  migration page.
- Python 3.13 floor for ymprint (ym PR #10) is still on hold.
