# Override tags
In both the cell magic and decorator APIs, you can use "override tags" to alter the behaviour and display of your calculations. They work the same way in both APIs.

There are currently four + one acceptable override tags:

1. `params`
2. `symbolic`
3. `long`
4. `short`

Additionally, there is the `sympy` tag.

Override tags 1-4 are mutually exclusive, you can only use one tag at a time, e.g. `params` or `short` not `params short`. 

However, you can use the `sympy` tag alongside one of the tags 1-4 to combine their behaviours.

Last, you can also include an integer

# Override tag behaviour
The following are demonstrations and examples of how each override tag works with a brief discussion on when you may use one or another.

## `params`
Use `params` when you want to display a quantity of variables. 

Typically, handcalcs will display calculations vertically, one after another. By using `params`, the variables will be arranged in three columns (to save vertical space) and will be in the format of `var = value` without showing any formulas or numeric substitutions other than the final result.

**Example:**
![Example showing the params override tag](../images/params.png)

## `symbolic`
Use `symbolic` when you want to display only the symbolic representation of your calculations, without any numeric substitution. 

Using symbolic can be handy when you want to keep your document less cluttered. Final values can then displayed in a separate cell afterwards.#

**Example:**
![Example showing the symbolic override tag](../images/symbolic1.png)
![Example showing the symbolic override tag](../images/symbolic2.png)

## `long`
Use `long` when you have a calculation that's _too long_ to fit on one line and you want to break up the calculation over three lines. 

handcalcs makes an attempt to figure out if your calculation is too long and, if so, it will apply the `long` style formatting to that line on it is own. However, you can use `long` to force this formatting style in all calculations in the cell.

**Example:**
![Example showing the long override tag](../images/long1.png)
![Example showing the long override tag](../images/long2.png)

## `short`
Use `short` when you have a calculation that is erroneously being interpreted by handcalcs as a "long" format line and you want to force it to render on one line, instead of over three lines. 

handcalcs makes an attempt to figure out if your calculation is too long and, if so, it will apply the `long` style formatting to that line on it is own. However, sometimes it gets it wrong. The `short` tag is a way you can force your calculations into the default "short" format.

**Example:**
![Example showing the short override tag](../images/short1.png)
![Example showing the short override tag](../images/short2.png)

## `sympy`
Use `sympy` if you want to combine a sympy symbolic workflow with a handcalcs numeric substitution and rendering. The `sympy` tag can be combined with one of the other override tags to control the rendering in the cell.

There is a bit of nuanced approach to have a smooth workflow. See the [Using Sympy](sympy.md) section for more information. 

**Example:**
![Example showing the short override tag](../images/sympy1.png)
![Example showing the short override tag](../images/sympy2.png)