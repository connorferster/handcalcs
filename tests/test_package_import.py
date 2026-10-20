"""
``import handcalcs`` must work without IPython (it is an optional dependency)
and in a plain Python process with IPython installed. Each case runs in a fresh
interpreter so the import is not already cached.
"""
import subprocess
import sys
import textwrap


def run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)], capture_output=True, text=True
    )


def test_import_without_ipython():
    # A None entry in sys.modules makes ``import IPython`` raise ImportError.
    result = run(
        """
        import sys
        sys.modules["IPython"] = None
        import handcalcs
        from handcalcs import HandCalcs, ASCIIRenderer
        print(HandCalcs(ASCIIRenderer())("a = 2\\nb = a * 3"))
        print(hasattr(handcalcs, "render"))
        """
    )
    assert result.returncode == 0, result.stderr
    assert "b = a * 3 = 2 * 3 = 6" in result.stdout
    assert result.stdout.strip().endswith("False")


def test_import_with_ipython_outside_a_shell():
    # IPython installed but no running shell: the %%render magic is not loaded.
    result = run(
        """
        import handcalcs
        print(hasattr(handcalcs, "render"))
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"
