from dataclasses import dataclass
from handcalcs import global_config
from handcalcs.ast_parser import ast_parse
from ast_comments import parse

@dataclass
class HandcalcsCell:
    def __init__(self, source: str, globals: dict, function_recurse_limit: int = 3):
        self.source = source
        self.globals = globals
        self.frl = function_recurse_limit
        self.ast_tree = None
        self.hc_tree = None
        self.global_config = global_config._config
        # self.override_precision = line_args["precision"]
        # self.override_scientific_notation = line_args["sci_not"]
        # self.override_commands = line_args["override"]

    def parse(self):
        self.ast_tree = parse(self.source)
        self.hc_tree = ast_parse(self.ast_tree, self.frl)

    def convert(self):
        self.transformed_tree = transform_tree(self.hc_tree, self.globals, self.global_config)

    def format(self):
        self.latex_str = format_tree(self.transformed_tree)

    def __call__(self):
        self.parse()
        self.convert()
        self.format()
        return self.latex_str