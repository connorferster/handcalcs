# ASCII renderer

`ASCIIRenderer` produces monospaced text: readable in a terminal, a log file, a
docstring, a commit message or a test snapshot.

```python
from handcalcs.renderers import ASCIIRenderer
```

```{hc-example}
:renderer: ascii
:setup: from math import sqrt
## Bolt group
# Shear is shared equally between the bolts.
n = 4  # bolts
V_f = 120  # kN
V_b = V_f / n
f = 1; g = 2; h = 4
if V_b <= 40:
    status = "OK"
```

The registered name is `ascii`: `%hc_default_renderer ascii` in Jupyter, or
`handcalcs.set_option("default_renderer", "ascii")`. In a 2.0 pre-release this renderer
was `PlainTextRenderer` (`plain_text`); the old names were removed without an alias.

## Headings

Headings are underlined in the setext style used by reStructuredText, and set off by
blank lines. `##` is level 1:

```{hc-example}
:renderer: ascii
## Beam design
### Loads
w = 5  # kN/m
L = 6  # m
#### Moment
M = w * L**2 / 8
##### Shear
V = w * L / 2
```

The underline for each heading level is set by the class attribute `HEADING_RULES`, a
dict of `level: (character, overline)`. Levels deeper than the last entry use the last
entry. To underline every level with `-` and no overline:

```python
from handcalcs.renderers import ASCIIRenderer

class DashRenderer(ASCIIRenderer):
    HEADING_RULES = {1: ("-", False)}
```

## Lined-up `=` signs

The left-hand sides of the calculation lines between two headings are right-aligned,
so the `=` signs form one column. Parameter grids (a `;` line, or `# hc: -g`) and long
calculations (`# hc: -m`) are shifted to line up with them:

```{hc-example}
:renderer: ascii
b = 0.3; d = 0.55; phi = 0.9
f_c = 30  # MPa
A_gross = b * d
M_r = phi * f_c * 1000 * b * d**2 / 6  # kN m
```

## Conventions

| Source | Text |
|---|---|
| `## Heading`, `### Heading`, ... | The heading underlined (see [Headings](#headings)) |
| Comment lines | One line of prose |
| Inline comment | In parentheses after the line |
| `import ...` | `[Python import]: import ...` |
| Parameter grid | Columns, aligned on `=` |
| `# hc: -m` | Following rows indented to line up under the first `=` |
| `if` / `for` body | Indented four spaces |
| `# hc: --pagebreak` | A line holding a form feed (`\f`) |

- Names: Greek letter names become Greek letters, including a Greek name before an
  uppercase letter or digit (`DeltaH` → `ΔH`). Underscores are kept (`I_y`, `N_pl_Rd`);
  `__` is shown as a space. A name in the `symbols` option is shown from its spec
  (`N_{pl,Rd}` → `N_pl,Rd`).
- Operators: `**` with a number exponent → superscript digits (`b²`); `sqrt` → `√`;
  `*` and `/` stay as they are.

The Greek letters, `√` and superscripts are Unicode, so the output is "ASCII" in layout
rather than in character set. For pure 7-bit text, remove the symbol rules in a
subclass; see
[Symbols and functions](../customizing/symbols-and-functions.md).

## Uses

- **Snapshot tests** of calculation code: compare the rendered text with a stored file.
- **Logging** the calculation behind a result.
- **Docstrings and comments**: paste the output under a function to record its
  derivation.
- **A starting point** for your own text-based renderer.
  See [Example: a Unicode renderer](../building-renderers/example-unicode.md).

## Source

{source}`src/handcalcs/renderers/ascii.py`
