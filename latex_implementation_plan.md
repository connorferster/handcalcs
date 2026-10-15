# LatexRenderer implementation plan / session notes

Branch: `features/latex_renderer`. This file is the single source of truth for resuming
the LatexRenderer work (it supersedes the old `latex_plan.md`).

## Standing instructions from the user (2026-10-14)
- The user is part-way through implementing `LatexRenderer` (`src/handcalcs/renderers/latex.py`)
  and is happy with the progress so far. The task now is to evaluate and fix the odd behaviours
  in its output.
- Evaluate progress with the demo:
  `uv run python -c "from handcalcs import HandCalcs; from handcalcs.renderers import LatexRenderer; hc = HandCalcs(renderer=LatexRenderer()); import rich; rich.print(hc.demo())"`
  (`print` is better for exact inspection; see the note below.)
- ~~Ignore `tests/test_latex_renderer.py`~~. Phase 7 replaced the old token tests with golden and focused tests,
  and those **are** maintained (see "How to check progress").
- Sessions get disconnected, so keep this file up to date and commit and push often.

## How to check progress

```bash
uv run python -c "from handcalcs import HandCalcs; from handcalcs.renderers import LatexRenderer; hc = HandCalcs(renderer=LatexRenderer()); print(hc.demo())"
```

- Use `print`, not `rich.print`, when inspecting output. `rich` treats `[...]` as markup
  (for example, `[steel, concrete, timber]` disappears) and soft-wraps long lines.
- The demo source is in `src/handcalcs/renderers/demo.py`.
- Small ad-hoc probes: `HandCalcs(renderer=LatexRenderer())(source_str)`.
- `tests/test_latex_renderer.py` compares the demo, section by section, against `tests/golden/latex_demo.tex`. It also has
  focused tests per issue and a pdflatex compile test (skipped if pdflatex is not installed). After an intended output change:
  `HANDCALCS_UPDATE_GOLDEN=1 uv run pytest tests/test_latex_renderer.py`, then review `git diff tests/golden`.
- **Compile check:** `uv run python scripts/latex_demo_check.py [out_dir]` prints the LaTeX,
  wraps it in an `article` + `amsmath` document, compiles it with pdflatex (TinyTeX at
  `~/.TinyTeX/bin/x86_64-linux/pdflatex`) and reports errors and warnings. The output must
  compile, not just look plausible. Claude's Read tool can view the whole PDF. Page-ranged
  reads need `pdftoppm`, which is not installed.

## Architecture recap (what the renderer plugs into)

- `BaseRenderer` (`renderers/base.py`) renders nodes into a *master list*:
  - a `str` is a whole line;
  - an all-string `list` is one calc line, with components joined by `context.space`;
  - `[header, body_list]` is a block.

  `join` and `join_item` then add `indent * depth`, the separators and `context.newline`.
- Rules: `"{node_type}:pre|sym|num|post"` mutate nodes before or after the handler.
  `"header:{block_type}"` builds block headers. A bare `"{node_type}"` replaces the
  handler.
- `format_param_grid` and `format_calc_grid` are override hooks for `params_block` and
  multiline (`# hc: -m`) calcs. `HTMLRenderer` overrides both, along with `join_item`
  and `complete`. Use it as the model for a "structural" renderer.
- `CalcsBlock.body_pre` and `body_post` are inserted into the body list by
  `render_block_body`.

## DECIDED (2026-10-14): target **B, a pure LaTeX fragment**

The user chose B: `\section*{}` headings, plain-paragraph prose and
`\[\begin{aligned} ... \end{aligned}\]` math groups with `&=` alignment. The output should
compile with pdflatex (amsmath). The original options are kept below for context.

### Original question: what document is the output?

The demo mixes prose (headings, comment paragraphs, imports, if/for headers) with math.
Choose one of these targets:

- **A. Markdown + MathJax (recommended).** Headings are `##`, prose is plain paragraphs,
  and each math group is `$$\begin{aligned} ... \end{aligned}$$`. This renders in
  Jupyter (display with `Markdown`, not `Latex`), VS Code, GitHub and mkdocs, and pandoc
  can convert it to `.tex`.
- **B. Pure LaTeX fragment.** Headings are `\section*{}`, prose is plain paragraphs, and
  math is `\[\begin{aligned}...\end{aligned}\]`. It can be pasted into a `.tex` file, but
  in Jupyter's `Latex` display (`interfaces/jupyter.py`) MathJax does not render
  sectioning commands or prose formatting.

Either way, use `aligned` inside display math rather than a bare `align`. `align`
numbers every row and is not valid inside `$$`. v1 handcalcs used `\[\begin{aligned}`.
Make the outer wrappers small, overridable functions (heading, paragraph, math-open,
math-close) so the other target is cheap to add later.

## DECIDED (2026-10-14): LatexRenderer stays a pure LaTeX renderer

It is fine for the output to look broken in Jupyter (`Latex` display/MathJax cannot render `\section*`, `\noindent` and
`list`). The user will write a separate **MarkdownRenderer** that combines Markdown prose with LaTeX math for
Jupyter. Do not add Markdown/MathJax concessions to LatexRenderer.

Update 2026-10-15: MarkdownRenderer is implemented (`renderers/markdown.py`, plan and log in
`markdown_renderer_plan.md`) and is the `%%render` default through the `jupyter_renderer` option.
It shares LatexRenderer's math. `OPERATOR_SYMBOLS` and `MATH_FUNCS` are class attributes so the
subclass can override them. A change to LaTeX math output also changes Markdown output, so run
both golden tests.

## Diagnosis of the current demo output

### Root cause: one `space` and `newline` for two modes

`create_context` sets `space='\\ '` and `newline='\\\n'` globally, so every join (math
rows *and* prose) uses math-mode tokens. This causes most of the visible oddities:

- `\ ` appears between words in prose, headings, imports and if/for headers.
- `\\` ends every line, including Markdown headings, `\begin{align}` and `\end{align}`.
  The `\\` before `\end{align}` also adds an empty (numbered) row.
- Blank `# hc: -b` line breaks become stray `\` lines.
- The `\hspace*{1em}` indent prefixes `\begin{align}` and every row of nested blocks.

**Fix:** keep the context's `space` as a plain `' '` (spacing in math mode is
insignificant). Override `join_item` (as `HTMLRenderer` does) so that the renderer
knows whether it is emitting a math group or a text line:

- Text items (headings, comment paragraphs, imports, if/for headers) are emitted as
  text lines separated by blank lines.
- A math group (`CalcsBlock`, params grid, multiline grid) is emitted as
  `open` + rows joined with ` \\\n` (no `\\` after the last row) + `close`.
- Nested-block depth becomes `\quad` inside math, or an indent or quote in text. Do not
  emit raw `\hspace*` before environments.

### Issue inventory

Severity: **C** = the output is wrong or does not compile. **M** = the output renders,
but looks wrong. **m** = polish.

| # | Sev | Issue | Where | Fix |
|---|-----|-------|-------|-----|
| 1 | C | `%` emitted raw, which comments out the rest of the LaTeX line. `mod_op:pre` is registered under the wrong type (the node type is `modulo_op`). `swap_py_operators` returns early for it and has no `return` in that branch. | `latex.py:168,203` | Register `modulo_op:pre`, add it to the guard, set the symbol to `\bmod`, and return. |
| 2 | C | Pow: `b\ ^{\ 2}`. The `**` symbol is left as-is when the exponent is not a `Constant` (`b ** (c+1)`). | `latex.py:163,209` | Add a dedicated `pow_op` handler: `{base}^{exp}`, braces always, no precedence parens on the exponent. |
| 3 | C | A negative base is not parenthesised: `-3^{2} = 9`, `-10.423^{2}`. **This also affects plaintext** (`-3² = 9`). | `base.py` `infix_binop` | When the left operand of a `PowOp` renders with a leading `-`, wrap it in lpar/rpar (mirroring the existing check in `render_unary_op`). Fix this in base. |
| 4 | C | Dict and set braces `{ }` are emitted unescaped, so they become TeX groups and vanish: `{cat: 1}` shows as `cat: 1`. | base `set`/`dictionary` handlers | Add LaTeX handlers that emit `\{ \}`, or put `lbrace`/`rbrace` in the context and use them in base. |
| 5 | C | Inline comments are raw text inside math: `\left(Unbraced length of beam, in mm\right)`. They are italic, the spaces collapse, and `mm^4` breaks. | base `inline_comment` | Add a LaTeX `inline_comment` handler: `\;\textrm{(...)}` with LaTeX-escaped content. |
| 6 | C | No text escaping anywhere. Strings, comments and imports can contain `% & # _ ^ $ { } ~ \` and backticks. | n/a | Add one `latex_escape(text)` helper and use it for every text-mode string. |
| 7 | C | If/for headers contain math but sit outside any math environment. `->` is literal. | base `header:if_block`/`header:for_block` | Register LaTeX headers: text plus inline `$...$` (target A), or `\text{Since } ... \rightarrow ...` inside the math group. |
| 8 | C | `\Alpha`, `\Beta`, `\Epsilon`, `\Zeta`, `\Eta`, `\Iota`, `\Kappa`, `\Mu`, `\Nu`, `\Omicron`, `\Rho`, `\Tau` and `\Chi` do not exist in LaTeX. `\omicron` does not exist either. | `latex.py:119-145` | Map them to `\mathrm{A}`, `\mathrm{B}`, … and `o`. |
| 9 | C | An empty `\begin{align}\end{align}` is emitted when every line in a CalcsBlock is ignored (`acc = [] # hc: -i`). | `calcs_block:pre` + `render_block_body` | Drop the open/close when the filtered body is empty. This is easiest inside the new `join_item`. |
| 10 | M | No `&` alignment: rows use `=` rather than `&=`. | calc_line | Insert `&` before the first `assign` in each math row. Do this in the LaTeX `join_item` or with a `context.assign_first='&='` setting. |
| 11 | M | Division: `\frac{\left(-b + …\right)\ }{\ \left(2\cdot a\right)}` has redundant parens and spaces. Floor division has the same problem. | `infix_binop` via `div_op:pre` | Add dedicated `div_op` and `floor_op` handlers that render `\frac{L}{R}` and `\left\lfloor\frac{L}{R}\right\rfloor`. Render each operand without precedence parens. |
| 12 | M | Params block (`f = 1; g = 2; h = 4`) uses the plain-text `ljust` grid with `\ \ \ \ ` gaps and is outside math. | `format_param_grid` | ~~Override it: an `aligned` group with `f &= 1 & g &= 2 & h &= 4 \\`.~~ **Done** (session 4): v1-style `aligned` grid with a `\;` gap (`f &= 1 \; &g &= 2 \; &h &= 4 \;`); `# hc: -h` blocks add per-cell comments. |
| 13 | M | The multiline calc (`# hc: -m`) uses the plain-text grid (`     \ =\ `). | `format_calc_grid` | Override it with `&=` rows joined by `\\`. |
| 14 | M | `math.pi` is shown literally in the symbolic column. Attribute nodes get no `name:sym` rules. | n/a | Add an `attribute:sym` rule: drop the `math`/`numpy` namespace and apply the greek and subscript swaps (`\pi`). |
| 15 | M | `and`, `or`, `not`, `in`, `not in`, `is` and `is not` are raw words in math. They render as italic letters and their spaces collapse (`\mathrm{material} in \mathrm{materials}`). | `*_op` nodes, `unary_op` | Add `:pre` symbol swaps: `\land`/`\lor`, or `\ \mathrm{and}\ `. Use `\lnot`, `\in`, `\notin`, `\mathrm{is}` and `\mathrm{is\ not}`, and add explicit spacing (`\;`). |
| 16 | M | `not (temp < 0)` renders as `not temp < 0`. The parens are dropped because the operand of a unary op is a `Compare`. | base `render_unary_op` | Add `Compare`/bool-op precedence to `OP_PRECEDENCE`, or always parenthesise a `Compare` operand of `not`. |
| 17 | M | String constants are raw (`steel`, `[steel, concrete, timber]`). | `constant` | Add a LaTeX `constant` handler. For `str`, emit `\textrm{“steel”}` or `\texttt{'steel'}`, escaped. |
| 18 | M | Scientific notation: `2e+05`, `-1.04231e+01`, `4.3134e+08`. | `constant` | In the same handler, rewrite `…e±XX` as `… \times 10^{XX}`, stripping the `+` sign and leading zeros. |
| 19 | M | `True`, `False` and `None` are italic letters. | `constant` | Emit `\mathrm{True}` and so on. |
| 20 | M | `==` is shown as `==`. | `swap_angle_ops` | ~~Change it to `=`.~~ **User decision: keep `==`, as in Python.** |
| 21 | m | Comparison symbols get a doubled space (`\  < \ `). | `swap_angle_ops` | Once `space` is `' '`, emit only the bare `<`, `\le`, … |
| 22 | m | `test_for_long_var_strs(name_elems[0], BRC)` passes the *class*, not `base_context`. It works by accident. | `latex.py:263` | Pass `base_context`. |
| 23 | m | Long subscripts are italic: `a_{dictionary}`, `x_{rate}`. | `swap_subscripts` | Wrap multi-character subscript components in `\mathrm{}`, as v1 did. |
| 24 | m | `acc.append(...)` shows `\mathrm{acc}.` (sym) but `acc.` (num), and `= acc.\operatorname{append}(11.31)` adds nothing. | `function_call` / namespace render | Render the namespace symbolically in both columns, and consider dropping the numeric column for method calls whose value is `None`. |
| 25 | m | Complex numbers: `3+4j`. | `constant` | Emit `3 + 4i` (or keep `j`, which engineers often prefer). |
| 26 | m | `\operatorname{degrees} \left(` has a trailing space in the identifier. | `swap_func_symbols` | Cosmetic. Remove the trailing space, since `\left` already separates the tokens. |
| 27 | m | `[Python import]: from math import …` | `import` | In text mode, use `\texttt{from math import …}` (B) or `` `from math import …` `` (A), or suppress imports entirely. |

## Phased plan

Commit (and push) after each phase, or after each sub-bullet when it is self-contained.
Re-run the demo after each one and paste a snippet into the progress log below.

- [x] **Phase 0: Base-level correctness (benefits all renderers)**
  - [x] #3: parenthesise a negative left operand of `PowOp` in `infix_binop`.
  - [x] #16: parenthesise a `Compare` or bool-op operand of a unary `not`.
- [x] **Phase 1: Output structure (root cause).** Needs the target decision above.
  - [x] Set the context `space=' '` and newline `'\n'`. Add LaTeX tokens such as
        `math_newline=' \\\\'` and `math_indent='\\quad '`.
  - [x] Override `join_item`: separate text items from math groups. Emit math groups as
        `open` / rows / `close` with no trailing `\\`, and drop empty groups (#9).
  - [x] `&=` alignment on the first `=` of each row (#10).
  - [x] Add `latex_escape` and use it in text-mode handlers for headings, comment
        paragraphs (render a `comments_block` as one paragraph, as HTML does) and
        imports (#6, #27).
  - [x] Handle the `# hc: -b` line break: `\\[6pt]` inside math, a blank line in text.
  - [x] Nested if/for blocks: indent with `\quad` inside math.
- [x] **Phase 2: Block headers and grids**
  - [x] `header:if_block` and `header:for_block` with math correctly delimited, and
        `\rightarrow` (#7).
  - [x] `format_param_grid` (#12) and `format_calc_grid` (#13).
- [x] **Phase 3: Operators**
  - [x] Fix modulo (#1).
  - [x] Add dedicated `pow_op` (#2) and `div_op`/`floor_op` (#11) handlers. Remove
        those branches from `swap_py_operators`.
  - [x] Comparisons: `==` becomes `=`, plus spacing (#20, #21).
  - [x] Bool, identity and membership ops, and `not` (#15).
- [x] **Phase 4: Values**
  - [x] Add a LaTeX `constant` handler for strings (#17), scientific notation (#18),
        bool/None (#19) and complex numbers (#25).
  - [x] Escaped braces for dict and set (#4). Optionally use `\left[ \right]` for long
        lists.
  - [x] Inline comments as `\;\textrm{(…)}` (#5).
- [x] **Phase 5: Names**
  - [x] Fix the invalid greek capitals (#8).
  - [x] `attribute:sym` for `math.pi` → `\pi` (#14).
  - [x] `\mathrm` long subscripts (#23), and pass `base_context` (#22).
  - [x] Clean up namespaces and method calls (#24, #26).
- [x] **Phase 6: Integration**
  - [x] `complete()`: the output is a bare fragment (no preamble). `scripts/latex_demo_check.py` wraps it for compiling.
  - [x] `interfaces/jupyter.py`: **left as `Latex`** (user decision, below).
  - [x] Verify that the whole demo compiles in `pdflatex`, and check the PDF visually.
- [x] **Phase 7: Tests**
  - [x] Replace the token tests with golden-output tests: one per demo section, plus
        focused tests for #1-#4, #8 and #18.

## Progress log

- 2026-10-14: Investigation done and plan written (this file). No code changes yet.
  Waiting on the target-format decision (A vs B).
- 2026-10-14 (session 2): Merged `latex_plan.md` into this file and recorded the user's standing
  instructions. Re-ran the demo; the diagnosis above still matches. Still waiting on the A/B decision.
- 2026-10-14: The user chose **target B (pure LaTeX fragment)**. Starting Phase 0.
- 2026-10-14: Phase 0 is done (#3 neg pow base, #16 `not (compare)` parens), and plaintext output is verified.
- 2026-10-14: Phases 1 and 2 are done, and the demo compiles with pdflatex. As implemented:
  - The context uses a plain space and newline. `LatexRenderer.join_item` classifies items. A CalcsBlock
    body is recognised by its `MATH_OPEN` sentinel (set by `calcs_block:pre` as `body_pre`).
  - Top-level math groups are `\[\begin{aligned}`. Inside nested blocks they are flush-left
    `\noindent$\displaystyle\begin{aligned}[t]` boxes, so the indentation shows. Nested bodies are indented
    with a `list` env (`BLOCK_OPEN`/`BLOCK_CLOSE`). Text paragraphs get `\noindent`. `# hc: -b` becomes `\medskip`.
  - `latex_escape` exists and is used by the heading, comment_line and import handlers (still TODO: inline comments and strings).
  - Structural tokens are class attributes on `LatexRenderer`, so they are easy to override.
  - Still to do: the `-i`-only CalcsBlock now emits nothing (#9 fixed). #6 is partly done.
- 2026-10-14: Phase 3 is done. Operator symbols live in the `OPERATOR_SYMBOLS` table, keyed by node type, so the swap is idempotent. There are dedicated
  `pow_op`/`div_op`/`floor_op` handlers. Word operators render as `\;\mathrm{and}\;`, `\mathrm{not}\;` and so on.
  Also fixed: the parser key `"Floor"` → `"FloorDiv"` (every `//` crashed the parse), and base `infix_binop` now wraps a signed
  right operand (`7 * (-3)`), which affects all renderers.
  OPEN QUESTION for the user: `==` currently renders as `=`. Inside a calc line this reads ambiguously
  (`t = a = 7 and ...`). Alternatives are `\overset{?}{=}` or `==`.
- 2026-10-14: Phase 4 is done. The LaTeX `constant` handler covers strings, sci notation (`\times 10^{n}`), bool/None and complex.
  `set`/`dictionary` use `\{ \}`, and inline comments use `\quad\text{(...)}` with escaping. #24 is fixed by a LaTeX `function_call`
  handler: in the num pass it reuses the identifiers the sym pass already swapped. (Base num-mode rendered the function name and namespace
  by *value*, and `swap_subscripts` mangled `__main__`.) Still to do: long lists overflow the line (aligned can't break).
- 2026-10-14: Phase 5 is done. Invalid greek capitals now map to `\mathrm{A}` and so on, and `omicron` to `o`. An `attribute:sym` rule maps
  math/numpy constants (`math.pi` → `\pi`). Multi-letter subscripts are `\mathrm`. `__` → `\ ` and `___` → `\_`. User function names
  are escaped (`\operatorname{calc\_area}`) and skipped by `swap_subscripts`. The `BRC` arg bug (#22) is fixed.
  The whole demo compiles with no errors or warnings.
- 2026-10-14: Phase 6 is done for target B. `complete()` returns the bare fragment, and the user supplies the preamble (`amsmath`).
  NOTE: `interfaces/jupyter.py` still shows `latex` output with `IPython.display.Latex`. MathJax there ignores `\section*`, `\noindent`,
  `list` and `\medskip`; this is the trade-off the user accepted with target B. Next: Phase 7 (golden tests replacing
  `tests/test_latex_renderer.py`), pending the user's go-ahead. Open questions for the user are `==` rendering, and whether top-level math should be
  centred (now) or flush-left like nested blocks.
- 2026-10-14: Phase 5 is done. `swap_greeks`, `swap_subscripts` and `test_for_long_var_strs` are replaced by one pure
  `latex_identifier()` and a single `name:sym` rule (`swap_identifier`). It nests subscripts and maps greek names (via the module-level
  `GREEK` table, where invalid capitals become `\mathrm{A}` etc. and `omicron` becomes `o`). Any other multi-character component is set as `\mathrm{}`, including in subscripts.
  `__` becomes `\ ` and `___` becomes `\_`. It returns early on input that contains `\` or `{`, so it is idempotent. A LaTeX `attribute` handler drops the `math`/`cmath`/`numpy`/`np`
  namespaces (`math.pi` → `\pi`, `math.inf` → `\infty`). `\operatorname{}` has no trailing space and escapes `_`.
  Seen in passing (not yet fixed): `z = math.inf` renders as `z = \infty = \infty = \infty`, because an attribute-only line is not
  collapsed the way a constant is. A `def` block renders nothing in the probe. Check these in Phase 6.
- 2026-10-14: Phase 6 is done. The user decided that LatexRenderer stays pure LaTeX, with a MarkdownRenderer to follow for Jupyter. A visual check of the PDF
  found these fixes: `latex_prose()` (used for headings, comment paragraphs and inline comments) turns paired backticks into `\texttt{}` and opening
  `'`/`"` into TeX left quotes. Function calls drop any `MATH_NAMESPACES` prefix. Methods that keep their namespace use `\mathrm{append}`, not
  `\operatorname` (which put an operator gap after the `.`). Known overflow, not fixed: an `aligned` row cannot break, so long rows
  (the deliberately one-line `M_u`, the 25-element `acc` list and the long logic rows with comments) run past the margin. The `-m` flag is
  the user's tool for long equations. Base-level behaviours seen in all renderers: `z = math.inf` repeats its value, a `def` block renders
  nothing, and a list shows its final (post-mutation) value.

- 2026-10-14: Phase 7 is done, and **all phases are complete**. There are new golden, focused and compile tests, and the full suite passes (343). Fixes found while
  writing them: a params grid now drops trailing padding cells (ragged `aligned` rows), and a bare call (namespace `Name("")`, which is
  truthy) is no longer mistaken for a method (it stays `\operatorname`). Candidates for follow-up: the base-level oddities noted under Phase 6,
  and long-row overflow.
- 2026-10-14 (session 3): Reviewed the plan. The branch is clean and pushed, 343 tests pass and the demo compiles with no errors or warnings.
  Ticked the stale `latex_escape` box in Phase 1 (escaping now covers headings, comments, imports, strings and inline comments).
  Still open: long-row overflow.
- 2026-10-14 (session 3): Fixed `z = math.inf` repeating its value. Base `render_calcline` now drops a value column that
  repeats the one before it, so `z = math.inf` → `z = \infty`, `q = y` → `q = y = 3` and `v = 2 + 3` → `v = 2 + 3 = 5`
  (all renderers). Updated 6 tests that pinned the repeated columns and added `test_repeated_value_columns_collapse`. The demo golden file is unchanged.
  The user ruled the other two base-level items **non-issues**:
  - A `def` block renders nothing because it is not implemented yet (OK for now).
  - A list shows its post-mutation value for structural reasons (out of scope).
- 2026-10-14 (session 3): User decisions, now implemented:
  - **`==` renders as `==`**, like Python (`OPERATOR_SYMBOLS['eq_op']`). TeX puts no space between adjacent relations, so it sets compactly.
  - **All math is flush-left.** `MATH_OPEN`/`MATH_CLOSE` are now the `\noindent$\displaystyle\begin{aligned}[t] … \end{aligned}$`
    box at every depth (the `NESTED_MATH_*` pair is gone). A box gets none of the display skip a centred `\[` got, so
    `math_group()` puts a `MATH_SKIP` (`\medskip`) paragraph before and after each group, including the params grid. The demo
    compiles cleanly and was checked visually. The golden diff contains only wrapper changes.
  Remaining open item: long-row overflow (the `-m` flag is the workaround).
- 2026-10-14 (session 3): **Overflow exploration** (no code changes). Measured with the default `article` text width of 345pt.
  The demo has 7 overfull boxes. `scripts/latex_demo_check.py` reports none of them, because it only greps `!` and `Warning`.
  | Group | Too wide by | Scale to fit |
  |---|---|---|
  | `x_1`/`x_2` group | 12.7pt | 0.96 |
  | `M_u` (`-m` group) | 95pt | 0.78 |
  | `M_u` one-liner | 463pt | 0.43 |
  | nested `value_computed` | 75pt | 0.78 |
  | `acc` (25-element list) | 370pt | 0.48 |
  | logic block (13 rows; long rows + comments) | 187pt | 0.65 |
  | `Since … is True:` header (text, not math) | 198pt | n/a |
  Evaluated the user's candidate, the scale-to-fit approach from https://stackoverflow.com/a/55750239 (measure the box and
  `\resizebox{\linewidth}{!}` it if too wide). The prototype (`\hcfit` macro around each math group, graphicx) compiles and removes every math
  overflow. Its problems:
  (1) it scales the *whole* `aligned` group, so one long row shrinks all its neighbours (all 13 logic rows go to 0.65);
  (2) it is unbounded, so `M_u` and `acc` at about 0.45 are unreadable;
  (3) it needs `graphicx` and a macro in the preamble;
  (4) it cannot help text-mode overflow (the `Since` header);
  (5) the answer's own author warns against font scaling.
  Verdict: only usable as a *capped* safety net (scale only when 0.85 or more would fit) for small overshoots.
  Other options considered: TeX picks the layout (emit the one-line and `-m` forms and choose with `\sbox` and `\ifdim\wd`; exact, no scaling,
  kernel only, but it doubles the output and decides per group); renderer-side fixes for each cause (elide long collections,
  comment placement, breakable header delimiters); and auto-`-m` from an estimated width (Python cannot measure TeX widths).
  `breqn` was rejected (fragile, does not work with `aligned`).
- 2026-10-14 (session 3): **Overflow steps 1 and 2 are done** (the user approved them).
  - Step 1: `scripts/latex_demo_check.py` now lists every overfull box (pt, tex line, source line). The compile test asserts
    the overfull count is at most `KNOWN_OVERFULL = 5`; lower it as overflows are fixed. I checked that the guard fails when the budget is set to 4.
  - Step 2 (renderer-side fixes for each cause):
    - Collections with more than `MAX_ITEMS = 10` items are elided to their first and last `EDGE_ITEMS = 3` items around `\ldots`
      (LaTeX `list`/`tuple`/`set`/`dictionary` handlers via `join_items`). This fixes `acc` (370pt).
    - A calc line with substitution columns puts its inline comment on its own `&\quad\text{(…)}` row (`join_math_row`, `COMMENT_OPEN`).
      Param lines keep their comment inline. This takes the logic block from 187pt to 38.6pt.
    - If-headers use `\bigl( \bigr)` instead of `\left( \right)`, so TeX can wrap a long condition. This fixes the `Since` header (198pt).
  - Remaining overfull (5): the `x_1`/`x_2` group at 12.7pt; `M_u -m` at 95pt (its numeric row alone is too wide); the one-line `M_u` at 366pt (deliberate);
    nested `value_computed` at 75pt; and the logic block at 38.6pt (the `material_ok`/`material_missing` rows are long without comments).
    Next candidates: step 3 (opt-in capped scale-to-fit) for the small ones, and auto `-m` or TeX-chosen layout for the rest.
- 2026-10-15 (session 4): **Params grid made v1-like; `# hc: -h` params block with comments** (commit `8328423`).
  - Compared with v1 (`superceded/handcalcs.py`, `format_parameters_cell`): same `r l r l` aligned columns and `&` cell joins. v1 had no
    explicit gap; its visible gap was the `\;` it appended after every value. `format_param_grid` now emits
    `f &= 1 \; &g &= 2 \; &h &= 4 \;` (the `\qquad` is gone).
  - A `;` params line has nowhere to put a comment, so those are still dropped. New comment-capable form: **`# hc: -h`**
    (`--params-block`/`--params`) directly above an assignment groups the consecutive single assignments after it into a
    `ParamsBlock(with_comments=True)`, ending at a blank line, a standalone comment, or a non-assignment statement
    (`_parse_body`, `_blank_between`; blank rows are recorded in `_classify_comments`). `command_parser` now has `add_help=False`
    so `-h` is free. `render_comment_command` does not store `params_block` in the global context.
  - Cells carry a 4th component, the comment. LaTeX puts it one `\;` after the value (its leading `\quad` is dropped) followed by
    `\qquad` before the next cell (not after the last), so the gap to the next assignment is wider. HTML adds a
    `<td class="hc-param-comment">` per cell; plain text already joined all components with a 4-space gap between cells.
  - The demo's `# hc: params_cols=3` was a typo (silently ignored); it is now `# hc: -h`. Golden file, `test_params_grid_is_aligned_and_ragged`,
    a new `-h` test and the `test_parser.py` command dicts were updated. 347 tests pass; the demo PDF compiles.
  - Open: with comments a 3-column grid is wide (use `param_cols=2`); the `-h` command should be documented user-side.
