<p>
  <img src="https://travis-ci.org/connorferster/handcalcs.svg?branch=master">
<a href='https://coveralls.io/github/connorferster/handcalcs?branch=master'><img src='https://coveralls.io/repos/github/connorferster/handcalcs/badge.svg?branch=master' alt='Coverage Status' /></a>
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg">
  <img src="https://img.shields.io/pypi/v/handcalcs">
  <img src="https://img.shields.io/pypi/pyversions/handcalcs">
  <img src="https://img.shields.io/github/license/connorferster/handcalcs">
  <img src="https://img.shields.io/pypi/dm/handcalcs">
</p>
<p align="center">
  <img src="docs/images/handcalcs.jpg"><br>
  Covert art by <a href = "https://www.instagram.com/joshuahoibergtattoos/">Joshua Hoiberg</a>
</p>

<h1 align = "center">handcalcs:<br>Python calculations in Jupyter,<br>as though you wrote them by hand.</h1>

`handcalcs` is a library to render Python calculation code automatically in Latex, but in a manner that mimics how one might format their calculation if it were written with a pencil:  write the symbolic formula, **followed by numeric substitutions**, and then the result.

Because `handcalcs` shows the numeric substitution, the calculations become significantly easier to check and verify by hand.


## Contents

* [Basic Demo](https://github.com/connorferster/handcalcs#basic-demo)
* [Installation](https://github.com/connorferster/handcalcs#installing)
* [Basic Usage](https://github.com/connorferster/handcalcs#basic-usage-1-as-a-jupyter-cell-magic-render)
* [Enhanced Usage](https://github.com/connorferster/handcalcs#basic-usage-2-as-a-decorator-on-your-functions-handcalc)
* [Features](https://github.com/connorferster/handcalcs#features)
* [PDF Printing in Jupyter](https://github.com/connorferster/handcalcs#pdf-printing-in-jupyter)
* [Expected Behaviours](https://github.com/connorferster/handcalcs#expected-behaviours)
* [Gotchas and Disclaimer](https://github.com/connorferster/handcalcs#gotchas)
* [YouTube Tutorials](https://github.com/connorferster/handcalcs#youtube-tutorials)
* [Applications and Compatibility with Other Libraries (wiki)](https://github.com/connorferster/handcalcs/wiki)



## Basic Demo

![handcalcs demo 1](docs/images/basic_demo.gif)


## Installing

You can install using pip:

`pip install handcalcs`

## Basic Usage 1: As a Jupyter cell magic (`%%render`)
`handcalcs` is intended to be used with either Jupyter Notebook or Jupyter Lab as a _cell magic_.

First, import the module and run the cell:

```python
import handcalcs.render
```

Then, in any cell that you want to render with `handcalcs`, just use the render cell magic at the top of your cell:

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

**That is it!**

Once rendered, you can then export your notebook as a PDF, provided you have a Latex environment installed on your system. If you are new to working with Latex and would like to install it on your system so you can use this functionality, please see the section [Installing Tex](https://github.com/connorferster/handcalcs/wiki), in the wiki.

## Basic Usage 2: As a decorator on your functions, `@handcalc()`

This is the same kind of thing except instead of running your code in a Jupyter cell, you are running your code in a Python function, which is treated like a Jupyter cell. 

Start by importing the `@handcalc()` decorator:

```python
from handcalcs.decorator import handcalc
```

Then, write your function. Your function MUST `return locals()`:

```python
@handcalc()
def my_calc(x, y, z):
  a = 2*x / y
  b = 3*a
  c = (a + b) / z
  return locals()
```

#### `@handcalc(left: str = "", right: str = "", jupyter_display: bool = False)`

Returns a tuple consisting of `(latex_code: str, locals: dict)`, where `locals` is a dictionary of all variables in the scope of the function namespace.

* `left` and `right` are strings that can precede and follow the encoded Latex string, such as `\\[` and `\\]` or `$` and `$`
* `jupyter_display`, when True, will return only the `locals` dictionary and instead will display the encoded Latex string rendering with `display(Latex(latex_code))` from `IPython.display`. Will return an error if not used within 

In your decorated function, everything between `def my_calc(...)` and `return locals()` is now like the code in a Jupyter cell, except it's a standard Python function.

Used in this way, you can use `@handcalc()` to dynamically generate Latex code for display in Jupyter and non-Jupypter Python environments (e.g. streamlit). 


## Comment Tags

`handcalcs` makes certain assumptions about how you would like your calculation formatted and does not allow for a great deal of customization in this regard. However, there are currently **three** customizations you can make using `# comment tags` as the _first line of your cell_ after the `%%render` cell magic. You can only use __one__ comment tag per cell.

**Comment tags can be used with both the Jupyter cell magic and the function decorator**. To use a comment tag with the decorator, the comment tag must be the first line after the signature (i.e. the `def func_name():`)

### `# Parameters`: 
`handcalcs` renders lines of code vertically, one after the other. However, when you are assigning variables, or displaying resulting variables, you may not want to waste all of that vertical space. 

Using the `# Parameters` comment tag, your list of parameters will instead render in three columns, thereby saving vertical space.

![Parameters](docs/images/parameters.gif)


### `# Long` and `# Short`: 
To save vertical space, `handcalcs` _attempts_ to figure out how long your calculation is and, if it is short enough, renders it out fully on one line.

If `handcalcs`'s internal test deems the calculation as being too long to fit onto one line, it breaks it out into multiple lines. 

Use the `# Long` or `# Short` comment tags to override the length check and display the calculation in the "Long" format or the "Short" format for all calculations in the cell. e.g.

```python
    # Format for "short" calculations (can fit on one line):
    c = 2*a + b/3 = 2*(2) + (3)/3 = 5

    # Format for "long" calculations (requires multi-line format)
    c = 2*a + b/3
      = 2*(2) + (3)/3
      = 5
```

![Short and Long calculations](docs/images/shortandlong.gif)


### `# Symbolic`
The primary purpose of `handcalcs` is to render the full calculation with the numeric substitution. This allows for easy traceability and verification of the calculation. 

However, there may be instances when it is preferred to simply display calculations symbolically. For example, you can use the `# Symbolic` tag to use `handcalcs` as a fast way to render Latex equations symbolically.

Alternatively, you may prefer to render out all of input parameters in one cell, your formulae symbolically in the following cell, and then all the final values in the last cell, skipping the numeric substitution process entirely.

Keep in mind that even if you use the `# Symbolic` tag with your calculations, you still need to declare those variables (by assigning values to them) ahead of time in order for your calculation to be valid Python.

![handcalcs with forallpeople](docs/images/symbolic.gif)

---

## Units Packages Compatibility

`handcalcs` was designed to be used with the units package, [forallpeople](https://github.com/connorferster/forallpeople) (and [forallpeople](https://github.com/connorferster/forallpeople) was designed to be compatible with `handcalcs`). However, it has been recently reported that [pint](pint.readthedocs.org) can work to good effect, also.

![handcalcs with forallpeople](docs/images/forallpeople.gif)


**For potential compatibility with other units packages, please see [the wiki.](https://github.com/connorferster/handcalcs/wiki)**

---

## Features

### Quickly display the values of many variables
In Python, displaying the value of many variables often requires tediously typing them all into a series of `print()` statements. `handcalcs` makes this much easier:

![display variable demo](docs/images/outputs.gif)

### Get Just the Latex Code, without the render
If you just want to generate the rendered Latex code directly to use in your own Latex files, you can use the `%%tex` cell magic instead:

```python
%%tex
a = 2
b = 3
c = 2*a + b/3
```

Then you can just copy and paste the result into your own LaTeX document.

![tex cell magic demo](docs/images/tex.gif)

---

### Subscripts (and sub-subscripts, etc.)

Subscripts in variable names are automatically created when `_` is used in the variable name. Sub-subscripts are nested for each separate `_` used in series.

![Subscripts demo](docs/images/subscripts.gif)


----

### Greek symbols

Any variable name that contains a Greek letter (e.g. "pi", "upsilon", "eta", etc.) as a string or substring will be replaced by the appropriate Latex code to represent that Greek letter.

* Using lower case letters as your variable name will make a lower case Greek letter.

* Using a Capitalized Name for your variable will render it as an upper case Greek letter.

![Greek symbols demo](docs/images/greeks.gif)

---

### Functions, built-in or custom

If you are using Python functions in your calculation, eg. `min()` or `tan()`, they will be replaced with Latex code to represent that function in Latex.

If you are creating your own functions, then they will be rendered in Latex as a custom operator.

If you are using a function with the name `sqrt` (whether your own custom implementation or from `math.sqrt`), then it will be rendered as the radical sign.

![Functions](docs/images/funcs.gif)

---

### Rendered in-line Comments

Any comments placed after a line of calculation will be rendered as an inline comment in the Latex. 

This makes it convenient to make notes along side your calculations to briefly explain where you may have acquired or derived a particular value.

![Comments](docs/images/comments.gif)

---

### Skip the substitution

Any calculation entirely wrapped in parentheses, `()`, will be rendered as just `param = result`, without the substitution. 

This can be convient when you want to calculate a parameter on the fly and not have it be the focus of the calculation.

![Skip the substitution](docs/images/skip_subs.gif)

---

### Conditional statements

Many calculations in the "real world" are dependent on context.

`handcalcs` allows for the inclusion of some simple conditional statements into its code in a way that makes it easier to understand the context of the calculation.

![Conditional calculations](docs/images/conditionals.gif)

*Note: Multiple "lines" of calculations can be used after the conditional expression provided that they are all on the same line and separated with "`;`". See [Expected Behaviours](https://github.com/connorferster/handcalcs#expected-behaviours) for more context.*

---

### Numeric integration

You can use `scipy.quad` to perform numeric integration on a pre-defined function and have `handcalcs` perform a basic rendering of it.

This behaviour is triggered if you use a function with either `integrate` or `quad` in the name.

![Numeric integration](docs/images/integration.gif)

---

## PDF Printing in Jupyter

Jupyter Notebooks/Lab are able to print notebooks to PDF through two methods. Both can produce great results with handcalcs:

1. **Export to HTML**: Open the exported HTML page in your browser and print to PDF using your system's own PDF printer
    * Pros: No additional software required, you can include images copy-pasted into your Jupyter notebook, and you can change the scale of the printed PDF in your brower's print window.
    2. Cons: Page breaks can be less graceful on html output and you cannot otherwise customize the output further like you can with a .tex file
2. **Export to PDF (via Latex)**: Using your previously installed Latex distribution, Jupyter will first export your notebook to a .tex file and then render the file to PDF. This requires you to have a Latex distribution already installed on your system (Instructions: [windows](https://miktex.org/howto/install-miktex), [mac os](https://tug.org/mactex/mactex-download.html), [ubuntu](https://linuxconfig.org/how-to-install-latex-on-ubuntu-20-04-focal-fossa-linux)).
    * Pros: Page breaks tend to work better and you have the ability to customize your output further using the generated .tex file
    * Cons: Cannot easily rescale the PDF print (e.g. to ensure really long equations fit on the page) and you cannot include images copy/pasted into your Notebook. Images can be used but must be linked in with Markdown and the file must reside in the same directory as your Notebook.

PDF notebooks made with handcalcs tend to look better if the code input cells are suppressed. To make this convenient, handcalcs ships with two modified nbconvert template files that can be installed by running a function in Jupyter before exporting.

###  `handcalcs.install_templates.install_html(swap_in:str = "", swap_out:str = "full.tpl", restore:bool = False)`

### `handcalcs.install_templates.install_latex(swap_in:str = "", swap_out:str = "article.tplx", restore:bool = False)`

**`swap_in`**: the name of the handcalcs template file you wish to install. When not provided, the function will print a list of available templates whose names are acceptable inputs for this argument.<br>
**`swap_out`**: the name of the nbconvert template file you wish to replace (default file is nbconvert's default html or latex template, respectively)<br>
**`restore`**: when set to `True`, the function will remove your previously installed template file and restore the default nbconvert template.

### Design rationale
While there are methods for manually changing the template that nbconvert uses, this has to be performed on the command line as a separate conversion step. This default template override approach is not available from within the Jupyter GUI interface.

I have found that the easiest and most reliable way to quickly change the default export behaviour is to swap out and replace the default template files. By using this approach, you can export your notebooks directly from the Jupyter GUI menu options and have your notebooks look how you wish without fussing with multiple configuration settings that may or may not take.


### Note
When handcalcs installs these templates, they make a semi-permanent change to your templates that will persist for all of your other notebooks that you print from with Jupyter, regardless of whether you are working with handcalcs or not. It does this because it is "physically" swapping out and replacing your nbconvert default template files for your local installation  meaning it will persist past the end of your Jupyter session.

This change can be reverted at any time by using the `restore = True` argument. Additionally, the function will not let you repeatedly install the same template. If you wish to install another template, the function will prompt you to run the function with `restore = True` before attempting another installation.

In this way, handcalcs can fully manage these template installations for you. However, if you manually alter the file names of an installed handcalcs template in the nbconvert templates directory, there is no guarantee that your original template can be successfully restored.

### Example of use
You can perform the same below process using either `install_html` or `install_latex` functions.


```python
>>> from handcalcs.install_templates import install_html
>>> from handcalcs.install_templates import install_latex

>>> install_html() # Use with no arguments to discover available templates
Available templates:
 ['full_html_noinputs.tpl']
>>> install_html('full_html_noinputs.tpl') # Select the template you wish to install
/usr/Name/path/to/your/nbconvert/templates/dir/html/full.tpl
-is now-
/usr/Name/path/to/your/nbconvert/templates/dir/html/full_swapped.tpl

/usr/Name/path/to/your/handcalcs/templates/dir/html/full_html_noinputs.tpl
-is now-
/usr/Name/path/to/your/nbconvert/templates/dir/html/full.tpl

>>> install_html(restore = True) # To revert this change to your template files
/user/Name/path/to/your/nbconvert/templates/dir/html/full.tpl
-was deleted, and replaced with-
/user/Name/path/to/your/nbconvert/templates/dir/html/full_swapped.tpl
```
---

##  Expected Behaviours

`handcalcs` is intended to render arithmetical calculations written in Python code. It is not intended to render arbitrary Python into Latex. 

Given that, handcalcs only renders a small subset of Python and there is a lot that will not work, especially anything that happens over multiple lines (e.g. function definitions, `for` loops, `with` statements, etc.).

`handcalcs` works by parsing individual _lines_ of Python within a cell. It does not parse the cell as a whole. Therefore all statements to be rendered must be contained on a single line.

### Accepted datatypes

`handcalcs` will make an attempt to render all datatypes. However it is not intended for "collections"-based types (e.g. `list`, `tuple`, `dict`, etc.)

Objects are rendered into Latex by two main approaches:

1. If the object has a `_repr_latex_()` method defined, then that method is used.

    a) If the object has some alternate method for rendering itself into Latex code, e.g. `.latex()` or `.to_latex()`, that will be attempted as well.
    
    In order for the representation to be rendered properly, the object's Latex represention must use commands that are implemented with MathJax and/or Katex.
2. If the object does not have a Latex method, then `str()` is used.

If you are using object types which have str methods that render as `<MyObject: value=34>`, then that's what the Latex interpreter will see and attempt to render.

### Arithmetic operators

* `+` renders as `+`
* `-` renders as `-`
* `*` renders as the "dot operator" (Latex: \cdot)
* `/` always renders as a fraction
* `**` renders as superscripts
* `%` renders as the "mod function" (Latex: \mod)

Currently `//` is not rendered but you can easily use `math.floor` as a function instead.

### Brackets (parentheses) are critical

Brackets are used to remove ambiguity in how the Latex is rendered. For example:

```python
a = 23.2
b = 9.4
c = (3*a)/(sqrt(2*a + b**2))
```
Here, brackets are used to define both numerator and denominator, unambiguously.

However, even though it is correct and valid Python, the below will produce unexpected results:

```python
a = 23.2
b = 9.4
c = (3*a)/sqrt(2*a + b**2)
```
![Incorrect brackets](docs/images/wrong_brackets.gif)

Under-the-hood, parsed Python code in `handcalcs` is represented as a nested deque: every set of parentheses (no matter the context) begins a new nested deque which is recursively converted to Latex code. 

The above line would look like this (represented as a list, for brevity): `[[3, '*', 'a'], '/', 'sqrt', [2, '*', 'a', '+', 'b', '**', '2' ]]`. Notice how the `sqrt` is all alone after the `/` operator?

To render the fraction properly, a lookahead is performed and the next item after the `/` is rendered as the denominator. In this instance, the next item is the function name, `sqrt`, and not the full expression. 

Bracketing the entire denominator causes `handcalcs` to see the whole expression (as a nested deque) in the lookahead.

**If you have Latex output that does not look quite right, check to see if you are using brackets and fractions in this unambiguous manner.**

All actual calculations are handled by Jupyter when the cell is run. The resulting values are stored in the user's namespace dictionary and `handcalcs` uses the variable's corresponding value from the namespace dict as the result to display. Consequently, even if the representation of your calculation seems odd, the result will be correct _provided that you are using a unique variable name._ (see, [Gotchas](https://github.com/connorferster/handcalcs#gotchas))


### `for` loops and other iterations

Showing rendered iterations is not supported. The intention for use is that you perform your iterations in a cell that is not rendered and then, once the iteration has produced the desired resulting value, you render the result in a separate cell.

## Gotchas

Because `handcalcs` is designed for use within the Jupyter environment, and because Jupyter cells can be run out of order, there exists the possibility of having a big mess of beautifully rendered but **completely incorrect** calculations if you _re-use variable names throughout your notebook_.

`handcalcs` uses the notebook's user namespace dictionary to look up values for all variables in the namespace. If your calculations are re-using variable names throughout the notebook, then the dictionary entry for that name may not be what you think it is when you run cells out of the order originally intended.

You _can_ re-use variable names to good effect throughout a notebook, _IFF_ the cells are run in the correct order (easier if this is just top to bottom). 

**On this note: if you are using `handcalcs` for any kind of reporting that may become a legal document (e.g. design engineering calculations), it is up to YOU to ensure that the results are what you expect them to be. `handcalcs` is free and open-source software and the author(s) are not responsible for incorrect calculations that result from its use.**

That being said, the very purpose for the way `handcalcs` renders its math is to make it very easy to confirm and verify calculations by hand.

## YouTube Tutorials

**Getting Started with handcalcs (assumes zero Python knowledge)**

[https://www.youtube.com/watch?v=ZNFhLCWqA_g](https://www.youtube.com/watch?v=ZNFhLCWqA_g)

**Engineering Calculations: handcalcs-on-Jupyter vs. Excel**

[https://www.youtube.com/watch?v=n9Uzy3Eb-XI](https://www.youtube.com/watch?v=n9Uzy3Eb-XI)

## Applications and Compatibility with OPP (Other People's Packages)

** Please see [the wiki](https://github.com/connorferster/handcalcs/wiki) for applications of `handcalcs` in education and engineering, in addition to examples of using `handcalcs` with other Python libraries such [streamlit](https://github.com/connorferster/handcalcs/wiki/Handcalcs-on--Streamlit) and [papermill](https://github.com/connorferster/handcalcs/wiki/Handcalcs-on-Papermill).
