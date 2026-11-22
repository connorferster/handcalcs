# Changelog

## 2.0.0 (unreleased)

handcalcs 2.0 is a rewrite: the parser builds a tree of nodes, and pluggable
**renderers** turn it into Markdown (the Jupyter default), LaTeX, HTML, ASCII text,
Excel (live formulas) or Word (editable equations). `pip install handcalcs` now
installs 2.0. Notebooks written for 1.x need a few changes; see
[Coming from handcalcs v1](../getting-started/migrating-from-v1.md), or pin
`"handcalcs<2"` to stay on 1.x for now.

The sections for 2.0.0rc1 to rc5 below list everything that is new. For people
coming from 1.x, the main points:

- **Comment commands** (`# hc: -f .2f`, `-m`, `-g`, `-i`/`-s` with conditions,
  `--check`, `--boxed`, `--pagebreak`) replace the v1 cell override tags.
- **Headings, prose and light Markdown in comments**, and Jinja templating.
- **More of Python renders**: nested `if`/`for`, indexing, comprehensions, conditional
  expressions, `with` blocks, line continuations, bare expressions.
- **Units**: forallpeople and pint quantities, `# hc: -u` for unit inputs.
- **SymPy substitution** with `# hc: -y` (v1's `%%render sympy`), `%%source latex`
  (v1's `%%tex`), `%render` for one line, `@handcalc(display=True)`, a command line
  (`handcalcs script.py -o calc.docx`) and `inputs=` to render one script with many
  input sets.

Behaviour changed during the release candidates (see each section): comment commands
are read, never run (rc3); a value keeps the `-f` format of its line (rc3); a lone
line ending in `;` is a one-cell grid row and `# hc: -c` no longer reshapes `;`
lines (rc5).

`@handcalc(jupyter_display=True)` still works, with a deprecation warning; it will
be removed in handcalcs 3.0.

### Changes since 2.0.0rc5

- **The `exporters` extra is gone.** nb-hideinputs, which it installed, no longer hides
  input cells with current nbconvert. Use nbconvert's own `--no-input` instead
  (`jupyter nbconvert --to html --no-input calcs.ipynb`; see
  [Exporting a notebook](../interfaces/jupyter.md#exporting-a-notebook)).

### Fixes since 2.0.0rc5

- **`# ##` and `#  ##` are headings**, the same as `###`: spaces between the comment
  marker and the heading's `#`s no longer turn it into a comment line.
- **`# hc: -b` adds about one blank line in every renderer.** The HTML renderer added
  nothing; it now adds a spacer (`.hc-break`). The Markdown renderer's `&nbsp;`
  paragraph added about two lines between equations in Jupyter; it is now a small
  spacer `<div>`. In LaTeX the break is `\vspace{\baselineskip}` instead of `\medskip`.
- **Long equations no longer run off the page in Word**: the Word renderer estimates
  each equation's width against the document's text width. A substituted row that is
  too wide is split one step per row, as with `-m`; a wide `# hc: -g` grid is set in
  fewer columns; and a row that is still too wide is set in a smaller font, down to
  60% ([details](../renderers/word.md#long-equations)).
- **Line magics and `!` commands inside a `%%render` cell** (`%time x = f(y)`,
  `!ls`) raised a `SyntaxError`. They now run with the cell and are left out of the
  render. With `inputs=` they give a clear error instead.
- **Long equations no longer run off the page in LaTeX**: TeX cannot break a line
  inside an `aligned` group, so long calculations overflowed the right margin (an
  `Overfull \hbox` warning). The LaTeX renderer now estimates each row's typeset width:
  a substituted row wider than the line (`MAX_ROW_WIDTH`, 345 pt) is split one step per
  line as with `-m`, a wide `# hc: -g` grid is set in fewer columns, and a group that is
  still too wide is scaled down to the line by `\hcfit`. The scaling needs `graphicx`,
  now in the file preamble
  ([details](../renderers/latex.md#long-equations)).

- **pint quantities of numpy arrays show their values** (#384): in the LaTeX and
  Markdown renderers, `array([2, 4]) * ureg.kN` rendered every element as the format
  code (`.5g`). The array is now drawn as other numpy arrays are, `[2, 4] kN`, in every
  renderer, so the format code and `max_items` apply to its elements.

## 2.0.0rc5 (2026-11-19)

The fifth release candidate of handcalcs 2.0. Install it with
`pip install "handcalcs>=2.0.0rc5"`; a plain `pip install handcalcs` still installs
1.x until 2.0.0 is released.

### Features

- **`;` grids keep the layout you write**: each `;` line is a row of the grid, so
  `a = 1; b = 2` over `c = 3; d = 4; e = 5` lays out two cells over three. Before,
  the cells were reflowed three to a row. End a line with `;` (`f = 6;`) for a
  one-cell row. `# hc: -c N` now sets the width of
  `# hc: -g` grids only, which still reflow
  ([details](../getting-started/writing-calculations.md#parameter-grids)).
- **SymPy substitution, `# hc: -y`**: `x = f`, where `f` holds a SymPy expression, runs
  and renders as `x = <the expression>` with the values its symbols have when the line
  runs, so the algebra done in SymPy becomes a calculation, as v1's `%%render sympy`
  did. On its own line it applies to every such line until `# hc: sympy = False`. Works
  in scripts, `%%render` and `@handcalc` (where the expression may be an argument).
  SymPy is not a dependency.
- **`%%source`** prints a cell's rendered text (LaTeX, Markdown, HTML, plain text)
  instead of displaying it, to copy into another document. `%%source latex` uses the
  LaTeX renderer for that cell, as v1's `%%tex` did. It takes `%%render`'s `inputs=`
  arguments, and `%source` prints one line.
- **`# hc: -u` shows unit inputs as values** (#353): a line that is a number times
  units, `P = 5 * kN`, renders as `P = 5 kN` instead of `P = 5 · kN = 5 · 1 kN = 5 kN`.
  Lines that calculate keep every step. Turn it on for what follows, for one line
  (inline), or everywhere with `set_option("units", True)`
  ([details](../cookbook/units.md#calculate-with-forallpeople)).
- **Stacked fractions in the HTML renderer**, with typeset maths: italic names in a
  serif maths font. `HTMLRenderer(fractions="inline")` keeps divisions on one line
  ([details](../renderers/html.md#fractions)).
- **`@handcalc(display=True)`** shows the render (displayed in Jupyter, printed
  elsewhere) and returns only the function's result; `jupyter_display=True` from
  handcalcs 1 still works (#369, [details](../interfaces/decorator.md#showing-the-render)).
- **A command line**: `handcalcs script.py -o calc.docx` (see
  [Command line](../interfaces/command-line.md)).
- **Excel formulas with US units have unit factors only where they are needed.**
  Formulas used to convert every reference to SI and back, so a sheet in US
  units was full of factors that cancel: `M_u = w_u * L**2 / 8` was
  `=w_u*14593.9029372*(L*0.3048)^2/8/1355.81794833`. It is now `=w_u*L^2/8`. A
  factor is written only where units do not cancel, in its simplest form:
  `DCR = M_u / phi_M_n` (kip·ft over kip·in) is `=M_u/phi_M_n*12`. Factors are
  exact with forallpeople 3.5 or later, and its new `us_structural` environment
  shows mixed-unit results in US units
  ([details](../renderers/excel.md#units)). Formulas give the same results as
  before. Sheets in base SI units are unchanged; with prefixed units the factors
  fold too (`=F*L` for kN and mm, instead of `=F*1000*(L*0.001)`).
- **`# hc: --boxed`** draws a box around a line's result: `\boxed{}` in LaTeX and
  Markdown, a framed result in HTML, a boxed formula in Word, a bordered value cell in
  Excel, and a box drawn with line characters in ASCII. On its own line it boxes the
  result of every following line
  ([reference](comment-commands.md#boxed-results)).
- **`float()` and `int()` in the Excel renderer**: `float(x)` is the value itself and
  `int(x)` becomes `TRUNC`. With units, both match Python: forallpeople gives the
  magnitude in the displayed unit (`float(4 * ksi)` is `4`), and pint the dimensionless
  value. This means the ACI pattern `sqrt(float(f_c / psi))` now works
  ([details](../renderers/excel.md#units)).

### Fixes

- **A substituted value that is itself a sum is bracketed** (#224): a complex number
  with a real and an imaginary part, or a SymPy sum, product or power, now reads
  `2 · (3+4j)`, `(3+4j)²` and `-(3+4j)` instead of `2 · 3+4j`, `3+4j²` and `-3+4j`, in
  every renderer. The LaTeX renderer no longer brackets a SymPy value standing on its
  own (`z = 3 + 4i`, not `z = (3 + 4i)`).
- A bare expression under `--check` whose symbolic and substituted forms are the same
  (`2 <= 3  # hc: --check`) showed both (`2 ≤ 3 = 2 ≤ 3 ✓`); the repeat is now dropped,
  as for an assignment.
- **`round()` of a value with units in the Excel renderer** gave a different result from
  Python. forallpeople's `round(x, n)` only changes how many digits are shown, but the
  sheet used `ROUND` on the SI value: `round(M / P, 3)` with `M / P = 4.80 mm` became
  `5 mm` (0.0048 m rounded to 0.005 m). The formula now leaves the value unchanged.
  With pint, it rounds the magnitude in the quantity's own unit, as pint does.
- The HTML renderer's tints (the result highlight, parameter grids, block headers,
  import chips, muted comments) now print in WeasyPrint PDFs.
- A power with an exponent that isn't a number (`a**(1/2)`) rendered as `a**(1 / 2)` in
  HTML; it is now a superscript.
- The test dependencies require forallpeople 3.5.0 (3.4.1 fixed how a value is displayed
  when its factor matches no defined unit, #352; 3.5 gives the Excel renderer exact unit
  factors).
- A parameter line (`w = 5`) in a mode without the result column, such as
  `mode = "ass sym"` (v1's `%%render symbolic`), showed only its name (`w`). It now
  shows its value: `w = 5`.

## 2.0.0rc4 (2026-11-11)

The fourth release candidate of handcalcs 2.0. Install it with
`pip install "handcalcs>=2.0.0rc4"`; a plain `pip install handcalcs` still installs
1.x until 2.0.0 is released.

### Features

- **`.to()` unit conversions in the Excel renderer**: `F = F.to("kip")` or
  `M = (F * L).to("kipft")` sets the unit a row displays, with forallpeople or pint
  (a unit string or a unit expression such as `ureg.kip * ureg.ft`). The formula is
  unchanged, since the row's unit already scales the SI result, and the symbolic column
  shows only the value being converted
  ([details](../renderers/excel.md#units)).

## 2.0.0rc3 (2026-11-06)

The third release candidate of handcalcs 2.0. Install it with
`pip install "handcalcs>=2.0.0rc3"`; a plain `pip install handcalcs` still installs
1.x until 2.0.0 is released.

### Breaking changes

- **Comment commands are read, never run** (#354). In the assignment form
  (`# hc: multiline = False`), each value must be a literal: a number, a string, `True`,
  `False` or `None`. An expression such as `# hc: format_code = "." + "2f"` is now an
  error.
- **A value keeps the `-f` format of the line that calculated it** (#357), on the lines
  that substitute it: after `DCR = C_f / C_r  # hc: -f .3f`, `ok = DCR <= 1.0` shows
  `0.833 <= 1.0`, not `0.83292 <= 1.0`. A line's own `-f` still wins, and a name
  assigned again without `-f` goes back to the format in effect. Calculations with an
  inline `-f` can show different numbers in the lines below it
  ([details](../getting-started/formatting-numbers.md#where-to-set-it)).
- **Light markup in comments** (#356) changes how some existing comments render:
  `**bold**` and `*italic*` are now styled (the Markdown renderer used to escape them),
  `\*` is a literal `*`, and in the LaTeX and Markdown renderers a pair of `$` is math.
  Formulas (`w*L**2/8`) and prices ("costs $5 to $10") stay as written; see *Features*.
- **The ASCII renderer spaces comparison operators** (#357) like the arithmetic ones:
  `DCR <= 1.0`, not `DCR<=1.0`, as the HTML renderer does.

### Features

- **Math in comments** (#350, #356): `$...$` in a heading, comment line or inline
  comment is LaTeX math in the LaTeX and Markdown renderers, as in v1. `\$` is a literal
  `$`. Turn it off with `LatexRenderer(comment_math=False)` or
  `MarkdownRenderer(comment_math=False)`
  ([details](../getting-started/writing-calculations.md#styling-comments)).
- **Bold, italic and code in comments** (#356): `**bold**`, `*italic*` and `` `code` ``
  are styled in every renderer: Markdown, LaTeX, HTML, Word (including inline comments)
  and Excel (rich text). The ASCII renderer shows them as written.
- **`@handcalc(..., docstring=False)`** (#339, #355): leave the function's docstring out
  of the render. It is rendered by default, as before.
- **`find_inputs(..., detail=True)`** (#358): each input as an `InputSpec` with its
  value, the units it is written in (`"mm"`, `"kN / m"`), the comment at the end of its
  line and its line number, for building a form or an input file from a script
  ([details](../interfaces/object-oriented.md#finding-a-scripts-inputs)).
- **`handcalcs.testing`** (#349): a renderer-neutral feature suite. `FEATURE_CASES`
  holds a calculation for each feature with the names its output must show and hide,
  and `check_case(renderer, case)` checks a renderer against one, so renderers in other
  packages can test every feature
  ([details](../building-renderers/testing.md#run-the-shared-feature-suite)).

### Fixes

- **`# hc: -s` and `# hc: -m` work after forallpeople's
  `si.environment(..., top_level=True)`** (#354). Before, `s` (seconds) and `m` (metres)
  in `builtins` made them valid Python expressions, and they were silently ignored:
  after `# hc: -i`, everything that followed stayed hidden.
- **Two or more multi-line calculations in a row** (after a standalone `# hc: -m`)
  render one below the other, instead of being joined into one row
  (`= 0.8 M_p = 7 * 8`), in every renderer (#354).
- In the Excel renderer, a comment command inside an `if` block (`# hc: -s`, `-i`,
  `-f`) now applies to the lines after the block, as in the other renderers.
- Docs: the migration guide explains that a standalone comment command stays in effect
  for the lines after it (#359).
- Development: `uv.lock` updates certifi, nbconvert and tornado for security fixes
  (#360). The package's own requirements are unchanged.

## 2.0.0rc2 (2026-10-29)

The second release candidate of handcalcs 2.0. Install it with
`pip install "handcalcs>=2.0.0rc2"`; a plain `pip install handcalcs` still installs
1.x until 2.0.0 is released.

- **`# hc: -s`** (`--show`) shows lines again after `# hc: -i`; at the end of a line it
  shows that line of a hidden section.
- **Conditional show and hide** (#343): `# hc: -s M_f > 0` shows what follows if the
  expression is true and hides it if not; `# hc: -i A_s < A_req` the opposite. The
  expression uses the values at the comment
  ([details](../cookbook/showing-and-hiding.md#show-or-hide-a-section-on-a-condition)).
- **`hidden_by_default` option** (#343): start every calculation hidden and show only
  what `-s` marks.
- **`destination=`** on `@handcalc` and `%%render`, as on `HandCalcs`: write the render
  to a file. `%%render destination=` writes the file instead of displaying the render.
- **Fixed:** a hidden section (`# hc: -i` on its own line) no longer shows its
  headings, comments, `if`/`for` headers, or an empty parameter grid, in any renderer.
- **Changed:** a comment command changes only the settings it names. Before,
  `# hc: -f .2f` also turned off an earlier `# hc: -m`, `-p` or `-i`; to turn one off,
  use the assignment form (`# hc: multiline = False`) or, for `-i`, `# hc: -s`.
- **Fixed:** a value with its own `_repr_latex_` that is not a quantity (e.g. an
  uncertain value, 1 ± 0.1) is rendered with that LaTeX in the LaTeX and Markdown
  renderers, instead of its plain text (#340).
- **Fixed:** an inline comment stays at the end of its calculation's row in the LaTeX,
  Markdown and Word renderers, instead of moving to a row of its own.
- **Fixed:** a parameter written in scientific notation is shown as written (`10E6`,
  not 10<sup>7</sup>; `12.5e3`, not 12500).
- **Changed:** the parameter grid command is `# hc: -g` (`--grid`). The rc1 spelling
  `-h` still works.

## 2.0.0rc1 (2026-10-23)

The first release candidate of handcalcs 2.0: a rewrite around a node tree and
pluggable renderers. Install it with `pip install "handcalcs>=2.0.0rc1"`; a plain
`pip install handcalcs` still installs 1.x until 2.0.0 is released.

- **Renderers**: Markdown (the Jupyter default), LaTeX, HTML, ASCII text, Excel, Word
  (editable Word equations; #222) and the base renderer. Renderers can be subclassed and customized, or written from scratch.
- **`ASCIIRenderer`** (`ascii`) for terminals, logs and docstrings: setext-underlined
  headings and calc lines aligned on `=`. It replaces the 2.0 pre-release
  `PlainTextRenderer` (`plain_text`), which has no alias.
- **`HandCalcs` interface** for rendering source strings and files from Python.
  `destination=` writes the render to a file ready to open: a complete LaTeX
  document or HTML page (the renderer's `preamble` and `postamble`), or the saved
  `.docx` or `.xlsx` ([details](../interfaces/object-oriented.md#writing-a-file)).
- **`# hc:` comment commands**, per line or per section, replacing the v1 cell override
  tags.
- **Headings, prose and Jinja templating** in comments.
- **Nested conditionals and `for` loops.**
- **Configuration** reduced to `format_code`, `default_renderer`,
  `jupyter_renderer` and `line_values`, plus custom options for renderers.
- **Names** ([naming variables](../getting-started/writing-calculations.md#naming-variables)):
  comma subscripts by default (`N_pl_Rd` → N<sub>pl,Rd</sub>; #101), Greek letters joined
  to other letters (`DeltaH`, `ΔH` → ΔH; #117), accents (`x_hat`, `V_dot`, `M_star`) and
  the `symbols` option for display specs, all parsed once and shared by every renderer.
- **Line continuations** (`\`) break a long equation at the same place (#259).
- **`%render`** line magic renders a single line (#179).
- **Bare expressions** (`2 * a`) show their result when they use only arithmetic,
  built-ins, and `math` or numpy functions (#54).
- **Many input sets from one script**: `HandCalcs(...)(script, inputs={...})` renders
  a script with different given values, keeping their units (quantities are
  converted to them); `find_inputs` lists a
  script's inputs ([details](../interfaces/object-oriented.md#rendering-many-input-sets));
  `%%render inputs=case` does the same for a notebook cell.
- **Each line shows the values it ran with.** A name assigned again later, an `if`
  test whose variable changes in its branch, and a bare expression that calls a
  function all show the values from when their line ran (the `line_values` option).
- **More of Python is rendered**: indexing and slices (`xs[i]` as a subscript),
  tuple unpacking and chained assignment, augmented assignment (`a += b` as
  `a = a + b`), the body of a `with` block, f-strings, lambdas, generator
  expressions and attributes of an expression (`(L * 2).magnitude`).
- **Numbers**: integers are never shown in scientific notation by the default
  format; format codes apply to numpy arrays, and 2-D arrays are shown as matrices.
- **Errors in a `%%render` cell are raised**, with the usual traceback, instead of
  rendering nothing.
- **`@handcalc`** stops at the `return` that ran, and uses the `default_renderer`
  when no renderer is given (`@handcalc` or `@handcalc()`). `HandCalcs()` with no
  renderer uses it too.
- **Long collections** show their first and last items around an ellipsis (the
  `max_items` and `edge_items` settings).

See [Coming from handcalcs v1](../getting-started/migrating-from-v1.md) for how to
update notebooks.
