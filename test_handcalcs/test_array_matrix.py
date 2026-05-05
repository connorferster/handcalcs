"""
Tests for 1D array and 2D matrix rendering in handcalcs.

Covers:
  - _is_2d_array helper
  - render_array (1D sequences)
  - render_matrix (2D sequences / matrices)
  - latex_repr dispatch order (sympy before array)
  - convert_parameter extract-restore guard
  - set_truncation helper (int and tuple)
  - truncation config shared by both paths
  - matrix_environment config
  - optional numpy and pint support
"""

import pytest
from collections import deque
from handcalcs.handcalcs import (
    latex_repr,
    _is_2d_array,
    set_truncation,
    ParameterLine,
    convert_parameter,
)
from handcalcs import global_config


# ── helpers ───────────────────────────────────────────────────────────────────

def lr(item, *, precision=3):
    """Call latex_repr with the standard test defaults."""
    return latex_repr(
        item,
        use_scientific_notation=False,
        precision=precision,
        preferred_formatter="L",
    )


@pytest.fixture()
def array_config():
    """Yield a setter for array/matrix config keys; original values restored on teardown.

    Uses set_truncation / direct dict access so both int and tuple values are
    accepted without triggering set_option's type check.
    """
    keys = ("array_truncate_threshold", "array_truncate_end", "matrix_environment")
    orig = {k: global_config._config[k] for k in keys}

    def _set(key, val):
        if key in ("array_truncate_threshold", "array_truncate_end"):
            set_truncation(**{
                "threshold" if key == "array_truncate_threshold" else "end": val
            })
        else:
            global_config.set_option(key, val)

    yield _set
    # Restore originals via set_truncation so int↔tuple round-trip works
    set_truncation(
        threshold=orig["array_truncate_threshold"],
        end=orig["array_truncate_end"],
    )
    global_config.set_option("matrix_environment", orig["matrix_environment"])


@pytest.fixture()
def pint_ureg():
    """Skip the test if pint is not installed; otherwise return a UnitRegistry."""
    pint = pytest.importorskip("pint")
    ureg = pint.UnitRegistry(auto_reduce_dimensions=True)
    ureg.default_format = "~"
    return ureg


# ── _is_2d_array ──────────────────────────────────────────────────────────────

class TestIs2DArray:

    @pytest.mark.parametrize("value", [
        [[1, 2], [3, 4]],
        [[1.0, 2.0], [3.0, 4.0]],
        [[1], [2], [3]],       # column vector
        [[1, 2, 3]],           # row vector
    ])
    def test_list_of_lists_is_2d(self, value):
        assert _is_2d_array(value)

    @pytest.mark.parametrize("value", [
        [1, 2, 3],
        [1.0, 2.0],
        [],
        "hello",
        {"a": 1},
        ["a", "b"],            # list of strings → not 2D
        42,
    ])
    def test_non_2d_inputs(self, value):
        assert not _is_2d_array(value)

    def test_numpy_2d(self):
        np = pytest.importorskip("numpy")
        assert _is_2d_array(np.array([[1, 2], [3, 4]]))

    def test_numpy_1d(self):
        np = pytest.importorskip("numpy")
        assert not _is_2d_array(np.array([1, 2, 3]))

    def test_numpy_0d(self):
        np = pytest.importorskip("numpy")
        assert not _is_2d_array(np.array(5))


# ── 1D array rendering ────────────────────────────────────────────────────────

class TestRenderArray:

    def test_integers(self):
        assert lr([1, 2, 3]) == "[1,\\ 2,\\ 3]"

    def test_floats(self):
        assert lr([1.0, 2.0, 3.0]) == "[1.000,\\ 2.000,\\ 3.000]"

    def test_empty(self):
        assert lr([]) == "[]"

    def test_single_element(self):
        assert lr([7]) == "[7]"

    def test_numpy_1d(self):
        np = pytest.importorskip("numpy")
        assert lr(np.array([1.0, 2.0, 3.0])) == "[1.000,\\ 2.000,\\ 3.000]"

    # truncation ---------------------------------------------------------------

    def test_truncation(self, array_config):
        array_config("array_truncate_threshold", 6)
        array_config("array_truncate_end", 2)
        assert lr(list(range(10))) == "[0,\\ 1,\\ 2,\\ 3,\\ \\ldots,\\ 8,\\ 9]"

    def test_truncation_threshold_disabled(self, array_config):
        array_config("array_truncate_threshold", -1)
        assert lr(list(range(7))) == "[0,\\ 1,\\ 2,\\ 3,\\ 4,\\ 5,\\ 6]"

    def test_no_truncation_when_at_threshold(self, array_config):
        """An array exactly at the threshold should not be truncated."""
        array_config("array_truncate_threshold", 5)
        array_config("array_truncate_end", 2)
        assert lr([1, 2, 3, 4, 5]) == "[1,\\ 2,\\ 3,\\ 4,\\ 5]"

    def test_tuple_threshold_uses_row_dim(self, array_config):
        """1-D render_array uses dim=0 of a tuple threshold, ignoring the col dim."""
        array_config("array_truncate_threshold", (4, 2))  # row=4, col=2 (col irrelevant for 1D)
        array_config("array_truncate_end", (1, 1))
        # 7 elements > row threshold 4 → truncated; head=3, tail=1
        assert lr(list(range(7))) == "[0,\\ 1,\\ 2,\\ \\ldots,\\ 6]"

    def test_truncation_tail_only(self, array_config):
        """When tail >= threshold the head is empty; only ellipsis + tail items shown."""
        array_config("array_truncate_threshold", 3)
        array_config("array_truncate_end", 3)
        assert lr(list(range(6))) == "[\\ldots,\\ 3,\\ 4,\\ 5]"


# ── 2D matrix rendering ───────────────────────────────────────────────────────

class TestRenderMatrix:

    def test_2x2_integers(self):
        assert lr([[1, 2], [3, 4]]) == "\\begin{bmatrix}1 & 2 \\\\ 3 & 4\\end{bmatrix}"

    def test_2x2_floats(self):
        assert lr([[1.5, 2.5], [3.5, 4.5]]) == (
            "\\begin{bmatrix}1.500 & 2.500 \\\\ 3.500 & 4.500\\end{bmatrix}"
        )

    def test_column_vector(self):
        assert lr([[1], [2], [3]]) == "\\begin{bmatrix}1 \\\\ 2 \\\\ 3\\end{bmatrix}"

    def test_row_vector(self):
        assert lr([[1, 2, 3]]) == "\\begin{bmatrix}1 & 2 & 3\\end{bmatrix}"

    def test_3x3(self):
        assert lr([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == (
            "\\begin{bmatrix}1 & 2 & 3 \\\\ 4 & 5 & 6 \\\\ 7 & 8 & 9\\end{bmatrix}"
        )

    # matrix environment config ------------------------------------------------

    def test_pmatrix_environment(self, array_config):
        array_config("matrix_environment", "pmatrix")
        assert lr([[1, 2], [3, 4]]) == "\\begin{pmatrix}1 & 2 \\\\ 3 & 4\\end{pmatrix}"

    def test_vmatrix_environment(self, array_config):
        array_config("matrix_environment", "vmatrix")
        assert lr([[1, 2], [3, 4]]) == "\\begin{vmatrix}1 & 2 \\\\ 3 & 4\\end{vmatrix}"

    def test_Bmatrix_environment(self, array_config):
        array_config("matrix_environment", "Bmatrix")
        assert lr([[1, 2], [3, 4]]) == "\\begin{Bmatrix}1 & 2 \\\\ 3 & 4\\end{Bmatrix}"

    # truncation ---------------------------------------------------------------

    def test_row_truncation(self, array_config):
        array_config("array_truncate_threshold", 3)
        array_config("array_truncate_end", 1)
        matrix = [[1, 2], [3, 4], [5, 6], [7, 8]]
        assert lr(matrix) == (
            "\\begin{bmatrix}"
            "1 & 2 \\\\ 3 & 4 \\\\ \\vdots & \\vdots \\\\ 7 & 8"
            "\\end{bmatrix}"
        )

    def test_no_row_truncation_when_disabled(self, array_config):
        array_config("array_truncate_threshold", -1)
        matrix = [[1, 2], [3, 4], [5, 6]]
        assert lr(matrix) == (
            "\\begin{bmatrix}1 & 2 \\\\ 3 & 4 \\\\ 5 & 6\\end{bmatrix}"
        )

    def test_no_row_truncation_when_at_threshold(self, array_config):
        array_config("array_truncate_threshold", 3)
        array_config("array_truncate_end", 1)
        matrix = [[1, 2], [3, 4], [5, 6]]   # exactly 3 rows == threshold
        assert lr(matrix) == (
            "\\begin{bmatrix}1 & 2 \\\\ 3 & 4 \\\\ 5 & 6\\end{bmatrix}"
        )

    # Jupyter / MathJax safety -------------------------------------------------

    def test_no_literal_newlines(self):
        """Output must be newline-free to embed safely inside an aligned environment."""
        assert "\n" not in lr([[1, 2], [3, 4]])

    # numpy --------------------------------------------------------------------

    def test_numpy_2d(self):
        np = pytest.importorskip("numpy")
        arr = np.array([[1, 2], [3, 4]])
        assert lr(arr, precision=0) == "\\begin{bmatrix}1 & 2 \\\\ 3 & 4\\end{bmatrix}"

    def test_numpy_column_vector(self):
        np = pytest.importorskip("numpy")
        arr = np.array([[1], [2], [3]])
        assert lr(arr, precision=0) == "\\begin{bmatrix}1 \\\\ 2 \\\\ 3\\end{bmatrix}"

    def test_numpy_float_matrix(self):
        np = pytest.importorskip("numpy")
        arr = np.array([[1.0, 2.0], [3.0, 4.0]])
        assert lr(arr) == "\\begin{bmatrix}1.000 & 2.000 \\\\ 3.000 & 4.000\\end{bmatrix}"

    # 2D truncation ---------------------------------------------------------------

    def test_col_truncation_only(self, array_config):
        """Column-only truncation: \\cdots replaces middle columns; no row ellipsis."""
        array_config("array_truncate_threshold", (-1, 3))  # rows off, cols = 3
        array_config("array_truncate_end", (3, 1))         # col tail = 1
        # 2 x 5 matrix; col threshold=3, tail=1 → head=2 cols, cdots, last col
        matrix = [[float(c) for c in range(1, 6)] for _ in range(2)]
        row = "1.000 & 2.000 & \\cdots & 5.000"
        assert lr(matrix) == f"\\begin{{bmatrix}}{row} \\\\ {row}\\end{{bmatrix}}"
        # Confirm row ellipsis tokens are absent
        assert "\\vdots" not in lr(matrix)
        assert "\\ddots" not in lr(matrix)

    def test_row_and_col_truncation_tuple(self, array_config):
        """Tuple threshold truncates rows and columns independently.

        4x5 matrix, threshold=(3,3), end=(1,1):
          rows: head=2, tail=1  →  rows 0,1 shown, vdots row, row 3
          cols: head=2, tail=1  →  cols 0,1 shown, cdots, col 4
          corner: ddots at the intersection of the two ellipsis lines
        """
        array_config("array_truncate_threshold", (3, 3))
        array_config("array_truncate_end", (1, 1))
        matrix = [[float(r * 5 + c + 1) for c in range(5)] for r in range(4)]
        expected = (
            "\\begin{bmatrix}"
            "1.000 & 2.000 & \\cdots & 5.000 \\\\ "
            "6.000 & 7.000 & \\cdots & 10.000 \\\\ "
            "\\vdots & \\vdots & \\ddots & \\vdots \\\\ "
            "16.000 & 17.000 & \\cdots & 20.000"
            "\\end{bmatrix}"
        )
        assert lr(matrix) == expected

    def test_scalar_threshold_truncates_both_dims(self, array_config):
        """Scalar threshold applies equally to rows and columns."""
        array_config("array_truncate_threshold", 3)
        array_config("array_truncate_end", 1)
        matrix = [[float(r * 5 + c + 1) for c in range(5)] for r in range(4)]  # 4 x 5
        result = lr(matrix)
        assert "\\vdots" in result   # rows truncated
        assert "\\cdots" in result   # cols also truncated
        assert "\\ddots" in result   # corner


# ── pint unit arrays ──────────────────────────────────────────────────────────

class TestPintArrays:

    def test_unit_appended_as_cdot(self, pint_ureg):
        values = [1 * pint_ureg.kip, 2 * pint_ureg.kip, 3 * pint_ureg.kip]
        result = lr(values, precision=0)
        assert "\\cdot" in result
        assert result.endswith("\\mathrm{kip}")

    def test_truncation_with_units(self, array_config, pint_ureg):
        array_config("array_truncate_threshold", 6)
        array_config("array_truncate_end", 2)
        values = [i * pint_ureg.kip for i in range(1, 8)]  # 7 items
        assert lr(values, precision=0) == (
            "[1,\\ 2,\\ 3,\\ 4,\\ \\ldots,\\ 6,\\ 7] \\cdot \\mathrm{kip}"
        )

    def test_no_truncation_with_units(self, array_config, pint_ureg):
        array_config("array_truncate_threshold", -1)
        values = [i * pint_ureg.kip for i in range(1, 6)]  # 5 items
        assert lr(values, precision=0) == (
            "[1,\\ 2,\\ 3,\\ 4,\\ 5] \\cdot \\mathrm{kip}"
        )


# ── convert_parameter guard ───────────────────────────────────────────────────

class TestConvertParameter:
    """Tests for the extract-restore guard in convert_parameter.

    split_parameter_line stores the raw computed Python value as the third token
    of line.line.  convert_parameter must extract it before swap_symbolic_calcs
    (which calls str() on every token and crashes on numpy arrays) and restore it
    afterward so round_and_render_parameter can render it with the correct precision.
    """

    def test_numpy_array_does_not_crash(self):
        """Numpy array as ParameterLine value must not raise ValueError."""
        np = pytest.importorskip("numpy")
        arr = np.array([[1.0, 2.0], [3.0, 4.0]])
        line = ParameterLine(deque(["A", "=", arr]), "", "")
        result = convert_parameter(line, {"A": arr}, **global_config._config)
        # Value must be preserved at position [-1] for round_and_render_parameter
        assert result.line[-1] is arr

    def test_python_list_passes_through(self):
        """Python list as ParameterLine value is preserved unchanged."""
        lst = [1, 2, 3]
        line = ParameterLine(deque(["v", "=", lst]), "", "")
        result = convert_parameter(line, {"v": lst}, **global_config._config)
        assert result.line[-1] is lst

    def test_scalar_passes_through(self):
        """Scalar int as ParameterLine value is preserved unchanged."""
        line = ParameterLine(deque(["x", "=", 42]), "", "")
        result = convert_parameter(line, {"x": 42}, **global_config._config)
        assert result.line[-1] == 42


# ── set_truncation helper ─────────────────────────────────────────────────────

class TestSetTruncation:

    def teardown_method(self):
        set_truncation(threshold=-1, end=3)

    def test_scalar_sets_both_keys(self):
        set_truncation(threshold=5, end=2)
        assert global_config._config["array_truncate_threshold"] == 5
        assert global_config._config["array_truncate_end"] == 2

    def test_tuple_sets_both_keys(self):
        set_truncation(threshold=(5, 3), end=(2, 1))
        assert global_config._config["array_truncate_threshold"] == (5, 3)
        assert global_config._config["array_truncate_end"] == (2, 1)

    def test_int_after_tuple_no_error(self):
        set_truncation(threshold=(5, 3))
        set_truncation(threshold=-1)  # restoring int after tuple must not raise
        assert global_config._config["array_truncate_threshold"] == -1

    def test_none_args_leave_config_unchanged(self):
        set_truncation(threshold=4)
        set_truncation(end=2)         # only end changes
        assert global_config._config["array_truncate_threshold"] == 4
        assert global_config._config["array_truncate_end"] == 2
