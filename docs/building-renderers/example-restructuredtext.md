# Example: a reStructuredText renderer

**Technique: tokens, handlers and `join_item`.** reStructuredText (reST) is the markup of
Sphinx and docutils. Its math is LaTeX, so this renderer starts from `LatexRenderer` and
keeps all of its math. What changes is the text around the math: headings, paragraphs,
imports, how math groups are wrapped, and how block bodies are indented.

## The code

```{literalinclude} ../_examples/rst_renderer.py
:language: python
```

## The result

```{hc-example}
:renderer-file: _examples/rst_renderer.py
:renderer-class: RstRenderer
:output-language: rst
:setup: from math import sqrt
## Web check
# The web must be at least class 2.
h_w = 310; t_w = 6; F_y = 350
x_1 = h_w / t_w  # slenderness
if h_w / t_w <= 1100 / sqrt(F_y):
    web_class = 1
```

## How it works

The changes fall into the three levers, in order of size.

**Tokens.** `MATH_SKIP`, `PARAGRAPH` and `LINE_BREAK` replace LaTeX commands (`\medskip`,
`\noindent`) with reST equivalents. `MATH_OPEN` and `MATH_CLOSE` become the bare
`aligned` environment; they also act as markers that `LatexRenderer.join_item` uses to
recognise a math group, so they must stay distinct strings.

**Handlers.** `heading`, `comment_line` and `import` are replaced, because LaTeX's
versions emit `\section*` and escape text for LaTeX. The math handlers (names,
operators, constants) are all inherited.

**Methods.**

- `math_group` wraps a group's rows in a `.. math::` directive and indents them, which
  reST requires.
- `paragraph` returns text unchanged (LaTeX adds `\noindent`).
- `join_item` handles the one shape that differs: a block with a header (an `if` or
  `for`). reST indents a block body as a block quote, so the method joins the body one
  level deeper, indents every line, and converts the header's inline `$...$` math (from
  the inherited `header:if_block` handler) to the `:math:` role. Every other item goes to
  `LatexRenderer.join_item`.
- `complete` strips the surrounding blank lines.
- `preamble` and `postamble` are emptied, so a file written with `destination=` holds
  only the reST, not the LaTeX document the parent class {ref}`writes <to-file>`.

## Checking the output

reST is strict about indentation and blank lines, so check the output with docutils:

```python
import docutils.core

docutils.core.publish_string(rst_text, writer_name="html",
                             settings_overrides={"halt_level": 2})
```

`halt_level=2` turns warnings into exceptions, which makes this a one-line test. See
[Testing your renderer](testing.md).

**Next:** [Example: structured data](example-json.md).
