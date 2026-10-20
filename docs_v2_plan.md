# handcalcs v2 docs rewrite — plan and status

Resume here. Branch: `docs/prerelease_docs_upa` (based on `hc2/dev`).
Commit after every page or two; update the **Status** table below in the same commit.

## Goal

Rewrite the docs from scratch for the v2 release with Sphinx and the
[Shibuya](https://shibuya.lepture.com/) theme. Six focus areas:

1. Getting started / basic usage
2. Using the renderers
3. Using the interfaces
4. Customizing existing renderers (e.g. colors in the HTML output, Markdown tokens)
5. Building a new renderer (architecture, commonly overridden methods, examples; links into the source)
6. Developer's guide (links into the source)

## Design: layers of an onion

Every section works the same way, so a reader always knows where to look:

- **Layer 0, the landing page** (`index.md`): one paragraph on what handcalcs does, a
  30-second example, and a card grid with one card per section ("I want to...").
- **Layer 1, the section index** (`<section>/index.md`): the "what you need to know to
  get going" page. Short, task-first, one runnable example, and a "Go deeper" card grid
  pointing at the section's other pages. Someone who reads only this page can do the
  common thing.
- **Layer 2, topic pages**: one task or concept each, in full.
- **Layer 3, reference**: exhaustive tables and the API (autodoc), linked from layer 2
  rather than read in order.

Each page opens with a one- or two-sentence summary and ends with "Next" / "See also"
links.

## Tooling decisions

- **Sphinx + Shibuya**, pages in **MyST Markdown** (the existing docs and the README are
  Markdown, so contributors don't have to learn reST). `myst-parser` with `colon_fence`,
  `dollarmath`, `amsmath`, `deflist`, `fieldlist` enabled.
- `sphinx-design` for cards, tabs and grids; `sphinx-copybutton` for code blocks.
- `sphinx.ext.autodoc` + `napoleon` for the API reference; `sphinx.ext.intersphinx`
  for Python.
- **Source links**: an `extlinks` role, `{source}` ``src/handcalcs/renderers/base.py``, that
  points to GitHub at a single ref set in `conf.py` (`HC_SOURCE_REF`, currently
  `hc2/dev`; change it to the release tag at release). Also `sphinx.ext.linkcode` so
  every autodoc entry gets a `[source]` link to the same ref, with line numbers.
- **Live examples**: a small local extension (`docs/_ext/hc_example.py`) with a
  `hc-example` directive. It runs handcalcs on the directive's body at build time and
  shows the source next to the real output, so examples can never go stale:
  - `plain_text` / `latex` / `base` → output shown as a code block
  - `markdown` → output parsed as MyST (math is typeset by MathJax)
  - `html` → output embedded as raw HTML
- Dependencies: `doc` optional dependency in `pyproject.toml` (already exists, holds only
  `sphinx`) gets the theme and extensions. Build: `uv run --extra doc sphinx-build docs docs/_build/html`.
- Old MkDocs files (`mkdocs.yml`, the v1 pages in `docs/`) are removed; `docs/images` stays
  for anything still accurate. v1 screenshots are **not** reused where v2 output differs;
  the `hc-example` directive replaces them.

## Site map

```
index.md                         Landing: what/why, 30-second example, 6 cards
getting-started/
  index.md                       L1: install, first %%render cell, first HandCalcs() script
  installation.md                pip/uv, extras ([excel], [doc]), Jupyter setup
  how-it-works.md                What a cell becomes: calc lines, params, comments,
                                 headings, conditionals, loops; symbolic/numeric/result
  writing-calculations.md        Calc lines, params grids (; and -h), headings (##),
                                 comment lines, inline comments, Jinja in comments
  comment-commands.md            # hc: flags (-f -m -p -h -c -b -i -w) with examples
  formatting-numbers.md          format_code, per-line/per-block overrides
  configuration.md               set_option/save_config/reset, config file location,
                                 HANDCALCS_CONFIG
  units.md                       forallpeople / pint
  gotchas.md                     What isn't rendered, out-of-order cells, disclaimer
  migrating-from-v1.md           v1 → v2 changes (override tags → # hc: commands, etc.)
interfaces/
  index.md                       L1: comparison table, pick one
  jupyter.md                     %%render, %hc_default_renderer, %hc_format_code,
                                 display classes
  object-oriented.md             HandCalcs(renderer)(source | Path, globals), demo()
  decorator.md                   @handcalc(renderer, render_context), return value
renderers/
  index.md                       L1: comparison table (output type, where it displays),
                                 choosing, selecting by name
  plain-text.md
  latex.md
  markdown.md
  html.md
  excel.md                       (rewrite of docs/excel_renderer.md)
  base.md                        BaseRenderer output (the nested list)
customizing/
  index.md                       L1: the three levers (context/config, class tokens,
                                 registered rules) + one 5-line example
  render-context.md              Context fields (space, newline, lpar, format_code, ...)
                                 and passing them through config / render_context
  html-styling.md                CSS classes, the custom properties (--hc-gap, ...),
                                 adding colors (host CSS and subclass STYLE), dark mode
  latex-markdown-tokens.md       MATH_OPEN/CLOSE, ROW_SEP, BLOCK_PREFIX, HEADINGS,
                                 COMMENT_OPEN, OPERATOR_SYMBOLS, MATH_FUNCS
  symbols-and-functions.md       Adding symbols/functions with name:sym and
                                 function_call:pre rules
  per-instance-handlers.md       register_handler on one renderer instance
  recipes.md                     Short copy-paste recipes (colored results, units in
                                 bold, hide imports, ...)
building-renderers/
  index.md                       L1: the 20-line renderer, and the mental model
  architecture.md                Pipeline: source → parse (HcSequence) → render tree
                                 → join → complete; diagram; links to source
  nodes.md                       Node types a renderer sees, grouped (line/block/
                                 inline/operator/values), attributes; links
  registration.md                register / register_handler; classifiers: bare,
                                 {type}:pre|sym|num|post, header:{type}, root:pre|post;
                                 execution order
  render-context.md              BaseRenderContext: global vs line, current_mode,
                                 how comment commands change it
  overridable-methods.md         create_context, complete, join / join_items /
                                 join_item, format_param_grid, format_calc_grid,
                                 render_header; when to override each
  output-tree.md                 The nested-list shapes join() consumes
  example-unicode.md             Tutorial: subclass PlainTextRenderer (rules only)
  example-restructuredtext.md    Tutorial: subclass LatexRenderer, swap tokens + join
  example-json.md                Tutorial: non-text output (override complete)
  testing.md                     Testing a renderer (golden files, pytest patterns)
  publishing.md                  Naming/registry, Jupyter display class, packaging
developers/
  index.md                       L1: clone, uv sync, run tests, build docs
  repository-layout.md           Package map with source links
  parsing.md                     ast_parser, nodes, sequence, comment_parser,
                                 function_recursion; links
  rendering-internals.md         base.py walkthrough (render_node rule order,
                                 precedence/parenthesization, param lines)
  adding-a-node-type.md          Parser + BaseRenderer + each built-in renderer
  testing.md                     Test suite layout, golden tests, regenerating
  documentation.md               Building these docs, hc-example directive, style
  releasing.md                   Version bump, HC_SOURCE_REF, publish workflow
reference/
  index.md
  api.md                         autodoc: HandCalcs, handcalc, config, renderers
  comment-commands.md            Table of every # hc: flag
  configuration-options.md       Table of options/defaults
  node-types.md                  Table: node type string → class → module
  classifiers.md                 Table of every registration classifier form
  changelog.md
```

## Phases

1. Scaffold: deps, `conf.py`, Shibuya config, `hc-example` extension, landing page, empty
   section indexes, remove MkDocs. Build passes.
2. Getting started (all pages).
3. Interfaces.
4. Renderers.
5. Customizing.
6. Building renderers (verify each example runs; examples are tested by the build).
7. Developer's guide.
8. Reference + API.
9. Polish: cross-links, "Next" links, `-W` (warnings as errors) build, README docs link,
   RTD config (`.readthedocs.yaml`) if wanted.

## Status

| Phase | State | Notes |
|---|---|---|
| 0 Plan | done | this file |
| 1 Scaffold | done | builds clean; `hc-example` directive works for md/html/code |
| 2 Getting started | done | all 10 pages |
| 3 Interfaces | done | decorator page describes intended behaviour (see issue) |
| 4 Renderers | done | excel.md adapted from the old page |
| 5 Customizing | done | examples in docs/_examples, run by hc-example |
| 6 Building renderers | done | 12 pages; src role links objects to exact lines |
| 7 Developers | done | 8 pages |
| 8 Reference | done | classifiers tables generated by hc-registry at build time |
| 9 Polish | done | `sphinx-build -E -W` passes with zero warnings |

## Release pass (2026-10-20, v2.0rc1)

Goal: merge this branch into hc2/dev for v2.0rc1 with lots of recipes. Merge order agreed
with the other sessions: features/final_pass → features/ascii_renderer → this branch last
(merge origin/hc2/dev in first; never rebase).

| Step | State | Notes |
|---|---|---|
| KaTeX math + tabbed live examples | done | `sphinxcontrib-katex`; hc-example shows Rendered / raw tabs; LaTeX output converted by `latex_to_myst` |
| Cookbook section (`docs/cookbook/`) | done | numbers, showing-and-hiding, checks, symbols, units, documents, workflows; old customizing/recipes folded in |
| final_pass handoffs 1-3 | done | IfExp, `.to()` on expressions, cbrt/factorial/inf, print skip, `--pagebreak`, `--check` |
| final_pass #54 via `_` | done | handoff 4; render_cell documented |
| More live examples | done | formatting-numbers, comment-commands, migration guide, a fuller example per renderer page |
| Units bugs (reported to final-pass agent) | done | handoff 5; cookbook/units.md examples now live | fap/pint formatting in LaTeX/Markdown/HTML; then make cookbook/units.md examples live |
| `-i` on import/expr lines (reported) | done | handoff 5 |
| ASCIIRenderer rename (handcalcs-7f, PR #309) | waiting | no aliases; merge hc2/dev with `-X find-renames=40%`; rename PlainTextRenderer/plain_text across docs; plain-text.md → ascii.md |
| PR into hc2/dev | todo | after the two feature PRs merge |

## Source issues found while writing (report to user; not fixed in this branch)

- **`@handcalc` renders nothing.** `HcSequence.from_source` turns a top-level
  `def` into a single `NoValue`, so the decorator returns `(value, '')` (or `['']` for
  BaseRenderer). `tests/test_decorator.py` only checks types, so it passes. Docs show
  decorator examples as static code (no `hc-example`).
- **`# hc: -w` (`if_winner_only`) is parsed but nothing reads it.** Documented as
  reserved.
- **`# hc: -i` line followed by an inline `# hc: -p` line** rendered the `-p` line as
  three separate lines (`p2` / `=` / `6.00`) in PlainText (seen with a `-b` before it).
- **forallpeople unit symbols in the numeric column render empty**: `L = 6 * m` shows
  `6 *  = 6 m`.

- **Consecutive `-m` calcs in PlainText** are joined onto one line
  (`= 8 d = a * b + b`): the multi-line grid string is space-joined with the next line.
- **`x = (expr).method()`** crashes the parser (`AttributeError: 'BinOp' object has no
  attribute 'id'`, ast_parser.py ~456).
- **Inline `# hc: -i` on an `import` line** does not hide it; `-i` on a `;` line renders
  a broken grid cell.
- **Conditional expressions** (`x = 1 if a else 0`) render as `x =  = 1`.

- **`%%render` swallows exceptions**: a cell that raises displays nothing and the
  traceback is captured by `cell_capture` (jupyter.py). Documented as a warning.

- **LatexRenderer/MarkdownRenderer `create_context` collide with config**: setting
  `space`, `newline`, `indent`, `lpar` or `rpar` with `set_option` raises
  `TypeError: RenderContext() got multiple values for keyword argument` (latex.py
  `create_context` passes them explicitly *and* in `**kwargs`). Documented as a caveat.

## Not done (needs a decision)

- No `.readthedocs.yaml` / Pages workflow yet (hosting undecided).
- README still has the v1 content; not touched.
- `requires-python` is missing from pyproject (uv warns; CI tests 3.11-3.14).

## Open questions for the user

- Hosting: Read the Docs (add `.readthedocs.yaml`) or GitHub Pages (add a workflow)?
- `HC_SOURCE_REF`: `hc2/dev` until release, then `v2.0.0`?
- Should the README shrink to a short intro + link to the docs?

## Resume checklist

1. `git log --oneline -10` and `git status`; check file mtimes for edits you didn't make
   (another session may still be alive — ask the user before continuing if so).
2. Read the Status table; continue the first phase not marked done.
3. Build: `uv run --extra doc sphinx-build -b html docs docs/_build/html` (foreground).
