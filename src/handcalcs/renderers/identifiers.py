"""
Recognising Greek letters in Python identifiers, shared by every renderer.

A Greek letter can be written three ways in an identifier component (the text
between single underscores), or in a word of one (the text between ``__``):

- as a whole name: ``sigma`` in ``sigma_max``;
- as a Unicode letter anywhere: ``ΔH``, ``σ``;
- as a name prefix followed by an uppercase letter or a digit: ``DeltaH``,
  ``gammaM0``, ``alpha2`` (renderers turn this off with ``GREEK_PREFIXES``).

``split_greek`` finds them and returns the word as pieces; each renderer keeps
its own output table and formatting, so only the recognition lives here.
"""

from __future__ import annotations

# Every recognised name and its Unicode letter. ``lamb`` stands in for
# ``lambda``, which is a Python keyword.
GREEK_UNICODE = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "varepsilon": "ϵ",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "vartheta": "ϑ",
    "iota": "ι",
    "kappa": "κ",
    "lamb": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "omicron": "ο",
    "pi": "π",
    "varpi": "ϖ",
    "rho": "ρ",
    "varrho": "ϱ",
    "sigma": "σ",
    "varsigma": "ς",
    "tau": "τ",
    "upsilon": "υ",
    "phi": "φ",
    "varphi": "ϕ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
    "Alpha": "Α",
    "Beta": "Β",
    "Gamma": "Γ",
    "Delta": "Δ",
    "Epsilon": "Ε",
    "Zeta": "Ζ",
    "Eta": "Η",
    "Theta": "Θ",
    "Iota": "Ι",
    "Kappa": "Κ",
    "Lamb": "Λ",
    "Mu": "Μ",
    "Nu": "Ν",
    "Xi": "Ξ",
    "Omicron": "Ο",
    "Pi": "Π",
    "Rho": "Ρ",
    "Sigma": "Σ",
    "Tau": "Τ",
    "Upsilon": "Υ",
    "Phi": "Φ",
    "Chi": "Χ",
    "Psi": "Ψ",
    "Omega": "Ω",
}

GREEK_NAMES = tuple(GREEK_UNICODE)

# The name of each Unicode letter (the inverse of ``GREEK_UNICODE``).
UNICODE_NAMES = {letter: name for name, letter in GREEK_UNICODE.items()}

# Names that are recognised as a prefix only: ``lambdaR`` is a valid identifier
# although ``lambda`` is not. Each maps to its canonical name.
PREFIX_ONLY = {"lambda": "lamb", "Lambda": "Lamb"}

# Prefix candidates, longest first, so ``varepsilonR`` matches ``varepsilon``
# and ``epsilonR`` is not cut short.
_PREFIXES = sorted(
    [(name, name) for name in GREEK_NAMES] + list(PREFIX_ONLY.items()),
    key=lambda pair: -len(pair[0]),
)


def split_greek_prefix(component: str) -> tuple[str | None, str]:
    """
    Split a leading Greek name from a component when an uppercase letter or a
    digit follows it: ``"DeltaH"`` -> ``("Delta", "H")``, ``"lambdaR"`` ->
    ``("lamb", "R")``. Anything else -> ``(None, component)``, including a whole
    name (``"Delta"``) and a lowercase continuation (``"metal"``, ``"beta"``,
    ``"Pin"``).
    """
    for prefix, name in _PREFIXES:
        if component.startswith(prefix) and len(component) > len(prefix):
            following = component[len(prefix)]
            if following.isupper() or following.isdigit():
                return name, component[len(prefix) :]
    return None, component


def split_greek(word: str, prefixes: bool = True) -> list[tuple[bool, str]]:
    """
    A word as ``(is_greek, text)`` pieces, where a Greek piece's text is its
    canonical name (a key of ``GREEK_UNICODE``):

    - ``"sigma"`` -> ``[(True, "sigma")]``
    - ``"ΔHvap"`` -> ``[(True, "Delta"), (False, "Hvap")]``
    - ``"DeltaH"`` -> ``[(True, "Delta"), (False, "H")]`` (only with ``prefixes``)
    - ``"metal"`` -> ``[(False, "metal")]``

    A word with no Greek letter is always one text piece, so a renderer can
    keep its usual formatting for it.
    """
    if word in GREEK_UNICODE:
        return [(True, word)]
    pieces: list[tuple[bool, str]] = []
    if prefixes:
        name, word = split_greek_prefix(word)
        if name is not None:
            pieces.append((True, name))
    text = ""
    for char in word:
        if char in UNICODE_NAMES:
            if text:
                pieces.append((False, text))
                text = ""
            pieces.append((True, UNICODE_NAMES[char]))
        else:
            text += char
    if text or not pieces:
        pieces.append((False, text))
    return pieces


def has_greek(pieces: list[tuple[bool, str]]) -> bool:
    return any(is_greek for is_greek, _ in pieces)


def unicode_greek(word: str, prefixes: bool = True) -> str:
    """A word with its Greek names swapped for Unicode letters (``DeltaH`` -> ``ΔH``)."""
    return "".join(
        GREEK_UNICODE[text] if is_greek else text
        for is_greek, text in split_greek(word, prefixes)
    )


def greek_identifier(identifier: str, prefixes: bool = True) -> str:
    """
    An identifier with the Greek names in each ``_``-separated component, and in
    each ``__``-separated word of one, swapped for Unicode letters. The
    underscores are kept for the renderer to interpret: ``sigma_max`` ->
    ``σ_max``, ``Delta__H`` -> ``Δ__H``, ``DeltaT_max`` -> ``ΔT_max``.
    """
    # Placeholders for the double/triple underscores, which are not separators.
    text = identifier.replace("___", "\0").replace("__", "\1")
    components = [
        "\1".join(unicode_greek(word, prefixes) for word in component.split("\1"))
        for component in text.split("_")
    ]
    return "_".join(components).replace("\1", "__").replace("\0", "___")
