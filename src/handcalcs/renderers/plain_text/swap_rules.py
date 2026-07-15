def swap_greeks(node, context: Optional[dict] = None) -> None:
    """
    Swaps out any greek substrings or unicode symbols
    """
    if not isinstance(node, Name): return
    GREEK_LOWER = {
        "alpha": "α",
        "beta": "β",
        "gamma": "γ",
        "delta": "δ",
        "epsilon": "ε",
        "varepsilon": "ϵ",
        "zeta": "ζ",
        "theta": "θ",
        "vartheta": "ϑ",
        "iota": "ι",
        "kappa": "κ",
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
        "omega": "ω",
        "eta": "η",
        "psi": "ψ",
        "lamb": "λ",
    }

    GREEK_UPPER = {
        "Alpha": "Α",
        "Beta": "Β",
        "Gamma": "Γ",
        "Delta": "Δ",
        "Epsilon": "Ε",
        "Zeta": "Ζ",
        "Theta": "Θ",
        "Iota": "Ι",
        "Kappa": "Κ",
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
        "Omega": "Ω",
        "Eta": "Η",
        "Psi": "Ψ",
        "Lamb": "Λ",
    }

    for name, unicode in (GREEK_LOWER | GREEK_UPPER).items():
        id_components = node.identifier.split("_")
        swapped_components = []
        for comp in id_components:
            if comp == name:
                comp = unicode
            swapped_components.append(comp)
        swapped_id = "_".join(swapped_components)
        node.identifier = swapped_id
    

def swap_py_operators(node) -> HcNode:
    if node.type not in ('mult_op', 'pow_op', 'div_op', 'floor_op'):
        return node
    elif node.type == 'mult_op':
        node.symbol = ')('
        node.pre = '('
        node.post = ')'
        return node
    elif node.type == 'div_op':
        node.symbol = ') / ('
        node.pre = '('
        node.post = ')'
        return node
    elif node.type == 'floor_op':
        node.symbol = ') / ('
        node.pre = 'floor[('
        node.post = ')]'
        return node
    elif node.type == 'pow_op' and isinstance(node.exponent, int):
        return node
    else:
        return node
        

