import pathlib
import warnings
from typing import Optional
from .parsing.sequence import HcSequence
from .renderers import BaseRenderer, get_renderer
from .renderers import demo
from . import config



class HandCalcs:

    def __init__(self, renderer = None):
        if renderer is None:
            renderer = self.__default_renderer()
        self.renderer = renderer
        # Global config settings (format_code + any custom fields) seed the render
        # context of every HandCalcs instance, whatever renderer is used. Only
        # 'default_renderer' is specific to bare instantiation and is excluded here.
        self._context_settings = {
            key: value
            for key, value in config.get_config().items()
            if key != "default_renderer"
        }
        self.hc_ast = None

    @staticmethod
    def __default_renderer():
        """
        Instantiate the renderer named by the 'default_renderer' global config
        option. If that name is not registered (e.g. a custom renderer whose module
        has not been imported), warn and fall back to BaseRenderer.
        """
        name = config.get_option("default_renderer", "base")
        renderer_cls = get_renderer(name)
        if renderer_cls is None:
            warnings.warn(
                f"Configured default_renderer '{name}' is not a registered renderer; "
                "falling back to BaseRenderer. If it is a custom renderer, ensure its "
                "module is imported before instantiating HandCalcs()."
            )
            renderer_cls = BaseRenderer
        return renderer_cls()

    
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
        base_context = self.renderer.create_context(**self._context_settings)
        rendered_tree = self.renderer.render(self.hc_ast, base_context)
        completed_render = self.renderer.complete(rendered_tree, base_context)
        return completed_render


    def demo(self):
        """
        Renders the demo with the current renderer
        """
        source = self.__read(demo.source)
        eval_globals = self.__evaluate(source)
        demo_ast = self.__parse(source, eval_globals)
        base_context = self.renderer.create_context(**self._context_settings)
        rendered_tree = self.renderer.render(demo_ast, base_context)
        completed_render = self.renderer.complete(rendered_tree, base_context)
        return completed_render


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
    
    
