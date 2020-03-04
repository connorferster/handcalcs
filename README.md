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

## Installing

You can install using pip:

`pip install handcalcs`

### External requirements

Printing to PDF requires you to have a Latex environment with pdflatex installed
on your system and to have `pdflatex` available on your `PATH` so that you can run
`pdflatex` as a command from your terminal.

#### Windows installation of latex

Installation on Windows is easiest by installing the TeX distribution, [MiKTeX](https://miktex.org/howto/install-miktex).
After installation, ensure that you allow automatic downloading of required
to make operation easiest.

#### OSX installation of latex

Installation on Mac OS X is easiest by installing [MacTeX](http://www.tug.org/mactex/mactex-download.html).
Be sure to read the installation page to prevent/assist with any issues.

#### Linux installation of latex

`$ sudo apt install texlive-latex-extra`
You can also refer to [this page](https://linuxconfig.org/how-to-install-latex-on-ubuntu-18-04-bionic-beaver-linux) to review all of the options available for the
TeXLive installation.

### Additional system setup (Optional, but convenient)

`handcalcs` uses the Python import system to import any calculation scripts that
create. Therefore its best to setup your system to make it easy to put new scripts
into your Python path.

1. Create a "calcs" folder you where you will begin building your calculation library. This can be anywhere on your system you like and can have any name.
2. Copy the absolute path of your folder and paste it into a blank text file. Save that file as a `.pth` file and save it in your Python `site-packages` directory. You can find your `site-packages` directory by typing `python -m site` in your command line. Note: This requires `python` to be in your system's PATH variable. (i.e. you have to be able to launch Python by typing `python` in a terminal).
3. In your new "calcs" folder, create a blank text file and name it `__init__.py`. Within that file, insert the following:

```python

from os.path import dirname, basename, isfile
import glob
modules = glob.glob(dirname(__file__)+"/*.py")
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]
from . import *
```

This will allow you to create subfolders in your "calc" folder so you can organize your calculation scripts more conveniently. For every folder you create with its own subfolders, include a copy of the same `__init__.py` file in the folder.

## Basic usage

The most basic use is just to import the library:

```
>>> import handcalcs as hand
>>> bending_resistance = hand.Calc("calcs.wood.timber.mr") # Loads calcs/wood/timber/mr.py, my pre-written script
>>> bending_resistance.inputs # Remind yourself what the function parameters are for your script
<Signature (b, d, f_b, K_Zb, K_L, K_D, K_H, K_Sb, K_T, phi=0.9)>

>>> results = bending_resistance(300, 1200, 19.2, 1, 1, 1, 1, 1, 1) # Calc object is now a callable function based on your script
>>> results # The Calc object returns a dict with all of the intermediate values of your script included
{'b': 300, 'd': 1200, 'f_b': 19.2, 'K_Zb': 1, 'K_L': 1, 'K_D': 1, 'K_H': 1, 'K_Sb': 1, 'K_T': 1, 'phi': 0.9, 'F_b': 19.2, 'S': 72000000.0, 'M_r': 1244160000.0}

>>> bending_resistance.print(filename = "Bending Resistance Results")
"handcalcs: Latex rendering complete."

>>> print(bending_resistance._source)
def main(b, d, f_b, K_Zb, K_L, K_D, K_H, K_Sb, K_T, phi = 0.9):
    # Cl. 6.5.4.1 General Bending Moment Resistance
    ## Parameters
    phi = 0.9

    ## Specified strength in bending
    F_b = f_b * (K_D*K_H*K_Sb*K_T)

    ## Section Modulus
    S = (b * d**2) / 6

    ## Moment resistance
    M_r = phi * F_b * S * K_Zb * K_L
    return locals()
```


The PDF file that is created from `.print()` is created directly from the source
code of the script, as seen below.

<img src = "https://github.com/connorferster/handcalcs/blob/master/rendered_latex_pdf_example.png">

## API



### Properties


### Methods
