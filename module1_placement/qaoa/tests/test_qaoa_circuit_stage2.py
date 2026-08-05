"""
Stage 2b/2c — QAOA Circuit Statevector Sanity Tests
=====================================================

Stage 2b: 28-qubit, p=1, gamma=0, beta=0 → the QAOA circuit should reduce
to just Hadamard on all qubits (cost unitary = identity, mixer unitary =
identity), producing the exact uniform superposition.  Verified via GPU
AerSimulator with shot-based uniformity checks (birthday uniqueness,
marginal probabilities) — avoids materialising the 4GB statevector.

Stage 2c: 2-qubit toy QUBO — verifies that the QUBO→Ising conversion and
RZ/CX-RZ-CX gate decomposition produce the correct relative phases.  This
is a cheap, exact test that isolates the conversion correctness question
from the 28-qubit scale question.

Both tests use plain ``assert`` in ``main()``.
"""

from __future__ import annotations

import sys
import os
import numpy as np

# ── Path setup ───────────────────────────────────────────────────────────
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator, AerError

from module1_placement.qaoa.one_hot_qubo import build_qubo, QUBODict
from module1_placement.qaoa.qaoa_circuit import (
    build_qaoa_circuit,
    _qubo_to_ising,
    TOTAL_QUBITS,
)



def _stage_2b() -> None:
    """Stage 2b: 28-qubit uniform superposition sanity check.

    With gamma=0 and beta=0, the cost unitary is identity (all RZ angles
    are zero) and the mixer unitary is identity (all RX angles are zero).
    The circuit is just H^⊗28, producing the exact uniform superposition
    |+⟩^⊗28 with probability 1/2^28 for every basis state.

    **Memory note**: a full 28-qubit statevector is 2^28 × 16 bytes ≈ 4 GB,
    which can OOM-kill on constrained hosts.  Instead of save_statevector(),
    we use a shot-based uniformity check:
      - 8192 shots from a true uniform distribution over 2^28 ≈ 268M states
        should produce (nearly) all unique bitstrings (birthday paradox:
        probability of any collision ≈ 8192²/(2×2^28) ≈ 0.125, so ≤ a few
        duplicates is expected).
      - We verify: (a) large number of unique bitstrings, (b) no single
        bitstring dominates, (c) each qubit has ≈50% marginal probability
        of being 1 (binomial test).
    """
    print("\n" + "-" * 60)
    print("Stage 2b: 28-qubit uniform superposition (gamma=0, beta=0)")
    print("-" * 60)

    qubo = build_qubo()

    # Build the full QAOA circuit (includes measurement)
    qc = build_qaoa_circuit(qubo, gammas=[0.0], betas=[0.0], n_qubits=TOTAL_QUBITS)

    n_shots = 8192
    sim = AerSimulator(method="statevector", device="GPU")
    try:
        qc_t = transpile(qc, sim)
        result = sim.run(qc_t, shots=n_shots).result()
    except (AerError, RuntimeError) as e:
        print(f"  (GPU execution failed ({e}), falling back to CPU)")
        sim = AerSimulator(method="statevector", device="CPU")
        qc_t = transpile(qc, sim)
        result = sim.run(qc_t, shots=n_shots).result()
    counts = result.get_counts(qc_t)

    n_unique = len(counts)
    max_count = max(counts.values())

    print(f"  Shots: {n_shots}")
    print(f"  Unique bitstrings observed: {n_unique}")
    print(f"  Max count for any single bitstring: {max_count}")

    # (a) With 8192 samples from 2^28 ≈ 268M states, essentially all
    # samples should be unique.  Allow a few birthday collisions.
    assert n_unique >= n_shots * 0.99, (
        f"Too few unique bitstrings: {n_unique} out of {n_shots} shots. "
        f"Expected nearly all unique for uniform distribution over 2^28 states."
    )
    print(f"  ✓ Nearly all bitstrings unique ({n_unique}/{n_shots} ≥ 99%)")

    # (b) No single bitstring should appear many times.
    assert max_count <= 5, (
        f"A single bitstring appeared {max_count} times — suspicious for "
        f"uniform distribution over 2^28 states."
    )
    print(f"  ✓ No bitstring dominates (max count = {max_count} ≤ 5)")

    # (c) Per-qubit marginal probability ≈ 0.5.  For each qubit, count
    # how many of the n_shots measurements had that qubit as 1.
    # Under uniform superposition, each qubit has P(1) = 0.5 exactly.
    # With n=8192, the 99.9% binomial CI is ≈ [0.446, 0.554].
    qubit_ones = [0] * TOTAL_QUBITS
    for bitstring, count in counts.items():
        # Qiskit bitstring: rightmost char = qubit 0
        for q in range(TOTAL_QUBITS):
            if bitstring[TOTAL_QUBITS - 1 - q] == '1':
                qubit_ones[q] += count

    marginals = [ones / n_shots for ones in qubit_ones]
    print(f"  Per-qubit marginal P(1) — min: {min(marginals):.4f}, "
          f"max: {max(marginals):.4f}, mean: {np.mean(marginals):.4f}")

    for q in range(TOTAL_QUBITS):
        p = marginals[q]
        assert 0.40 < p < 0.60, (
            f"Qubit {q}: marginal P(1) = {p:.4f}, far from 0.5 — "
            f"not consistent with uniform superposition."
        )
    print(f"  ✓ All {TOTAL_QUBITS} qubit marginals within [0.40, 0.60]")

    print("  ✓ Stage 2b PASSED — uniform superposition confirmed via "
          "shot-based uniformity check")


def _stage_2c() -> None:
    """Stage 2c: 2-qubit toy QUBO exact phase verification.

    Constructs a minimal 2-variable QUBO by hand:
        H_QUBO = 3*x_0 + 5*x_0*x_1

    where x_0, x_1 ∈ {0,1} mapped to qubits 0, 1.

    The 4 possible QUBO energies are:
        (x_0, x_1) = (0,0) → 0
        (x_0, x_1) = (1,0) → 3
        (x_0, x_1) = (0,1) → 0
        (x_0, x_1) = (1,1) → 3 + 5 = 8

    After QUBO→Ising conversion x_i = (1−Z_i)/2:

        H_QUBO = 3*(1-Z_0)/2 + 5*(1-Z_0)/2*(1-Z_1)/2

        Linear in Z_0:
          From 3*x_0:       -3/2
          From 5*x_0*x_1:   -5/4
          Total:             -3/2 - 5/4 = -11/4

        Linear in Z_1:
          From 5*x_0*x_1:   -5/4

        ZZ term (Z_0*Z_1):
          From 5*x_0*x_1:   +5/4

        Constant:
          From 3*x_0:       +3/2
          From 5*x_0*x_1:   +5/4
          Total:             +3/2 + 5/4 = 11/4  (dropped — global phase)

    So H_Ising = -(11/4)*Z_0  - (5/4)*Z_1  + (5/4)*Z_0*Z_1

    Starting from |+⟩|+⟩ (uniform superposition, amplitude 1/2 each),
    applying exp(-i*gamma*H_Ising) multiplies each basis state |z_0 z_1⟩
    by exp(-i*gamma * eigenvalue), where the eigenvalue of H_Ising on
    |z_0 z_1⟩ uses Z eigenvalues +1 for |0⟩ and −1 for |1⟩.

    Eigenvalues of H_Ising:
        |00⟩: Z_0=+1, Z_1=+1 → -(11/4)(+1) - (5/4)(+1) + (5/4)(+1)(+1) = -11/4 - 5/4 + 5/4 = -11/4
        |01⟩: Z_0=+1, Z_1=-1 → -(11/4)(+1) - (5/4)(-1) + (5/4)(+1)(-1) = -11/4 + 5/4 - 5/4 = -11/4
        |10⟩: Z_0=-1, Z_1=+1 → -(11/4)(-1) - (5/4)(+1) + (5/4)(-1)(+1) = +11/4 - 5/4 - 5/4 = +1/4
        |11⟩: Z_0=-1, Z_1=-1 → -(11/4)(-1) - (5/4)(-1) + (5/4)(-1)(-1) = +11/4 + 5/4 + 5/4 = +21/4

    Cross-check against QUBO energies (up to constant offset 11/4):
        |00⟩ (x=0,0): QUBO=0,  Ising eigenval = -11/4 → 0 + const  ✓ (const = -11/4, QUBO + const = -11/4)
        |01⟩ (x=0,1): QUBO=0,  Ising eigenval = -11/4 → 0 + const  ✓
        |10⟩ (x=1,0): QUBO=3,  Ising eigenval = +1/4  → 3 + const  ✓ (3 - 11/4 = 1/4)
        |11⟩ (x=1,1): QUBO=8,  Ising eigenval = +21/4 → 8 + const  ✓ (8 - 11/4 = 21/4)

    Phase applied to each state: exp(-i*gamma*eigenvalue).
    After the cost unitary, the state is:
        (1/2) * sum_{z} exp(-i*gamma*E_z) |z⟩
    """
    print("\n" + "-" * 60)
    print("Stage 2c: 2-qubit toy QUBO exact phase verification")
    print("-" * 60)

    # Build a 2-variable QUBO by hand using the same frozenset format
    # as one_hot_qubo.py, but with fake (cell, site) variable labels.
    # We use (0,0) for variable 0 and (0,1) for variable 1, which maps
    # to qubit indices 0 and 1 via cell*7+site.
    var_0 = (0, 0)  # qubit 0
    var_1 = (0, 1)  # qubit 1

    toy_qubo: QUBODict = {
        frozenset({var_0}): 3.0,                # 3 * x_0
        frozenset({var_0, var_1}): 5.0,          # 5 * x_0 * x_1
    }

    # Verify the Ising conversion matches our hand-derivation
    h_ising, J_ising = _qubo_to_ising(toy_qubo)

    print(f"  QUBO: 3*x_0 + 5*x_0*x_1")
    print(f"  Ising h coefficients: {h_ising}")
    print(f"  Ising J coefficients: {J_ising}")

    # Expected Ising coefficients (from hand derivation above):
    #   h[0] = -3/2 - 5/4 = -11/4 = -2.75
    #   h[1] = -5/4 = -1.25
    #   J[(0,1)] = +5/4 = +1.25
    assert abs(h_ising.get(0, 0.0) - (-11.0/4.0)) < 1e-12, (
        f"h[0] = {h_ising.get(0, 0.0)}, expected -11/4 = {-11.0/4.0}"
    )
    assert abs(h_ising.get(1, 0.0) - (-5.0/4.0)) < 1e-12, (
        f"h[1] = {h_ising.get(1, 0.0)}, expected -5/4 = {-5.0/4.0}"
    )
    assert abs(J_ising.get((0, 1), 0.0) - (5.0/4.0)) < 1e-12, (
        f"J[(0,1)] = {J_ising.get((0, 1), 0.0)}, expected 5/4 = {5.0/4.0}"
    )
    print("  ✓ Ising conversion coefficients match hand derivation")

    # Now build the cost unitary and test with exact statevector simulation.
    # Use a 2-qubit circuit (not the full 28-qubit one).
    gamma = 0.7  # arbitrary non-trivial angle

    # Build a 2-qubit cost unitary manually (the build_cost_unitary function
    # creates a TOTAL_QUBITS-qubit circuit, so we build a small one directly
    # to test the gate decomposition correctness).
    qc = QuantumCircuit(2, name="ToyQAOA")
    # Uniform superposition
    qc.h(0)
    qc.h(1)

    # Apply cost unitary gates manually using the Ising coefficients:
    # RZ(2*gamma*h[0]) on qubit 0
    qc.rz(2.0 * gamma * h_ising[0], 0)
    # RZ(2*gamma*h[1]) on qubit 1
    qc.rz(2.0 * gamma * h_ising[1], 1)
    # CX-RZ-CX for J[(0,1)]
    qc.cx(0, 1)
    qc.rz(2.0 * gamma * J_ising[(0, 1)], 1)
    qc.cx(0, 1)

    qc.save_statevector()

    # CPU-only for 2-qubit toy case (GPU launch overhead exceeds benefit)
    sim = AerSimulator(method="statevector")
    qc_t = transpile(qc, sim)
    result = sim.run(qc_t, shots=0).result()
    sv = result.get_statevector(qc_t)
    sv_data = np.asarray(sv.data)

    # Expected eigenvalues of H_Ising for each basis state:
    ising_eigenvalues = {
        0b00: -11.0/4.0,    # |00⟩
        0b01: -11.0/4.0,    # |01⟩  (Qiskit little-endian: bit 0 = qubit 0)
        0b10:  +1.0/4.0,    # |10⟩
        0b11: +21.0/4.0,    # |11⟩
    }

    # Wait — need to be careful about Qiskit's little-endian bit ordering.
    # In Qiskit, the basis state integer index has qubit 0 as the LEAST
    # significant bit:
    #   index 0 = |00⟩ → qubit 0 = 0, qubit 1 = 0 → Z_0=+1, Z_1=+1
    #   index 1 = |01⟩ → qubit 0 = 1, qubit 1 = 0 → Z_0=-1, Z_1=+1
    #   index 2 = |10⟩ → qubit 0 = 0, qubit 1 = 1 → Z_0=+1, Z_1=-1
    #   index 3 = |11⟩ → qubit 0 = 1, qubit 1 = 1 → Z_0=-1, Z_1=-1
    #
    # So the eigenvalue at index k uses:
    #   Z_0 = +1 if (k & 1) == 0 else -1
    #   Z_1 = +1 if (k & 2) == 0 else -1
    #
    # Recalculate:
    #   index 0: Z_0=+1, Z_1=+1 → E = -11/4(+1) - 5/4(+1) + 5/4(+1)(+1) = -11/4
    #   index 1: Z_0=-1, Z_1=+1 → E = -11/4(-1) - 5/4(+1) + 5/4(-1)(+1) = +11/4 - 5/4 - 5/4 = +1/4
    #   index 2: Z_0=+1, Z_1=-1 → E = -11/4(+1) - 5/4(-1) + 5/4(+1)(-1) = -11/4 + 5/4 - 5/4 = -11/4
    #   index 3: Z_0=-1, Z_1=-1 → E = -11/4(-1) - 5/4(-1) + 5/4(-1)(-1) = +11/4 + 5/4 + 5/4 = +21/4

    ising_eigenvalues_by_index = {
        0: -11.0/4.0,    # x=(0,0), QUBO energy = 0
        1:  +1.0/4.0,    # x=(1,0), QUBO energy = 3
        2: -11.0/4.0,    # x=(0,1), QUBO energy = 0
        3: +21.0/4.0,    # x=(1,1), QUBO energy = 8
    }

    # Cross-check: QUBO energy = Ising eigenvalue + constant (11/4)
    qubo_energies_by_index = {0: 0.0, 1: 3.0, 2: 0.0, 3: 8.0}
    const_offset = 11.0 / 4.0
    for idx in range(4):
        reconstructed = ising_eigenvalues_by_index[idx] + const_offset
        assert abs(reconstructed - qubo_energies_by_index[idx]) < 1e-12, (
            f"Index {idx}: Ising eigenval {ising_eigenvalues_by_index[idx]} + "
            f"const {const_offset} = {reconstructed}, but QUBO energy = "
            f"{qubo_energies_by_index[idx]}"
        )
    print("  ✓ Ising eigenvalues match QUBO energies (modulo constant)")

    # Expected statevector: (1/2) * exp(-i*gamma*E_k) for each basis state k
    print(f"\n  gamma = {gamma}")
    print(f"  Expected vs actual amplitudes:")

    tol = 1e-7
    for idx in range(4):
        E_k = ising_eigenvalues_by_index[idx]
        expected = 0.5 * np.exp(-1j * gamma * E_k)
        actual = sv_data[idx]

        # Compare as complex numbers
        diff = abs(actual - expected)
        status = "✓" if diff < tol else "✗"

        print(f"    |{idx:02b}⟩  expected={expected.real:+.8f}{expected.imag:+.8f}j  "
              f"actual={actual.real:+.8f}{actual.imag:+.8f}j  "
              f"diff={diff:.2e}  {status}")

        assert diff < tol, (
            f"Amplitude mismatch at |{idx:02b}⟩: expected {expected}, "
            f"got {actual}, diff = {diff}"
        )

    print("  ✓ All 4 amplitudes match expected phases exactly")

    # Additional check: verify relative phase relationships.
    # |00⟩ and |10⟩ have the same Ising eigenvalue (-11/4), so they
    # should have the same phase (same amplitude).
    assert abs(sv_data[0] - sv_data[2]) < tol, (
        f"|00⟩ and |10⟩ should have same amplitude (same Ising eigenvalue) "
        f"but got {sv_data[0]} and {sv_data[2]}"
    )
    print("  ✓ |00⟩ and |10⟩ degenerate (same QUBO energy 0) — confirmed")

    print("  ✓ Stage 2c PASSED — Ising conversion and gate decomposition "
          "verified")


def main() -> None:
    print("=" * 60)
    print("Stage 2b/2c: QAOA Circuit Statevector Sanity Tests")
    print("=" * 60)

    _stage_2b()
    _stage_2c()

    print("\n" + "=" * 60)
    print("STAGE 2b/2c: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
