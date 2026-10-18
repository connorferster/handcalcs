# handcalcs v2.0 — pre-release review

**Date:** 2026-10-18
**Audited ref:** `origin/hc2/dev` @ `e1097cf` (this branch was fast-forwarded to it). The other branches checked were `docs/prerelease_docs_upa` and `features/reportlab_renderer`.
**Method:** I ran the test suite on Python 3.11–3.14 and `black --check` as CI does. I built the sdist and wheel with flit and smoke-tested the wheel in a clean venv. I exercised `%%render` in a real IPython shell and probed the parser with edge-case snippets. I built the Sphinx docs with `-W`, and trial-merged both open branches into `hc2/dev` in throwaway worktrees.

---

## Verdict

**Not ready to tag 2.0.0 yet. It can be ready this week.** The core is in good shape:

- 775 tests pass on 3.13 and 3.14 in about 2 s.
- Coverage of the v2 code is about 93% (the "75%" total counts the `superceded/` v1 code).
- The Markdown, LaTeX, HTML, plain-text and Excel renderers all render the demo.
- The new Sphinx docs build with zero warnings.

Several problems would still give users a broken experience on day one. One is that **`import handcalcs` fails on a clean `pip install`**, and two others affect a supported interface or Python version. Each one is small to fix. Most of the remaining work is merging and housekeeping: docs, packaging metadata and CI. The ReportLab extraction is done on the handcalcs side (§4).

Suggested path: fix the blockers (§1), merge the docs branch, publish **2.0.0rc1** to PyPI as a pre-release, smoke-test it from PyPI in a fresh notebook, then tag 2.0.0.

---

## 1. Release blockers

| # | Issue | Where | Fix size |
|---|---|---|---|
| B1 | **`import handcalcs` crashes without IPython.** IPython is imported at top level but is not a dependency, and the guard catches `AttributeError` rather than `ImportError`. On a clean `pip install handcalcs` in a plain venv, `import handcalcs` raises `ModuleNotFoundError: No module named 'IPython'`. | `src/handcalcs/__init__.py:7-12` | 1 line: `except (ImportError, AttributeError):`. Also add a test that imports handcalcs with IPython blocked. |
| B2 | **`@handcalc` renders nothing.** The decorator passes the full `@handcalc(...)\ndef f(...):` source to the parser. The parser has no `ast.FunctionDef` branch and returns `NoValue`, so every renderer returns an empty render: `(7, '')`, `['']` or `'\n'`. `tests/test_decorator.py` only checks types, so it passes. (The docs session found this too, and the docs show decorator examples as static code.) | `interfaces/decorator.py:29-32`; `parsing/ast_parser.py` (no `FunctionDef` case) | Small: `textwrap.dedent` the source, parse it, take the `FunctionDef` body, and render that (ideally with the `return` line). Add content assertions to the tests. |
| B3 | **Decorating a nested function or a method fails** with `IndentationError: unexpected indent`, because `inspect.getsource` returns indented source. | `interfaces/decorator.py:29` | Fixed by the `dedent` in B2. |
| B4 | **Python 3.11 and 3.12 are broken.** `exec(stripped, locals=kwarg_locals)` uses a keyword that only exists from 3.13. Every `# hc: key=value` comment raises `TypeError`, which gives 104 failures and errors on each version. CI's matrix includes 3.11 and 3.12. | `parsing/comment_parser.py:45` | 1 line: `exec(stripped, {}, kwarg_locals)`. Then set `requires-python` (see P1). |
| B5 | **CI would fail the release PR.** `black src --check` reports 52 files to reformat. Also, `python-pytest.yml` only runs on pushes and PRs to `main`, so none of the `hc2/dev` work has been through CI. | `.github/workflows/python-pytest.yml` | Run `black src` (or scope black to exclude `superceded/`) in one commit. Add `hc2/dev` to the workflow triggers. |
| B6 | **The PyPI page would show the v1 README.** The README still documents `import handcalcs.render`, `%%tex`, `@handcalc(override=..., precision=...)`, `display_precision` and v1 override tags. It is the package's `readme`, so it becomes the PyPI landing page. | `README.md` | Rewrite it as a short v2 intro plus a link to the hosted docs (see §3). |

---

## 2. High priority (fix before 2.0.0 if at all possible)

### 2.1 Upgrade path for v1 users
Anyone with an unpinned `handcalcs` gets v2 on their next install, and the two most common v1 entry points fail hard:

- `import handcalcs.render` raises `ModuleNotFoundError`. This is the first cell of almost every v1 notebook.
- `@handcalc()` raises `TypeError: handcalc() missing 1 required positional argument: 'renderer'`.

**Recommendation:**
- Add a tiny `handcalcs/render.py` shim. It should `import handcalcs` (which registers the magics) and emit a `FutureWarning` that points to the migration guide.
- Make `renderer` optional in `handcalcs()`, defaulting to the configured `default_renderer` the way `HandCalcs()` does. If v1 keyword arguments such as `override` or `precision` are passed, raise a clear error that links to the migration page.
- Add a top-level `load_ipython_extension` so `%load_ext handcalcs` works. It currently prints "The handcalcs module is not an IPython extension".
- Put the breaking change prominently in the GitHub release notes.

### 2.2 `%%render` swallows exceptions
A cell that raises (for example `x = 1/0`) displays nothing, and the traceback is captured by `cell_capture`. Users will think handcalcs is broken. `interfaces/jupyter.py:105-109`: when `exec_result.success` is false, re-raise or show the captured stderr/traceback instead of `return None`.

### 2.3 Parser gaps and crashes in common engineering code
Reproduced on `hc2/dev` with `PlainTextRenderer`; HTML, LaTeX and Markdown share the parser:

| Input | Output |
|---|---|
| `x = (2 + 3).bit_length()` | **crash**: `AttributeError: 'BinOp' object has no attribute 'id'` (`ast_parser.py:456`; `ast_parser.py:680` has the same pattern for attributes) |
| `y = xs[0] * 2` (subscript) | `y =  * 2 = 2`: the subscript is dropped |
| `x = 1 if a else 0` | `x =  = 1` |
| `s = f'{a} m'` | `s =  = 2 m` |
| `b = (a := 3) + 1` | `b =  + 1 = 4` |
| `f = lambda x: x*2` | `f =  = <function <lambda> ...>` |
| `a += 2` | `a = 3`: the augmented assignment disappears |
| `while ...:` block | the whole block disappears |
| `with ...:` block | the whole block disappears |
| `import math # hc: -i` | the import is still shown |
| `math.sqrt(4)` in plain text | `math.√(4)`: the prefix stripping is HTML-only (see the memory note), so other renderers show a half-converted form |

Subscripts and conditional expressions are common in calc sheets, so I'd fix those two plus the crash. For the rest, unsupported nodes should at least show as `HcNotImplemented` (or the original source text) rather than an empty column. Document what remains in `getting-started/gotchas.md`. Also note that numeric substitution uses *final* namespace values. `t = t + i` inside a loop therefore shows `3 + 2 = 3`, which is inherent to the design and worth stating in the gotchas page.

### 2.4 `set_option` breaks the LaTeX and Markdown renderers for some names
`set_option("space" | "newline" | "indent" | "lpar" | "rpar", ...)` makes the LaTeX and Markdown renderers raise `TypeError: RenderContext() got multiple values for keyword argument ...`. The cause is that `latex.py:250-262` passes these arguments explicitly *and* via `**kwargs`. The fix is to merge the defaults, e.g. `{**defaults, **kwargs}`.

### 2.5 HTML escaping is inconsistent
Inline comments are escaped, but comment lines, headings and string values are not. `# a < b & c` emits raw `a < b & c`, which is malformed HTML, and `s = '<i>hi</i>'` injects markup. If raw HTML in comments is intentional, document it. String values should be escaped in any case.

### 2.6 An unknown `# hc:` flag exits the process
Comment commands are parsed with `argparse`, which calls `sys.exit(2)` on an unrecognised option. A typo such as `# hc: --mdoe no_num` therefore raises `SystemExit` and prints argparse's usage text, instead of raising an ordinary error that names the line. Under `HandCalcs()` in a script, that ends the whole program. Found 2026-10-18. The fix is `argparse.ArgumentParser(exit_on_error=False)` plus overriding `error()` to raise a `ValueError` (`parsing/commands.py`).

### 2.7 A format code is applied to literal exponents (LaTeX/Markdown)
With `# hc: -f .3f`, `a**2` renders as `a^{2.000}` in the LaTeX and Markdown renderers; the plain-text renderer is unaffected. Found 2026-10-18. Exponent literals should keep their source form.

---

## 3. Documentation

### State
- **`hc2/dev` still has the v1 MkDocs docs.** That means `mkdocs.yml`, eight v1 pages and many v1 GIFs and screenshots. `docs/_build/` exists locally but is gitignored.
- **The v2 rewrite exists but is unmerged.** It lives on `docs/prerelease_docs_upa`: 15 commits, 58 HTML pages, built with Sphinx and Shibuya in MyST Markdown. Its live `hc-example` directive runs handcalcs at build time, so the examples cannot go stale.
- **Coverage of the rewrite is excellent.** It has Getting started (10 pages, including *Migrating from v1*, *Gotchas* and *Units*), Interfaces, Renderers (one page each), Customizing, Building renderers (12 pages with source links), a Developer guide and a Reference section (API autodoc, comment commands, config options, node types and a changelog). This is a big improvement over v1.
- **I verified the build.** `sphinx-build -E -W` passes with zero warnings on the branch. It **also passes after trial-merging `hc2/dev` into it**. The only conflict is `.gitignore`, a trivial union, and the merge also deletes the stale plan files cleanly.

### To do before release
1. **Merge `docs/prerelease_docs_upa` → `hc2/dev`.** Resolve the `.gitignore` conflict, and make sure the merge does not bring back `HTML_alternatives.md`, `latex_implementation_plan.md` and the other plan files that 3bc1532 removed (the trial merge dropped them correctly). The merge also brings the `doc` extra: `sphinx`, `shibuya`, `myst-parser`, `sphinx-design` and `sphinx-copybutton`.
2. **Choose hosting** (still undecided in `docs_v2_plan.md`). Read the Docs needs a `.readthedocs.yaml`; GitHub Pages needs a workflow. Read the Docs gives versioned docs (v1 and v2 side by side) for free, which helps v1 users. I recommend it.
3. **Set `HC_SOURCE_REF` in `docs/conf.py` to the release tag** (`v2.0.0`) at release, so the source links do not drift as `hc2/dev` and `main` move.
4. **Update the docs as the §1/§2 fixes land.** The decorator page currently describes *intended* behaviour (B2), and the docs carry caveats for the `%%render` exception swallowing and the `set_option` collision. Once those are fixed, update the pages and convert the decorator examples to live `hc-example` blocks.
5. **Rewrite the README** (B6): v2 quick start, renderer list, install extras and a link to the docs. Fix the badges too: Coveralls points at `branch=master`, and the repo uses `main` and has no coverage upload in CI. README links such as `docs/excel_renderer.md` are relative and break on PyPI; use absolute URLs.
6. **Turn the changelog into release notes.** `reference/changelog.md` has a good 2.0.0 summary. Reuse it for the GitHub release notes, adding the breaking-change table from the migration page and the date when you tag.
7. **Retire the docs-adjacent clutter at the repo root.** `wiki_text.md` is v1 FAQ and LaTeX-install text. `Examples/streamlit_example.py` uses `from handcalcs.handcalcs import handcalc`, which is v1 and no longer exists. `excel_renderer.md` and `Excel_Renderer_Plan.md` are design notes. Delete them or move them out of the release branch; the useful parts of `wiki_text.md` could become a docs page.
8. **The `%%render sympy` path is gone.** The migration page says "not available in 2.0"; make sure the old `docs/sympy.md` is not still linked anywhere after the merge.

---

## 4. `ym_handcalcs` / ReportLab renderer (known issue)

**Update, 2026-10-18: resolved on the handcalcs side.** Nothing ReportLab-related remains in `hc2/dev`. Everything this section originally listed has been dealt with:

1. **Core changes:** they were ported to `hc2/dev` separately. PR #296 brought the `--mode` command and the `no_num`/`no_sym`/`drop_numeric`/`drop_symbolic` aliases (`mode_columns()` in `renderers/base.py`). They ship in 2.0, but the docs branch does not document them yet.
2. **Breakage:** `ReportLabRenderer` now subclasses `BaseRenderer`, not `HTMLRenderer`, and implements its own inline rules. HTML changes therefore no longer reach the PDF, and all of its tests pass against current `hc2/dev`. Two guard tests keep it that way.
3. **Internals:** it now depends only on `handcalcs.renderers.base` and the parser node classes, and a test enforces that. The target package should still pin `handcalcs>=2.0,<2.1` until those are declared stable.
4. **Core fixes found along the way, now merged:** PR #297 fixes a calc after an ignored (`# hc: -i`) first line splitting into one line per part (LaTeX dropped it entirely). PR #298 is an HTML renderer tidy-up with byte-identical output.

**Still open:** the move itself. The pushed `features/reportlab_renderer` branch (4821cf1) is the only copy of `ym_handcalcs`; `ymprint` does not have it yet. Its core code is identical to `hc2/dev`, and the branch adds only ReportLab files: `src/ym_handcalcs/`, `tests/test_reportlab_renderer.py`, `tests/golden/reportlab_*.txt`, `scripts/reportlab_demo_check.py`, `reportlab_renderer_plan.md`, the `reportlab` dev dependency and a `reportlab_demo/` `.gitignore` line. Copy them to the target library, add `handcalcs` and `reportlab` as dependencies there, then delete the branch.

---

## 5. Packaging and metadata

| # | Issue | Recommendation |
|---|---|---|
| P1 | No `requires-python`, so uv warns on every command, and flit builds a `py2.py3-none-any` wheel with no Python floor. The code needs ≥3.10 (it uses PEP 604 `X | Y` unions), and needs ≥3.13 until B4 is fixed. | Add `requires-python = ">=3.11"` after fixing B4, and keep CI on 3.11–3.14. |
| P2 | **The wheel ships `handcalcs/superceded/`.** That is the v1 code, its test suite (including a file named `#test_handcalcs.py`) and a 265 KB `style.css`, adding up to 40 files nobody imports. | Delete `superceded/` from the release branch (it lives on in git history and the v1 tags). If you want to keep it, exclude it in `[tool.flit.sdist]` and the wheel. |
| P3 | `IPython` is not declared even though the Jupyter interface is a headline feature. | After B1, add a `jupyter = ["ipython"]` extra (or a dependency), and document `pip install "handcalcs[jupyter]"`. |
| P4 | `parsing/function_recursion/source_expander.py` imports `ast_comments`, which is not a dependency. Nothing imports the module, and it is full of debug `print`s with emoji. | Delete it or move it out of the package until function recursion is revived. |
| P5 | There is no `handcalcs.__version__`. | Add `__version__ = "2.0.0"`. flit can read the version from it with `dynamic = ["version"]`, giving one source of truth. |
| P6 | Metadata is thin. There is one classifier, no `requires-python`, no `keywords` and no Documentation, Changelog or Issues URLs. The author email is `connorferster@gmail.com`; check that this is the address you want on PyPI. | Add Python-version, OS-independent, Framework :: Jupyter, Topic :: Scientific/Engineering and Development Status :: 5 classifiers, plus the URLs. |
| P7 | Stale root files: `requirements.txt` (v1 deps: pyparsing, more-itertools, nbconvert), `vis_pyproject.toml` (a different `handcalcs 0.1.0` hatchling project), `mkdocs.yml` (removed by the docs merge) and an `exporters = ["nb-hideinputs"]` extra that v2 never references. | Delete them. Drop the `exporters` extra unless v2 still documents it. |
| P8 | `uv.lock` is gitignored (`*.lock`), so CI resolves fresh every run. | Fine for a library. Optionally commit the lock so CI is reproducible. |
| P9 | A local `flit build` would ship the untracked `.ipynb_checkpoints/*.py` files under `src/handcalcs/` (they appeared in my local wheel). | Build only from CI's clean checkout (the publish workflow already does), or add `**/.ipynb_checkpoints/` to `.gitignore` and delete them. |

---

## 6. CI and release workflow

- **`python-pytest.yml`:** trigger it on `hc2/dev` (B5). `actions/checkout@v3` and `setup-python@v3` are old, so bump them to v4/v5. Consider `astral-sh/setup-uv` instead of `pip install uv`. Add a job that builds the wheel, installs it into a bare venv and runs `python -c "import handcalcs"`; that would have caught B1.
- **`python-publish.yml`:** it fires on a published GitHub release, using `flit build` and a `PYPI_API_TOKEN` secret.
  - Check that the secret is still valid. The last upload was 1.11.0.
  - Consider PyPI Trusted Publishing, which needs no token.
  - Set `python-version: '3.13'` rather than `'3.x'`.
  - The workflow builds from whatever ref the release tag points at, so **tag on `main` after merging `hc2/dev`**.
- **Version:** `pyproject.toml` says `2.0.0rc1`. Publish that rc first as a GitHub *pre-release*: pip ignores pre-releases unless asked, so v1 users are not affected. Then bump to `2.0.0` for the final release.

---

## 7. Code quality (non-blocking)

- `parsing/ast_parser.py` has about 60 commented-out code lines (the old function-recursion block in `__post_init__`), three TODOs, and a debug `print` at line 569 (`ForBlock, alternate target`). The `print`s at lines 814–816 should become warnings or exceptions.
- `HandCalcs.__repr__` returns `HandCalcs(renderer=<...BaseRenderer object at 0x...>())`; it should use `type(self.renderer).__name__`. The `HandCalcs.__call__` annotation says `-> str`, but the renderers return lists (base) or a workbook object (Excel).
- `HandCalcs.__read` and `__parse` take unused `supplied_locals` parameters, and `__call__` ignores `supplied_locals`.
- An invalid `format_code` (e.g. `"nonsense"`) is silently ignored. `set_option` could validate it with `format(1.0, code)`.
- In the `# hc:` comment commands, `-w` / `--if-winner-only` is parsed but never read (the docs mark it "reserved").
- `parse_kwargs` `exec`s comment text. That is acceptable, because users run their own code anyway, but it is worth one line in the docs.
- Tests skipped by default: 4 need the `formulas` package (Excel recalculation) and 2 need KaTeX/mini-racer. Add `formulas` to the dev group so CI runs them.

---

## 8. What's in good shape

- **Tests:** 775 tests run in about 2 s, with golden-file tests for LaTeX and Markdown. Coverage of the v2 code is ≈93%, and the parser nodes are at 100%.
- **Renderers:** all five built-in renderers render the demo. The LaTeX escaping of `%`, `&`, `_` and `$` is correct. Markdown is a sensible Jupyter default and renders correctly through `%%render`, as verified in an IPython shell. `%hc_default_renderer latex` switches correctly.
- **Optional dependencies:** the ExcelRenderer degrades well without XlsxWriter, raising a clear `ImportError` that names `handcalcs[excel]`.
- **Config:** the config system is well designed. It uses `platformdirs`, has a `HANDCALCS_CONFIG` override, tolerates malformed files, and custom options don't break any renderer.
- **Units:** pint and forallpeople both work. The forallpeople empty-symbol bug noted in the docs plan no longer reproduces.
- **Docs:** the docs rewrite is thorough and builds strictly.

---

## 9. Suggested release checklist (in order)

1. [x] B1: fix the `ImportError` guard in `__init__.py` and add an IPython-less import test. *(branch `fixes/release_blockers`)*
2. [x] B4: fix the `exec` keyword in `comment_parser.py`; add `requires-python = ">=3.11"`. *(`fixes/release_blockers`)*
3. [x] B2 and B3: decorator dedent and body extraction, plus content assertions in `test_decorator.py`. *(`fixes/release_blockers`; also needed innerscope>=0.8.0 for closures on 3.13+)*
4. [ ] §2.1: the `handcalcs.render` shim, an optional `renderer` in `@handcalc`, and `load_ipython_extension`.
5. [ ] §2.2: surface exceptions from `%%render`.
6. [ ] §2.3 (at least the crash, subscripts and conditional expressions) and §2.4 (the `create_context` merge).
7. [x] The `--mode`/`no_num` core changes from the ReportLab branch ship in 2.0 (PR #296). Still to do: document them on the docs branch.
8. [ ] Delete `superceded/`, `function_recursion/` and the stale root files (P2, P4, P7). Add `__version__`, the metadata and the `jupyter` extra (P3, P5, P6).
9. [x] Run `black src`; point CI at `hc2/dev`; add the wheel smoke-test job (B5, §6). *(`fixes/release_blockers`; also fixed the matrix, which tested 3.13 in every cell)*
10. [ ] Merge `docs/prerelease_docs_upa` → `hc2/dev`; update the decorator, gotchas and caveat pages for the fixes. The README rewrite (B6) is done on `fixes/release_blockers`; add the hosted docs link at its TODO.
11. [ ] Set up docs hosting; set `HC_SOURCE_REF = "v2.0.0"`.
12. [ ] PR `hc2/dev` → `main` with green CI on 3.11–3.14 × 3 OSes.
13. [ ] Publish `2.0.0rc1` as a GitHub pre-release. Then `pip install --pre handcalcs` in a fresh venv and notebook and run the demo, the decorator, `%%render` and Excel.
14. [ ] Bump to `2.0.0`, tag and release. Post the migration notes.
15. [ ] Separately: copy `ym_handcalcs` from `features/reportlab_renderer` to its target library and pin `handcalcs>=2.0,<2.1` there; then delete the branch (§4). The `hc-result` breakage is already fixed.
