"""
Classical Baseline for Placement
=================================

Enumerates all valid, collision-free placements of 4 logic cells onto
7 physical sites using classical brute force (``itertools.permutations``).

This serves as ground truth for validating the quantum Grover-based
placement oracle.
"""

from __future__ import annotations

import itertools
from typing import List, Tuple


def enumerate_valid_placements() -> List[Tuple[int, int, int, int]]:
    """Return every valid, collision-free placement of 4 cells onto 7 sites.

    A placement is a 4-tuple ``(site0, site1, site2, site3)`` where each
    ``site_k`` is in ``{0, 1, ..., 6}`` and all four are pairwise distinct.

    This is exactly the set of 4-permutations of 7 elements:
    ``7 × 6 × 5 × 4 = 840``.

    Returns
    -------
    list[tuple[int, int, int, int]]
        All 840 valid placements, in lexicographic order.
    """
    return list(itertools.permutations(range(7), 4))  # type: ignore[return-value]


def count_valid_placements() -> int:
    """Return the number of valid, collision-free placements.

    Must equal 840 (= 7 × 6 × 5 × 4).

    Returns
    -------
    int
        The count of valid placements.
    """
    return len(enumerate_valid_placements())


# ── Site-adjacency topology ──────────────────────────────────────────
#
# 7 sites in a 2×4 grid (row=1,col=3 is unused):
#   Row 0:  [0] [1] [2] [3]
#   Row 1:  [4] [5] [6] [ . ]
#
# 8 undirected adjacency edges (Manhattan distance = 1), stored as both
# directions for O(1) lookup:
SITE_ADJACENCY_EDGES = frozenset({
    (0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2),
    (4, 5), (5, 4), (5, 6), (6, 5),
    (0, 4), (4, 0), (1, 5), (5, 1), (2, 6), (6, 2),
})


def enumerate_valid_placements_with_adjacency() -> List[Tuple[int, int, int, int]]:
    """Return every valid, collision-free, chain-adjacent placement.

    Filters ``enumerate_valid_placements()`` by the chain constraint:
    cell 0 must be adjacent to cell 1, AND cell 1 must be adjacent to
    cell 2. Cell 3 has no adjacency requirement.

    Adjacency is defined by ``SITE_ADJACENCY_EDGES`` (orthogonal
    neighbors on a 2×4 grid with one unused corner).

    Returns
    -------
    list[tuple[int, int, int, int]]
        All valid, collision-free, chain-adjacent placements.
    """
    return [
        p for p in enumerate_valid_placements()
        if (p[0], p[1]) in SITE_ADJACENCY_EDGES
        and (p[1], p[2]) in SITE_ADJACENCY_EDGES
    ]


def count_valid_placements_with_adjacency() -> int:
    """Return the number of valid, collision-free, chain-adjacent placements.

    Returns
    -------
    int
        The count of adjacency-constrained placements.
    """
    return len(enumerate_valid_placements_with_adjacency())
