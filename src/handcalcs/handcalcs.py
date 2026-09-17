import pathlib
from typing import Optional
from .parsing.sequence import HcSequence
from .renderers import BaseRenderer
from .renderers import demo



class HandCalcs:

    def __init__(self, renderer = BaseRenderer()):
        self.renderer = renderer
        self.hc_ast = None

    
    def __call__(self, source_or_path: str | pathlib.Path, supplied_globals: Optional[dict] = None, supplied_locals: Optional[dict] = None) -> str:
        """
        Parses the data from 'filepath' and creates a HandCalcs object.

        If 'supplied_globals' and 'supplied_locals' are each None, then the source code will be executed to
        create the globals and locals dicts. If either dictionary are supplied, code execution will not occur.
        Empty dictionaries are acceptable but will produce numerical substitutions of 'NoValue()'.
        """
        source = self.__read(source_or_path)
        passed_globals = supplied_globals
        if supplied_globals is None:
            passed_globals = self.__evaluate(source)
        self.hc_ast = self.__parse(source, passed_globals)
        rendered_tree = self.renderer.render(self.hc_ast)
        return self.renderer.join(rendered_tree)

    def demo(self):
        """
        Renders the demo with the current renderer
        """
        source = self.__read(demo.source)
        eval_globals = self.__evaluate(source)
        demo_ast = self.__parse(source, eval_globals)
        rendered_tree = self.renderer.render(demo_ast)
        return rendered_tree




    def __repr__(self):
        return f"HandCalcs(renderer={self.renderer}())"
        
        
    def __read(self, source_or_path: str | pathlib.Path, supplied_globals: Optional[dict] = None, supplied_locals: Optional[dict] = None): 
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
        return source
        
    def __evaluate(self, source):
        eval_globals = eval_locals = {}
        exec(source, eval_globals, eval_locals)
        return eval_globals
        
        
    def __parse(self, source: str, supplied_globals: Optional[dict] = None, supplied_locals: Optional[dict] = None):
        if supplied_globals is None:
            supplied_globals = {}
        if supplied_locals is None:
            supplied_locals= {}
    
        hc_ast = HcSequence.from_source(source, hc_globals=supplied_globals, hc_locals=supplied_locals)
        return hc_ast
    
    
