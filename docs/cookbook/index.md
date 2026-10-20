# Cookbook

Complete recipes for things people ask handcalcs to do. Each one is a short, working
example; most show the rendered output, produced when these docs were built. The
GitHub issue that asked for it is linked where there is one.

## Find a recipe

| I want to... | Recipe |
|---|---|
| **Numbers** | |
| set the precision of one variable | [Precision of one variable](numbers.md#set-the-precision-of-one-variable) |
| use scientific or engineering notation | [Scientific notation](numbers.md#show-large-and-small-numbers-in-scientific-notation), [engineering notation](numbers.md#engineering-notation-exponents-in-multiples-of-three) |
| hide floating-point noise like `5.55e-17` | [Snap noise to zero](numbers.md#snap-floating-point-noise-to-zero) |
| drop trailing zeros, add thousands separators | [Trailing zeros](numbers.md#drop-trailing-zeros), [separators](numbers.md#thousands-separators) |
| **Showing and hiding** | |
| show only the result of a line | [Results only](showing-and-hiding.md#show-only-the-result-of-a-line) |
| show only formulas, or only results | [Formulas or results for a section](showing-and-hiding.md#show-only-formulas-or-only-results-for-a-whole-section) |
| hide a line, or the imports | [Hide a line](showing-and-hiding.md#hide-a-line), [hide imports](showing-and-hiding.md#hide-import-lines) |
| break a long equation | [Long equations](showing-and-hiding.md#break-a-long-equation-over-several-lines) |
| render one line of a notebook cell | [`%render`](showing-and-hiding.md#render-one-line-in-a-notebook) |
| lay out inputs in a grid | [Inputs in a grid](showing-and-hiding.md#lay-out-inputs-in-a-grid) |
| **Checks** | |
| state pass or fail in words | [Verdict in a comment](checks.md#write-the-verdict-in-a-comment) |
| show only the governing case | [Governing branch](checks.md#show-only-the-governing-branch) |
| check several load cases | [Several cases at once](checks.md#check-several-load-cases-at-once) |
| **Notation** | |
| write N<sub>pl,Rd</sub>, ΔH, γ<sub>M0</sub> | [Subscripts](symbols.md#eurocode-style-subscripts), [Greek letters](symbols.md#greek-letters-joined-to-text) |
| give a variable any symbol | [Any symbol for any name](symbols.md#any-symbol-for-any-name) |
| stop `psi` becoming ψ, or turn off subscripts | [Keep a name as text](symbols.md#keep-a-name-as-text), [no subscripts](symbols.md#no-subscripts-at-all) |
| use Σ, ×, ∛, n! or my own function names | [Functions](symbols.md#sigma-for-sum-and-your-own-function-names), [operators](symbols.md#times-sign-for-multiplication), [cube roots and factorials](symbols.md#cube-roots-factorials-and-infinity) |
| **Units** | |
| calculate with forallpeople or pint | [Units](units.md) |
| show a result in particular units | [Specific units](units.md#show-a-result-in-specific-units) |
| **Reports** | |
| make a PDF, Word or HTML document | [Write to a file](documents.md#write-a-calculation-straight-to-a-file), [Word](documents.md#a-word-document) |
| number equations, add a title block | [Equation numbers](documents.md#number-the-equations), [title block](documents.md#a-title-block-on-every-calculation) |
| start a new page | [Page breaks](documents.md#start-a-new-page) |
| change colors or alignment | [Colors](documents.md#colors), [alignment](documents.md#left-aligned-or-centred-equations) |
| **Apps** | |
| render from a script, or a function | [Scripts](workflows.md#render-from-a-plain-python-script), [functions](workflows.md#turn-a-calculation-function-into-a-rendered-one) |
| run one calculation for many designs | [Many designs](workflows.md#run-one-calculation-for-many-designs) |
| show calculations in a web or desktop app | [Web apps](workflows.md#rendered-calculations-in-a-web-app), [desktop apps](workflows.md#rendered-calculations-in-a-desktop-app) |

## How the recipes work

Most recipes need nothing but a [comment command](../getting-started/comment-commands.md)
or a [setting](../getting-started/configuration.md). The rest subclass a built-in
renderer and change a class attribute or register a rule, the three levers described in
[Customizing a renderer](../customizing/index.md). A recipe written for the Markdown
renderer works on the LaTeX renderer too: register the same function on a
`LatexRenderer` subclass.

To use a recipe's renderer in Jupyter, import the module that defines it and select it by
name, for example `%hc_default_renderer eng_markdown`.

```{toctree}
:hidden:

numbers
showing-and-hiding
checks
symbols
units
documents
workflows
```
