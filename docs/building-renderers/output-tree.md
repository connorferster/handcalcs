# The render tree

`renderer.render()` returns a **render tree**: the pieces each handler returned, nested
the way the nodes are nested. `complete()` receives it. With the built-in handlers, the
tree uses three shapes, which is all `join_item` needs to understand.

| Shape | Means | Produced by |
|---|---|---|
| `"text"` | A whole line | headings, comment lines, parameter grids, multi-line calcs, `-b` breaks (`"\n"`) |
| `["part", "part", ...]` | One line, as parts to be joined with `context.space` | calculation lines (`["c", "=", "a + b", "=", "2 + 3", "=", "5"]`), imports, expressions |
| `[header, [items...]]` | A block: a header line, then a body of items one level deeper | `CalcsBlock` and `CommentsBlock` (header `""`), `if`/`for` blocks |

A falsy item (`""`, `None`, `[]`) renders nothing: it is what a comment command or an
ignored line leaves behind.

A block whose header is empty is a **flat group**: its body stays at the current depth.
That is how a run of calculation lines is kept together (so the LaTeX renderer can put it
in one `aligned` environment) without being indented.

```{hc-example}
:renderer: base
:hide-source:
## Check
a = 2
b = a * 3  # note
if b > 5:
    c = b - 5
```

from

```python
## Check
a = 2
b = a * 3  # note
if b > 5:
    c = b - 5
```

Reading it from the outside in: a heading string; a flat group (header `''`) holding the
two calculation lines; and the `if` (an `ElifBlock` renders as its true branch), which is
a header string and a body containing a flat group with one line.

## Your own shapes

Handlers can return anything, as long as your `complete()` (and `join_item`, if you use
`join`) knows what to do with it. The [structured data example](example-json.md) returns
dicts from its line handlers; the Excel renderer returns row objects; the Word renderer
returns OMML strings for calc lines and small objects for headings and params tables. If you keep the
base handlers for some node types and use `join`, keep their outputs in the three shapes
above.

**Next:** [Example: a Unicode renderer](example-unicode.md).
