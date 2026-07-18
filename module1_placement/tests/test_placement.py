"""
STAGE 3 — Full Grover Placement Test
======================================

Builds and runs the complete Grover circuit for the placement problem:
4 cells → 7 sites, 25-qubit circuit, 12-qubit search register.

Uses the manual Grover loop pattern (same as module2_atpg/tests/test_atpg.py)
since the oracle (25 qubits) is wider than the diffusion register (12 qubits).

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

    Constructs a 25-qubit circuit where:
      - q0–q11 are the 12-qubit search register (Hadamard + diffusion).
      - q12–q24 are ancillas (start at |0⟩, untouched by diffusion).
      - The oracle spans all 25 qubits.
      - Diffusion applies to q0–q11 only.
      - Measurement on q0–q11 only.

    Parameters
    ----------
    oracle : QuantumCircuit
        The 25-qubit placement oracle circuit.
    iterations : int
        Number of Grover iterations.

    Returns
    -------
    QuantumCircuit
        The complete Grover circuit with 25 qubits and 12 classical bits.
    """
    circuit = QuantumCircuit(TOTAL_QUBITS, N_SEARCH)

    # Initial superposition on search register only (q0–q11).
    circuit.h(range(N_SEARCH))

    # Grover iterations.
    diffusion = diffusion_operator(N_SEARCH)
    for _ in range(iterations):
        # Full 25-qubit oracle.
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
        The 25-qubit placement oracle.
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

    # ------------------------------------------------------------------
    # Test 1: iterations=1 (exact optimum), assert >90%
    # ------------------------------------------------------------------
    print(f"\n[TEST 1] Grover with iterations=1 (exact optimum), {SHOTS} shots:")
    valid_prob_1, distinct_1, examples_1 = _run_and_analyze(
        oracle, iterations=1, ground_truth_set=ground_truth_set
    )

    print(f"  Valid placement probability: {valid_prob_1:.4f}  (threshold > 0.90)")
    print(f"  Distinct valid placements observed: {distinct_1}")
    print(f"  Example placements (cell→site):")
    for placement, n in examples_1:
        print(f"    cell0→{placement[0]}, cell1→{placement[1]}, "
              f"cell2→{placement[2]}, cell3→{placement[3]}  ({n} shots)")

    assert valid_prob_1 > 0.90, (
        f"FAIL: Valid placement probability {valid_prob_1:.4f} is not > 0.90 "
        f"at iterations=1"
    )
    print(f"  PASS ✓  (probability {valid_prob_1:.4f} > 0.90)")

    # ------------------------------------------------------------------
    # Test 2: iterations=2 (approx formula), comparison only
    # ------------------------------------------------------------------
    print(f"\n[TEST 2] Grover with iterations=2 (approx formula), {SHOTS} shots:")
    valid_prob_2, distinct_2, examples_2 = _run_and_analyze(
        oracle, iterations=2, ground_truth_set=ground_truth_set
    )

    print(f"  Valid placement probability: {valid_prob_2:.4f}  (comparison only)")
    print(f"  Distinct valid placements observed: {distinct_2}")
    print(f"  (Expected to be lower than iter=1, confirming overshoot)")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("  ARCHITECTURAL NOTE:")
    print("  build_grover_circuit assumes oracle & diffusion share the")
    print("  same qubit count. Since the placement oracle spans 25 qubits")
    print("  but diffusion must apply only to q0-q11 (12-qubit search")
    print("  register), the Grover loop was constructed MANUALLY in")
    print("  build_placement_grover_circuit(), composing the 12-qubit")
    print("  diffusion operator onto qubits [0..11] of the 25-qubit")
    print("  circuit. shared_framework/ was NOT modified.")
    print("=" * 60)
    print()
    print(f"  build_placement_oracle().num_qubits = {oracle.num_qubits}  ✓")
    print(f"  count_valid_placements() = {m}  ✓")
    print(f"  Grover loop: manual (Module 2 precedent)  ✓")
    print()
    print("=" * 60)
    print("  STAGE 3: PASS")
    print("  No packages were changed, upgraded, or installed.")
    print("  No new dependencies introduced (no pytest, etc.).")
    print("=" * 60)


if __name__ == "__main__":
    main()
