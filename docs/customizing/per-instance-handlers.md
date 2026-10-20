# Customizing one instance

`@Renderer.register(...)` changes a renderer **class** and every instance created from it.
To change one renderer object only, call `register_handler` on the instance. It takes the
same [classifiers](../building-renderers/registration.md) as `register`.

```{literalinclude} ../_examples/hide_imports.py
:language: python
```

```{hc-example}
:renderer-file: _examples/hide_imports.py
:renderer-class: make_renderer
import math
a = 2
b = math.sqrt(a)
```

Other `MarkdownRenderer` objects still show imports.

## When to use it

- **Quick experiments** in a notebook, without defining a class.
- **Per-request settings** in an application, where each request builds its own renderer.
- **Tests**, where a handler must not leak into other tests.

For anything you reuse, a subclass is clearer: it has a name, can be selected in
Jupyter, and can be imported from your own package.

## How it works

Each renderer instance copies its class's handler and rule tables when it is created, and
`register_handler` adds to the copies. Registering a bare node type (`"import"`) replaces
that node's handler; registering a rule (`"import:post"`) appends to that node's rule list.
Instances created *before* a class-level `register` call keep the old tables.

**Next:** the [cookbook](../cookbook/index.md), for complete recipes.
