import argparse

command_parser = argparse.ArgumentParser()

command_parser.add_argument("-m", "--multiline", "--mult", action="store_true")
command_parser.add_argument("-l", "--singleline", "--single", action="store_false")
command_parser.add_argument("-f", "--sigfigs", "--sf")
command_parser.add_argument("-d", "--sigdigs", "--sd")
command_parser.add_argument(
    "-e", "--scientific-notation", "--scinot", action="store_true"
)
command_parser.add_argument("-c", "--if-cases", "--cases", action="store_true")
command_parser.add_argument("-w", "--if-winner-only", "--winner", action="store_false")
command_parser.add_argument(
    "-r", "--render-block-comments", "--comments", action="store_false"
)
