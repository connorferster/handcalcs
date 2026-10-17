# Styling the HTML output

The HTML renderer's output is a `<div class="handcalcs">` with its own small stylesheet.
That stylesheet only handles layout (spacing, indentation, grid alignment), and every
rule in it is wrapped in `:where()`, which gives it **zero specificity**. Any CSS you
write for `.handcalcs` wins, so you can style the output from your page without touching
handcalcs.

## Option 1: style it from your page

Target the [classes](../renderers/html.md#output-structure) the renderer emits:

```css
.handcalcs {
  font-family: "Iowan Old Style", Georgia, serif;
  color: #1f2937;
}
.handcalcs h1 { color: #0f766e; font-size: 1.25rem; }
.handcalcs .hc-comment { color: #6b7280; font-style: italic; }
.handcalcs .hc-header { font-weight: 600; }
.handcalcs .hc-params { border-top: 1px solid #e5e7eb; }
```

This is the best option when you control the page (a web app, a report template).

### Spacing knobs

The layout reads four CSS custom properties, set on `.handcalcs`. Override them the same
way:

| Property | Default | Controls |
|---|---|---|
| `--hc-gap` | `0.35em` | Vertical space between lines |
| `--hc-indent` | `1.5em` | Indentation of an `if`/`for` body |
| `--hc-param-gap` | `2em` | Space between the columns of a parameter grid |
| `--hc-eq-gap` | `0.3em` | Space on each side of `=` in a grid |

```css
.handcalcs { --hc-gap: 0.6em; --hc-indent: 2em; }
```

## Option 2: ship the style with the renderer

When the output goes somewhere you don't control (an email, a notebook, a file you hand
to someone), put the styles in the renderer. `HTMLRenderer.STYLE` is the stylesheet,
emitted once per render; extend it in a subclass:

```python
from handcalcs.renderers import HTMLRenderer

class BrandHTMLRenderer(HTMLRenderer):
    name = "brand_html"
    STYLE = HTMLRenderer.STYLE + (
        ".handcalcs :where(h1,h2,h3){color:#0f766e;}"
        ".handcalcs :where(.hc-comment){color:#6b7280;}"
    )
```

Keep wrapping your selectors in `:where()` so a host page can still override them.

### A color theme with dark mode

Define the colors as custom properties, then redefine them in a
`prefers-color-scheme: dark` media query:

```python
STYLE = HTMLRenderer.STYLE + (
    ".handcalcs{--hc-accent:#0f766e;--hc-muted:#6b7280;}"
    "@media (prefers-color-scheme:dark){.handcalcs{--hc-accent:#5eead4;--hc-muted:#9ca3af;}}"
    ".handcalcs :where(h1,h2,h3,h4,h5,h6){color:var(--hc-accent);}"
    ".handcalcs :where(.hc-comment){color:var(--hc-muted);}"
)
```

## Option 3: add your own markup

CSS can only style elements that exist. To style a part of a line, such as the result of
each calculation, add an element with a rule. A `calc_line:post` rule receives each
calculation line after it is rendered, as a list of parts
(`["M", "=", "w · L²/8", "=", "5 · 6²/8", "=", "22.5", "(kN m)"]`), and can change them:

```{literalinclude} ../_examples/html_colors.py
:language: python
:pyobject: highlight_result
```

The full renderer, with the style for `.hc-result` and a dark-mode theme:

```{literalinclude} ../_examples/html_colors.py
:language: python
:lines: 1-21
```

```{hc-example}
:renderer-file: _examples/html_colors.py
:renderer-class: ThemedHTMLRenderer
## Beam check
# Simply supported beam with a uniform load.
w = 5  # kN/m
L = 6  # m
M = w * L**2 / 8  # kN m
if M > 20:
    status = "check deflection"
```

The rule finds the result by position: the part after the last `=` (the context's
`assign` symbol). Lines with a single `=` are parameters, which it leaves plain.
[Registration](../building-renderers/registration.md) explains rules in full.

## Escaping

The HTML renderer does not escape the text of comments, so a comment can contain markup
(`# See <a href="...">clause 13.3</a>`). Don't render untrusted text with it.

**Next:** [LaTeX and Markdown tokens](latex-markdown-tokens.md).
