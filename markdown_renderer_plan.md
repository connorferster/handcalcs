# MarkdownRenderer implementation plan / session notes

Branch: `features/markdown_renderer`. This file is the single source of truth for resuming
the MarkdownRenderer work. Keep the checklist and progress log below up to date.

## Standing instructions from the user (2026-10-15)

> Put a plan together for implementation of the MarkdownRenderer (inheriting from the
> LatexRenderer). The purpose of the MarkdownRenderer is to be the default renderer for
> Jupyter-type environments where math will be rendered in latex. Use blockquote `>` for
> nested indentation. Put together a plan for the implementation in
> markdown_renderer_plan.md. [...] Make frequent commits and pushes.

- Sessions get disconnected: keep this file current, and commit and push after each step.
- `LatexRenderer` stays a pure LaTeX fragment renderer (decided 2026-10-14, see
  `latex_implementation_plan.md`). Do **not** add Markdown/MathJax concessions to it. Put
  them in `MarkdownRenderer` overrides. The exception is a genuine bug that affects both
  renderers. Raise those with the user instead of silently changing LaTeX output or its
  golden file. The user approved one such fix (Phase 3, `\arcsinh`).

## How to check progress

```bash
uv run python -c "from handcalcs import HandCalcs; from handcalcs.renderers import MarkdownRenderer; hc = HandCalcs(renderer=MarkdownRenderer()); print(hc.demo())"
```

- Use `print`, not `rich.print`, because `rich` eats `[...]`.
- Ad-hoc probes: `HandCalcs(renderer=MarkdownRenderer())(source_str)`.
- When Phase 5 is done: `uv run pytest tests/test_markdown_renderer.py` (golden file
  `tests/golden/markdown_demo.md`, regenerate with `HANDCALCS_UPDATE_GOLDEN=1`).
- Real rendering check: `scripts/markdown_demo_check.py` (Phase 5) writes
  `markdown_demo.ipynb` with the demo as one Markdown cell. Open it in JupyterLab,
  VS Code and Colab. Neither `node` nor `jupyter` is installed in this sandbox, so the visual
  check is manual for the user. `markdown-it-py` and `nbformat` are available.

## Target format

Markdown prose with LaTeX math, as rendered by Jupyter front-ends (JupyterLab and Notebook 7
use marked and MathJax 3, VS Code uses markdown-it and KaTeX, Colab uses MathJax). Output is
displayed through `IPython.display.Markdown`.

| Element | LatexRenderer | MarkdownRenderer |
|---|---|---|
| Heading | `\section*{...}` | `#`, `##`, ... (already drafted) |
| Comment paragraph | `\noindent text` | plain paragraph, Markdown-escaped |
| Import | `\texttt{...}` | `` `import math` `` |
| Calc group | `\medskip` + `$\displaystyle\begin{aligned}[t]...$` | `$$\begin{aligned} ... \end{aligned}$$` on **one line** |
| Row separator | ` \\` + newline | ` \\ ` (same line) |
| Line break (`\n\n` in source) | `\medskip` | `&nbsp;` spacer paragraph |
| Nested block body | `\begin{list}...\end{list}` | every line prefixed with `> ` per level |
| Block header | `Since $...$ is True:` | unchanged (inline `$...$` math) |

Example of the target (the nested if/for part of the demo):

```markdown
Since $\bigl(\frac{b_{w}}{2 \cdot t_{f}} \le ...\bigr)$ is True:

> Since $\bigl(\frac{h_{w}}{t_{w}} \le ...\bigr)$ is True:
>
> > $$\begin{aligned} \mathrm{class}_{\mathrm{section}} &= 3 \end{aligned}$$
>
> Trailing text back at depth 1
```

### Why a math group is one physical line (key decision)

JupyterLab and Notebook pull math out of the raw cell text before Markdown parsing
(`removeMath`). In a multi-line `$$ ... $$` block inside a blockquote, the `> ` prefixes of
the inner lines end up **inside** the LaTeX and break it. Blank lines inside `$$` also end the
paragraph in marked and markdown-it. If every math group is a single line (`$$` ... `$$`),
there is only one `> ` prefix, and it sits outside the math. This works under every
front-end's math extraction strategy. The cost is less readable raw Markdown, which is
acceptable because the output is meant to be rendered. **Verify early (Phase 1) in JupyterLab
and VS Code** using the check notebook.

### Blockquote rules

- A block (`[header, body]`) emits its header as a paragraph at the current level. Its body
  is joined at `depth + 1`, and every body line, blank lines included, gets one `>` prefix
  (`"> " + line`, or `">"` for an empty line). Each level prefixes once, so recursion
  produces `> > ` for depth 2. Never use `"> " * depth`.
- A blank line between items at the same level must carry the level's prefix (`>`). Otherwise
  the quote ends and the next quote starts a new blockquote.
- **Lazy continuation hazard:** a `> text` line directly after a `> > text` line is absorbed
  into the inner quote. Always end a nested body with a blank line at the parent level
  (`>`, or a truly empty line at depth 0) before the next item.
- Ending a block (no more items at that depth) needs a blank line with no prefix after the
  quote. Otherwise following depth-0 text lazily continues the quote.

## Current state (start of 2026-10-15)

- Uncommitted work by the user:
  - `renderers/__init__.py` exports `MarkdownRenderer`.
  - `interfaces/jupyter.py` adds `"markdown"` to `_RENDERERS` and `_DISPLAY`
    (`IPython.display.Markdown`).
  - `renderers/markdown.py` is a near-full **copy** of `latex.py` (785 lines). The class is
    renamed `MarkdownRenderer(LatexRenderer)` with `name = 'markdown'`, `$$` math tokens,
    `ROW_SEP = "<br>"`, a Markdown heading handler, a raw comment-line handler, and a backtick
    import handler.
- Demo output today shows these problems: `\medskip` and `\begin{list}` leak; `<br>` row
  separators (MathJax ignores them, so rows run together); blank lines inside `$$`;
  `\textasciicircum{}` inside `\text{}` (MathJax does not support it).
- **Registry note:** `BaseRenderer.__init_subclass__` copies the parent's handler dicts and
  rule lists. Node and header handlers registered on `MarkdownRenderer` *replace* the
  inherited ones. Rules (`:pre|sym|num|post`) are *appended* to the inherited list. So the
  copied file currently runs every LaTeX swap rule twice. They happen to be idempotent, but
  this is fragile. Only re-register a rule if the LaTeX rule cannot do the job by reading a
  class attribute.

## Plan

### Phase 0: Slim the draft to a true subclass
- [ ] Commit the user's wiring changes (`__init__.py`, `jupyter.py`) together with the plan.
- [ ] Rewrite `renderers/markdown.py` to import from `latex.py` (`LatexRenderer`,
      `latex_escape`, `latex_identifier`, `OPERATOR_SYMBOLS`, ...). Keep only:
      the class with overridden tokens and methods, the heading, comment_line, import and
      inline_comment handlers, and any Phase 2–3 overrides. Drop all copied rules and
      handlers that are identical to LaTeX.
- [ ] Check that the demo still renders. Check that LaTeX output is unchanged:
      `uv run pytest tests/test_latex_renderer.py`.

### Phase 1: Structural layer (`join_item`, `math_group`, `complete`)
- [ ] Class tokens: `MATH_OPEN = "$$\\begin{aligned}"`, `MATH_CLOSE = "\\end{aligned}$$"`,
      `ROW_SEP = " \\\\ "`, `MATH_SKIP = ""`, `PARAGRAPH = ""`, `LINE_BREAK = "&nbsp;"`,
      `BLOCK_PREFIX = "> "`. `BLOCK_OPEN` and `BLOCK_CLOSE` are unused.
- [ ] Override `math_group(rows)` to return `f"{MATH_OPEN} {ROW_SEP.join(rows)} {MATH_CLOSE}"`,
      a single line with no skips. This also fixes the params grid, which goes through
      `math_group`.
- [ ] Override `format_calc_grid`. Its rows are joined with `ROW_SEP`, so they are already
      single-line. Confirm that `# hc: -m` output has no newline.
- [ ] Override `paragraph(text)` to return `text` unchanged.
- [ ] Override `join_item`:
  - bare string: paragraph + `\n\n`. A whitespace-only string (a one-shot line break)
    becomes a `LINE_BREAK` (`&nbsp;`) spacer paragraph, mirroring `\medskip`. Inside a
    blockquote it is prefixed like any other line (`> &nbsp;`). The user decided this
    on 2026-10-15. Check that consecutive breaks don't pile up into large gaps; collapse
    adjacent spacers to one if they do;
  - CalcsBlock body: `join_math_group` (inherited, uses the new `math_group`);
  - headerless block: body at the same depth (inherited behaviour);
  - `[header, body]`: header paragraph, then `self.quote(self.join_items(body, depth + 1))`;
  - all-string list: paragraph.
- [ ] `quote(chunks)`: join the chunks, strip trailing blank lines, prefix every line (`>`
      on empty lines), and end with `\n\n`. This handles the lazy-continuation rules above.
- [ ] Confirm that `join_math_row` puts `&` before the first assign symbol. The inline
      comment row it splits off uses `ROW_SEP`, so it stays on one line.
- [ ] `complete()`: inherited (`strip() + "\n"`). Collapse runs of 3+ newlines if any
      appear.
- [ ] Probe: nested if/elif/else and nested for loops in the demo render as `>` and `> >`
      with no lazy-continuation leakage. Use `markdown-it-py` to parse the output and
      assert the blockquote nesting depth of each math line.
- [ ] Build the Phase 5 check notebook early (just `nbformat` + one Markdown cell) so the
      user can eyeball JupyterLab and VS Code rendering of the one-line `$$` in blockquotes.

### Phase 2: Text escaping (prose vs. text-in-math)
- [ ] `markdown_prose(text)` for headings, comment lines and comment paragraphs. Backtick
      pairs pass through as code spans (Markdown-native, so no `\texttt`). Outside code
      spans, backslash-escape the Markdown specials that change meaning mid-line:
      `\ * _ [ ] < > # | ~`, plus `$` (escaped `\$`, or prose with a dollar sign becomes
      math in Jupyter). Leave `.`, `-`, `+`, `!` and `(`/`)` alone; they only matter at
      line start. A leading `#`/`-`/`+`/`1.` is escaped only at the start of a paragraph.
      Quotes are left as typed (no TeX `` `` ''`` conversion).
- [ ] Heading: `"#" * min(level, 6) + " " + markdown_prose(content)`. Strip a trailing `#`.
- [ ] `math_text(text)` for content placed inside `\text{...}` in math (inline comments and
      string constants). MathJax 3 and KaTeX treat `\text` content literally except
      `\ { } $` (and `%` in KaTeX). Escape `{`→`\{`, `}`→`\}`, `$`→`\$`, `%`→`\%`, and
      `\`→`\backslash` (wrapped as `$\backslash$` inside text, or split the `\text`). Do
      **not** use `\textasciicircum`/`\textbackslash`, which MathJax lacks; `^`, `_`, `~`,
      `&` and `#` are fine literally in MathJax `\text` (verify `&` and `#` in KaTeX). Backtick
      pairs inside comments: drop the backticks or use `\texttt{}` (KaTeX and MathJax both
      support `\texttt` in math).
- [ ] Inline comment handler: `COMMENT_OPEN + math_text(content) + COMMENT_CLOSE`.
- [ ] String constant: override the `constant` handler. Strings become
      `\text{"value"}` (straight quotes, `math_text`-escaped). Delegate other types to
      the LaTeX handler (`LR.node_handlers['constant']`).
- [ ] Block headers (`Since $...$ is True:`, `Iterating over each $x$ in $X$:`,
      `Evaluating $f(x)$:`) are already Markdown + inline math. Check the long
      `if` condition still renders (inline `$` may not wrap in narrow cells, which is
      acceptable).

### Phase 3: MathJax / KaTeX compatibility of the math itself
- [ ] `<` / `>` comparisons: an unprotected `a <b` can be read as an HTML tag by the
      sanitizer or Markdown parser. In MarkdownRenderer use `\lt` / `\gt` (MathJax and KaTeX
      both support them). Override with a `lt_op:pre` / `gt_op:pre` rule that reads a
      class-level operator table. Better: change the LaTeX `swap_operator_symbols` to look up
      `renderer.OPERATOR_SYMBOLS` (a class attribute) so the subclass only overrides the
      dict. **That is a refactor of latex.py with no output change.** Confirm with the
      golden test.
- [ ] Function names: `\arcsinh`, `\arccosh` and `\arctanh` are not defined in MathJax,
      KaTeX or amsmath, so they are also a LaTeX bug. **Fix in both renderers (user decided
      2026-10-15):** in `latex.py` map `asinh`/`acosh`/`atanh` to `\operatorname{arcsinh}` etc.
      MarkdownRenderer inherits the fix. Regenerate `tests/golden/latex_demo.tex` only if the
      demo uses them, review the diff, and add a focused LaTeX test. Commit this separately
      from Markdown work. Also make the math-funcs table a class attribute (same refactor as
      above) so subclasses can override it.
- [ ] Audit every macro the LaTeX renderer emits for MathJax 3 (default TeX packages) and
      KaTeX support. These are expected to be fine: `\bigl \bigr \frac \sqrt \left \right
      \lfloor \lceil \cdot \times \bmod \le \ge \ne \in \notin \infty \mathrm
      \operatorname \text \quad \qquad \; \ldots \colon \rightarrow`. Fix any that fail.
- [ ] The `aligned` environment with multiple `rl` column pairs (params grid) works in
      MathJax 3 and KaTeX. Verify `[t]` is not emitted (MATH_OPEN no longer has it).

### Phase 4: Jupyter default renderer
- [ ] **New config option `jupyter_renderer` (user decided 2026-10-15).** In `config.py`:
      `DEFAULTS["jupyter_renderer"] = "markdown"`, add it to `_BASE_OPTION_TYPES` as `str`,
      and document it in the module docstring next to `default_renderer`.
      `default_renderer` keeps governing bare `HandCalcs()` only.
- [ ] `HandCalcs.__init__` (`object_oriented.py`): exclude `jupyter_renderer` from
      `_context_settings`, as `default_renderer` already is.
- [ ] `interfaces/jupyter.py`: `%%render` reads `jupyter_renderer` (not `default_renderer`)
      and resolves the class with `get_renderer(name)` instead of the hard-coded
      `_RENDERERS` dict. Raise a clear error for an unknown name.
- [ ] Choose the display class from the renderer: add `display_type` (or a mapping keyed by
      `renderer.name`) with `"markdown" → Markdown`, `"latex" → Latex`, `"html" → HTML`,
      default `Pretty`.
- [ ] `%hc_default_renderer`: set `jupyter_renderer` (it is the Jupyter magic). Accept any
      registered renderer name that has a display class, `markdown` included. Update both
      error messages (they hard-code `('latex', 'html', 'plain_text')`).
- [ ] Tests in `tests/test_config.py`: the default value, type validation, and that the
      option does not leak into the render context.
- [ ] ~~`_repr_markdown_` on the object-oriented result~~: not now (user, 2026-10-15).

### Phase 5: Tests, golden file and check script
- [ ] `tests/test_markdown_renderer.py`, modelled on `tests/test_latex_renderer.py`:
  - golden demo comparison, section by section, against `tests/golden/markdown_demo.md`
    (`HANDCALCS_UPDATE_GOLDEN=1` to regenerate);
  - no LaTeX text-mode leakage anywhere in the output: `\medskip`, `\noindent`,
    `\begin{list}`, `\section`, `\texttt` outside math, `<br>`;
  - every `$$` group is on one line, has balanced `$$`, and contains no blank line;
  - blockquote depth: parse with `markdown-it-py` and assert nesting for if/for/def,
    including the lazy-continuation case (depth 2 → depth 1 → depth 0);
  - escaping: prose with `*`, `_`, `$`, `<`, backticks; an inline comment with
    `{ } $ % \ ^`; string constants with quotes;
  - `\lt`/`\gt` used for comparisons; no `\arcsinh`-style undefined macros;
  - LatexRenderer output unchanged (its golden test already guards this).
- [ ] `scripts/markdown_demo_check.py`: print the demo Markdown and write
      `markdown_demo.ipynb` (one Markdown cell, plus a code cell using `%%render` for a live
      check). If `node` and `mathjax-full` are available, also typeset every math fragment
      and report errors, the counterpart of the pdflatex compile check. Skip with a message
      otherwise.
- [ ] Jupyter interface test (if IPython is importable): `%%render` with the default config
      displays a `Markdown` object, and `%hc_default_renderer latex` switches it to `Latex`.
  - line breaks: a blank source line yields exactly one `&nbsp;` paragraph, including inside
    a blockquote.

### Phase 6: Docs and wrap-up
- [ ] Update the docstrings in `markdown.py` (class docstring describes the target format
      and the blockquote rules).
- [ ] README / docs: MarkdownRenderer is the Jupyter default (`jupyter_renderer` config
      option); `%hc_default_renderer latex` switches it.
- [ ] Update `latex_implementation_plan.md` cross-reference and the memory note.

## Decisions (user, 2026-10-15)
1. `\arcsinh`/`\arccosh`/`\arctanh`: fix in **both** renderers (Phase 3).
2. Jupyter default: a **new `jupyter_renderer` config option** (default `"markdown"`);
   `default_renderer` still governs bare `HandCalcs()` (Phase 4).
3. One-shot line breaks: an **`&nbsp;` spacer paragraph** (Phase 1).
4. `_repr_markdown_` on the object-oriented interface: **not now**.

## Progress log
- 2026-10-15: Explored the user's draft `markdown.py` (a copy of `latex.py`) and the demo
  output. Wrote this plan.
- 2026-10-15: Recorded the user's answers to the open questions (see Decisions).
