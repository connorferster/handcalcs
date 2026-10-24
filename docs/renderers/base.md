# Base renderer

`BaseRenderer` is the renderer every other renderer inherits from. Used directly, it
returns the **render tree**: a nested Python list, before any joining into text.

```python
from handcalcs.renderers import BaseRenderer
```

```{hc-example}
:renderer: base
## Check
a = 2
b = a * 3  # note
if b > 5:
    c = b - 5
```

Pass it explicitly, `HandCalcs(BaseRenderer())`, to get the render tree; a bare
`HandCalcs()` uses the ASCII renderer unless you set `default_renderer`.

## When you would use it

- **To see the structure** a renderer works with before you write one. Each string is a
  finished line; each list of strings is a line's components; a two-item
  `[header, body]` list is a block. [The render tree](../building-renderers/output-tree.md)
  explains the shapes.
- **To post-process** the rendered pieces yourself instead of using a renderer's
  `complete()`.

`BaseRenderer` also has a `join()` method that turns the tree into plain text, the first
step most text renderers take in their own `complete()`:

```python
from handcalcs import HandCalcs
from handcalcs.renderers import BaseRenderer

renderer = BaseRenderer()
hc = HandCalcs(renderer)
tree = hc("a = 2\nb = a * 3\n")
print(renderer.join(tree))
```

## Source

{source}`src/handcalcs/renderers/base.py`
