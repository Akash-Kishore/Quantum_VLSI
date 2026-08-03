"""
Stage 2 — Exhaustive Statevector Verification of the Generalized Oracle
=========================================================================

For all 11 fault sites × all 8 classical inputs (88 total cases),
prepares each input classically, runs the oracle circuit through
``AerSimulator(method="statevector")`` + ``save_statevector()``, and
asserts:

1. The phase at the input's basis-state index is -1 when the fault is
   detected (matching ``fault_family.py``'s ground truth) and +1 otherwise.
2. All ancilla qubits (q3–q9) return to |0⟩ — zero residual probability
   outside the q0–q2 subspace.

Uses plain ``assert`` in ``main()`` — no pytest, per project convention.

Package-lock barrier (repeated per project convention):

==========  ============================
Package     Version — DO NOT CHANGE
==========  ============================
Python      3.10
qiskit      1.2.4
qiskit-aer  0.15.1 (gpu-cu11)
numpy       1.26.4
matplotlib  3.8.4
CUDA (WSL2) 11.8
==========  ============================
"""

from __future__ import annotations

import sys
import os

# Ensure project root is on sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from module2_atpg.generalized_faults.fault_family import (
    FaultSite,
    enumerate_fault_sites,
    evaluate_faulty,
    evaluate_full_adder,
)
from module2_atpg.generalized_faults.generalized_oracle import (
    NUM_QUBITS,
    build_generalized_atpg_oracle,
)


def _input_to_basis_index(a: int, b: int, cin: int) -> int:
    """Convert (a, b, cin) to the statevector basis-state index.

    Qiskit's statevector uses little-endian ordering: qubit 0 is the
    least-significant bit.  With q0=A, q1=B, q2=Cin and q3–q9 = 0,
    the index is::

        index = a * 2^0 + b * 2^1 + cin * 2^2

    (All ancilla qubits are 0 after correct uncomputation.)

    Parameters
    ----------
    a, b, cin : int
        Single-bit inputs (0 or 1).

    Returns
    -------
    int
        The basis-state index in the 2^10 = 1024 element statevector.
    """
    return a + (b << 1) + (cin << 2)


def _is_detecting(fault_site: FaultSite, a: int, b: int, cin: int) -> bool:
    """Check if (a, b, cin) detects the given fault, per fault_family.py.

    Parameters
    ----------
    fault_site : FaultSite
        The fault to test.
    a, b, cin : int
        Single-bit inputs.

    Returns
    -------
    bool
        True if the input detects the fault.
    """
    good_cout, good_sum = evaluate_full_adder(a, b, cin)
    bad_cout, bad_sum = evaluate_faulty(fault_site, a, b, cin)

    if fault_site.fault_class == "product_term":
        return bad_cout != good_cout
    elif fault_site.fault_class == "xor_chain":
        return bad_sum != good_sum
    else:  # control
        return False


def main() -> None:
    """Run exhaustive statevector verification for all 88 cases."""

    sites = enumerate_fault_sites()
    assert len(sites) == 11

    sim = AerSimulator(method="statevector", device="CPU")
    total_cases = 0
    pass_count = 0
    fail_count = 0

    for site in sites:
        oracle = build_generalized_atpg_oracle(site)

        for a in range(2):
            for b in range(2):
                for cin in range(2):
                    total_cases += 1

                    # Build test circuit: prepare input state, apply oracle
                    qc = QuantumCircuit(NUM_QUBITS)

                    # Prepare classical input on q0–q2
                    if a:
                        qc.x(0)
                    if b:
                        qc.x(1)
                    if cin:
                        qc.x(2)

                    # Apply oracle
                    qc.compose(oracle, inplace=True)

                    # Save statevector
                    qc.save_statevector()

                    # Run
                    transpiled = transpile(qc, sim)
                    result = sim.run(transpiled, shots=1).result()
                    sv = result.get_statevector(qc)
                    data = np.array(sv.data)

                    # --- Check 1: phase at the input basis state ---
                    idx = _input_to_basis_index(a, b, cin)
                    detecting = _is_detecting(site, a, b, cin)
                    expected_phase = -1.0 if detecting else +1.0

                    amplitude = data[idx]
                    # The amplitude should be real (±1) for a classical input
                    assert abs(amplitude.imag) < 1e-10, (
                        f"Non-real amplitude at {site} input ({a},{b},{cin}): "
                        f"{amplitude}"
                    )
                    actual_phase = amplitude.real

                    assert abs(actual_phase - expected_phase) < 1e-10, (
                        f"PHASE MISMATCH: {site.fault_class} "
                        f"{site.identifier} SA{site.stuck_at} "
                        f"input ({a},{b},{cin}): "
                        f"expected {expected_phase}, got {actual_phase}"
                    )

                    # --- Check 2: ancillas return to |0⟩ ---
                    # The only nonzero amplitude should be at index `idx`
                    # (all ancillas at 0).
                    for other_idx in range(len(data)):
                        if other_idx == idx:
                            continue
                        assert abs(data[other_idx]) < 1e-10, (
                            f"ANCILLA LEAK: {site.fault_class} "
                            f"{site.identifier} SA{site.stuck_at} "
                            f"input ({a},{b},{cin}): "
                            f"nonzero amplitude {data[other_idx]} at "
                            f"index {other_idx}"
                        )

                    pass_count += 1

    assert total_cases == 88, f"Expected 88 cases, ran {total_cases}"
    assert pass_count == 88, f"Expected 88 passes, got {pass_count}"

    print(f"{pass_count}/{total_cases} cases correct")
    print()
    print("Phase verification: ALL 88 PASS")
    print("Ancilla uncomputation: ALL 88 PASS (zero residual outside q0-q2)")
    print()
    print("=" * 50)
    print("ALL TESTS PASSED")
    print("=" * 50)


if __name__ == "__main__":
    main()
