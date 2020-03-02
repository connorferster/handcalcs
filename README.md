# handcalcs: Your Python code as beautifully formatted latex math.



`handcalcs` is a library designed for working engineers and educators who want
their Python code to present as a finished calculation PDF report, just like you it
would be if you had written it out by hand.

The purpose of this library is to allow you to simply write the calculation logic
without having to painstakingly format it as a report, much like you might have
to do if you were to program your calculation as an Excel spreadsheet or as a
MathCAD document.

Intended users: working engineers, teachers, and students who want to
focus on simply writing the calculation code and to have formatting just be "taken
care of".

## Examples of use:

<img src = "https://github.com/connorferster/forallpeople/blob/master/Jupyter_example.PNG">


## Installing

You can install using pip:

`pip install handcalcs`

## External requirements

Printing to PDF requires you to have a Latex environment with pdflatex installed
on your system and to have `pdflatex` available on your `PATH` so that you can run
`pdflatex` as a command from your terminal.

### Windows installation of latex

### OSX installation of latex

### Linux installation of latex

## Additional system setup (Optional, but convenient)



## Basic usage

The most basic use is just to import the library:

`import handcalcs as hand`


## API

Each `Physical` instance offers the following methods and properties:

### Properties

* `.value`: A `float` that represents the numerical value of the physical quantity in SI base units
* `.dimensions`: A `Dimensions` object (a `NamedTuple`) that describes the dimension of the quantity as a vector
* `.factor`: A `float` that represents a factor that the value should be multiplied by to linearly scale the quantity into an alternate unit system (e.g. US customary units or UK imperial) that is defined in SI units.
* `.latex`: A `str` that represents the pretty printed `repr()` of the quanity in latex code.
* `.html`: A `str` that represents the pretty printed `repr()` of the quantity in HTML code.
* `.repr`: A `str` that represents the traditional machine readable `repr()` of the quantity: `Physical` instances default to a pretty printed `__repr__()` instead of a machine readable `__repr__()` because it makes them more compatible with other libraries (e.g. `numpy`, `pandas`, [handcalcs](https://github.com/connorferster/handcalcs), and `jupyter`).

### Methods

Almost all methods return a new `Physical` because all instances are **immutable**.

* `.round(self, n: int)`: Returns a `Physical` instance identical to `self` except with the display precision set to `n`. You can also call the python built-in `round()` on the instance to get the same behaviour.
* `.sqrt(self, n: float)`: Returns a `Physical` that represents the square root of `self`. `n` can be set to any other number to compute alternate roots.
* `.split(self)`: Returns a 2-tuple where the 0-th element is the `.value` of the quantity and the 1-th element is the `Physical` instance with a value set to `1` (i.e. just the dimensional part of the quantity). To reconstitute, multiply the two tuple elements together. This is useful to perform computations in `numpy` that only accept numerical input (e.g. `numpy.linalg.inv()`): the value can be computed separately from the dimension and then reconstituted afterwards.
* `.in_units(self, unit_name: str = "")`: Returns a new `Physical` instance with a `.factor` corresponding to a dimensionally compatible unit defined in the `environment`. If `.in_units()` is called without any arguments, then a list of available units for that quantity is printed to `stdout`.
