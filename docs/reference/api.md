# API

Every entry links to its source with `[source]`.

## Interfaces

```{eval-rst}
.. autoclass:: handcalcs.HandCalcs
   :members: __call__, demo
   :special-members: __call__

.. autofunction:: handcalcs.handcalc

.. autofunction:: handcalcs.find_inputs
```

The Jupyter magics (`%%render`, `%hc_default_renderer`, `%hc_format_code`) are described
in [the Jupyter interface](../interfaces/jupyter.md).

## Configuration

```{eval-rst}
.. autofunction:: handcalcs.set_option
.. autofunction:: handcalcs.get_option
.. autofunction:: handcalcs.get_config
.. autofunction:: handcalcs.reset_option
.. autofunction:: handcalcs.reset_config
.. autofunction:: handcalcs.save_config
.. autofunction:: handcalcs.config.config_path
```

## Renderers

```{eval-rst}
.. autofunction:: handcalcs.renderers.get_renderer

.. autoclass:: handcalcs.renderers.BaseRenderer
   :members: name, create_context, render, render_root, render_node, render_header, complete, to_file, join, join_items, join_item, register, register_handler, format_param_grid, format_calc_grid

.. autoclass:: handcalcs.renderers.ASCIIRenderer
   :members: complete

.. autoclass:: handcalcs.renderers.LatexRenderer
   :members: create_context, complete, join_item, paragraph, join_math_group, math_group, join_math_row, format_param_grid, format_calc_grid

.. autoclass:: handcalcs.renderers.MarkdownRenderer
   :members: join_item, quote, paragraph, math_group

.. autoclass:: handcalcs.renderers.HTMLRenderer
   :members: complete, create_context, format_param_grid, format_calc_grid

.. autoclass:: handcalcs.renderers.ExcelRenderer
   :members: complete, write_sheet, render_root

.. autoclass:: handcalcs.renderers.WordRenderer
   :members: complete, write_item, join_math_row, format_param_grid, format_calc_grid
```

## Render context

```{eval-rst}
.. autoclass:: handcalcs.renderers.base.RenderContext
   :members: sparse

.. autoclass:: handcalcs.renderers.base.BaseRenderContext
   :members: current
```

## Feature suite

```{eval-rst}
.. autoclass:: handcalcs.testing.FeatureCase
.. autodata:: handcalcs.testing.FEATURE_CASES
   :no-value:
.. autofunction:: handcalcs.testing.check_case
.. autofunction:: handcalcs.testing.render_case
.. autofunction:: handcalcs.testing.output_text
.. autofunction:: handcalcs.testing.check_text
```

See [Testing your renderer](../building-renderers/testing.md#run-the-shared-feature-suite).

## Helpers

```{eval-rst}
.. autofunction:: handcalcs.renderers.latex.latex_identifier
.. autofunction:: handcalcs.renderers.identifiers.parse_identifier
.. autofunction:: handcalcs.renderers.identifiers.parse_spec
.. autofunction:: handcalcs.renderers.identifiers.identifier_options
.. autofunction:: handcalcs.renderers.identifiers.split_greek
.. autoclass:: handcalcs.renderers.identifiers.Symbol
.. autoclass:: handcalcs.renderers.identifiers.IdentifierOptions
.. autofunction:: handcalcs.renderers.latex.latex_prose
.. autofunction:: handcalcs.renderers.latex.format_latex_number
.. autofunction:: handcalcs.renderers.base.infix_binop
.. autofunction:: handcalcs.renderers.base.render_condition
.. autofunction:: handcalcs.renderers.base.render_block_body
```
