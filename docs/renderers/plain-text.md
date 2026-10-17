# Plain-text renderer

`PlainTextRenderer` produces Unicode text: readable in a terminal, a log file, a commit
message or a test snapshot.

```python
from handcalcs.renderers import PlainTextRenderer
```

```{hc-example}
:renderer: plain_text
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

## Conventions

| Source | Text |
|---|---|
| `## Heading` | `# Heading` (one `#` fewer) |
| Comment lines | One line of prose |
| Inline comment | In parentheses after the line |
| `import ...` | `[Python import]: import ...` |
| Parameter grid | Columns, aligned on `=` |
| `# hc: -m` | Following rows indented to line up under the first `=` |
| `if` / `for` body | Indented four spaces |

- Names: Greek letter names become Greek letters. Underscores are kept (`I_y`).
- Operators: `**` with a number exponent → superscript digits (`b²`); `sqrt` → `√`;
  `*` and `/` stay as they are.

## Uses

- **Snapshot tests** of calculation code: compare the rendered text with a stored file.
- **Logging** the calculation behind a result.
- **A starting point** for your own text-based renderer. It is the simplest built-in
  renderer: a `complete()` method and four rules.
  See [Example: a Unicode renderer](../building-renderers/example-unicode.md).

## Source

{source}`src/handcalcs/renderers/plaintext.py`
