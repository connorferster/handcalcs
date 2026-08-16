import argparse

command_parser = argparse.ArgumentParser()

command_parser.add_argument("-m", "--multiline", "--mult", action="store_true")
command_parser.add_argument("-f", "--format")
command_parser.add_argument("-w", "--if-winner-only", "--winner", action="store_false")
command_parser.add_argument("-i", "--ignore", action="store_true")
command_parser.add_argument("-p", "--param-line", action="store_true")
