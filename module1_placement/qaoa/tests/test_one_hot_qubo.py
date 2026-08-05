"""
Stage 1 — Pure-Python Validation of the One-Hot QUBO Model
============================================================

Three checks using plain ``assert`` statements (no pytest):

1. **Structural check**: every QUBO key has length ≤ 2 (no hidden
   higher-order terms).
2. **Brute-force cross-check**: enumerate all 7^4 = 2401 one-hot-valid
   assignments (each cell picks exactly one site), evaluate QUBO energy,
   and confirm strict energy separation between the 96 valid placements
   and the remaining 2305 invalid ones.
3. **Collision-only sanity**: a hand-constructed single-collision
   assignment has higher energy than a known valid assignment, by
   approximately PENALTY_B.

Ends with ``STAGE 1: PASS`` only if all asserts succeed.
"""

from __future__ import annotations

import sys
import os
import itertools

# ── Path setup ───────────────────────────────────────────────────────────
# Ensure the project root is on sys.path so both module1_placement and
# module1_placement.qaoa are importable.
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from module1_placement.qaoa.one_hot_qubo import (
    build_qubo,
    qubo_energy,
    NUM_CELLS,
    NUM_SITES,
    PENALTY_B,
)
from module1_placement.classical_baseline import (
    enumerate_valid_placements_with_adjacency,
)


def _one_hot_assignment(placement: tuple) -> dict:
    """Convert a (site0, site1, site2, site3) tuple to a full 28-variable
    one-hot assignment dict.

    Parameters
    ----------
    placement : tuple of int
        Length-4 tuple where ``placement[cell]`` is the site index (0–6)
        assigned to that cell.

    Returns
    -------
    dict[(cell, site), int]
        28-entry dict with exactly one variable per cell set to 1.
    """
    assignment = {}
    for cell in range(NUM_CELLS):
        for site in range(NUM_SITES):
            assignment[(cell, site)] = 1 if site == placement[cell] else 0
    return assignment


def main() -> None:
    print("=" * 60)
    print("Stage 1: One-Hot QUBO Validation")
    print("=" * 60)

    qubo = build_qubo()

    # ── Check (a): Structural check ──────────────────────────────────
    print("\n[Check a] Structural: all QUBO keys have length ≤ 2 ...")
    for key in qubo:
        assert len(key) <= 2, (
            f"QUBO key has {len(key)} variables (expected ≤ 2): {key}"
        )
    num_linear = sum(1 for k in qubo if len(k) == 1)
    num_quadratic = sum(1 for k in qubo if len(k) == 2)
    print(f"  Linear terms:    {num_linear}")
    print(f"  Quadratic terms: {num_quadratic}")
    print(f"  Total terms:     {len(qubo)}")
    print("  ✓ Structural check PASSED")

    # ── Check (b): Brute-force cross-check ───────────────────────────
    print("\n[Check b] Brute-force: enumerating all 7^4 = 2401 one-hot "
          "assignments ...")

    # Ground truth: the 96-member set of valid placements with adjacency.
    valid_set = set(enumerate_valid_placements_with_adjacency())
    assert len(valid_set) == 96, (
        f"Expected 96 valid placements, got {len(valid_set)}"
    )

    # Enumerate all possible one-hot-valid assignments: each cell picks
    # exactly one of 7 sites.  7^4 = 2401 combinations.  This includes
    # cases where multiple cells pick the SAME site (collisions), which
    # are invalid.
    valid_energies = []
    invalid_energies = []

    for combo in itertools.product(range(NUM_SITES), repeat=NUM_CELLS):
        # combo = (site_for_cell0, site_for_cell1, site_for_cell2, site_for_cell3)
        assignment = _one_hot_assignment(combo)
        energy = qubo_energy(qubo, assignment)

        if combo in valid_set:
            valid_energies.append(energy)
        else:
            invalid_energies.append(energy)

    assert len(valid_energies) == 96, (
        f"Expected 96 valid energies, got {len(valid_energies)}"
    )
    assert len(invalid_energies) == 2401 - 96, (
        f"Expected {2401 - 96} invalid energies, got {len(invalid_energies)}"
    )

    max_valid_energy = max(valid_energies)
    min_invalid_energy = min(invalid_energies)
    energy_gap = min_invalid_energy - max_valid_energy

    print(f"  Valid placements:   {len(valid_energies)}")
    print(f"  Invalid placements: {len(invalid_energies)}")
    print(f"  Max valid energy:   {max_valid_energy:.4f}")
    print(f"  Min invalid energy: {min_invalid_energy:.4f}")
    print(f"  Energy gap:         {energy_gap:.4f}")
    print(f"  Min valid energy:   {min(valid_energies):.4f}")
    print(f"  Max invalid energy: {max(invalid_energies):.4f}")

    assert max_valid_energy < min_invalid_energy, (
        f"ENERGY SEPARATION FAILED: max valid ({max_valid_energy:.4f}) "
        f">= min invalid ({min_invalid_energy:.4f}). "
        f"Gap = {energy_gap:.4f}. Penalty weights need adjustment."
    )
    print("  ✓ Brute-force cross-check PASSED — strict energy separation "
          "confirmed")

    # ── Check (c): Collision-only sanity ─────────────────────────────
    print("\n[Check c] Collision-only sanity check ...")

    # Hand-construct a fully-valid assignment:
    #   cell 0 → site 0, cell 1 → site 1, cell 2 → site 2, cell 3 → site 3
    # This is collision-free, and sites 0-1 and 1-2 are adjacent, so it
    # should be in the valid set.
    valid_placement = (0, 1, 2, 3)
    assert valid_placement in valid_set, (
        f"Expected {valid_placement} to be in the valid set"
    )
    valid_assignment = _one_hot_assignment(valid_placement)
    valid_energy = qubo_energy(qubo, valid_assignment)

    # Hand-construct an assignment with exactly one collision:
    #   cell 0 → site 0, cell 1 → site 1, cell 2 → site 2, cell 3 → site 2
    # Cell 2 and cell 3 both at site 2 — single collision.
    # The adjacency chain (cell0↔cell1, cell1↔cell2) is still satisfied
    # since cell 0 at 0, cell 1 at 1, cell 2 at 2 are adjacent.
    # Only difference from the valid case is: cell 3 moved from site 3
    # to site 2 (creating collision with cell 2).
    collision_placement = (0, 1, 2, 2)
    assert collision_placement not in valid_set, (
        f"Expected {collision_placement} to NOT be in the valid set"
    )
    collision_assignment = _one_hot_assignment(collision_placement)
    collision_energy = qubo_energy(qubo, collision_assignment)

    energy_diff = collision_energy - valid_energy
    expected_diff = PENALTY_B  # one collision adds B to the energy

    print(f"  Valid placement {valid_placement}: energy = {valid_energy:.4f}")
    print(f"  Collision placement {collision_placement}: energy = {collision_energy:.4f}")
    print(f"  Energy difference: {energy_diff:.4f}")
    print(f"  Expected (≈ PENALTY_B = {PENALTY_B}): {expected_diff:.4f}")

    # The collision adds exactly B to the collision term.  However, the
    # adjacency reward for cell3 may also change (cell3 at site2 vs site3
    # — cell3 is unconstrained so no adjacency change), and there is no
    # one-hot violation (still exactly one site per cell — note that
    # collision_placement has two cells at site 2 but each cell still has
    # exactly one site selected).
    #
    # Actually, the only term that changes is H_collision: one new
    # collision (cell2, cell3 both at site 2) adds exactly +B.
    # The one-hot constraint is still satisfied (each cell has exactly
    # one variable set), and the adjacency reward only involves cell
    # pairs (0,1) and (1,2) — cell 3 is unconstrained.
    #
    # But wait: the valid_placement (0,1,2,3) has cell3 at site 3.
    # The collision_placement (0,1,2,2) has cell3 at site 2.
    # Neither (0,1) nor (1,2) cell pairs involve cell3, so adjacency
    # rewards are identical.  The ONLY difference is one collision term.
    assert abs(energy_diff - expected_diff) < 1e-9, (
        f"COLLISION SANITY FAILED: energy diff {energy_diff:.6f} != "
        f"expected {expected_diff:.6f} (tolerance 1e-9)"
    )
    print("  ✓ Collision-only sanity check PASSED")

    # ── Final verdict ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STAGE 1: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
