# Building a renderer

A renderer is a Python class. It inherits a complete, working rendering pipeline from
`BaseRenderer` (or from one of the built-in renderers) and changes only what is
different about its output format. This page gives you the mental model and a working
renderer; the pages after it go into each part.

## The mental model

```text
 your code ──run──▶ values
     │                │
     └──parse──▶ tree of nodes, each variable paired with its value
                      │
          renderer.render()   one handler per node type, plus rules around it
                      │
                      ▼
                render tree      nested lists of strings (or anything you return)
                      │
          renderer.complete()   join into the final output
                      │
                      ▼
                   output        str, bytes, a workbook, a list of dicts...
```

You customize the two middle steps:

1. **Handlers and rules** decide what each node becomes. A *handler* renders one node
   type (`calc_line`, `name`, `div_op`, ...). A *rule* runs before or after a handler to
   adjust the node or its result: swapping `alpha` for `α`, wrapping a result in a tag.
   You register both with a decorator.
2. **`complete()`** turns the tree of rendered pieces into the final output. For text
   formats it calls `join()`, whose per-item method `join_item()` is where layout lives:
   newlines, indentation, wrapping blocks.

## A first renderer

This renderer produces plain text and changes one thing, how multiplication is shown:

```python
from handcalcs.renderers import BaseRenderer


class TimesRenderer(BaseRenderer):
    name = "times"  # registers it, so %hc_default_renderer times works

    def complete(self, tree, base_context):
        return self.join(tree, base_context)  # nested lists -> text


@TimesRenderer.register("mult_op:pre")
def times_sign(renderer, node, base_context):
    node.symbol = "×"
    return node
```

```python
>>> from handcalcs import HandCalcs
>>> print(HandCalcs(TimesRenderer())("a = 2\nb = a * 3\n"))
a = 2
b = a × 3 = 2 × 3 = 6
```

Everything else (calculation lines, parameter grids, conditionals, comment commands,
number formats) comes from `BaseRenderer`.

## Choosing a parent class

| Start from | When your format is | You get |
|---|---|---|
| `BaseRenderer` | something new | the full pipeline; Python-style symbols; plain text from `join()` |
| `ASCIIRenderer` | text with Unicode math | Greek letters, `√`, superscripts |
| `LatexRenderer` | anything that embeds LaTeX math | Greek, subscripts, fractions, operators; math groups |
| `MarkdownRenderer` | a Markdown dialect | the above, with Markdown structure |
| `HTMLRenderer` | HTML | `<sub>`/`<sup>`, entities, a CSS layout |

Inheriting from the closest built-in renderer means less code, and a renderer that is
shown correctly in Jupyter (see [Publishing](publishing.md)).

## Go deeper

::::{grid} 1 2 2 2
:gutter: 2

:::{grid-item-card} Architecture
:link: architecture
:link-type: doc
The full pipeline, step by step, with links to the source.
:::

:::{grid-item-card} Nodes
:link: nodes
:link-type: doc
Every node type a renderer receives, and its attributes.
:::

:::{grid-item-card} Handlers and rules
:link: registration
:link-type: doc
`register`, classifiers, signatures and order of execution.
:::

:::{grid-item-card} The render context
:link: render-context
:link-type: doc
Global and line settings, `current_mode`, and the pitfalls.
:::

:::{grid-item-card} Overridable methods
:link: overridable-methods
:link-type: doc
`complete`, `join_item`, `create_context`, the grid formatters, and when to override each.
:::

:::{grid-item-card} The render tree
:link: output-tree
:link-type: doc
The nested-list shapes `join()` understands.
:::
::::

### Worked examples

::::{grid} 1 1 3 3
:gutter: 2

:::{grid-item-card} Unicode text
:link: example-unicode
:link-type: doc
Rules only: Unicode subscripts and math signs on top of `ASCIIRenderer`.
:::

:::{grid-item-card} reStructuredText
:link: example-restructuredtext
:link-type: doc
Tokens, handlers and `join_item` on top of `LatexRenderer`.
:::

:::{grid-item-card} Structured data
:link: example-json
:link-type: doc
Output that is not text: new handlers and a new `complete()`.
:::
::::

Then: [testing your renderer](testing.md) and [publishing it](publishing.md).

```{toctree}
:hidden:

architecture
nodes
registration
render-context
overridable-methods
output-tree
example-unicode
example-restructuredtext
example-json
testing
publishing
```
