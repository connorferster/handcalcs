# Tests

```console
$ uv run pytest                       # everything
$ uv run pytest tests/test_latex_renderer.py -q
$ uv run pytest --cov=handcalcs       # with coverage
```

## Layout

| Files | Cover |
|---|---|
| `test_parser.py`, `test_sequence.py` | Source → node tree, and the post-parse passes |
| `test_nodes.py`, `test_line_nodes.py`, `test_block_nodes.py`, `test_inline_nodes.py`, `test_operator_nodes.py`, `test_null_values.py` | Node classes |
| `test_render_nodes.py`, `test_base_renderer.py`, `test_infix.py`, `test_multiline.py` | `BaseRenderer` handlers on hand-built nodes |
| `test_ascii.py`, `test_latex_renderer.py`, `test_markdown_renderer.py`, `test_excel_*.py` | Each renderer, through the full pipeline |
| `test_handcalcs.py`, `test_demo.py`, `test_decorator.py`, `test_jupyter.py` | The interfaces |
| `test_config.py` | Configuration |

`tests/conftest.py` provides `renderer` (a fresh `BaseRenderer`) and `make_context` (a
`BaseRenderContext` factory) for rendering a single hand-built node in isolation, so node
tests don't depend on the parser.

`submodule_1.py` and `submodule_2.py` are import targets for the parser tests.

## Golden files

The LaTeX and Markdown renderers are tested against `tests/golden/latex_demo.tex` and
`tests/golden/markdown_demo.md`: the rendered demo, compared section by section. After an
**intended** change to the output, regenerate and review:

```console
$ HANDCALCS_UPDATE_GOLDEN=1 uv run pytest tests/test_latex_renderer.py tests/test_markdown_renderer.py
$ git diff tests/golden
```

## Optional checks

Some tests are skipped unless a tool is available:

- **LaTeX compile**: `test_latex_renderer.py` compiles the demo with `pdflatex` if it is
  installed. `scripts/latex_demo_check.py` does the same by hand and reports overfull
  boxes.
- **KaTeX**: `test_markdown_renderer.py` typesets every math fragment with KaTeX when
  `HANDCALCS_KATEX_JS` points to `katex.min.js` and `mini-racer` is installed:

  ```console
  $ HANDCALCS_KATEX_JS=katex.min.js uv run --with mini-racer pytest tests/test_markdown_renderer.py
  ```

- **Excel recalculation**: `scripts/excel_demo.py` writes the Excel demo; run it with
  `uv run --with formulas` to recalculate every formula independently and compare it
  with Python.

## Configuration in tests

Tests that touch configuration point `HANDCALCS_CONFIG` at a temporary file and reset
the in-memory config (see the `isolated_config` fixture in `test_jupyter.py`), so a
developer's own saved config never affects results.

## The docs as tests

Every `hc-example` block in these docs runs handcalcs when the docs are built, and a
failure stops the build with the exception. Building the docs is therefore a check on the
examples (see [Documentation](documentation.md)).
