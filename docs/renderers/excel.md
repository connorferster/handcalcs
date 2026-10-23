# Excel renderer

The `ExcelRenderer` turns a handcalcs cell into a **live Excel worksheet**.
Every calculation becomes a real Excel formula that references the other rows
through worksheet-scoped defined names. If you edit an input in Excel, the sheet
recalculates. The sheet is also laid out like a handcalc: a symbolic column with
subscripts, superscripts and Greek letters, plus headings and comment paragraphs.

## Installing

The renderer writes workbooks with [XlsxWriter](https://xlsxwriter.readthedocs.io),
an optional dependency:

```console
$ pip install "handcalcs[excel]"
```

## Usage

```python
from handcalcs import HandCalcs
from handcalcs.renderers.excel import ExcelRenderer

source = '''
## Roots of a quadratic
from math import sqrt
a = 2  # leading coefficient
b = -7; c_0 = 3
# hc: -f .3f
x_1 = (-b + sqrt(b**2 - 4*a*c_0)) / (2*a)  # larger root
'''

HandCalcs(renderer=ExcelRenderer(sheet_name="Quadratic"))(
    source, destination="quadratic.xlsx"
)
```

With `destination=`, the workbook is saved there and its `Path` is returned. Without
it, the renderer returns an `ExcelWorkbook` object rather than a string (`complete()`,
which `HandCalcs` calls for you, builds it):

- `.save(path)` writes the `.xlsx` file and returns its `Path`;
- `.to_bytes()` returns the file contents (e.g. for a web download);
- `.rows` holds the row records the sheet was written from.

Pass `filepath=` to the renderer to have every render it makes saved there.

### Several cells in one workbook

Names are scoped to their worksheet, so each sheet can reuse the same variable
names. Render each cell, then write its rows to a sheet of one
`xlsxwriter.Workbook`:

```python
import xlsxwriter

renderer = ExcelRenderer()
workbook = xlsxwriter.Workbook("beams.xlsx")
for sheet_name, source in [("Beam 1", beam_1), ("Beam 2", beam_2)]:
    rows = HandCalcs(renderer=renderer)(source).rows
    renderer.write_sheet(workbook, rows, sheet_name)
workbook.close()
```

## Layout

| row type   | A      | B | C        | D | E           | F    | G       |
|------------|--------|---|----------|---|-------------|------|---------|
| input      | symbol | = | comment  | = | **value**   | unit |         |
| calculation| symbol | = | symbolic | = | **formula** | unit | comment |

- **Inputs** are literal assignments (`a = 2`, `L = 300*mm`). Their value cell
  is the one to edit.
- **Calculations** hold a formula such as `=(-b+SQRT(b^2-4*a*c_0))/(2*a)`. The
  Python result is stored as the formula's cached value, so viewers that do not
  recalculate still show numbers.
- **Headings** (`## Title`) and **comment paragraphs** (consecutive `#` lines)
  are merged across columns A–E. Heading sizes follow a type scale from the
  10 pt body: 16, 14, 12.5 and 11.5 pt.
- A docstring becomes a comment paragraph.
- The **symbol** and **symbolic** columns typeset names as the other renderers do
  ([naming variables](../getting-started/writing-calculations.md#naming-variables)),
  but Excel has one subscript level, so every subscript is shown after a comma
  (`N_pl_Rd` → N<sub>pl,Rd</sub>) whatever the `subscripts` option says. The defined
  names keep the Python identifier (`DeltaH` stays the name `DeltaH`).

## Options

```python
ExcelRenderer(
    sheet_name="Calculations",
    value_format={"bold": False, "text_color": "#000000", "cell_color": "#FFF2CC"},
    formula_format={"bold": True, "text_color": "#000000", "cell_color": None},
    filepath=None,
    general_format="General",
)
```

- `value_format` styles the input value cells. The default is a light-yellow
  fill, the common engineering convention for "edit me".
- `formula_format` styles the formula cells.
- Each key is optional and merged over the defaults. Colours may be `"#RRGGBB"`,
  `"RRGGBB"` or an `(r, g, b)` tuple. Invalid options raise `ValueError` when
  the renderer is created.
- `general_format` is the Excel number format used for Python format codes with
  no exact Excel equivalent, such as the default `.5g`.

## Comment commands

| command    | effect in Excel |
|------------|-----------------|
| `-f CODE` | sets the Excel number format: `.3f` → `0.000`, `,.2f` → `#,##0.00`, `.2e` → `0.00E+00`, `.1%` → `0.0%` |
| `-b`       | inserts a blank row |
| `-i`       | writes the row but **hides** it, so formulas that use it still work |
| `-p`       | forces the input layout; a calculation keeps its formula |
| `-h`, `;`  | each assignment becomes its own input row |
| `-m`, `-c` | no effect (the layout is fixed) |

## Conditionals

An `if`/`elif`/`else` tree becomes one row per assigned variable, with a nested
`IF` formula:

```python
if h_w / t_w <= 1100 / sqrt(F_y):
    web_class = 1
elif h_w / t_w <= 1700 / sqrt(F_y):
    web_class = 2
else:
    web_class = 4
```

gives `=IF(h_w/t_w<=1100/SQRT(F_y),1,IF(h_w/t_w<=1700/SQRT(F_y),2,4))`. The
symbolic column shows the cases, one per line. A branch that does not assign a
variable keeps its previous value, or `#N/A` if it had none. Branches may
contain assignments, nested `if` trees and comments.

## Units

[pint](https://pint.readthedocs.io) and
[forallpeople](https://github.com/connorferster/forallpeople) values are
supported. A value cell holds the magnitude in the value's display unit, and the
unit column shows the unit. Formulas convert every reference to SI base units
and convert the result back, so mixed units stay correct after an edit:

```python
F = 12.5 * kN
L = 300 * mm
M = F * L      # =F*1000*(L*0.001)/1000, shown in kN·m
```

Imports of `pint`/`forallpeople`, `ureg = pint.UnitRegistry()`, `mm = ureg.mm`
and `si.environment(...)` produce no rows. Offset units (°C, °F) are not
supported.

## What cannot be converted

A worksheet can only hold assignments, so the renderer raises
`ExcelRendererIncompatibleError` **before writing anything** for:

- `for`/`while` loops, function definitions, `try`;
- expression statements such as `print(...)`;
- imports other than `math`, `pint` and `forallpeople`;
- lists, tuples, dicts, sets, comprehensions, index or key lookups (`xs[0]`),
  `in`/`is`, keyword arguments,
  `None` and complex numbers;
- tuple unpacking (`a, b = 1, 2`) and chained assignment (`a = b = 1`);
- functions with no Excel equivalent;
- variables used in a formula but never assigned on the sheet.

The error message names the offending construct and the variable being assigned.

Supported functions: `sqrt`, `exp`, `log` (`LN`, or `LOG` with a base), `log10`,
the trigonometric and hyperbolic functions and their inverses, `atan2` (with
Excel's argument order), `radians`, `degrees`, `abs`/`fabs`, `floor`, `ceil`,
`trunc`, `factorial`, `pow`, `hypot`, `min`, `max` and `round`. Also the
constants `pi`, `e` and `tau`. Note that Python's `round` rounds halves to even,
while Excel's `ROUND` rounds them away from zero.

## Notes

- Excel reserves names that look like cell references (`x1`, `L1`, `R1C1`) and
  the single letters `c` and `r`. Such variables get a trailing underscore on
  the sheet (`x1_`, `c_`).
- A reassigned variable gets a versioned name (`M_u`, then `M_u_2`), so earlier
  rows keep their own values. `M_u *= 2` is a reassignment too, with the formula
  `=M_u*2`. The body of a `with` block becomes ordinary rows.
- `HandCalcs(renderer=ExcelRenderer()).demo()` renders a worked steel-beam
  check that uses each feature on this page. The general handcalcs demo has
  loops and collections, so the ExcelRenderer supplies its own (`demo_source`).
- `scripts/excel_demo.py` saves that demo to `excel_demo/excel_demo.xlsx`. Run
  it with `uv run --with formulas` to recalculate every formula independently
  and compare it with Python.

## Source

- {source}`src/handcalcs/renderers/excel/renderer.py`: the renderer and its node handlers
- {source}`src/handcalcs/renderers/excel/formulas.py`: Python expressions to Excel formulas
- {source}`src/handcalcs/renderers/excel/writer.py`: writing the workbook
- {source}`src/handcalcs/renderers/excel/units.py`: unit handling

The Excel renderer is a good example of a renderer whose output is not text; see
[Example: a non-text renderer](../building-renderers/example-json.md).
