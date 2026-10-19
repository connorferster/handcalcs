import pytest

from handcalcs.renderers.identifiers import (
    GREEK_UNICODE,
    split_greek,
    split_greek_prefix,
    unicode_greek,
)


@pytest.mark.parametrize(
    "component, expected",
    [
        ("DeltaH", ("Delta", "H")),
        ("DeltaT", ("Delta", "T")),
        ("gammaM0", ("gamma", "M0")),
        ("alpha2", ("alpha", "2")),
        ("SigmaF", ("Sigma", "F")),
        ("epsilonR", ("epsilon", "R")),
        ("varepsilonR", ("varepsilon", "R")),
        ("varphiA", ("varphi", "A")),
        ("lambdaR", ("lamb", "R")),
        ("LambdaR", ("Lamb", "R")),
        ("DeltaHvap", ("Delta", "Hvap")),
        ("DeltaΣ", ("Delta", "Σ")),
    ],
)
def test_split_greek_prefix(component, expected):
    assert split_greek_prefix(component) == expected


@pytest.mark.parametrize(
    "component",
    [
        "metal", "pier", "beta", "Betas", "etalon", "psion", "alphabet", "Pin",
        "Pi", "Mud", "Rhombus", "Taunt", "Chin", "xtheta", "Delta", "lambda",
        "x", "", "H",
    ],
)
def test_split_greek_prefix_no_split(component):
    assert split_greek_prefix(component) == (None, component)


@pytest.mark.parametrize(
    "word, prefixes, expected",
    [
        ("sigma", True, [(True, "sigma")]),
        ("sigma", False, [(True, "sigma")]),
        ("DeltaH", True, [(True, "Delta"), (False, "H")]),
        ("DeltaH", False, [(False, "DeltaH")]),
        ("ΔHvap", False, [(True, "Delta"), (False, "Hvap")]),
        ("ΔH", True, [(True, "Delta"), (False, "H")]),
        ("Σρ", True, [(True, "Sigma"), (True, "rho")]),
        ("xσ", True, [(False, "x"), (True, "sigma")]),
        ("λ", True, [(True, "lamb")]),
        ("metal", True, [(False, "metal")]),
        ("", True, [(False, "")]),
    ],
)
def test_split_greek(word, prefixes, expected):
    assert split_greek(word, prefixes) == expected


def test_unicode_round_trip():
    for name, letter in GREEK_UNICODE.items():
        assert split_greek(letter) == [(True, name)]


@pytest.mark.parametrize(
    "word, expected",
    [("DeltaH", "ΔH"), ("sigma", "σ"), ("gammaM0", "γM0"), ("metal", "metal"), ("ΔH", "ΔH")],
)
def test_unicode_greek(word, expected):
    assert unicode_greek(word) == expected
