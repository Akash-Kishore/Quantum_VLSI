"""
One-Hot QUBO Model for Module 1 Placement
==========================================

Builds a QUBO (Quadratic Unconstrained Binary Optimization) cost function
for placing 4 logic cells onto 7 physical sites using a one-hot encoding.

Encoding
--------
Each of the 4 cells (cell 0–3) gets 7 binary variables, one per site (0–6).
Variable ``(cell, site)`` = 1 means "cell is assigned to site."
Total: 4 × 7 = 28 binary variables.

**Structural note**: unlike the Grover binary encoding where code 7 is an
invalid state requiring an explicit validity penalty, the one-hot encoding
*cannot represent* an invalid-code state.  If exactly one variable per cell
is set to 1, the cell is assigned to a valid site by construction.  The
one-hot constraint penalty (H_onehot) enforces the "exactly one" rule; no
separate validity term is needed.

Cost Function
-------------
H_C = H_onehot + H_collision + H_adjacency

- **H_onehot**: penalty for violating the one-hot constraint
  (each cell must have exactly one site selected).
- **H_collision**: penalty for two cells occupying the same site.
- **H_adjacency**: reward for required cell pairs being placed on
  adjacent sites (Manhattan distance 1 on the grid).

Site Topology (confirmed from module1_placement.classical_baseline)
-------------------------------------------------------------------
7 sites in a 2×4 grid with position (row=1, col=3) unused::

    Row 0:  [0] [1] [2] [3]
    Row 1:  [4] [5] [6] [ · ]

Site-to-coordinate mapping::

    site 0 → (row=0, col=0)
    site 1 → (row=0, col=1)
    site 2 → (row=0, col=2)
    site 3 → (row=0, col=3)
    site 4 → (row=1, col=0)
    site 5 → (row=1, col=1)
    site 6 → (row=1, col=2)
"""

from __future__ import annotations

from typing import Dict, Tuple, FrozenSet


# ── Constants ────────────────────────────────────────────────────────────

NUM_CELLS = 4
NUM_SITES = 7

# Penalty weights — placeholder values pending a tuning sweep in a later
# stage.  A and B must be large positive values to make constraint violations
# energetically unfavorable.  C is negative (a reward) to energetically
# favor adjacency-satisfying placements.  These are NOT final.
PENALTY_A = 10   # one-hot constraint penalty weight
PENALTY_B = 10   # collision penalty weight
PENALTY_C = -2   # adjacency reward (negative = reward)


# ── Site topology ────────────────────────────────────────────────────────
# Derived from the same 2×4 grid used in module1_placement.classical_baseline
# and module1_placement.placement_oracle.

SITE_COORDS: Dict[int, Tuple[int, int]] = {
    0: (0, 0),
    1: (0, 1),
    2: (0, 2),
    3: (0, 3),
    4: (1, 0),
    5: (1, 1),
    6: (1, 2),
}

# 8 undirected adjacency edges: Manhattan distance == 1 on the grid.
# Stored as a frozenset of frozensets for O(1) symmetric lookup.
ADJACENCY_PAIRS: frozenset = frozenset()
_adj_list = []
for _sa in range(NUM_SITES):
    for _sb in range(_sa + 1, NUM_SITES):
        _ra, _ca = SITE_COORDS[_sa]
        _rb, _cb = SITE_COORDS[_sb]
        if abs(_ra - _rb) + abs(_ca - _cb) == 1:
            _adj_list.append(frozenset({_sa, _sb}))
ADJACENCY_PAIRS = frozenset(_adj_list)
del _adj_list, _sa, _sb, _ra, _ca, _rb, _cb

# Also store as ordered-pair set for directional iteration.
ADJACENCY_ORDERED_PAIRS: frozenset = frozenset()
_ordered = []
for _edge in ADJACENCY_PAIRS:
    _a, _b = sorted(_edge)
    _ordered.append((_a, _b))
    _ordered.append((_b, _a))
ADJACENCY_ORDERED_PAIRS = frozenset(_ordered)
del _ordered, _edge, _a, _b

# Required cell-pair adjacency constraints (cell0↔cell1, cell1↔cell2).
# Cell 3 has no adjacency requirement.
REQUIRED_ADJ_CELL_PAIRS = [(0, 1), (1, 2)]

# All 6 cell pairs for collision checking.
ALL_CELL_PAIRS = [
    (ci, cj) for ci in range(NUM_CELLS) for cj in range(ci + 1, NUM_CELLS)
]


# ── Variable naming ─────────────────────────────────────────────────────
# A variable is identified by the tuple (cell, site).
# QUBO keys are:
#   - frozenset({(cell, site)})             for linear terms
#   - frozenset({(cell_i, site_a), (cell_j, site_b)})  for quadratic terms

Var = Tuple[int, int]              # (cell, site)
QUBOKey = FrozenSet[Var]
QUBODict = Dict[QUBOKey, float]


def _add_to_qubo(qubo: QUBODict, key: QUBOKey, value: float) -> None:
    """Accumulate a coefficient into the QUBO dict."""
    if key in qubo:
        qubo[key] += value
    else:
        qubo[key] = value


# ── QUBO builder ─────────────────────────────────────────────────────────

def build_qubo(alpha: float | None = None) -> QUBODict:
    """Build the one-hot QUBO for Module 1 placement.

    Parameters
    ----------
    alpha : float or None
        If given, scale all penalty weights uniformly by ``alpha``.
        Default ``None`` uses the module-level constants directly.

    Returns
    -------
    QUBODict
        Mapping from ``frozenset`` keys to ``float`` coefficients.
        Linear terms have keys of length 1; quadratic terms have keys
        of length 2.  No key has length > 2 (pure QUBO, no higher-order
        terms).
    """
    A = PENALTY_A if alpha is None else PENALTY_A * alpha
    B = PENALTY_B if alpha is None else PENALTY_B * alpha
    C = PENALTY_C if alpha is None else PENALTY_C * alpha

    qubo: QUBODict = {}

    # ── H_onehot ─────────────────────────────────────────────────────
    # For each cell c, penalise deviation from exactly-one-hot:
    #   A * (sum_{s} x[c,s] - 1)^2
    #
    # Algebraic expansion:
    #   (sum_s x_s - 1)^2
    #     = (sum_s x_s)^2 - 2*(sum_s x_s) + 1
    #     = sum_s x_s^2 + sum_{s<t} 2*x_s*x_t - 2*sum_s x_s + 1
    #
    # Since x_s ∈ {0,1}, x_s^2 = x_s, so:
    #     = sum_s x_s + 2*sum_{s<t} x_s*x_t - 2*sum_s x_s + 1
    #     = -sum_s x_s + 2*sum_{s<t} x_s*x_t + 1
    #
    # The constant +1 shifts the global energy but doesn't affect the
    # optimizer (dropped from the QUBO dict).  We keep only:
    #   Linear:    A * (-1) * x[c,s]          for each s
    #   Quadratic: A * (+2) * x[c,s]*x[c,t]   for each s < t
    for c in range(NUM_CELLS):
        for s in range(NUM_SITES):
            var_s: Var = (c, s)
            # Linear term: coefficient = A * (-1)
            _add_to_qubo(qubo, frozenset({var_s}), A * (-1.0))

            # Quadratic terms with other sites of the same cell
            for t in range(s + 1, NUM_SITES):
                var_t: Var = (c, t)
                _add_to_qubo(qubo, frozenset({var_s, var_t}), A * 2.0)

    # ── H_collision ──────────────────────────────────────────────────
    # For each pair of cells (i, j) and each site s, penalise both
    # being assigned to the same site:
    #   B * x[i,s] * x[j,s]
    #
    # This is naturally quadratic (product of two distinct binary
    # variables from different cells), no reduction needed.
    for (ci, cj) in ALL_CELL_PAIRS:
        for s in range(NUM_SITES):
            var_i: Var = (ci, s)
            var_j: Var = (cj, s)
            _add_to_qubo(qubo, frozenset({var_i, var_j}), B * 1.0)

    # ── H_adjacency ──────────────────────────────────────────────────
    # For each required cell-pair (cell_a, cell_b) and each pair of
    # adjacent sites (site_a, site_b), reward placing cell_a at site_a
    # and cell_b at site_b:
    #   C * x[cell_a, site_a] * x[cell_b, site_b]
    #
    # C < 0 makes this a reward (lowers energy for adjacent placements).
    # This is naturally quadratic (product of two variables from
    # different cells at different sites), no OR gadget or degree-3+
    # term is needed — staying pure quadratic throughout.
    for (cell_a, cell_b) in REQUIRED_ADJ_CELL_PAIRS:
        for (site_a, site_b) in ADJACENCY_ORDERED_PAIRS:
            var_a: Var = (cell_a, site_a)
            var_b: Var = (cell_b, site_b)
            _add_to_qubo(qubo, frozenset({var_a, var_b}), C * 1.0)

    return qubo


# ── Energy evaluator ─────────────────────────────────────────────────────

def qubo_energy(qubo_dict: QUBODict, assignment: Dict[Var, int]) -> float:
    """Evaluate the QUBO energy for a concrete variable assignment.

    Parameters
    ----------
    qubo_dict : QUBODict
        QUBO dict as returned by :func:`build_qubo`.
    assignment : dict[(cell, site), int]
        Mapping from each ``(cell, site)`` variable to its binary value
        (0 or 1).  Must contain an entry for every variable that appears
        in the QUBO.

    Returns
    -------
    float
        The total QUBO energy.
    """
    energy = 0.0
    for key, coeff in qubo_dict.items():
        vars_in_key = list(key)
        if len(vars_in_key) == 1:
            # Linear term: coeff * x_i
            energy += coeff * assignment[vars_in_key[0]]
        elif len(vars_in_key) == 2:
            # Quadratic term: coeff * x_i * x_j
            energy += coeff * assignment[vars_in_key[0]] * assignment[vars_in_key[1]]
        else:
            raise ValueError(
                f"QUBO key has {len(vars_in_key)} variables (expected 1 or 2): {key}"
            )
    return energy
