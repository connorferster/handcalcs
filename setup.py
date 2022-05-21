#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the 'upload' functionality of this file, you must:
#   $ pipenv install twine --dev

import io
import os
import sys
from shutil import rmtree

from setuptools import find_packages, setup, Command

# Package meta-data.
NAME = 'handcalcs'
DESCRIPTION = 'Converts your Python calculation script into beautifully rendered Latex, similar to how you would write a calculation by hand.'
URL = 'https://github.com/connorferster/handcalcs'
EMAIL = 'connorferster@gmail.com'
AUTHOR = 'Connor Ferster'
REQUIRES_PYTHON = '>=3.7.0'
VERSION = '1.4.0'

# What packages are required for this module to be executed?
REQUIRED = [
    'pyparsing',
    'nbconvert>=6.0.0',
    'innerscope >= 0.2.0',
    'more-itertools >= 8.5.0',
    'jupyterlab >= 3.0.0'
    # 'requests', 'maya', 'records',
]

# What packages are optional?
EXTRAS = {
    # 'fancy feature': ['django'],
}

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    project_slug = NAME.lower().replace("-", "_").replace(" ", "_")
    with open(os.path.join(here, project_slug, '__version__.py')) as f:
        exec(f.read(), about)
else:
    about['__version__'] = VERSION


# Where the magic happens:
setup(
    name=NAME,
    version=about['__version__'],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    package_data={'': ['*.json']},
    include_package_data=True,
    entry_points={
        'nbconvert.exporters': [
            'HTML_noinput = handcalcs.exporters:HTMLHideInputExporter',
            'PDF_noinput = handcalcs.exporters:PDFHideInputExporter',
            'LaTeX_noinput = handcalcs.exporters:LatexHideInputExporter',
        ],
    },

    install_requires=REQUIRED,
    extras_require=EXTRAS,
    license='Apache',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 3 - Alpha",
        "Topic :: Scientific/Engineering :: Mathematics",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
