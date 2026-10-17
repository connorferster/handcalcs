# Recipes

Short customizations for common requests. Each one is a complete snippet. They use the
three levers described in [Customizing a renderer](index.md).

## Show results only, everywhere

A setting; no code needed.

```python
import handcalcs
handcalcs.set_option("mode", "ass res")
```

Or for part of a calculation: `# hc: mode = "ass res"`.

## Use `:=` (or anything else) between the steps

```python
handcalcs.set_option("assign", ":=")   # plain-text and HTML renderers
```

The LaTeX and Markdown renderers also read `assign`, but it ends up inside math, so give
it LaTeX: `handcalcs.set_option("assign", "\\coloneqq")` (needs the `mathtools` package in
LaTeX).

## Highlight calculated results

- HTML: [Option 3 in Styling the HTML output](html-styling.md#option-3-add-your-own-markup).
- Markdown: [Colors in Markdown math](latex-markdown-tokens.md#example-colors-in-markdown-math).

## Hide import lines

```python
renderer = MarkdownRenderer()
renderer.register_handler("import", lambda renderer, node, base_context: "")
```

See [Customizing one instance](per-instance-handlers.md). For a class, use
`@MyRenderer.register("import")` on the same function.

## `×` instead of `·` for multiplication

```python
class TimesMarkdownRenderer(MarkdownRenderer):
    OPERATOR_SYMBOLS = MarkdownRenderer.OPERATOR_SYMBOLS | {"mult_op": "\\times"}
```

## `ln` instead of `log`

```python
class LnLatexRenderer(LatexRenderer):
    MATH_FUNCS = LatexRenderer.MATH_FUNCS | {"log": "\\ln"}
```

## Wrap the whole output

Override `complete()`, call the parent's, and add to the result:

```python
class FramedLatexRenderer(LatexRenderer):
    def complete(self, tree, base_context):
        body = super().complete(tree, base_context)
        return "\\begin{framed}\n" + body + "\\end{framed}\n"
```

The same pattern adds a page header to HTML output or a title line to plain text.

## Centred LaTeX displays

```python
class DisplayLatexRenderer(LatexRenderer):
    MATH_OPEN = "\\[\n\\begin{aligned}"
    MATH_CLOSE = "\\end{aligned}\n\\]"
    MATH_SKIP = ""
```

## A narrower indent in plain text

```python
handcalcs.set_option("indent", "  ")
```

(Only for the plain-text and base renderers; see the
[caution](render-context.md#four-ways-to-set-a-field) for LaTeX and Markdown.)

## A different symbol for one variable

```python
@MyMarkdownRenderer.register("name:pre")
def swap_symbols(renderer, node, base_context):
    if node.identifier == "V_dot":
        node.identifier = "\\dot{V}"
    return node
```

See [Symbols and functions](symbols-and-functions.md).
