# Newly implemented: the remaining plan-doc issues

Branch `features/greek_identifiers`, cut 2026-10-19 from `features/word_renderer` at `8a07fb9`.
This file covers what was implemented, the decisions taken on open questions, and the
coordination with the Word renderer session.

## Scope

The plan docs in the repo root list three outstanding items:

| Plan | Issue | Status on this branch |
|---|---|---|
| `plan_222_word_renderer.md` | #222 Word renderer | **Not touched.** The Word session owns it, on `features/word_renderer`. |
| `plan_117_greek_identifiers.md` | #117 Greek letters joined to text | **Implemented**, steps 1–5 (see below). Step 6, the docs, is drafted below but not applied. |
| `plan_258_trailing_zeros_pr.md` | #258 v1 `trailing_zeros` PR | **No code.** See [#258](#258-no-code-change). |

## #117: Greek identifiers

### What changed for users

| Identifier | Plain text | LaTeX / Markdown | HTML | Excel display |
|---|---|---|---|---|
| `DeltaH` | `ΔH` (was `DeltaH`) | `\Delta H` (was `\mathrm{DeltaH}`) | `ΔH` (was `DeltaH`) | `ΔH` (was `DeltaH`) |
| `DeltaT_max` | `ΔT_max` | `\Delta T_{\mathrm{max}}` | `ΔT<sub>max</sub>` | `ΔT<sub>max</sub>` |
| `gammaM0` | `γM0` | `\gamma \mathrm{M0}` | `γM0` | `γM0` |
| `alpha2` | `α2` | `\alpha 2` | `α2` | `α2` |
| `Delta__H` | `Δ H` (was `Δ__H`) | `\Delta\ H` (was `\mathrm{Delta\ H}`) | `Δ H` (unchanged) | `Δ H` (was `Delta H`) |
| `ΔH` (Unicode) | `ΔH` | `\Delta H` (was `\mathrm{ΔH}`, which broke pdflatex) | `ΔH` | `ΔH` |
| `metal`, `Pin`, `beta`, `xtheta` | unchanged | unchanged | unchanged | unchanged |
| `Annual__Rate` | `Annual Rate` (was `Annual__Rate`) | unchanged | unchanged | unchanged |

- **R1**: LaTeX maps Unicode Greek letters to commands.
- **R2**: each `__`-separated word gets the whole-word Greek lookup, in every renderer. Plain
  text now shows `__` as a space. `___` is still shown as it is in plain text.
- **R3**: a component that starts with a Greek name followed by an uppercase letter or a digit
  is split there, with the longest name winning (`varepsilonR`). `lambdaR` → λR works, although
  `lambda` alone is a keyword. Turn R3 off with a subclass:
  ```python
  class MyRenderer(LatexRenderer):
      GREEK_PREFIXES = False
  ```
- Excel **defined names are unchanged**: `DeltaH` is still the name `DeltaH`. A test pins this.
- Removing `swap_greeks` from `rule_handlers["name"]["sym"]` (HTML or plain text) still turns
  off all Greek translation, because the new logic lives inside `swap_greeks`. LaTeX's switch
  is `swap_identifier`, as before.

### Code

- `src/handcalcs/renderers/identifiers.py` (new) holds the shared recognition:
  - `GREEK_UNICODE` / `GREEK_NAMES` / `UNICODE_NAMES`: one name table. `PREFIX_ONLY` adds
    `lambda`/`Lambda` as prefixes only.
  - `split_greek_prefix(component)`: `"DeltaH"` → `("Delta", "H")`, or `(None, component)`.
  - `split_greek(word, prefixes)`: a word as `(is_greek, text)` pieces, where a Greek
    piece's text is its canonical name. This is the function a new renderer should build on.
  - `unicode_greek(word)` and `greek_identifier(identifier)`: the Unicode swap that plain
    text, HTML and Excel use. It keeps the underscores.
- `BaseRenderer.GREEK_PREFIXES: ClassVar[bool] = True` (`base.py`).
- `latex.py`: `latex_identifier(identifier, greek_prefixes=True)` and a new helper,
  `latex_word`. Every call site passes `renderer.GREEK_PREFIXES`.
- `html.py`, `plaintext.py`, `excel/symbolic.py`: their duplicated Greek tables were
  replaced by `GREEK_UNICODE`. `html.GREEK` and `symbolic.GREEK` stay as aliases.
  `symbolic_identifier(identifier, greek_prefixes=True)`.
- Tests: `tests/test_identifiers.py` (unit tests and the plan's negative list),
  `tests/test_greek_identifiers.py` (the cross-renderer table for plain text, LaTeX, Markdown,
  HTML and Excel, the `GREEK_PREFIXES = False` switch, and Excel defined names), and new cases
  in `tests/test_latex_renderer.py`. The suite went from 860 passed to 989 passed, with 6 skipped.
- Affected-name probe: I searched `docs/`, `Examples/`, `tests/` and the `docs/prerelease_docs_upa`
  branch for `<greek name>[A-Z0-9]…` and found no hits outside the new tests. The LaTeX golden
  demo is unchanged.

### Decisions on the plan's open questions

Nobody had answered these, so I went with the plan's recommendations. Each is easy to reverse.

1. R3 is **on by default**, with `GREEK_PREFIXES = False` as the escape hatch. To ship it off
   instead, flip the default in `base.py` and in the three tests that assume it's on.
2. A prefix splits before an **uppercase letter or a digit** (`alpha2` → α2). For uppercase
   only, drop `or following.isdigit()` in `split_greek_prefix`.
3. #101 (comma subscripts) is **not** included. It stays a separate PR on top of `identifiers.py`.

Deviation from the plan: the plan named a `split_words()` helper. I didn't add it, because each
renderer uses different `__` placeholders. `greek_identifier()` does the `__`-word handling for
the Unicode renderers instead.

### Not done: docs (plan step 6, on the docs branch)

The v2 docs live on `docs/prerelease_docs_upa`, which also still lacks #259/#179/#54. I didn't
switch branches. Text to add:

- `writing-calculations.md`, naming section: "Write a Greek letter joined to other letters
  either as Unicode (`ΔH = …`) or as a Greek name followed by an uppercase letter or digit
  (`DeltaH`, `gammaM0`). A lowercase continuation never splits (`metal`, `beta`). `__` is a
  space, and each word in a `__` label also gets the Greek lookup (`Delta__H` → Δ H)."
- `symbols-and-functions.md`: the `GREEK_PREFIXES = False` recipe.
- v1 → v2 migration guide: v1 had none of R1–R3. Names like `PiD`, `MuS`, `Eta2`, `Chi2` or
  `BetaTest` now render as Greek; set `GREEK_PREFIXES = False` to keep the old output.
- "Building renderers": a `name:sym` rule registered *after* the built-ins now sees `ΔH` where
  it used to see `DeltaH`.

## #258: no code change

The memory notes from the batch-1 session say that #221 (trailing zeros in v2) was dropped
because "v2 already implements it". Plan option A ("port to v2") is therefore already met. What's
left is a GitHub action that I haven't taken: close PR #258 with the reply drafted in
`plan_258_trailing_zeros_pr.md`, adjusted to point at the existing v2 feature. I left it for you
because it's outward-facing.

## Coordination with the Word renderer session

- The Word session is running twice, as `handcalcs-fd` and `handcalcs-c3`. Both have the same
  session id, `128aef54…`, because of the ttyd orphan issue, and both are waiting for your input.
  I messaged `handcalcs-fd` only, so the two copies don't both act. `handcalcs-c3` is probably
  the stale copy.
- **Message 1** (2026-10-19, sent before any code changed): announced the branch, the shared
  `identifiers.py`, `BaseRenderer.GREEK_PREFIXES` and the output changes. I asked it to build
  the OMML identifier code on `identifiers.py` instead of copying a Greek table, and to rebase
  onto or merge this branch once it lands. No action is needed on its branch now.
- **Message 2** (after implementation): the final API. `split_greek` is the entry point for
  OMML, and `split_words` doesn't exist (message 1 mentioned it). It also covers how OMML
  should typeset the pieces to match LaTeX: a Greek run in `m:r`, and a one-letter remainder
  italic with a longer one upright (`m:sty m:val="p"`). The commit list is at the end.
- Overlap check: this branch changes `base.py` by one class attribute only. It doesn't touch
  `word_renderer/` or `pyproject.toml`. If the Word branch adds class attributes next to
  `CONTINUATION_INDENT`, expect a trivial merge conflict there.

## Commits

See `git log features/word_renderer..features/greek_identifiers`.
