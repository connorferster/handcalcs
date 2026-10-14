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
- **Ignore `tests/test_latex_renderer.py`**. An earlier Claude session wrote those as token tests,
  and they are not authoritative. They fail since `complete()` now joins its output, which is expected.
- Sessions get disconnected, so keep this file up to date and commit and push often.

## How to check progress

```bash
uv run python -c "from handcalcs import HandCalcs; from handcalcs.renderers import LatexRenderer; hc = HandCalcs(renderer=LatexRenderer()); print(hc.demo())"
```

- Use `print`, not `rich.print`, when inspecting output. `rich` treats `[...]` as markup
  (for example, `[steel, concrete, timber]` disappears) and soft-wraps long lines.
- The demo source is in `src/handcalcs/renderers/demo.py`.
- Small ad-hoc probes: `HandCalcs(renderer=LatexRenderer())(source_str)`.
- The current `tests/` LaTeX tests are quick token tests and are **not** authoritative.
  Judge progress against the demo. Phase 7 replaces them.
- Paste the output into a MathJax or KaTeX sandbox, or compile it with `pdflatex`, to check
  that it renders. The output must render, not just look plausible.

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
| 12 | M | Params block (`f = 1; g = 2; h = 4`) uses the plain-text `ljust` grid with `\ \ \ \ ` gaps and is outside math. | `format_param_grid` | Override it: an `aligned` group with `f &= 1 & g &= 2 & h &= 4 \\`. |
| 13 | M | The multiline calc (`# hc: -m`) uses the plain-text grid (`     \ =\ `). | `format_calc_grid` | Override it with `&=` rows joined by `\\`. |
| 14 | M | `math.pi` is shown literally in the symbolic column. Attribute nodes get no `name:sym` rules. | n/a | Add an `attribute:sym` rule: drop the `math`/`numpy` namespace and apply the greek and subscript swaps (`\pi`). |
| 15 | M | `and`, `or`, `not`, `in`, `not in`, `is` and `is not` are raw words in math. They render as italic letters and their spaces collapse (`\mathrm{material} in \mathrm{materials}`). | `*_op` nodes, `unary_op` | Add `:pre` symbol swaps: `\land`/`\lor`, or `\ \mathrm{and}\ `. Use `\lnot`, `\in`, `\notin`, `\mathrm{is}` and `\mathrm{is\ not}`, and add explicit spacing (`\;`). |
| 16 | M | `not (temp < 0)` renders as `not temp < 0`. The parens are dropped because the operand of a unary op is a `Compare`. | base `render_unary_op` | Add `Compare`/bool-op precedence to `OP_PRECEDENCE`, or always parenthesise a `Compare` operand of `not`. |
| 17 | M | String constants are raw (`steel`, `[steel, concrete, timber]`). | `constant` | Add a LaTeX `constant` handler. For `str`, emit `\textrm{“steel”}` or `\texttt{'steel'}`, escaped. |
| 18 | M | Scientific notation: `2e+05`, `-1.04231e+01`, `4.3134e+08`. | `constant` | In the same handler, rewrite `…e±XX` as `… \times 10^{XX}`, stripping the `+` sign and leading zeros. |
| 19 | M | `True`, `False` and `None` are italic letters. | `constant` | Emit `\mathrm{True}` and so on. |
| 20 | M | `==` is shown as `==`. | `swap_angle_ops` | Change it to `=`. |
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

- [ ] **Phase 0: Base-level correctness (benefits all renderers)**
  - [ ] #3: parenthesise a negative left operand of `PowOp` in `infix_binop`.
  - [ ] #16: parenthesise a `Compare` or bool-op operand of a unary `not`.
- [ ] **Phase 1: Output structure (root cause).** Needs the target decision above.
  - [ ] Set the context `space=' '` and newline `'\n'`. Add LaTeX tokens such as
        `math_newline=' \\\\'` and `math_indent='\\quad '`.
  - [ ] Override `join_item`: separate text items from math groups. Emit math groups as
        `open` / rows / `close` with no trailing `\\`, and drop empty groups (#9).
  - [ ] `&=` alignment on the first `=` of each row (#10).
  - [ ] Add `latex_escape` and use it in text-mode handlers for headings, comment
        paragraphs (render a `comments_block` as one paragraph, as HTML does) and
        imports (#6, #27).
  - [ ] Handle the `# hc: -b` line break: `\\[6pt]` inside math, a blank line in text.
  - [ ] Nested if/for blocks: indent with `\quad` inside math.
- [ ] **Phase 2: Block headers and grids**
  - [ ] `header:if_block` and `header:for_block` with math correctly delimited, and
        `\rightarrow` (#7).
  - [ ] `format_param_grid` (#12) and `format_calc_grid` (#13).
- [ ] **Phase 3: Operators**
  - [ ] Fix modulo (#1).
  - [ ] Add dedicated `pow_op` (#2) and `div_op`/`floor_op` (#11) handlers. Remove
        those branches from `swap_py_operators`.
  - [ ] Comparisons: `==` becomes `=`, plus spacing (#20, #21).
  - [ ] Bool, identity and membership ops, and `not` (#15).
- [ ] **Phase 4: Values**
  - [ ] Add a LaTeX `constant` handler for strings (#17), scientific notation (#18),
        bool/None (#19) and complex numbers (#25).
  - [ ] Escaped braces for dict and set (#4). Optionally use `\left[ \right]` for long
        lists.
  - [ ] Inline comments as `\;\textrm{(…)}` (#5).
- [ ] **Phase 5: Names**
  - [ ] Fix the invalid greek capitals (#8).
  - [ ] `attribute:sym` for `math.pi` → `\pi` (#14).
  - [ ] `\mathrm` long subscripts (#23), and pass `base_context` (#22).
  - [ ] Clean up namespaces and method calls (#24, #26).
- [ ] **Phase 6: Integration**
  - [ ] `complete()`: final wrapper for the chosen target.
  - [ ] `interfaces/jupyter.py`: if target A, display the `latex` output with
        `Markdown`, not `Latex`.
  - [ ] Verify that the whole demo renders in MathJax (and in `pdflatex` for target B).
- [ ] **Phase 7: Tests**
  - [ ] Replace the token tests with golden-output tests: one per demo section, plus
        focused tests for #1-#4, #8 and #18.

## Progress log

- 2026-10-14: Investigation done and plan written (this file). No code changes yet.
  Waiting on the target-format decision (A vs B).
- 2026-10-14 (session 2): Merged `latex_plan.md` into this file and recorded the user's standing
  instructions. Re-ran the demo; the diagnosis above still matches. Still waiting on the A/B decision.
- 2026-10-14: The user chose **target B (pure LaTeX fragment)**. Starting Phase 0.
