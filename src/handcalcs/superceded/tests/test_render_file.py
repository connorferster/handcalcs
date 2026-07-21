import handcalcs
import pytest


from IPython.testing.globalipapp import start_ipython


@pytest.fixture(scope="session")
def session_ip():
    return start_ipython()


@pytest.fixture(scope="function")
def ip(session_ip):
    # yield session_ip
    session_ip.run_line_magic(magic_name="load_ext", line="handcalcs.render")
    yield session_ip
    # session_ip.run_line_magic(magic_name="unload_ext", line="handcalcs.render")
    session_ip.run_line_magic(magic_name="reset", line="-f")


def test_render(ip):
    output = ip.run_cell_magic(magic_name="render", line="_testing", cell="x = 99")
    assert output == "\\[\n\\begin{aligned}\nx &= 99 \\; \n\\end{aligned}\n\\]"


def test_tex(ip):
    output = ip.run_cell_magic(magic_name="tex", line="_testing", cell="x = 99")
    assert output == "\\[\n\\begin{aligned}\nx &= 99 \\; \n\\end{aligned}\n\\]"


def test_parse_line_args():
    assert handcalcs.render.parse_line_args("params 5") == {
        "override": "params",
        "precision": 5,
        "sympy": False,
        "sci_not": None,
    }
    assert handcalcs.render.parse_line_args("symbolic") == {
        "override": "symbolic",
        "precision": None,
        "sympy": False,
        "sci_not": None,
    }
    assert handcalcs.render.parse_line_args("short long 3") == {
        "override": "long",
        "precision": 3,
        "sympy": False,
        "sci_not": None,
    }
    assert handcalcs.render.parse_line_args("symbolical, 1 sci_not") == {
        "override": "",
        "precision": 1,
        "sympy": False,
        "sci_not": True,
    }
