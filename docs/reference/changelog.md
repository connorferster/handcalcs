# Changelog

## 2.0.0 (unreleased)

A rewrite of handcalcs around a node tree and pluggable renderers.

- **Renderers**: Markdown (the Jupyter default), LaTeX, HTML, ASCII text, Excel, Word
  (editable Word equations; #222) and the base renderer. Renderers can be subclassed and customized, or written from scratch.
- **`ASCIIRenderer`** (`ascii`) for terminals, logs and docstrings: setext-underlined
  headings and calc lines aligned on `=`. It replaces the 2.0 pre-release
  `PlainTextRenderer` (`plain_text`), which has no alias.
- **`HandCalcs` interface** for rendering source strings and files from Python.
- **`# hc:` comment commands**, per line or per section, replacing the v1 cell override
  tags.
- **Headings, prose and Jinja templating** in comments.
- **Nested conditionals and `for` loops.**
- **Configuration** reduced to `format_code`, `default_renderer` and
  `jupyter_renderer`, plus custom options for renderers.
- **Names** ([naming variables](../getting-started/writing-calculations.md#naming-variables)):
  comma subscripts by default (`N_pl_Rd` → N<sub>pl,Rd</sub>; #101), Greek letters joined
  to other letters (`DeltaH`, `ΔH` → ΔH; #117), accents (`x_hat`, `V_dot`, `M_star`) and
  the `symbols` option for display specs, all parsed once and shared by every renderer.
- **Line continuations** (`\`) break a long equation at the same place (#259).
- **`%render`** line magic renders a single line (#179).
- **Bare expressions** (`2 * a`) show their result (#54).
- **Many input sets from one script**: `HandCalcs(...)(script, inputs={...})` renders
  a script with different given values, keeping their units (quantities are
  converted to them); `find_inputs` lists a
  script's inputs ([details](../interfaces/object-oriented.md#rendering-many-input-sets));
  `%%render inputs=case` does the same for a notebook cell.

See [Coming from handcalcs v1](../getting-started/migrating-from-v1.md) for how to
update notebooks.
