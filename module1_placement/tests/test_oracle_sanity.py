"""
STAGE 2 — Oracle Sanity Check (Aer Statevector Simulation)
============================================================

Deterministic, exact statevector check of the placement oracle on
three hand-picked classical inputs. No Hadamards, no diffusion, no
measurement sampling. Uses ``AerSimulator(method="statevector")`` with
``save_statevector()`` for efficient compiled simulation on CPU.

Must pass before proceeding to stage 3.
"""

from __future__ import annotations

import sys
import os

# Ensure project root is on sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from module1_placement.placement_oracle import build_placement_oracle, TOTAL_QUBITS


def _build_test_circuit(x_gates: list[int]) -> QuantumCircuit:
    """Build a 25-qubit circuit with specified X gates, then compose the oracle.

    Parameters
    ----------
    x_gates : list[int]
        Qubit indices to apply X gates on (prepares a classical basis state).

    Returns
    -------
    QuantumCircuit
        The prepared circuit with oracle composed.
    """
    qc = QuantumCircuit(TOTAL_QUBITS)
    for q in x_gates:
        qc.x(q)
    oracle = build_placement_oracle()
    qc.compose(oracle, inplace=True)
    return qc


def main() -> None:
    """Run all stage-2 oracle sanity checks."""

    # ------------------------------------------------------------------
    # Pre-check: oracle qubit count and decomposed gate count
    # ------------------------------------------------------------------
    oracle = build_placement_oracle()
    assert oracle.num_qubits == 25, (
        f"FAIL: Oracle has {oracle.num_qubits} qubits, expected 25. "
        f"Possible ancilla drift from mcx."
    )
    print(f"[STAGE 2] Oracle qubit count: {oracle.num_qubits}  ✓")

    decomposed_size = build_placement_oracle().decompose().size()
    print(f"[STAGE 2] Oracle decomposed gate count: {decomposed_size}")

    # ------------------------------------------------------------------
    # Test cases
    # ------------------------------------------------------------------
    # Each case: (name, meaning, x_gates, expected_index, should_be_negative)
    cases = [
        (
            "A",
            "Sites (0,1,2,3) — valid, collision-free",
            [3, 7, 9, 10],   # cell0=0, cell1=1(q3), cell2=2(q7), cell3=3(q9+q10)
            1672,
            True,   # should be ≈ -1+0j (marked)
        ),
        (
            "B",
            "Sites (0,0,1,2) — collision on cell0/cell1",
            [6, 10],          # cell0=0, cell1=0, cell2=1(q6), cell3=2(q10)
            1088,
            False,  # should be ≈ +1+0j (unmarked)
        ),
        (
            "C",
            "Sites (0,1,2,7) — cell3 has invalid code 7",
            [3, 7, 9, 10, 11],  # cell0=0, cell1=1(q3), cell2=2(q7), cell3=7(q9+q10+q11)
            3720,
            False,  # should be ≈ +1+0j (unmarked)
        ),
    ]

    all_passed = True
    sim = AerSimulator(method="statevector")

    for case_name, meaning, x_gates, expected_index, should_be_negative in cases:
        print(f"\n[STAGE 2] Case {case_name}: {meaning}")
        print(f"  X gates: {x_gates}")
        print(f"  Expected index: {expected_index}")

        circuit = _build_test_circuit(x_gates)
        circuit_copy = circuit.copy()
        circuit_copy.save_statevector()
        result = sim.run(circuit_copy).result()
        sv = result.get_statevector(circuit_copy)

        amplitude = sv.data[expected_index]
        abs_amplitude = abs(amplitude)
        total_prob = sum(abs(sv.data) ** 2)
        residual_prob = total_prob - abs_amplitude ** 2

        print(f"  sv.data[{expected_index}] = {amplitude}")
        print(f"  |amplitude| = {abs_amplitude:.10f}")
        print(f"  Residual probability (other states) = {residual_prob:.2e}")

        # Check 1: all probability mass on this state
        assert abs(abs_amplitude - 1.0) < 1e-6, (
            f"Case {case_name} FAIL: |amplitude| = {abs_amplitude}, expected ≈ 1.0"
        )

        # Check 2: nothing anywhere else
        assert residual_prob < 1e-6, (
            f"Case {case_name} FAIL: residual probability = {residual_prob}, "
            f"expected < 1e-6 (ancilla uncomputation error)"
        )

        # Check 3: sign
        if should_be_negative:
            if amplitude.real > 0 or abs(amplitude.imag) > 1e-6:
                print(f"  *** FAIL: Expected negative real amplitude (marked state), "
                      f"got {amplitude}")
                all_passed = False
                continue
            print(f"  Amplitude is negative (marked) ✓")
        else:
            if amplitude.real < 0 or abs(amplitude.imag) > 1e-6:
                print(f"  *** FAIL: Expected positive real amplitude (unmarked state), "
                      f"got {amplitude}")
                all_passed = False
                continue
            print(f"  Amplitude is positive (unmarked) ✓")

        print(f"  Case {case_name}: PASS ✓")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    if all_passed:
        print("=" * 50)
        print("  STAGE 2: PASS")
        print("=" * 50)
    else:
        print("=" * 50)
        print("  STAGE 2: FAIL")
        print("  The oracle has a sign or uncomputation bug.")
        print("  DO NOT proceed to stage 3.")
        print("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    main()
