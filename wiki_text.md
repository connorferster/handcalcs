## This seems like a lot of effort to write yet _another_ software to render math. Haven't you ever heard of Excel/Maple/MathCAD/Mathematica/MATLAB/Octave/SMATH Studio?

SMath Studio is excellent software and I highly recommend it. Octave is also great.

Many of these softwares are proprietary.

They do not show numeric substitutions. 

They do not auto-format your calculations. 

Many are not as extensible as `handcalcs` because they are not a part of the amazing python eco-system <3

## Printing to PDF with Latex

Printing to PDF requires you to have a Latex environment installed
on your system and to have a Latex compiler available on your system's `PATH` variable so Jupyter can execute `xelatex` on a command line.

Following an installation, you can open up a command line on your system and type `xelatex`. If the installation was successful and complete, the command will enter you into a Latex prompt instead of generating an error message.

### Latex for Windows

Installation on Windows is easiest by installing the TeX distribution, [MiKTeX](https://miktex.org/howto/install-miktex).
After installation, ensure that you allow automatic downloading of required
to make operation easiest.

### Latex for OSX

Installation on Mac OS X is easiest by installing [MacTeX](http://www.tug.org/mactex/mactex-download.html).

Be sure to read the installation page to prevent/assist with any issues.

### Latex for Linux

`$ sudo apt install texlive-latex-extra`
