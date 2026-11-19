# Command line: `handcalcs`

The `handcalcs` command renders a Python script without writing any Python around it.

```console
$ handcalcs beam.py --renderer excel --output beam.xlsx
Wrote beam.xlsx
```

`python -m handcalcs` is the same command (`uv run python -m handcalcs` in a uv
project). Run it with no arguments to see its help, which lists every renderer and its
options.

## Choosing the output

`handcalcs SCRIPT`
: prints the render to stdout as text, with the renderer named by the
  `default_renderer` [option](../getting-started/configuration.md) (ASCII unless you
  change it). `-` as `SCRIPT` reads the script from stdin.

`-o FILE`, `--output FILE`
: writes the render to `FILE` instead, as `HandCalcs(...)(source,
  destination=FILE)` does: a complete document for the LaTeX and HTML renderers, a saved
  `.docx` or `.xlsx` for the Word and Excel renderers. Without `--renderer`, the
  renderer is chosen from the extension:

  | Extension | Renderer |
  |---|---|
  | `.xlsx` | `excel` |
  | `.docx` | `word` |
  | `.tex` | `latex` |
  | `.md` | `markdown` |
  | `.html`, `.htm` | `html` |
  | `.txt` | `ascii` |

`-r NAME`, `--renderer NAME`
: the renderer, by its registered name. The Word and Excel renderers need `--output`.

```console
$ handcalcs beam.py                     # ASCII text to the terminal
$ handcalcs beam.py -o beam.docx        # Word, from the extension
$ handcalcs beam.py -r latex > beam.tex # a LaTeX document on stdout
```

## Renderer options

Any other `--name VALUE` is passed to the renderer as the keyword argument
`name=VALUE`, with dashes in the name becoming underscores. These are the same
arguments as the renderer's constructor in Python:

```console
$ handcalcs beam.py -o beam.xlsx --sheet-name Beam
$ handcalcs beam.py -o beam.html --theme-color '#1d4ed8'
$ handcalcs beam.py -o beam.docx --layout lines --template company.docx
```

- A value is read as a Python literal when it is one (`3`, `True`, `None`,
  `{"bold": True}`) and as a string otherwise (`Beam`, `#1d4ed8`). Quote it for your
  shell when it has spaces or braces.
- `--name=VALUE` works too. `--name` with no value is `True`; put such a flag after
  the script, or write `--name=True`, so it doesn't take the script as its value.
- An option the renderer doesn't take is an error that lists the ones it does.

The handcalcs options `--format-code`, `--line-values` and `--hidden-by-default` are
set the same way, for that run only:

```console
$ handcalcs beam.py --format-code .2f
```

## Inputs

`-i NAME=VALUE`, `--input NAME=VALUE` renders the script with `VALUE` in place of the
value it first assigns `NAME`, as `HandCalcs(...)(source, inputs=...)` does (see
[Rendering many input sets](object-oriented.md#rendering-many-input-sets)). Repeat it
for each input:

```console
$ handcalcs beam.py -i w=7.5 -i L=8 -o beam-case2.docx
```

- A number keeps the units of the script's line: with `L = 6 * m`, `-i L=8` runs and
  renders `L = 8 * m`.
- `VALUE` may also be an expression using names the script defines before its first
  input, such as its units. A quantity is converted to the line's units, so
  `-i L='8000 * mm'` renders `L = 8 * m` too.
- `--no-strict` ignores a `NAME` the script never assigns, which is otherwise an error.
- `--allow-computed` allows replacing a value the script computes.

## Custom renderers

A custom renderer is chosen by name once the module that defines it is imported.
`--import MODULE` imports it first (repeat it for several modules):

```console
$ handcalcs beam.py --import my_renderers -r rst -o beam.rst
```

`--list-renderers` (with any `--import`) prints the available renderers and their
options.

## Other options

`-q`, `--quiet`
: don't report the file written.

`-V`, `--version`
: print the handcalcs version.

The script runs with its own directory importable, as with `python script.py`, so it
can import the modules beside it.

## Source

{source}`src/handcalcs/__main__.py`
