"""
Parsing Python identifiers into symbols, shared by every renderer.

``parse_identifier`` turns an identifier into a ``Symbol`` tree (base words,
accents, primes, subscripts, superscripts); each renderer only formats the tree.
``_`` separates subscripts: siblings joined by commas in the ``"comma"`` style
(``N_pl_Rd`` -> N with subscript "pl,Rd"), or nested in the ``"nested"`` style
(``x_a_b`` -> x with subscript a, which has subscript b). A ``symbols`` mapping
replaces an identifier's display with a spec written in a small renderer-neutral
syntax (``"N_{pl,Rd}"``, see ``parse_spec``).

Greek letters:

A Greek letter can be written three ways in an identifier component (the text
between single underscores), or in a word of one (the text between ``__``):

- as a whole name: ``sigma`` in ``sigma_max``;
- as a Unicode letter anywhere: ``ΔH``, ``σ``;
- as a name prefix followed by an uppercase letter or a digit: ``DeltaH``,
  ``gammaM0``, ``alpha2`` (turned off with the ``greek_prefixes`` render-context field).

``split_greek`` finds them and returns the word as pieces; each renderer keeps
its own output table and formatting, so only the recognition lives here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

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

# Extra spellings, each mapped to its canonical name: ``lambda`` is a keyword,
# but ``lambdaR``, ``lambda_1`` and ``lambda_`` are valid identifiers.
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
    if word in PREFIX_ONLY:
        return [(True, PREFIX_ONLY[word])]
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


# A word of a symbol: its ``split_greek`` pieces.
Pieces = list[tuple[bool, str]]

SUBSCRIPT_STYLES = ("comma", "nested")
# Identifier components that decorate the component before them.
ACCENTS = ("hat", "bar", "dot", "ddot")
PRIME = "prime"
STAR = "star"


@dataclass
class Symbol:
    """
    One displayed symbol: its base (``__``-separated words, each a list of
    ``split_greek`` pieces), the accents over the base, its primes, and the
    symbols set as its subscripts and superscripts. Several subscripts are
    siblings, shown separated by commas.
    """

    words: list[Pieces]
    accents: list[str] = field(default_factory=list)
    primes: int = 0
    subscripts: list[Symbol] = field(default_factory=list)
    superscripts: list[Symbol] = field(default_factory=list)

    @property
    def is_text(self) -> bool:
        """True when the base has no Greek letter (one run of plain text)."""
        return not any(has_greek(pieces) for pieces in self.words)

    def text(self, space: str = " ") -> str:
        """The base as plain text, its Greek names left as they are."""
        return space.join("".join(text for _, text in pieces) for pieces in self.words)

    @property
    def is_plain(self) -> bool:
        """True for a base with no decoration, subscript or superscript."""
        return not (self.accents or self.primes or self.subscripts or self.superscripts)


@dataclass(frozen=True)
class IdentifierOptions:
    """How identifiers are parsed: see ``identifier_options``."""

    greek_prefixes: bool = True
    subscripts: str = "comma"
    symbols: Mapping[str, str] = field(default_factory=dict)


def identifier_options(renderer: Any, base_context: Any = None) -> IdentifierOptions:
    """
    The identifier options in effect: the ``greek_prefixes``, ``subscripts`` and
    ``symbols`` render-context fields (set with ``set_option`` or a ``# hc:``
    comment), defaulting to Greek prefixes on, comma subscripts and no symbols.
    """
    context = base_context.current if base_context is not None else None
    options = IdentifierOptions(
        greek_prefixes=bool(getattr(context, "greek_prefixes", True)),
        subscripts=getattr(context, "subscripts", "comma"),
        symbols=getattr(context, "symbols", None) or {},
    )
    if options.subscripts not in SUBSCRIPT_STYLES:
        raise ValueError(
            f"subscripts must be one of {SUBSCRIPT_STYLES}, not {options.subscripts!r}"
        )
    return options


def is_identifier(text: str) -> bool:
    """
    True for text a renderer should typeset as an identifier. A ``name:pre``
    rule may already have replaced it with markup (``\\dot{V}``, ``V&#775;``),
    which is left alone.
    """
    return text.isidentifier()


def _word(text: str, prefixes: bool) -> Pieces:
    return split_greek(text, prefixes)


def parse_identifier(
    identifier: str, options: IdentifierOptions = IdentifierOptions()
) -> Symbol:
    """
    Parse an identifier into a ``Symbol``:

    - ``___`` is a literal underscore and ``__`` a space between words;
    - ``_`` starts a subscript, in the ``options.subscripts`` style;
    - ``hat``, ``bar``, ``dot`` and ``ddot`` put an accent over the component
      before them,
      ``prime`` adds a prime to it and ``star`` a superscript ``*``
      (``M_star`` -> M*, ``x_hat_max`` -> x̂ with subscript max);
    - every word is split into Greek and text pieces (``split_greek``).

    An identifier in ``options.symbols`` is parsed from its spec instead (see
    ``parse_spec``). A leading or trailing underscore makes the whole
    identifier literal text (``_x``).
    """
    if identifier in options.symbols:
        return parse_spec(options.symbols[identifier], options.greek_prefixes)
    prefixes = options.greek_prefixes
    # A trailing underscore avoids a keyword clash (``lambda_``, ``class_``).
    identifier = identifier.rstrip("_") or identifier
    if identifier.startswith("_"):
        return Symbol(words=[[(False, identifier)]])
    text = identifier.replace("___", "\0").replace("__", "\1")
    symbols: list[Symbol] = []
    for component in text.split("_"):
        if symbols and component in ACCENTS:
            symbols[-1].accents.append(component)
        elif symbols and component == PRIME:
            symbols[-1].primes += 1
        elif symbols and component == STAR:
            symbols[-1].superscripts.append(Symbol(words=[[(False, "*")]]))
        else:
            words = [
                _word(word.replace("\0", "_"), prefixes)
                for word in component.split("\1")
            ]
            symbols.append(Symbol(words=words))
    base, *subscripts = symbols
    if options.subscripts == "comma":
        base.subscripts = subscripts
    else:
        parent = base
        for subscript in subscripts:
            parent.subscripts = [subscript]
            parent = subscript
    return base


def indexed_symbol(
    identifier: str, labels: list[tuple[str, bool]], options: IdentifierOptions
) -> Symbol:
    """
    The ``Symbol`` of a name indexed by ``labels`` (see ``Subscript.labels``):
    each index is one more subscript after the name's own, so ``xs[0]`` is xs
    with subscript 0 and ``M_Ed[1]`` is M with subscripts "Ed,1". A name index
    is parsed as an identifier (``A[i_max]``); an integer or string index is
    text, with a space between words.
    """
    symbol = parse_identifier(identifier, options)
    for text, is_name in labels:
        if is_name:
            symbol.subscripts.append(parse_identifier(text, options))
        else:
            symbol.subscripts.append(
                Symbol(words=[[(False, word)] for word in text.split()])
            )
    return symbol


class SpecError(ValueError):
    """A ``symbols`` spec that can't be parsed."""


_SPEC_STOPS = "_^,{}()"


def parse_spec(spec: str, greek_prefixes: bool = True) -> Symbol:
    """
    Parse a display spec from the ``symbols`` option into a ``Symbol``. The
    syntax is TeX-like but renderer-neutral:

    - ``N_{pl,Rd}``: subscripts in braces, siblings separated by commas;
      ``N_Rd`` takes the run of letters and digits after ``_``;
    - ``M^{*}``, ``x^2``: superscripts, the same way;
    - ``x_{a_{b}}``: a subscript can have its own subscripts;
    - spaces separate words (``Delta H``); ``'`` after a base adds a prime;
    - ``hat(x)``, ``bar(x)``, ``dot(V)``, ``ddot(x)`` put an accent over a base
      (``bar(x)_{m}``: the subscript stays outside);
    - Greek letters as names or Unicode, as in identifiers (``Delta H``,
      ``ΔH``, ``sigma_{max}``).
    """
    parser = _SpecParser(spec, greek_prefixes)
    symbol = parser.symbol()
    if parser.peek():
        parser.fail(f"unexpected {spec[parser.pos]!r}")
    return symbol


class _SpecParser:
    def __init__(self, spec: str, greek_prefixes: bool) -> None:
        self.spec = spec
        self.pos = 0
        self.prefixes = greek_prefixes

    def fail(self, message: str) -> None:
        raise SpecError(f"Can't parse symbol {self.spec!r} at {self.pos}: {message}")

    def peek(self) -> str:
        """The next character after any spaces (spaces only separate words)."""
        while self.pos < len(self.spec) and self.spec[self.pos] == " ":
            self.pos += 1
        return self.spec[self.pos] if self.pos < len(self.spec) else ""

    def read(self, stops: str) -> str:
        start = self.pos
        while self.pos < len(self.spec) and self.spec[self.pos] not in stops:
            self.pos += 1
        return self.spec[start : self.pos]

    def symbol(self) -> Symbol:
        base = self.read(_SPEC_STOPS).strip()
        if self.peek() == "(":
            symbol = self.accented(base)
        else:
            primes = len(base) - len(base.rstrip("'"))
            base = base.rstrip("'").strip()
            if not base:
                self.fail("expected a symbol")
            words = [_word(word, self.prefixes) for word in base.split()]
            symbol = Symbol(words=words, primes=primes)
        while self.peek() in ("_", "^") and self.peek():
            target = symbol.subscripts if self.peek() == "_" else symbol.superscripts
            self.pos += 1
            target.extend(self.group())
        return symbol

    def accented(self, accent: str) -> Symbol:
        """``accent(symbol)``, then any primes after the ``)``."""
        if accent not in ACCENTS:
            self.fail(f"unknown accent {accent!r} (use one of {', '.join(ACCENTS)})")
        self.pos += 1
        symbol = self.symbol()
        if self.peek() != ")":
            self.fail("expected ')'")
        self.pos += 1
        symbol.accents.append(accent)
        while self.peek() == "'":
            symbol.primes += 1
            self.pos += 1
        return symbol

    def group(self) -> list[Symbol]:
        if self.peek() != "{":
            atom = self.read(_SPEC_STOPS + " ")
            if not atom:
                self.fail("expected a subscript or superscript")
            return [Symbol(words=[_word(atom, self.prefixes)])]
        self.pos += 1
        items = [self.symbol()]
        while self.peek() == ",":
            self.pos += 1
            items.append(self.symbol())
        if self.peek() != "}":
            self.fail("expected '}'")
        self.pos += 1
        return items
