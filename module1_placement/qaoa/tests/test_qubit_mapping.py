"""
Stage 2a — Qubit Mapping Bijection Test
=========================================

Validates the (cell, site) ↔ qubit index mapping in isolation before
any circuit code uses it.  Per project convention after the Phase 6
little-endian decode bug: test the mapping layer independently first.

Checks:
  - TOTAL_QUBITS == 28
  - Forward mapping covers all 28 (cell, site) pairs and produces
    unique qubit indices in [0, 28)
  - Round-trip identity in both directions
  - Out-of-range inputs raise ValueError
"""

from __future__ import annotations

import sys
import os

# ── Path setup ───────────────────────────────────────────────────────────
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from module1_placement.qaoa.qubit_mapping import (
    variable_to_qubit_index,
    qubit_index_to_variable,
    TOTAL_QUBITS,
)
from module1_placement.qaoa.one_hot_qubo import NUM_CELLS, NUM_SITES


def main() -> None:
    print("=" * 60)
    print("Stage 2a: Qubit Mapping Bijection Test")
    print("=" * 60)

    # ── Check 1: TOTAL_QUBITS ────────────────────────────────────────
    print(f"\n[Check 1] TOTAL_QUBITS = {TOTAL_QUBITS}")
    assert TOTAL_QUBITS == 28, f"Expected 28, got {TOTAL_QUBITS}"
    print("  ✓ TOTAL_QUBITS == 28")

    # ── Check 2: Forward mapping covers all 28 pairs, unique indices ─
    print("\n[Check 2] Forward mapping: all 28 (cell, site) → unique index")
    seen_indices: set[int] = set()
    all_vars: list[tuple[int, int]] = []

    for cell in range(NUM_CELLS):
        for site in range(NUM_SITES):
            idx = variable_to_qubit_index(cell, site)
            assert 0 <= idx < TOTAL_QUBITS, (
                f"Index {idx} out of range for (cell={cell}, site={site})"
            )
            assert idx not in seen_indices, (
                f"Duplicate index {idx} for (cell={cell}, site={site})"
            )
            seen_indices.add(idx)
            all_vars.append((cell, site))

    assert len(seen_indices) == TOTAL_QUBITS, (
        f"Expected {TOTAL_QUBITS} unique indices, got {len(seen_indices)}"
    )
    assert seen_indices == set(range(TOTAL_QUBITS)), (
        f"Indices do not cover [0, {TOTAL_QUBITS}): "
        f"missing {set(range(TOTAL_QUBITS)) - seen_indices}"
    )
    print(f"  {len(seen_indices)} unique indices covering [0, {TOTAL_QUBITS})")
    print("  ✓ Bijection (forward) confirmed")

    # ── Check 3: Round-trip (cell, site) → index → (cell, site) ──────
    print("\n[Check 3] Round-trip: variable → index → variable")
    for cell, site in all_vars:
        idx = variable_to_qubit_index(cell, site)
        cell_back, site_back = qubit_index_to_variable(idx)
        assert (cell_back, site_back) == (cell, site), (
            f"Round-trip failed: ({cell}, {site}) → {idx} → "
            f"({cell_back}, {site_back})"
        )
    print(f"  All {len(all_vars)} round-trips passed")
    print("  ✓ Round-trip (var → idx → var) identity confirmed")

    # ── Check 4: Round-trip index → (cell, site) → index ─────────────
    print("\n[Check 4] Round-trip: index → variable → index")
    for idx in range(TOTAL_QUBITS):
        cell, site = qubit_index_to_variable(idx)
        idx_back = variable_to_qubit_index(cell, site)
        assert idx_back == idx, (
            f"Round-trip failed: {idx} → ({cell}, {site}) → {idx_back}"
        )
    print(f"  All {TOTAL_QUBITS} round-trips passed")
    print("  ✓ Round-trip (idx → var → idx) identity confirmed")

    # ── Check 5: Out-of-range raises ValueError ──────────────────────
    print("\n[Check 5] Out-of-range inputs raise ValueError")
    oob_cases_forward = [
        (-1, 0), (4, 0), (0, -1), (0, 7), (4, 7), (-1, -1),
    ]
    for cell, site in oob_cases_forward:
        try:
            variable_to_qubit_index(cell, site)
            assert False, (
                f"Expected ValueError for variable_to_qubit_index({cell}, {site})"
            )
        except ValueError:
            pass  # expected

    oob_cases_inverse = [-1, 28, 100, -100]
    for idx in oob_cases_inverse:
        try:
            qubit_index_to_variable(idx)
            assert False, (
                f"Expected ValueError for qubit_index_to_variable({idx})"
            )
        except ValueError:
            pass  # expected

    print(f"  {len(oob_cases_forward)} forward OOB cases raised ValueError")
    print(f"  {len(oob_cases_inverse)} inverse OOB cases raised ValueError")
    print("  ✓ Out-of-range validation confirmed")

    # ── Final verdict ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STAGE 2a: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
