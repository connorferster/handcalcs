# ExcelRenderer — Implementation Plan

Branch: `features/excel_renderer`. Requirements source: `excel_renderer.md`.

## Status

- [x] Phase 0 — plan written (2026-10-17)
- [x] Plan and all §10 recommendations approved by the user (2026-10-17)
- [x] Phase 1 — scaffold, config validation, optional dependency, registry
- [x] Phase 2 — names and number formats
- [x] Phase 3 — formula (`xl`) mode
- [x] Phase 4 — symbolic mode and rich text
- [x] Phase 5 — rows and compatibility
- [x] Phase 6 — writer
- [x] Phase 7 — conditionals
- [x] Phase 8 — units, docs, push

Resume rule: read this Status section and §10 (decisions) first; each phase ends
with a commit. Progress notes go in §11 (Progress log).
Before editing on resume, check that no other session is still live: run
`git status`, `git log -3`, and check file mtimes in `src/handcalcs/renderers/excel/` and
`tests/` for changes made in the last few minutes. If any, stop and ask the user.

---

## 1. Goal

Convert a handcalcs source cell into a **live, formula-based Excel worksheet**:
every calculation becomes a real Excel formula that references other rows through
**worksheet-scoped defined names**, so editing an input value in Excel recalculates
the sheet. The sheet is also formatted to read like a handcalc: a symbolic column
with subscripts, superscripts and Greek letters, headings, and comment paragraphs.

## 2. How it fits the existing pipeline

```
source ─► AST_Parser ─► HcSequence ─► ExcelRenderer.render()  ─► list[Row]  ─► complete() ─► .xlsx
                                       (node handlers, rules)     (row model)    (writer)
```

The handcalcs pipeline is unchanged: `HandCalcs(renderer=ExcelRenderer(...))(source)`.
Other renderers produce nested lists of strings and `complete()` joins them. The
ExcelRenderer instead produces a flat list of typed **row records**, and
`complete()` hands them to a **writer** that lays out the sheet. The split keeps all
handcalcs logic (formulas, symbols, compatibility checks) testable without opening a
workbook, and leaves room for a second writer backend later (see D1).

### 2.1 Row model (`excel/rows.py`)

```python
@dataclass
class CalcRow:        # | symbol | = | symbolic | = | formula | unit | comment |
    name: str              # Excel defined name (validated, versioned)
    symbol: RichText       # assignment target, display form
    symbolic: RichText     # RHS, display form
    formula: str           # "=..." referencing defined names
    cached: Any            # Python result, written as the formula's cached value
    number_format: str
    unit: str | None
    comment: str | None
    hidden: bool = False   # `# hc: -i` lines

@dataclass
class ParamRow:       # | symbol | = | comment | = | value | unit |
    name, symbol, value, number_format, unit, comment, hidden

@dataclass
class HeadingRow:  text: str; level: int
@dataclass
class CommentRow:  text: str          # one merged row per CommentsBlock
@dataclass
class BlankRow:    pass               # `# hc: -b`
```

`RichText` is a list of `(text, style)` runs where style is `None`, `"sub"` or
`"sup"`. It is what the writer turns into an Excel rich string.

### 2.2 Three render modes

The base handlers know two modes, `current_mode = 'sym'` and `'num'`. The
ExcelRenderer adds a third, **`'xl'`** (Excel formula text). For each `CalcLine` the
handler renders:

| pass  | mode  | output                                      | goes to          |
|-------|-------|---------------------------------------------|------------------|
| 1     | `xl`  | `(-b+SQRT(b^2-4*a*c))/(2*a)`                | `CalcRow.formula` |
| 2     | `sym` | markup `x<sub>1</sub> = (-b+√(b<sup>2</sup>…` | `symbol`, `symbolic` |
| value | —     | the Python value from `global_ns`           | `cached` / `value` |

The `num` (numeric substitution) column is not shown: Excel shows the live result in
the formula cell.

**Symbolic rules must not mutate nodes.** The HTML `name:sym` rules rewrite
`node.identifier` in place, which would corrupt a later `xl` pass. The Excel rules
return a copy (`dataclasses.replace`), and the `xl` pass runs first anyway.

### 2.3 Symbolic text as light markup → rich text

Symbolic handlers emit the same lightweight markup as the HTMLRenderer (`<sub>`,
`<sup>`, with `<`, `>`, `&` escaped). This lets `infix_binop` and the other base
helpers, which build strings, be reused. A small parser (`excel/rich_text.py`)
turns the markup into `RichText` runs. Excel limits:

- one level of sub/superscript only. Nested subscripts (`a_b_c`) flatten to one
  subscript run joined by `,` → a<sub>b,c</sub>.
- A power with a non-constant exponent stays inline as `^(...)`, matching HTML.
- Hats/bars/primes use the HTML unicode combining characters (U+0302, U+0305, U+2032);
  `sqrt` → `√(…)`; `*` → `·`; `<=`/`>=`/`!=` → `≤`/`≥`/`≠`; Greek names → Greek letters.

### 2.4 Formula translation (`'xl'` mode)

| Python                     | Excel                         | note |
|----------------------------|-------------------------------|------|
| `a + b`, `a - b`, `a * b`, `a / b` | same                  | |
| `a ** b`                   | `a^b`                         | |
| `-a ** b`                  | `-(a^b)`                      | **Excel negation binds tighter than `^`**: `-2^2 = 4` |
| `a // b`                   | `INT(a/b)`                    | INT floors, like Python |
| `a % b`                    | `MOD(a,b)`                    | same sign rule as Python |
| `==`, `!=`, `<`, …         | `=`, `<>`, `<`, …             | |
| `a < b < c` (chained)      | `AND(a<b,b<c)`                | |
| `and` / `or` / `not`       | `AND(…)` / `OR(…)` / `NOT(…)` | |
| `True`/`False`             | `TRUE`/`FALSE`                | |
| `"text"`                   | `"text"` (quotes doubled)     | |
| `math.pi` / `math.e`       | `PI()` / `EXP(1)`             | |
| `sqrt, exp, sin, cos, tan, asin, acos, atan, sinh, cosh, tanh, asinh, acosh, atanh, radians, degrees, fabs, abs, floor, ceil, log10` | `SQRT, EXP, SIN, …, ABS, INT, CEILING.MATH, LOG10` | |
| `log(x)` / `log(x, b)`     | `LN(x)` / `LOG(x,b)`          | |
| `atan2(y, x)`              | `ATAN2(x,y)`                  | **argument order swaps** |
| `pow(a, b)`, `hypot(a, b)` | `POWER(a,b)`, `SQRT(SUMSQ(a,b))` | |
| `min(…)`, `max(…)`         | `MIN(…)`, `MAX(…)`            | positional scalars only |
| `round(x, n)`              | `ROUND(x,n)`                  | Python rounds half to even, Excel half away from zero; documented |

The function is identified by the **callable object** captured in the namespace
(`value is math.sqrt`), with the bare/`math.` name as a fallback. A user's own
`sqrt` is therefore not mistaken for `math.sqrt`. Anything not in the table raises
`ExcelRendererIncompatibleError`. The table is a class attribute (as in
`LatexRenderer`) so it can be extended.

Parenthesization reuses `OP_PRECEDENCE` with one Excel-specific change: unary minus
ranks *above* `^`, so a unary operand that is a power is always wrapped.

### 2.5 Defined names (`excel/names.py`)

Each assignment target becomes a defined name scoped to the worksheet
(`'Sheet name'!x_1` → `$E$7`). A `SymbolTable` carried on the render context maps
each Python identifier to its *current* Excel name as rows are emitted.

- **Validity.** Excel rejects names that look like cell references (`x1`, `L1`,
  `AB12`, `R1C1`), the single letters `c`, `r`, `C`, `R`, and names with
  characters outside letters/digits/`_`/`.`. Such names get a trailing `_`
  (`x1` → `x1_`). The renderer checks the result for collisions.
- **Reassignment** (`M_u` appears twice in the demo): see D4. Recommended: version
  the name (`M_u`, `M_u_2`); later formulas reference the latest version.
- **Unknown names** (used in a formula but never assigned on the sheet, e.g. a
  value from `supplied_globals`): raise `ExcelRendererIncompatibleError` naming the
  variable (see D5).

### 2.6 Compatibility checking (`excel/compat.py`)

`ExcelRendererIncompatibleError(Exception)` carries the offending node type, the
source line where available, and a short reason. It is raised **during render**,
before any file is written. Incompatible:

- `ForBlock`, `FunctionBlock`, `Import` (but see D6), `ExprLine` (e.g. `print(...)`,
  bare expressions; except a bare string, which becomes a comment row, see D7);
- statements the parser drops: `while`, `with`, `try`, augmented assignment
  (`x += 1`), etc. The parser turns these into `NoValue`/`HcNotImplemented` at
  statement level. `render_root` checks every statement and raises on these
  instead of skipping them silently;
- collections (`List`, `Tuple`, `Set`, `Dictionary`), comprehensions, `in`/`not in`,
  `is`/`is not`, keyword arguments, complex numbers, `None`, `Attribute`s other
  than `math.pi`/`math.e`;
- tuple unpacking (`a, b = 1, 2`) and chained targets (`a = b = 1`);
- unmapped functions (§2.4);
- ElifBlocks that fail the rules in §3.

### 2.7 Comment commands

| command          | Excel behaviour |
|------------------|-----------------|
| `-f <code>`      | sets the row's Excel number format (§4.3) |
| `-b`             | `BlankRow` |
| `-p`             | forces the param-row layout; the value cell still holds a formula if the RHS is a calculation |
| `-i`             | the row is **written but hidden** (Excel hidden row), so formulas that reference it still work |
| `-m`, `mode=…`, `-c` | no effect (layout is fixed) |
| `-h` / `;` params blocks | each line becomes its own `ParamRow` (no grid on a sheet) |

## 3. ElifBlocks → `IF` formulas (`excel/conditionals.py`)

Its own submodule, as requested. Input: an `ElifBlock` (flattened `IfBlock`s plus
an optional trailing `ElseBlock`). Output: one `CalcRow` per assigned variable.

**Compatibility rules.** Every branch body may contain only `CalcLine`s (single
`Name` target), nested `ElifBlock`s that are compatible themselves, comment lines,
and comment commands. A variable assigned twice within one branch is incompatible
in v1. Any other node raises.

**Algorithm.**
1. Walk each branch and collect, in first-appearance order, the variables it
   assigns. Nested ElifBlocks contribute their variables recursively.
2. For each variable `v`, build a branch → expression map. A nested ElifBlock
   gives the branch a nested `IF(...)`.
3. Emit `=IF(test_1, expr_1, IF(test_2, expr_2, …, else_expr))`. Nested `IF` is
   used instead of `IFS` because it works in every Excel version and in LibreOffice.
4. **Branch that does not assign `v`:** the fallback is the previous definition of
   `v` if there is one, else `NA()` (D8).

Dependencies between variables assigned in the same branch (`if c: a = 1; b = a*2`)
come out right with no special handling: `b`'s row references the name `a`, whose
own `IF` picks the same branch.

The symbolic column of a conditional row is a piecewise display (D9). Recommended:
one line per branch, wrapped in the cell:

```
1,  if h_w/t_w ≤ 1000/√F_y
2,  if h_w/t_w ≤ 1700/√F_y
4,  otherwise
```

Nested trees are flattened into AND-ed conditions for display only. The formula
keeps the nesting.

## 4. Worksheet layout and formatting

### 4.1 Columns

| col | A | B | C | D | E | F | G |
|-----|---|---|---|---|---|---|---|
| calc row  | symbol | `=` | symbolic | `=` | **formula** | unit | comment |
| param row | symbol | `=` | comment  | `=` | **value**   | unit | — |

Values and formulas share column E, so the sheet reads as one aligned column of
results.

Alignment: everything centred except symbol (left), value/formula (right), unit
(left) and comment (left). Comments are grey (`#808080`) and italic. Column widths
are estimated from content length (min/max clamped); the symbolic column wraps.

### 4.2 Headings and comment paragraphs

- A `Heading` is one row merged across columns A–E, bold.
- A `CommentsBlock` (consecutive comment lines) is one row merged across A–E, with
  its lines joined into a paragraph and wrap on. Excel does not auto-fit the height
  of merged rows, so the writer estimates the height from text length ÷ merged width.
- Font sizes follow a major-second scale (×1.125) from a 10 pt body:
  `size = 10 × 1.125^(5 − level)` for heading levels 1–4, giving 16.02, 14.24, 12.66,
  11.25 pt. Excel only accepts sizes in 0.5 pt steps, so these round to
  **16, 14, 12.5, 11.5 pt**. Level ≥ 5 uses 11.5 pt bold.
- The body font is 10 pt for the whole sheet.

### 4.3 Number formats

The handcalcs `format_code` (default `.5g`, or a `-f` override) maps to an Excel
number format:

| Python | Excel |
|--------|-------|
| `.3f`  | `0.000` |
| `,.2f` | `#,##0.00` |
| `.2e`  | `0.00E+00` |
| `.1%`  | `0.0%` |
| `d`    | `0` |
| `.Ng` | no exact Excel equivalent → `General` (configurable via `general_format`) |

Unparseable codes fall back to `General` with a warning.

### 4.4 Configuration (nested dicts at instantiation)

```python
ExcelRenderer(
    sheet_name="Calculations",
    value_format={"bold": False, "text_color": "#000000", "cell_color": "#FFF2CC"},
    formula_format={"bold": True,  "text_color": "#000000", "cell_color": None},
)
```

- `value_format`: the value cell of param rows / simple assignments (the inputs).
- `formula_format`: the formula cell of calc rows.
- Each key is optional. A user dict is merged over the defaults. Unknown keys raise
  `ValueError`.
- Colours accept `"#RRGGBB"`, `"RRGGBB"`, or an `(r, g, b)` tuple of 0–255 ints,
  normalized by one `_normalize_color()` helper. Invalid values raise `ValueError`
  at instantiation, not at write time.
- Suggested defaults (open to change): inputs on a light-yellow fill (the common
  engineering convention for "edit me"), formulas bold with no fill.

## 5. Output API (D2)

Recommended:

- `complete()` returns an `ExcelWorkbook` result object holding the bytes, with
  `.save(path)` and `.to_bytes()`. If `ExcelRenderer(filepath=...)` is given,
  `complete()` also writes the file.
- For several sheets in one workbook (the reason names are worksheet-scoped),
  `ExcelRenderer.write_sheet(workbook, rows, sheet_name)` lets a caller render
  several cells into one `xlsxwriter.Workbook`.

## 6. Library (D1)

**Recommended: XlsxWriter** as an optional dependency (`handcalcs[excel]`):

- `write_formula(..., value=cached)` stores the Python result as the cached value,
  so the file shows numbers even in viewers that do not recalculate (Quick Look,
  Outlook preview, pandas/openpyxl `data_only`);
- worksheet-scoped names via `define_name("'Sheet'!x", "='Sheet'!$E$5")`;
- rich strings (`write_rich_string`) for sub/superscripts; merged ranges; mature
  formatting; actively maintained;
- limitation: it cannot edit an existing workbook.

Alternative, **openpyxl**: it can add a sheet to an existing `.xlsx`, but it cannot
write cached values (cells show blank until Excel recalculates) and its rich-text
support is newer. The row-model/writer split lets an openpyxl backend be added later
without touching the renderer.

Tests read files back with **openpyxl** (dev dependency) to check names, formulas,
formats and merges. One optional test evaluates the workbook with the `formulas`
package (skipped if not installed) and compares results with the Python values.
LibreOffice is not available in this environment.

## 7. Units (D3)

`excel_renderer.md` lists an optional unit column but no unit source. Units are
the hardest part, so they get their own phase (8), after the unitless renderer works
end to end. Recommended approach for pint / forallpeople values:

- **Unit column** = the display unit of the row's Python value (`str(q.units)` /
  forallpeople's unit string).
- **Number × unit params** (`L = 300*mm`) become a `ParamRow` with value `300` and
  unit `mm`, not a formula.
- **Formulas stay correct across mixed units:** every name reference is scaled to
  SI base, and the result is scaled back to its display unit:
  `M = F*L` → `=(F*1000)*(L*1)/1000`. Factors are computed in Python from the units
  library and are exact for all multiplicative units (not offset temperatures). A
  factor of 1 is omitted, so pure-SI sheets stay clean.
- A bare unit name used in an expression (`x = a * mm`) becomes its base factor
  constant.

Before phase 8, a value with units raises `ExcelRendererIncompatibleError("units
not yet supported")`, so that no silently wrong sheet is produced.

## 8. Module layout

```
src/handcalcs/renderers/excel/
    __init__.py         # ExcelRenderer, ExcelRendererIncompatibleError
    renderer.py         # ExcelRenderer(BaseRenderer): handlers, rules, config
    rows.py             # row dataclasses, RichText
    rich_text.py        # markup -> RichText runs
    formulas.py         # 'xl' mode handlers, function table, precedence
    names.py            # SymbolTable, Excel name validation/versioning
    conditionals.py     # ElifBlock -> per-variable IF formulas
    compat.py           # error class + statement-level checks
    number_formats.py   # Python format spec -> Excel number format
    writer.py           # XlsxWriter backend: layout, formats, widths, heights
tests/test_excel_*.py   # one file per module + an end-to-end demo test
scripts/excel_demo.py   # renders an Excel-compatible demo to excel_demo_build/ (gitignored)
```

`renderers/__init__.py` imports `ExcelRenderer` lazily, so `xlsxwriter` stays
optional. The renderer registers under `name = 'excel'`.

The base demo (`demo.py`) contains for loops, collections, imports, and `in`/`is`,
so it is intentionally **incompatible**. A separate `excel_demo` source covers the
Excel-compatible subset (quadratic, LTB, section-class elif tree, logical ops,
`-f`/`-b`/`-i` commands). The test suite also checks that the base demo raises a
clear error.

## 9. Phases (each ends with tests passing + a commit)

1. **Scaffold.** Package skeleton, `ExcelRendererIncompatibleError`, config
   validation (`value_format`/`formula_format`, colour normalization), optional
   dependency, registry entry. Tests: config validation.
2. **Names and number formats.** `names.py` (validity, mangling, versioning,
   unknown-name errors) and `number_formats.py`. Pure functions, heavily tested.
3. **Formula mode (`xl`).** Operators, precedence including the unary-minus/`^`
   trap, comparisons, booleans, constants, the function table with identity
   lookup, `math.pi`/`e`. Tests: a table of Python → formula cases.
4. **Symbolic mode and rich text.** Non-mutating `name:sym` rules (Greek, accents,
   subscripts), operator symbols, sqrt, powers, markup → `RichText` parser
   (flattening nested subscripts).
5. **Rows and compatibility.** `calc_line`, `params_block`, `heading`,
   `comments_block`, commands → row records; `render_root` statement checks;
   every incompatibility raises with a clear message.
6. **Writer.** XlsxWriter backend: columns, alignment, comment styling, merges,
   heading scale, configurable value/formula formats, cached values, worksheet-
   scoped names, hidden rows, widths and heights; `ExcelWorkbook` result /
   `filepath`. Tests read back with openpyxl. Optional `formulas` evaluation test.
   Demo script.
7. **Conditionals.** `conditionals.py`: compatibility rules, per-variable split,
   nested IF, fallbacks, piecewise symbolic display. Tests include the demo's
   section-class tree.
8. **Units** (§7), then docs (`docs/` page, README mention), final golden
   tests, push.

## 10. Decisions (approved 2026-10-17: all recommendations accepted)

| # | Question | Recommendation |
|---|----------|----------------|
| D1 | Library | XlsxWriter (cached values, rich strings); openpyxl for tests |
| D2 | Output API | `ExcelWorkbook` result with `.save()` + optional `filepath`; `write_sheet()` for multi-sheet |
| D3 | Where does the unit column come from? | pint/forallpeople values, with base-unit scaling in formulas (§7), in phase 8 |
| D4 | Reassigned variables (`M_u` twice) | version the names (`M_u`, `M_u_2`), not raise |
| D5 | Names used but never assigned on the sheet | raise (alternative: inline their value as a constant) |
| D6 | Imports: spec says incompatible, but nearly every cell has `from math import sqrt` | silently skip imports of `math` (needed for the function table); raise for any other import |
| D7 | Bare string statements (docstrings) | render as a comment row rather than raise |
| D8 | Branch that does not assign a variable | fall back to the previous definition, else `NA()` |
| D9 | Symbolic column for conditional rows | piecewise, one line per branch (§3) |
| D10 | Param-row column C holds the comment (per spec): `L = Unbraced length = 6000 mm` | keep as specified; confirm it is intended |
| D11 | Heading/comment merges span A–E (5 cols) while calc rows use 7 | keep A–E as specified; confirm |
| D12 | Default fills | inputs light yellow `#FFF2CC`, formulas bold, no fill |

## 11. Progress log

- 2026-10-17: plan drafted from `excel_renderer.md` after reviewing the parser node
  types, `BaseRenderer` pipeline, HTML symbolic rules and the demo.
- 2026-10-17: phase 1 done — scaffold, `options.py` config validation, `compat.py`
  error class, `handcalcs[excel]` extra, registry entry `'excel'`.
- 2026-10-17: phase 2 done — `names.py` (`to_excel_name` mangles cell-reference-like
  names and `TRUE`/`FALSE` with a trailing `_`; `SymbolTable` versions reassignments
  `M_u`, `M_u_2`, case-insensitive collision check, `lookup` raises for unassigned
  names) and `number_formats.py` (`f`/`e`/`%`/`d`, `,` grouping, `+` sign;
  `g`/none → `general_format`; others warn). Tests: `tests/test_excel_names.py`.
- 2026-10-17: phase 3 done — `formulas.py`. Deviation from §2.2: the `xl` pass is a
  standalone `FormulaBuilder` tree walker, not renderer handlers (Excel needs its own
  precedence table and spelling for nearly every node, and must not mutate nodes;
  `render_node` only gates rules on `sym`/`num` anyway). Parser facts learned:
  `FunctionCall.function_name.value` is the *string* name, not the callable, so
  functions are resolved through `global_ns` (namespace module → attribute; bare
  name → `global_ns`, then `builtins`, then `math` by name); `Attribute.namespace`
  is a str; conditional expressions parse to `NoValue` (raise). Also handled: Excel
  `^` is left-associative (`a**b**c` → `a^(b^c)`), negated right operands wrapped,
  `math.tau` → `2*PI()`, `from math import pi` by identity, user-assigned `pi`
  shadows it. `has_units()` helper raises for unit values until phase 8.
  Tests: `tests/test_excel_formulas.py` (note `c`/`r` are reserved: use other
  letters in fixtures).
- 2026-10-17: phase 4 done — `rich_text.py` (`parse_markup` → merged `(text, style)`
  runs, nested sub flattened with `,`; leaves escaped with `escape`, entities
  unescaped) and `symbolic.py` (non-mutating rules registered on `ExcelRenderer` by
  `register_symbolic_rules`: names with Greek/accents/star and a single flattened
  subscript, `·`, `⌊a / b⌋`, `mod`, constant powers as superscripts, other powers
  `a^(…)`, `√(…)`, module prefix dropped, `math.pi` → π, spaced `≤ ≥ ≠ =`;
  `symbolic_markup()` renders nodes in `sym` mode). Note: the base
  `function_call:pre` rule still mutates `pre`/`post` once (idempotent, harmless).
  Tests: `tests/test_excel_symbolic.py`.
- 2026-10-17: phase 5 done — `rows.py` (`ParamRow` gained `formula` for `-p` lines
  with a calculation), `evaluate.py` (`ValueEvaluator`: captured `Name.value` is the
  value at the *end* of the cell, so each row's cached result is re-evaluated in
  order; falls back to the captured value), and the handlers in `renderer.py`:
  `render_root` → flat `list[Row]`, state (`SymbolTable`, `FormulaBuilder`,
  `ValueEvaluator`) on `global_context.excel_state`. Formula is built before the
  target is assigned so `x = x*2` references the previous version. A top-level
  `def`, `x += 1`, `while` parse to `NoValue` → raise. `complete()` returns the rows
  until the writer lands. Tests: `tests/test_excel_rows.py`.
- 2026-10-17: two sessions ran concurrently (a "closed" session kept working);
  phase 5 was finished by the other one. Resume rule now checks for live writers.
- 2026-10-17: phase 6 done — `writer.py` (`SheetWriter`: §4.1 columns, scoped names
  → `$E$n`, formulas with cached values, rich strings with sub/superscript runs,
  A–E merged headings at 16/14/12.5/11.5 pt and wrapped paragraphs with estimated
  heights, grey italic comments, hidden `-i` rows, clamped widths; 10 pt body).
  `complete()` returns `ExcelWorkbook` (`.to_bytes()`, `.save()`, `.rows`) and saves
  to `filepath`; `ExcelRenderer.write_sheet(workbook, rows, sheet_name)` for
  multi-sheet. Fix: symbolic constants no longer use `format_code` (`-f .3f` made
  `b**2` read b^2.000). Demo source lives in `excel/demo.py` (W410x60 LTB check);
  `scripts/excel_demo.py` writes `excel_demo_build/excel_demo.xlsx` and, with
  `uv run --with formulas`, recalculates every formula cell and compares it with
  Python (all match). The `formulas` package returns `#REF!` for sheet-scoped names,
  so the check evaluates a copy with names promoted to workbook scope.
  Tests: `tests/test_excel_writer.py` (openpyxl read-back).
- 2026-10-17: phase 7 done — `conditionals.py`: `build_conditional` normalizes an
  `ElifBlock` (and nested raw `IfBlock`s: the parser leaves a nested `if/else` inside
  an elif branch unconverted, with its else in `.orelse`) into branches; one
  `CalcRow` per variable, first-appearance order, nested `IF`. Expressions are built
  against a `Scope` (names before the tree + new rows of variables already assigned
  on the branch path), so in-branch reads match Python's order; tests see the
  pre-tree names. Fallback = previous version, else `NA()` (cached `None`). Cached
  values come from running the taken path on the evaluator. Piecewise display, one
  `value,  if cond` line per case, nested tests joined with "and". Comment lines and
  comment commands inside branches are ignored; inline comments give the row comment.
  Demo gained a web-class tree. Tests: `tests/test_excel_conditionals.py`.
- 2026-10-17: phase 8 units done — `units.py` (duck-typed pint/forallpeople:
  `unit_value` → display magnitude, unit text, display→SI factor rounded to 12 sig.
  digits; forallpeople's display unit is read back from `format(q, ".15g")`;
  `unit_constant` for bare units; offset units raise). Builder scales sheet references
  `name*factor` (factors per Excel name in `ExcelState.factors`) and the result by
  `/factor` (`build_scaled`, `scale_formula`). A unit-bearing RHS with no sheet
  references is an input ParamRow (`L = 300*mm` → 300, "mm"). Skipped: pint/forallpeople
  imports, `ureg = pint.UnitRegistry()`, `mm = ureg.mm`, `si.environment(...)`.
  Conditionals compute values first so factors exist before formulas reference them.
  Names resolve globals → builtins (forallpeople `top_level=True` writes builtins).
  All unit workbooks recalculate to the Python values. Tests: `tests/test_excel_units.py`.
- 2026-10-17: docs — `docs/excel_renderer.md` (mkdocs nav "Excel Renderer"), README
  section "Export to a live Excel worksheet" (README uses CRLF line endings: edit with
  `newline=''`). All phases complete; branch pushed.
