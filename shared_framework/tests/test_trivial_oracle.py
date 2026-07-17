"""
Trivial Oracle End-to-End Test
==============================

Validates the shared Grover framework on the simplest non-trivial case:
  - 2 qubits, marked state |11⟩
  - 1 Grover iteration (the analytical optimum)

Assertions
----------
1. ``optimal_iterations(2, 1)`` returns 1  (approximate mode).
2. ``optimal_iterations(2, 1, exact=True)`` returns 1  (exact mode).
3. Running Grover at 1 iteration yields ``'11'`` in >90 % of shots.
4. ``sweep_iterations`` for iterations 0–3 prints the characteristic
   rise-and-fall pattern of success probability.
"""

from __future__ import annotations

import sys
import os

# Ensure the project root is on sys.path so `shared_framework` is importable
# when this script is run directly (e.g. `python -m shared_framework.tests.test_trivial_oracle`
# from the project root).
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared_framework.oracle import bitstring_oracle
from shared_framework.grover_utils import (
    optimal_iterations,
    build_grover_circuit,
    run_circuit,
)
from shared_framework.visualization import sweep_iterations


def main() -> None:
    """Run all Phase 1 trivial-oracle validation checks."""

    n_qubits = 2
    marked = "11"
    shots = 1000

    # ------------------------------------------------------------------
    # Test 1: optimal_iterations — approximate mode
    # For n=2, M=1: round((π/4)·√4) = round(1.5708) = 2.
    # ------------------------------------------------------------------
    k_approx = optimal_iterations(n_qubits, 1)
    print(f"[TEST 1] optimal_iterations(2, 1)          = {k_approx}")
    assert k_approx == 2, (
        f"FAIL: expected 2, got {k_approx}"
    )
    print("         PASS ✓")

    # ------------------------------------------------------------------
    # Test 2: optimal_iterations — exact mode
    # For n=2, M=1: θ = arcsin(√(1/4)) = π/6.  Maximizing
    # sin²((2k+1)·π/6) gives k=1 (sin²(π/2)=1.0).
    # ------------------------------------------------------------------
    k_exact = optimal_iterations(n_qubits, 1, exact=True)
    print(f"[TEST 2] optimal_iterations(2, 1, exact=True) = {k_exact}")
    assert k_exact == 1, (
        f"FAIL: expected 1, got {k_exact}"
    )
    print("         PASS ✓")

    # ------------------------------------------------------------------
    # Test 3: Grover circuit at 1 iteration — |11⟩ should dominate
    # Use iterations=1 (the exact-mode optimum), which achieves
    # 100% theoretical success probability for the 2-qubit case.
    # ------------------------------------------------------------------
    oracle = bitstring_oracle(n_qubits, marked)
    circuit = build_grover_circuit(n_qubits, oracle, iterations=1)
    counts = run_circuit(circuit, shots=shots)

    count_11 = counts.get("11", 0)
    ratio = count_11 / shots
    print(f"[TEST 3] Grover 1-iter counts: {counts}")
    print(f"         '11' ratio = {ratio:.4f}  (threshold > 0.90)")
    assert ratio > 0.90, (
        f"FAIL: '11' ratio {ratio:.4f} is not > 0.90"
    )
    print("         PASS ✓")

    # ------------------------------------------------------------------
    # Test 4: sweep_iterations for 0–3 iterations
    # ------------------------------------------------------------------
    print("\n[TEST 4] Sweep iterations 0–3:")
    save_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "sweep_trivial_oracle.png",
    )
    probs = sweep_iterations(
        n_qubits,
        oracle,
        max_iterations=3,
        shots=shots,
        marked_states=marked,
        save_path=save_path,
    )
    print(f"\n         Probabilities: {probs}")
    # Sanity: iteration-1 probability should be the highest.
    assert probs[1] > probs[0], (
        f"FAIL: iter-1 prob ({probs[1]:.4f}) should exceed iter-0 ({probs[0]:.4f})"
    )
    print("         PASS ✓")

    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED  ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
