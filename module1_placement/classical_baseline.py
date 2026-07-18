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
