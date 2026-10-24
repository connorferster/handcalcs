from .base import BaseRenderer, get_renderer
from .ascii import ASCIIRenderer
from .html import HTMLRenderer
from .latex import LatexRenderer
from .markdown import MarkdownRenderer

# The ExcelRenderer imports XlsxWriter only when it writes a workbook, so it is
# always importable (and registered as 'excel').
from .excel import ExcelRenderer

# The WordRenderer imports python-docx only when it builds a document, so it is
# always importable (and registered as 'word').
from .word import WordRenderer
