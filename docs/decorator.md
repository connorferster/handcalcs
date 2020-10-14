# Function decorator: `@handcalc()`

_Shout-out to @eriknw for developing [innerscope](https://github.com/eriknw/innerscope) and proactively integrating it into `handcalcs`. Thank you!_

Start by importing the `@handcalc()` decorator:

```python
from handcalcs.decorator import handcalc
```

## Decorator arguments
All arguments are optional with defaults shown below:

```python
@handcalc([
    override: str = "", 
    precision: int = 3, 
    left: str = "", 
    right: str = "",
    dec_sep: str = ".",
    jupyter_display: bool = False
    ])
```

A decorated function returns a 2-tuple with the following elements:

1. A `str` representing the function source as Latex code 
2. The return value of the function

If a return value is not specified in the function, then the function will return a `dict` representing the function's local namespace.

## Argument descriptions

* `override`: a `str` being one of `"params"`, `"symbolic"`, `"short"`, or `"long"`. See [override tags](../overrides.md) for more information.
* `precision`: an `int` to alter the of decimal precision displayed
* `left`: a `str` to prepend to the returned Latex string. Intended to be used to define the start of a Latex math environment (e.g. `"$"` or `"\\["`)
* `right`: a `str` to append to the returned Latex string. Intended to be used to define the end of a Latex math environment (e.g. `"$"` or `"\\]"`)
* `dec_sep`: a `str` to replace `.` as the decimal separator for rendered values (e.g. `,`)
* `jupyter_display`: a `bool` that, when True, will attempt to render the Latex string with `display(Latex(latex_code))` from `IPython.display`. The decorated function will only return the function's original return value (i.e. only the second element of the tuple). 
Will return an error if not used within a Jupyter environment.

In your decorated function, everything between `def my_calc(...)` and a return statement (if any) is now like the code in a Jupyter cell, except it's a standard Python function.

Used in this way, you can use `@handcalc()` to dynamically generate Latex code for display in Jupyter and non-Jupypter Python environments (e.g. streamlit). 

![Decorator example image](../images/decorator.png)