# Changelog

## 2.0.0 (unreleased)

A rewrite of handcalcs around a node tree and pluggable renderers.

- **Renderers**: Markdown (the Jupyter default), LaTeX, HTML, plain text, Excel and the
  base renderer. Renderers can be subclassed and customized, or written from scratch.
- **`HandCalcs` interface** for rendering source strings and files from Python.
- **`# hc:` comment commands**, per line or per section, replacing the v1 cell override
  tags.
- **Headings, prose and Jinja templating** in comments.
- **Nested conditionals and `for` loops.**
- **Configuration** reduced to `format_code`, `default_renderer` and
  `jupyter_renderer`, plus custom options for renderers.

See [Coming from handcalcs v1](../getting-started/migrating-from-v1.md) for how to
update notebooks.
