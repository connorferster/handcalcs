"""
handcalcs.testing's feature cases, run against every built-in renderer: each feature
renders without an error and shows (and hides) the names it should.
"""
import pytest

from handcalcs.renderers import get_renderer
from handcalcs.renderers.excel.compat import ExcelRendererIncompatibleError
from handcalcs.testing import FEATURE_CASES, check_case

RENDERERS = ["ascii", "latex", "markdown", "html", "word", "excel"]

# Calculations a worksheet cannot hold; the Excel renderer refuses them by design.
EXCEL_INCOMPATIBLE = {"expression", "collection", "for-block"}


@pytest.mark.parametrize("case", FEATURE_CASES, ids=lambda case: case.id)
@pytest.mark.parametrize("renderer_name", RENDERERS)
def test_feature_case(renderer_name, case):
    renderer = get_renderer(renderer_name)()
    if renderer_name == "excel" and case.id in EXCEL_INCOMPATIBLE:
        with pytest.raises(ExcelRendererIncompatibleError):
            check_case(renderer, case)
        return
    check_case(renderer, case)


def test_feature_case_ids_are_unique():
    ids = [case.id for case in FEATURE_CASES]
    assert len(ids) == len(set(ids))


def test_check_case_reports_missing_and_unexpected_names():
    from handcalcs.testing import FeatureCase

    case = FeatureCase("demo", "apple = 1\n", shown=("berry",), hidden=("apple",))
    with pytest.raises(AssertionError, match=r"missing \['berry'\], should be hidden \['apple'\]"):
        check_case(get_renderer("ascii")(), case)


def test_options_are_restored_after_a_case():
    import handcalcs
    from handcalcs.testing import render_case

    case = next(case for case in FEATURE_CASES if case.options)
    before = {name: handcalcs.get_option(name) for name in case.options}
    render_case(get_renderer("ascii")(), case)
    assert {name: handcalcs.get_option(name) for name in case.options} == before
