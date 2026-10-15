# Jupyter cell magics (`%%render` and `%%tex`)
An easy way to use `handcalcs` is as _cell magic_ in Jupyter Notebook or Jupyter Lab.

First, import the module and run the cell:

```python
import handcalcs.render
```

This imports two cell magics:

* `%%render`
* `%%tex`

And one line magic:

* `%decimal_separator`

## Using `%%render`

In any cell that you want to render into Latex with `handcalcs`, just use the `%%render` cell magic at the top of your cell:

```python
%%render
```

For example:

```python
%%render
a = 2
b = 3
c = 2*a + b/3
```

Displays:

![Basic output from render cell magic](../images/render.png)

## Choosing the output format (handcalcs v2)

In handcalcs v2, `import handcalcs` registers the `%%render` cell magic. By default,
`%%render` uses the `markdown` renderer. It shows the calculation as Markdown with LaTeX
math, which JupyterLab, Notebook 7, VS Code and Colab typeset with MathJax or KaTeX.
Each nested `if`/`for` block is indented as a blockquote.

To switch renderers for the rest of the session, use the `%hc_default_renderer` line magic:

```python
%hc_default_renderer latex
```

Any registered renderer name works (`markdown`, `latex`, `html`, `plain_text`, or a custom
renderer that has been defined). This sets the `jupyter_renderer` config option, which
is used only by `%%render`. A bare `HandCalcs()` still uses `default_renderer`. To keep the
choice permanently:

```python
import handcalcs
handcalcs.set_option("jupyter_renderer", "latex")
handcalcs.save_config()
```

## Using `%%tex`

Instead of rendering the Latex code and displaying it, the `%%tex` cell magic prints the Latex code that can be copy/pasted into another Latex document.

For example:

```python
%%tex
a = 2
b = 3
c = 2*a + b/3
```

Displays:

![Basic output from tex cell magic](../images/tex.png)

## Using `%decimal_separator`

Instead of using `.` as the decimal separator, this line magic allows the decimal separator to be changed to another character. The change will persist for all subsequent cells that are rendered and only needs to be set once.

For example:

```python
%decimal_separator ,
```

If we re-run the above cell now, we will see:

![Basic output from render cell magic with new decimal separator](../images/decimal_separator.png)

## Magic line arguments

Both `%%render` and `%%tex` accept line arguments in the following form:

```python
%%render [override] [sympy] [precision]
```


1. `override`: a `str` as one of `params`, `long`, `short`, or `symbolic` combined with, optionally, `sympy`. See [override tags](../overrides.md) for more information. 
2. `precision`: an `int` used to set the decimal precision or rendered values

For example:

![Basic output from render cell magic with new decimal separator](../images/cell_magic_overrides_example.png)

See [override tags](../overrides.md) for more information. 
