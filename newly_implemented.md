# Newly implemented: the remaining plan-doc issues

Branch `features/greek_identifiers`, cut 2026-10-19 from `features/word_renderer` at `8a07fb9`.
On 2026-10-19 it was rebased onto `hc2/dev` (`31b6837`) without that commit (the Word branch's
`word` extra), so the PR to `hc2/dev` contains only #117/#101.
This file covers what was implemented, the decisions taken on open questions, and the
coordination with the Word renderer session.

## Scope

The plan docs in the repo root list three outstanding items. #101 was added on 2026-10-19 at
your request (options A + D plus the shared identifier tree, from the chat plan):

| Plan | Issue | Status on this branch |
|---|---|---|
| `plan_222_word_renderer.md` | #222 Word renderer | **Not touched.** The Word session owns it, on `features/word_renderer`. |
| `plan_117_greek_identifiers.md` | #117 Greek letters joined to text | **Implemented**, steps 1–5 (see below). Step 6, the docs, is drafted below but not applied. |
| `plan_258_trailing_zeros_pr.md` | #258 v1 `trailing_zeros` PR | **No code.** See [#258](#258-no-code-change). |
| (chat plan, no file) | #101 comma subscripts | **Implemented**: the Symbol tree, `SUBSCRIPT_STYLE`/`subscripts` (A) and `symbols` (D). See [#101](#101-comma-subscripts-and-display-symbols). |

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
3. #101 (comma subscripts) was kept out of the #117 commits. It was added afterwards as its own
   commits on this branch (see below).

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

## #101: comma subscripts and display symbols

You chose option A (a subscript-style switch) plus option D (display aliases), on top of a
shared identifier tree.

### What changed for users

| Source | Before (LaTeX / HTML) | Now: comma style (default) | `subscripts = "nested"` |
|---|---|---|---|
| `N_pl_Rd` | `N_{\mathrm{pl}_{\mathrm{Rd}}}` / `N<sub>pl<sub>Rd</sub></sub>` | `N_{\mathrm{pl,Rd}}` / `N<sub>pl,Rd</sub>` | as before |
| `f_y_k` | `f_{y_{k}}` | `f_{y,k}` | `f_{y_{k}}` |
| `M_Ed_y` | `M_{\mathrm{Ed}_{y}}` | `M_{\mathrm{Ed},y}` | `M_{\mathrm{Ed}_{y}}` |
| `x_hat` | `x_{\mathrm{hat}}` / `x<sub>hat</sub>` | `\hat{x}` / x̂ | same |
| `x_bar_max` | `x_{\mathrm{bar}_{\mathrm{max}}}` | `\bar{x}_{\mathrm{max}}` | same |
| `M_star` | `M_{\mathrm{star}}` | `M^{*}` / `M<sup>*</sup>` | same |
| `f_prime_c` | `f_{\mathrm{prime}_{c}}` | `f'_{c}` / `f′<sub>c</sub>` | same |
| `lambda_` | `\mathrm{lambda}` (approx.) | `\lambda` / λ | same |

- **Option A, the subscript style.** `BaseRenderer.SUBSCRIPT_STYLE = "comma"` is the new
  default. Three ways to switch to nested:
  - for a renderer subclass: `SUBSCRIPT_STYLE = "nested"`;
  - for a session: `handcalcs.set_option("subscripts", "nested")`;
  - from the next line on: a standalone `# hc: subscripts = "nested"`. As an inline comment it
    applies to that line only.

  Any other value raises `ValueError`. In LaTeX, neighbouring upright words merge into one
  group (`\mathrm{pl,Rd}`), as Eurocode sets them. Excel has always shown one comma-joined
  subscript level, and it does so in either style.
- **Option D, display symbols.** The `symbols` context field maps an identifier to a display
  spec, for example `handcalcs.set_option("symbols", {"N_plRd": "N_{pl,Rd}"})` or
  `# hc: symbols = {"N_plRd": "N_{pl,Rd}"}`. The spec syntax is TeX-like but renderer-neutral:
  - subscripts in braces, with siblings separated by commas: `N_{pl,Rd}`;
  - `N_Rd` takes the run after `_`;
  - superscripts the same way: `M^{*}`, `x^2`;
  - nesting: `x_{a_{b}}`;
  - spaces separate words; `'` adds a prime;
  - Greek as a name or in Unicode: `ΔH_{vap}`, `sigma_{c}`.

  A bad spec raises `identifiers.SpecError` (a `ValueError`) with its position. Every renderer
  honours the option. Plain text shows `N_pl,Rd`; elsewhere plain text keeps raw underscores,
  so the docs' `unicode_subscripts` example still works.
- **Accents now work everywhere.** `hat`, `bar`, `prime` and `star` as a component decorate the
  component before them, in LaTeX, HTML and Excel. HTML used to catch only `_hat_` with an
  underscore after it, and LaTeX ignored accents entirely. Plain text still shows them raw.
- **Trailing underscores are dropped** (`class_` → class, `lambda_` → λ). This is the PEP 8
  convention for a name that clashes with a keyword. `lambda` is now also a whole-word Greek
  name (`lambda_1` → λ₁). A leading underscore keeps the name as literal text.
- **Unchanged**: Excel defined names, the LaTeX golden demo, and the docs' `name:pre` recipe.
  Text that isn't an identifier (`\dot{V}`, `V&#775;`) is left alone by every formatter.

### Code

- `identifiers.py` now also holds:
  - `Symbol`: words, accents, primes, `subscripts: list[Symbol]` and
    `superscripts: list[Symbol]`. Siblings are shown separated by commas.
  - `IdentifierOptions` (`greek_prefixes`, `subscripts`, `symbols`) and
    `identifier_options(renderer, base_context)`, which reads the context fields and falls
    back to the class attributes. `greek_prefixes` is now a context field too.
  - `parse_identifier(identifier, options)`, `parse_spec(spec)`, `SpecError` and
    `is_identifier()` (the idempotence guard).
- `base.py`: `SUBSCRIPT_STYLE: ClassVar[str] = "comma"`, next to `GREEK_PREFIXES`.
- `latex.py`: `latex_symbol()` and `latex_subscripts()` format the tree. The signature
  changed to `latex_identifier(identifier, options=None)`; it used to take a
  `greek_prefixes` boolean.
- `html.py`: **one `swap_identifier` rule plus `html_symbol()` replace `swap_greeks`,
  `swap_special_symbols` and `swap_subscripts`.** Removing `swap_identifier` turns off all
  identifier typesetting, as in LaTeX. No docs mention the old HTML rule names.
- `excel/symbolic.py`: `symbolic_identifier(identifier, options=None)` formats the tree,
  flattened to one level.
- `plaintext.py`: a new `swap_symbols` rule, registered before `swap_greeks`, plus
  `plain_symbol()`. `swap_greeks` is unchanged, so the docs recipe that removes it still turns
  Greek off.
- Tests: `tests/test_subscripts_and_symbols.py` covers the parser and spec parser, spec errors,
  and a cross-renderer table for comma, nested and symbols. It also covers the class attribute,
  the inline comment's scope and `set_option`. There are new cases in
  `tests/test_latex_renderer.py`. The suite is at 1080 passed, 6 skipped.

### Breaking changes (relative to v1 and today's `hc2/dev`)

| Change | Who is affected | Mitigation |
|---|---|---|
| Comma style is the default | Anyone with two or more `_` levels in LaTeX, Markdown or HTML output. This is the visible one. | `set_option("subscripts", "nested")`, or `SUBSCRIPT_STYLE = "nested"`. Add a migration-guide row. |
| `hat`/`bar`/`prime`/`star` components are accents in LaTeX | A name meant literally, e.g. `p_bar` for a pressure in bar | A `symbols` entry, e.g. `{"p_bar": "p_{bar}"}` |
| Trailing `_` is dropped; `lambda` is Greek | `lambda_1` was upright "lambda" | Intended, so none |
| HTML rule names are gone | Custom HTML subclasses that removed `swap_greeks` or `swap_subscripts` | Remove `swap_identifier` instead. Unreleased, so low risk. |
| `latex_identifier` takes `options`, not `greek_prefixes` | Anyone calling it directly. It shipped on this branch only. | None |

### Docs to add (docs branch, not done)

- Naming section: comma subscripts, `subscripts = "nested"`, and accents.
- A "Display symbols" section with the spec syntax. `customizing/symbols-and-functions.md`
  can replace its `name:pre` example (`SYMBOLS` with `V_dot`, `N_star`, `M_r`) with the
  `symbols` option (`{"V_dot": ...}` isn't even needed now: `V_dot` → V̇ is built in, and so is
  `N_star`).
- Migration guide: the first two rows of the table above.

### Decisions (you answered these on 2026-10-19)

1. **Single-letter subscripts stay italic** (`f_{y,k}`). No `UPRIGHT_SUBSCRIPTS` option.
2. **Accents in the spec syntax: added.** `hat(x)`, `bar(x)`, `dot(V)` and `ddot(x)`, with
   primes after the `)`. A subscript inside the parentheses still goes outside the accent:
   `bar(x_1)` → x̄₁. `_dot` and `_ddot` are now accent components in identifiers too
   (`V_dot` → V̇), in LaTeX, HTML and Excel. An unknown accent raises `SpecError`.
   - Breaking-change row: a name ending in `_dot`/`_ddot` meant literally (it used to show
     `V<sub>dot</sub>`). The fix is a `symbols` entry.
3. **Merge order: this branch first.** It goes to `hc2/dev` in its own PR, and the Word branch
   then rebases onto it and writes `word_identifier` on the `Symbol` tree. (The trial merge with
   Word's `2cae31b` was clean before the rebase; the rebase only dropped `8a07fb9`, which the
   Word branch still has.)
4. **#117 defaults confirmed**: prefix split on, and a split before an uppercase letter or a digit.
5. **Docs: update `docs/prerelease_docs_upa` now**, covering #117, #101 and the missing
   #259/#179/#54. That happens in its own worktree.
6. **PR #258: leave it open.** No GitHub action.

### Remaining open item

- Merging upright words in LaTeX only covers neighbours (`\mathrm{pl,Rd}`); mixed cases stay
  split (`\mathrm{Ed},y`). That's acceptable with decision 1.

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
- **Shared working directory, 2026-10-19.** Both sessions use `/home/engineering/handcalcs`,
  and the Word session checked out `features/word_renderer` there (it's at `2cae31b` with three
  new commits: `leading_sign`, OMML builders and the `WordRenderer`). From #101 on I worked in a
  separate git worktree, `/home/engineering/handcalcs-greek`, so neither session switches the
  other's branch. The untracked `newly_implemented.md` in the main checkout is a stale early copy;
  the real one is on this branch.
- **Message 3** (before the #101 code): the tree, `SUBSCRIPT_STYLE`, `symbols` and
  `identifier_options`. I suggested it hold off porting more of `latex_identifier` into its
  `word_identifier`, because that function (in `word/handlers.py`, with its own Greek tables)
  should become a formatter of `Symbol`. I asked it not to check out this branch in the shared
  directory.
- **Message 4** (after the #101 code): the final API, and how a `Symbol` maps to OMML.
- Overlap check: this branch changes `base.py` by two class attributes, `GREEK_PREFIXES` and
  `SUBSCRIPT_STYLE`. It doesn't touch
  `word_renderer/`, `src/handcalcs/renderers/word/` or `pyproject.toml`. If the Word branch adds
  class attributes next to `CONTINUATION_INDENT`, expect a trivial merge conflict there. The Word
  branch's `leading_sign` hook is also in `base.py`, but in a different place.

## Commits

See `git log features/word_renderer..features/greek_identifiers`.
