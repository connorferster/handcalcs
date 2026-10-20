# Classifiers

## Forms

| Classifier | Registers | Signature |
|---|---|---|
| `{type}` | the handler | `(renderer, node, base_context) -> rendered` |
| `{type}:pre` | rule before the handler, any mode | `(renderer, node, base_context) -> node` |
| `{type}:sym` | rule before the handler, symbolic mode | `(renderer, node, base_context) -> node` |
| `{type}:num` | rule before the handler, numeric mode | `(renderer, node, base_context) -> node` |
| `{type}:post` | rule after the handler | `(renderer, rendered, node, base_context) -> rendered` |
| `header:{type}` | header line of a block | `(renderer, node, base_context) -> str` |
| `root:pre`, `root:post` | item at the start / end of the render tree | `(renderer, root, base_context) -> item` |

See [Handlers and rules](../building-renderers/registration.md) for order of execution and
inheritance. `{type}` is any [node type](node-types.md).

## What each built-in renderer registers

These tables are generated from the renderers' registration tables when the docs are
built. For each renderer after `BaseRenderer`, only what it adds or replaces is listed;
everything else is inherited.

### `BaseRenderer`

```{hc-registry} base
```

### `ASCIIRenderer`

```{hc-registry} ascii
:own:
```

### `LatexRenderer`

```{hc-registry} latex
:own:
```

### `MarkdownRenderer` (inherits from `LatexRenderer`)

```{hc-registry} markdown
:own:
```

### `HTMLRenderer`

```{hc-registry} html
:own:
```

### `ExcelRenderer`

```{hc-registry} excel
:own:
```
