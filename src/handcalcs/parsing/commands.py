import argparse

# add_help=False frees ``-h`` for the params-block command (this parser reads
# ``# hc:`` comments, never a real command line).
command_parser = argparse.ArgumentParser(add_help=False)

command_parser.add_argument("-m", "--multiline", "--mult", action="store_true")
command_parser.add_argument("-f", "--format-code")
command_parser.add_argument("-w", "--if-winner-only", "--winner", action="store_false")
command_parser.add_argument("-i", "--ignore", action="store_true")
command_parser.add_argument("-p", "--param-line", action="store_true")
command_parser.add_argument("-b", "--line-break", action="store_true")
command_parser.add_argument("-c", "--param-cols", "--param_cols", type=int)

command_parser.add_argument("-h", "--params-block", "--params", action="store_true")
