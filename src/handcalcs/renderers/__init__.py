from .base import BaseRenderer, get_renderer
from .plaintext import PlainTextRenderer
from .html import HTMLRenderer
from .latex import LatexRenderer
from .markdown import MarkdownRenderer
# The ExcelRenderer imports XlsxWriter only when it writes a workbook, so it is
# always importable (and registered as 'excel').
from .excel import ExcelRenderer
