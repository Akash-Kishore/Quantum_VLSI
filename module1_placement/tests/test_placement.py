"""
STAGE 3 — Full Grover Placement Test
======================================

Builds and runs the complete Grover circuit for the placement problem:
4 cells → 7 sites, 27-qubit circuit, 12-qubit search register.

Uses the manual Grover loop pattern (same as module2_atpg/tests/test_atpg.py)
since the oracle (27 qubits) is wider than the diffusion register (12 qubits).

Phase 3b tests: adjacency-extended oracle at k=5 (both formulas agree).
Classical ground truth for the pre-adjacency 840-count is still verified.

Must only be run after stages 1 and 2 have passed.
"""

from __future__ import annotations

import sys
import os

# Ensure project root is on sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from qiskit import QuantumCircuit

from shared_framework.grover_utils import optimal_iterations, run_circuit
from shared_framework.diffusion import diffusion_operator
from module1_placement.placement_oracle import (
    build_placement_oracle,
    TOTAL_QUBITS,
)
from module1_placement.classical_baseline import (
    enumerate_valid_placements,
    count_valid_placements,
    enumerate_valid_placements_with_adjacency,
    count_valid_placements_with_adjacency,
)
from module1_placement.encoding import (
    decode_bitstring_to_placement,
    is_valid_collision_free,
)


N_SEARCH = 12  # search register qubits (q0–q11)
SHOTS = 1000


def build_placement_grover_circuit(
    oracle: QuantumCircuit,
    iterations: int,
) -> QuantumCircuit:
    """Build the placement Grover circuit with diffusion on search register only.

    Constructs a 27-qubit circuit (via ``TOTAL_QUBITS``) where:
      - q0–q11 are the 12-qubit search register (Hadamard + diffusion).
      - q12–q26 are ancillas (start at |0⟩, untouched by diffusion).
      - The oracle spans all 27 qubits.
      - Diffusion applies to q0–q11 only.
      - Measurement on q0–q11 only.

    Parameters
    ----------
    oracle : QuantumCircuit
        The 27-qubit placement oracle circuit.
    iterations : int
        Number of Grover iterations.

    Returns
    -------
    QuantumCircuit
        The complete Grover circuit with 27 qubits and 12 classical bits.
    """
    circuit = QuantumCircuit(TOTAL_QUBITS, N_SEARCH)

    # Initial superposition on search register only (q0–q11).
    circuit.h(range(N_SEARCH))

    # Grover iterations.
    diffusion = diffusion_operator(N_SEARCH)
    for _ in range(iterations):
        # Full 27-qubit oracle.
        circuit.compose(oracle, inplace=True)
        # Diffusion on q0–q11 only.
        circuit.compose(diffusion, qubits=list(range(N_SEARCH)), inplace=True)

    # Measure only the search register.
    circuit.measure(range(N_SEARCH), range(N_SEARCH))

    return circuit


def _run_and_analyze(
    oracle: QuantumCircuit,
    iterations: int,
    ground_truth_set: set,
) -> tuple[float, int, list]:
    """Run the Grover circuit and analyze results.

    Parameters
    ----------
    oracle : QuantumCircuit
        The 27-qubit placement oracle.
    iterations : int
        Number of Grover iterations.
    ground_truth_set : set
        Set of all valid placements from classical enumeration.

    Returns
    -------
    tuple[float, int, list]
        (valid_probability, distinct_valid_count, example_placements)
    """
    circuit = build_placement_grover_circuit(oracle, iterations)

    # Assert qubit count before running
    assert circuit.num_qubits == TOTAL_QUBITS, (
        f"FAIL: Grover circuit has {circuit.num_qubits} qubits, expected {TOTAL_QUBITS}."
    )

    counts = run_circuit(circuit, shots=SHOTS)

    valid_count = 0
    distinct_valid = set()
    examples = []

    for bitstring, n_shots in counts.items():
        placement = decode_bitstring_to_placement(bitstring)
        valid = is_valid_collision_free(placement)

        if valid:
            # Cross-check against ground truth
            assert placement in ground_truth_set, (
                f"FAIL: Decoded placement {placement} passes is_valid_collision_free "
                f"but is not in enumerate_valid_placements() output!"
            )
            valid_count += n_shots
            distinct_valid.add(placement)
            if len(examples) < 10:
                examples.append((placement, n_shots))

    valid_prob = valid_count / SHOTS
    return valid_prob, len(distinct_valid), examples


def main() -> None:
    """Run all stage-3 placement tests."""

    # ------------------------------------------------------------------
    # Classical ground truth
    # ------------------------------------------------------------------
    m = count_valid_placements()
    print(f"[STAGE 3] count_valid_placements() = {m}")
    assert m == 840, f"FAIL: Expected 840 valid placements, got {m}"
    print(f"  Confirmed: M = {m} = 7×6×5×4  ✓")

    ground_truth = enumerate_valid_placements()
    ground_truth_set = set(ground_truth)
    assert len(ground_truth_set) == 840  # no duplicates

    # ------------------------------------------------------------------
    # Iteration counts
    # ------------------------------------------------------------------
    k_approx = optimal_iterations(N_SEARCH, m)
    k_exact = optimal_iterations(N_SEARCH, m, exact=True)
    print(f"\n[STAGE 3] optimal_iterations(12, 840)              = {k_approx}")
    print(f"[STAGE 3] optimal_iterations(12, 840, exact=True)  = {k_exact}")

    # ------------------------------------------------------------------
    # Build oracle and verify qubit count
    # ------------------------------------------------------------------
    oracle = build_placement_oracle()
    print(f"\n[STAGE 3] Oracle circuit: {oracle.num_qubits} qubits, "
          f"{oracle.size()} gates")
    assert oracle.num_qubits == TOTAL_QUBITS, (
        f"FAIL: Oracle has {oracle.num_qubits} qubits, expected {TOTAL_QUBITS}."
    )

    # ==================================================================
    # Phase 3b: Adjacency-constrained Grover test
    # ==================================================================
    print("\n" + "=" * 60)
    print("  PHASE 3b: ADJACENCY-CONSTRAINED GROVER TEST")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Classical ground truth (adjacency)
    # ------------------------------------------------------------------
    m_adj = count_valid_placements_with_adjacency()
    print(f"\n[STAGE 3] count_valid_placements_with_adjacency() = {m_adj}")
    assert m_adj == 96, f"FAIL: Expected 96 adjacency placements, got {m_adj}"
    print(f"  Confirmed: M_adj = {m_adj}  ✓")

    ground_truth_adj = enumerate_valid_placements_with_adjacency()
    ground_truth_adj_set = set(ground_truth_adj)
    assert len(ground_truth_adj_set) == 96  # no duplicates

    # ------------------------------------------------------------------
    # Iteration counts (adjacency)
    # ------------------------------------------------------------------
    k_approx_adj = optimal_iterations(N_SEARCH, m_adj)
    k_exact_adj = optimal_iterations(N_SEARCH, m_adj, exact=True)
    print(f"\n[STAGE 3] optimal_iterations(12, 96)              = {k_approx_adj}")
    print(f"[STAGE 3] optimal_iterations(12, 96, exact=True)  = {k_exact_adj}")
    print(f"  (Both expected to be 5 — no overshoot this time)")

    # ------------------------------------------------------------------
    # Test 3 [Phase 3b]: iterations=5 (both formulas agree), assert >90%
    # ------------------------------------------------------------------
    k_adj = k_exact_adj
    print(f"\n[TEST 3] Grover with iterations={k_adj} (adjacency), {SHOTS} shots:")
    circuit_adj = build_placement_grover_circuit(oracle, iterations=k_adj)

    assert circuit_adj.num_qubits == TOTAL_QUBITS, (
        f"FAIL: Grover circuit has {circuit_adj.num_qubits} qubits, expected {TOTAL_QUBITS}."
    )

    counts_adj = run_circuit(circuit_adj, shots=SHOTS)

    adj_valid_count = 0
    adj_distinct_valid = set()
    adj_examples = []
    nontrivial_threshold = max(1, int(0.01 * SHOTS))  # ~1% of shots
    unexpected_marks = []

    for bitstring, n_shots in counts_adj.items():
        placement = decode_bitstring_to_placement(bitstring)
        in_ground_truth = placement in ground_truth_adj_set

        if in_ground_truth:
            adj_valid_count += n_shots
            adj_distinct_valid.add(placement)
            if len(adj_examples) < 10:
                adj_examples.append((placement, n_shots))
        elif n_shots >= nontrivial_threshold:
            # A non-trivial count on a state OUTSIDE the marked set at this
            # success rate is not expected sampling noise — it signals a bug.
            unexpected_marks.append((placement, n_shots))

    assert not unexpected_marks, (
        f"FAIL: {len(unexpected_marks)} placement(s) outside the M=96 adjacency set got "
        f"non-trivial shot counts (>= {nontrivial_threshold}): {unexpected_marks}. "
        f"This indicates the oracle is incorrectly marking an unintended state."
    )

    adj_valid_prob = adj_valid_count / SHOTS

    print(f"  Valid+adjacent probability: {adj_valid_prob:.4f}  (threshold > 0.90)")
    print(f"  Distinct valid+adjacent placements observed: {len(adj_distinct_valid)}")
    print(f"  Example placements (cell→site):")
    for placement, n in adj_examples:
        print(f"    cell0→{placement[0]}, cell1→{placement[1]}, "
              f"cell2→{placement[2]}, cell3→{placement[3]}  ({n} shots)")

    assert adj_valid_prob > 0.90, (
        f"FAIL: Valid+adjacent probability {adj_valid_prob:.4f} is not > 0.90 "
        f"at iterations={k_adj}"
    )
    print(f"  PASS ✓  (probability {adj_valid_prob:.4f} > 0.90)")

    # ------------------------------------------------------------------
    # Test 4 [Phase 3b]: Run at both formulas for reproducibility
    # ------------------------------------------------------------------
    if k_approx_adj != k_exact_adj:
        print(f"\n[TEST 4] Running at approx k={k_approx_adj} for comparison...")
        circuit_adj2 = build_placement_grover_circuit(oracle, iterations=k_approx_adj)
        counts_adj2 = run_circuit(circuit_adj2, shots=SHOTS)
        adj_valid_count2 = sum(
            n for bs, n in counts_adj2.items()
            if decode_bitstring_to_placement(bs) in ground_truth_adj_set
        )
        adj_valid_prob2 = adj_valid_count2 / SHOTS
        print(f"  Valid+adjacent probability: {adj_valid_prob2:.4f}  (comparison only)")
    else:
        print(f"\n[TEST 4] Both formulas agree at k={k_adj} — no separate comparison run needed.")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("  ARCHITECTURAL NOTE:")
    print("  build_grover_circuit assumes oracle & diffusion share the")
    print(f"  same qubit count. Since the placement oracle spans {TOTAL_QUBITS} qubits")
    print("  but diffusion must apply only to q0-q11 (12-qubit search")
    print("  register), the Grover loop was constructed MANUALLY in")
    print("  build_placement_grover_circuit(), composing the 12-qubit")
    print(f"  diffusion operator onto qubits [0..11] of the {TOTAL_QUBITS}-qubit")
    print("  circuit. shared_framework/ was NOT modified.")
    print("=" * 60)
    print()
    print(f"  build_placement_oracle().num_qubits = {oracle.num_qubits}  ✓")
    print(f"  count_valid_placements() = {m}  ✓")
    print(f"  count_valid_placements_with_adjacency() = {m_adj}  ✓")
    print(f"  Grover loop: manual (Module 2 precedent)  ✓")
    print()
    print("=" * 60)
    print("  STAGE 3: PASS")
    print("  No packages were changed, upgraded, or installed.")
    print("  No new dependencies introduced (no pytest, etc.).")
    print("=" * 60)


if __name__ == "__main__":
    main()
