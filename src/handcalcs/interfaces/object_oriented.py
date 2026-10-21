import os
import pathlib
import warnings
from typing import Any, Optional
from ..parsing.sequence import HcSequence
from ..parsing.inputs import InputBinding
from ..parsing import line_values
from ..renderers import BaseRenderer, get_renderer
from ..renderers import demo
from .. import config


class HandCalcs:

    def __init__(self, renderer=None):
        if renderer is None:
            renderer = self.__default_renderer()
        self.renderer = renderer
        # Global config settings (format_code + any custom fields) seed the render
        # context of every HandCalcs instance, whatever renderer is used. The
        # renderer-selection options are not render settings and are excluded here.
        self._context_settings = {
            key: value
            for key, value in config.get_config().items()
            if key not in config.NON_CONTEXT_OPTIONS
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

    def __call__(
        self,
        source_or_path: str | pathlib.Path,
        supplied_globals: Optional[dict] = None,
        supplied_locals: Optional[dict] = None,
        *,
        inputs: Optional[dict] = None,
        strict: bool = True,
        allow_computed: bool = False,
        destination: Optional[str | os.PathLike] = None,
    ) -> Any:
        """
        Renders 'source_or_path' and returns what the renderer produces: a str
        for the text renderers, a document or workbook for the Word and Excel
        renderers.

        If 'destination' is given, the render is written to that file instead
        (with the renderer's 'to_file': a complete LaTeX or HTML document, or the
        saved .docx or .xlsx) and its path is returned as a pathlib.Path.

        If 'supplied_globals' and 'supplied_locals' are each None, then the source code will be executed to
        create the globals and locals dicts. If either dictionary are supplied, code execution will not occur.
        Empty dictionaries are acceptable but will produce numerical substitutions of 'NoValue()'.

        'inputs' maps names to values that replace the values the source assigns them
        (see handcalcs.parsing.inputs.bind_inputs, which also describes 'strict' and
        'allow_computed'); the source is then executed with them. A number replaces only
        the number of a value with units, so 'L = 6 * m' with inputs={"L": 8} renders
        and runs as 'L = 8 * m'. A quantity is converted to the units of such a line,
        so with inputs={"L": 8000 * mm} it runs and renders as 'L = 8 * m' too. Other
        objects (arrays, quantities on a line without units) are used as they are.
        """
        source = self.__read(source_or_path)
        if inputs is not None:
            if supplied_globals is not None:
                raise TypeError(
                    "'inputs' cannot be combined with 'supplied_globals': a supplied "
                    "namespace is used without executing the source, and inputs only "
                    "take effect when it is executed."
                )
            binding = InputBinding(
                source, inputs, strict=strict, allow_computed=allow_computed
            )
            passed_globals, values = self.__evaluate(
                binding.exec_source, binding.namespace()
            )
            rendered = self.render_bound(binding, passed_globals, values)
            return self.__output(rendered, destination)
        passed_globals, values = supplied_globals, None
        if supplied_globals is None:
            passed_globals, values = self.__evaluate(source)
        self.hc_ast = self.__parse(source, passed_globals, line_values=values)
        return self.__output(self.__render(passed_globals), destination)

    def render_run(
        self,
        source: str,
        namespace: dict,
        values: Optional[line_values.LineValues] = None,
    ) -> Any:
        """
        Renders 'source' once it has run in 'namespace', with the 'values'
        recorded while it ran (see handcalcs.parsing.line_values). The
        '%%render' magic runs the cell itself and renders it with this.
        """
        self.hc_ast = self.__parse(source, namespace, line_values=values)
        return self.__render(namespace)

    def render_bound(
        self,
        binding: InputBinding,
        namespace: dict,
        values: Optional[line_values.LineValues] = None,
    ) -> str:
        """
        Renders the source of 'binding' once its 'exec_source' has run in
        'namespace' (which started as 'binding.namespace()'), with the 'values'
        recorded while it ran. The '%%render inputs=...' magic runs the cell
        itself and renders it with this.
        """
        source = binding.parse_source(namespace)
        self.hc_ast = self.__parse(source, namespace, line_values=values)
        binding.place_objects(self.hc_ast)
        return self.__render(namespace)

    def __render(self, passed_globals: dict) -> str:
        base_context = self.renderer.create_context(
            **(self._context_settings | {"global_ns": passed_globals})
        )
        rendered_tree = self.renderer.render(self.hc_ast, base_context)
        completed_render = self.renderer.complete(rendered_tree, base_context)
        return completed_render

    def __output(self, rendered: Any, destination: Optional[str | os.PathLike]) -> Any:
        """'rendered' itself, or the path of the file it is written to."""
        if destination is None:
            return rendered
        return self.renderer.to_file(rendered, destination)

    def demo(self, destination: Optional[str | os.PathLike] = None):
        """
        Renders the demo with the current renderer; with 'destination', writes it
        to that file and returns the path, as calling the object does.

        A renderer that cannot render the general demo (e.g. the ExcelRenderer,
        which has no worksheet form for loops or collections) provides its own
        source as a ``demo_source`` attribute, which is used instead.
        """
        source = self.__read(getattr(self.renderer, "demo_source", None) or demo.source)
        eval_globals, values = self.__evaluate(source)
        demo_ast = self.__parse(source, eval_globals, line_values=values)
        base_context = self.renderer.create_context(
            **(self._context_settings | {"global_ns": eval_globals})
        )
        rendered_tree = self.renderer.render(demo_ast, base_context)
        completed_render = self.renderer.complete(rendered_tree, base_context)
        # demo() returns the completed render (renderer.complete()), matching
        # calculate(); for the ASCIIRenderer that is the joined text.
        return self.__output(completed_render, destination)

    def __repr__(self):
        return f"HandCalcs(renderer={self.renderer}())"

    def __read(
        self,
        source_or_path: str | pathlib.Path,
        supplied_globals: Optional[dict] = None,
        supplied_locals: Optional[dict] = None,
    ):
        if isinstance(source_or_path, pathlib.Path):
            with open(source_or_path, "r", encoding="utf-8") as file:
                source = file.read()
        elif isinstance(source_or_path, str):
            source = source_or_path
        else:
            raise TypeError(
                "'source_or_path' must be either a string representing Python source code "
                f"or a pathlib.Path object to an existing .py file, not {type(source_or_path)}"
            )
        return source

    def __evaluate(self, source, namespace: Optional[dict] = None):
        """
        Runs 'source' in a copy of 'namespace' and returns the namespace and the
        values recorded line by line while it ran (None with the 'line_values'
        option off: the source runs with a single exec).
        """
        eval_globals = dict(namespace or {})
        if not config.get_option("line_values", True):
            exec(source, eval_globals)
            return eval_globals, None
        values = line_values.run(source, eval_globals)
        return eval_globals, values

    def __parse(
        self,
        source: str,
        supplied_globals: Optional[dict] = None,
        supplied_locals: Optional[dict] = None,
        line_values: Optional[line_values.LineValues] = None,
    ):
        if supplied_globals is None:
            supplied_globals = {}
        if supplied_locals is None:
            supplied_locals = {}

        hc_ast = HcSequence.from_source(
            source,
            hc_globals=supplied_globals,
            hc_locals=supplied_locals,
            line_values=line_values,
        )
        return hc_ast
