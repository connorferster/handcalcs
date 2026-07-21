import pathlib
from typing import Optional
from .parsing.sequence import HcSequence
from .renderers.plain_text.renderer import PlainTextRenderer



class HandCalcs:

    def __init__(self, renderer = PlainTextRenderer()):
        self.renderer = renderer
        self.hc_ast = None

    
    def __call__(self, source_or_path: str | pathlib.Path, supplied_globals: Optional[dict] = None, supplied_locals: Optional[dict] = None) -> str:
        """
        Parses the data from 'filepath' and creates a HandCalcs object.

        If 'supplied_globals' and 'supplied_locals' are each None, then the source code will be executed to
        create the globals and locals dicts. If either dictionary are supplied, code execution will not occur.
        Empty dictionaries are acceptable but will produce numerical substitutions of 'NoValue()'.
        """
        if isinstance(source_or_path, pathlib.Path):
            with open(source_or_path, 'r') as file:
                source = file.read()
        elif isinstance(source_or_path, str):
            source = source_or_path
        else:
            raise TypeError(
                "'source_or_path' must be either a string representing Python source code "
                f"or a pathlib.Path object to an existing .py file, not {type(source_or_path)}"
            )
        if supplied_globals is None and supplied_locals is None:
            supplied_globals = {}
            supplied_locals = {}
            exec(source, supplied_globals, supplied_locals)
            
        self.hc_ast = HcSequence.from_source(source, hc_globals=supplied_globals, hc_locals=supplied_locals)
        
        return self.renderer.render(self.hc_ast)

    def __repr__(self):
        return f"HandCalcs(renderer={self.renderer}())"
        