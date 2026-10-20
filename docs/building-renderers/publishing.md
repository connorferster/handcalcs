# Publishing your renderer

A renderer is just a class, so sharing it means putting it in an importable module. A few
details make it work smoothly with the rest of handcalcs.

## Give it a `name`

```python
class RstRenderer(LatexRenderer):
    name = "rst"
```

Defining a class with its own `name` registers it
({src}`__init_subclass__ <handcalcs.renderers.base.BaseRenderer.__init_subclass__>`), so it
can be selected by name:

- in Jupyter: `%hc_default_renderer rst`;
- in the configuration: `handcalcs.set_option("default_renderer", "rst")`, so a bare
  `HandCalcs()` uses it; or `"jupyter_renderer"` for `%%render`.

A class without its own `name` (for example a quick subclass in a notebook) is not
registered, and does not replace its parent's entry.

```{important}
Registration happens when the class is **defined**, so the module must be imported
before the name is used. If `default_renderer` names a renderer that has not been
imported, `HandCalcs()` warns and falls back to `BaseRenderer`. Import your renderer
module at the top of the notebook or script.
```

Choose a name that won't collide with the built-in names (`base`, `ascii`,
`latex`, `markdown`, `html`, `excel`) or other packages: a later class with the same name
replaces the earlier one in the registry.

## Jupyter display

`%%render` displays a renderer's output with the IPython display class of the nearest
built-in ancestor ({src}`display_class_for <handcalcs.interfaces.jupyter.display_class_for>`):

| Inherits from | Displayed as |
|---|---|
| `MarkdownRenderer` | `Markdown` |
| `LatexRenderer` | `Latex` |
| `HTMLRenderer` | `HTML` |
| `ASCIIRenderer`, `BaseRenderer` | `Pretty` |

A renderer built directly on `BaseRenderer` that produces, say, HTML should still inherit
from `HTMLRenderer` if it is meant for notebooks; or its users can display its output
themselves with `IPython.display`.

## A demo

`HandCalcs(renderer).demo()` renders the general demo. If your format can't represent
some of it (loops, collections), set a `demo_source` class attribute with your own
example source, as the Excel renderer does.

## Packaging

Put the renderer in a module of your package and depend on `handcalcs>=2`:

```text
my_handcalcs_rst/
    __init__.py      # from .renderer import RstRenderer
    renderer.py
pyproject.toml       # dependencies = ["handcalcs>=2"]
```

Users then write:

```python
from my_handcalcs_rst import RstRenderer
rst = HandCalcs(RstRenderer())(source)
```

## Contributing it to handcalcs

If your renderer would be useful to others, open an issue on
[GitHub](https://github.com/connorferster/handcalcs/issues) to discuss adding it. The
[developer's guide](../developers/index.md) covers the repository layout and tests.
