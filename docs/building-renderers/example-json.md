# Example: structured data

**Technique: new handlers and a new `complete()`.** Not every renderer produces text. This
one produces a list of dictionaries, one per heading, paragraph, calculation or block, so
a web front-end (or a template engine, or a database) can lay the calculation out itself.
It keeps the Unicode symbol rules of `PlainTextRenderer` for the strings inside each
entry.

## The code

```{literalinclude} ../_examples/data_renderer.py
:language: python
```

## The result

```{hc-example}
:renderer-file: _examples/data_renderer.py
:renderer-class: DataRenderer
:output-language: python
:setup: from math import sqrt
## Web check
# The web must be at least class 2.
h_w = 310; t_w = 6
x_1 = h_w / t_w  # slenderness
if x_1 <= 60:
    web_class = 1
```

`json.dumps(result)` turns it into JSON.

## How it works

**`calc_line`** replaces the built-in handler, which returns a list of parts, with one
that returns a dict. It follows the same steps as the built-in
{src}`render_calcline <handcalcs.renderers.base.render_calcline>`:

1. Render the comment **first**. An inline `# hc:` command sets the line context, and
   that has to happen before the rest of the line is rendered.
2. Honour `ignore` (`# hc: -i`) and `param_line` (set by the inherited `calc_line:pre`
   rule for parameters).
3. Render each step with `current_mode` set: targets and the symbolic step in `"sym"`,
   the numeric step and the result in `"num"`.
4. Reset the line context to empty, so this line's overrides don't leak to the next.

**`params_block`** renders each line as a parameter by setting `param_line` on the line
context, as the built-in handler does, and returns the cells directly instead of a grid.

**`heading`** and **`inline_comment`** return the raw content. (The inherited `pre` rule
on comments still runs first, so `{{ }}` values are filled in.)

**`complete`** walks the render tree. Every built-in block handler still returns
`[header, body]`, and the comment-line handler still returns a string, so `complete`
handles the three [tree shapes](output-tree.md) as well as the dicts.

## Variations

- Return the **numbers** as well as the strings: read `node.assigns[0].value` in the
  `calc_line` handler.
- Produce **XML** by building `xml.etree.ElementTree` elements in the handlers and
  serialising them in `complete`.
- Write **straight to a file or a service** in `complete`, as the Excel renderer does
  with its `filepath` option.

**Next:** [Testing your renderer](testing.md).
