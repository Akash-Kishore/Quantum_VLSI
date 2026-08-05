"""
QAOA Circuit Builder for Module 1 Placement
=============================================

Builds parameterised QAOA circuits from the one-hot QUBO defined in
``one_hot_qubo.py``, using the qubit mapping from ``qubit_mapping.py``.

QUBO-to-Ising Conversion  (x ∈ {0,1}  →  z ∈ {+1,−1})
-------------------------------------------------------
The QUBO cost function is defined over binary variables x_i ∈ {0,1}.
Qiskit's Z operator has eigenvalues +1 (for |0⟩) and −1 (for |1⟩).
The standard substitution is:

    x_i  =  (1 − Z_i) / 2

so that x_i = 0 when Z_i = +1 (state |0⟩) and x_i = 1 when Z_i = −1
(state |1⟩).

Substituting into the QUBO terms:

  **Linear term**:  h_x * x_i
    = h_x * (1 − Z_i) / 2
    = (h_x / 2) − (h_x / 2) * Z_i
    → constant: +h_x / 2  (dropped, global phase)
    → Ising linear coeff on Z_i:  −h_x / 2

  **Quadratic term**:  J_x * x_i * x_j
    = J_x * [(1 − Z_i)/2] * [(1 − Z_j)/2]
    = J_x/4 * (1 − Z_i − Z_j + Z_i*Z_j)
    → constant:  +J_x / 4  (dropped)
    → Ising linear on Z_i:  −J_x / 4
    → Ising linear on Z_j:  −J_x / 4
    → Ising quadratic Z_i*Z_j:  +J_x / 4

The cost unitary is then  exp(−i * gamma * H_Ising)  where H_Ising
contains only single-Z and Z⊗Z terms with the converted coefficients.

Gate decomposition:
  - Single Z_i with coefficient h:  →  RZ(2 * gamma * h) on qubit i
    (since exp(−i*gamma*h*Z) = RZ(2*gamma*h) up to global phase)
  - Z_i ⊗ Z_j with coefficient J:  →  CX(i,j), RZ(2*gamma*J) on j, CX(i,j)
    (standard CX-RZ-CX decomposition)

All constants (terms with no Z operators) are dropped — they contribute
only a global phase that doesn't affect measurement outcomes.
"""

from __future__ import annotations

from qiskit import QuantumCircuit

from module1_placement.qaoa.one_hot_qubo import QUBODict
from module1_placement.qaoa.qubit_mapping import (
    variable_to_qubit_index,
    TOTAL_QUBITS,
)


def _qubo_to_ising(qubo: QUBODict) -> tuple[dict[int, float], dict[tuple[int, int], float]]:
    """Convert a QUBO dict (x ∈ {0,1}) to Ising coefficients (Z ∈ {+1,−1}).

    Uses the substitution x_i = (1 − Z_i) / 2.  See module docstring for
    the full algebraic derivation.

    Parameters
    ----------
    qubo : QUBODict
        QUBO dict from ``build_qubo()``.

    Returns
    -------
    h_ising : dict[int, float]
        Single-qubit Z coefficients, keyed by qubit index.
    J_ising : dict[tuple[int, int], float]
        Two-qubit Z⊗Z coefficients, keyed by (qubit_i, qubit_j) with i < j.

    Notes
    -----
    Constant energy offset terms are dropped (global phase).
    """
    h_ising: dict[int, float] = {}
    J_ising: dict[tuple[int, int], float] = {}

    def _accum_h(qubit: int, value: float) -> None:
        h_ising[qubit] = h_ising.get(qubit, 0.0) + value

    def _accum_J(qi: int, qj: int, value: float) -> None:
        key = (min(qi, qj), max(qi, qj))
        J_ising[key] = J_ising.get(key, 0.0) + value

    for key, coeff in qubo.items():
        vars_in_key = list(key)
        if len(vars_in_key) == 1:
            # Linear QUBO term: h_x * x_i
            # → Ising linear on Z_i: −h_x / 2
            # (constant +h_x/2 dropped)
            (cell, site) = vars_in_key[0]
            qi = variable_to_qubit_index(cell, site)
            _accum_h(qi, -coeff / 2.0)

        elif len(vars_in_key) == 2:
            # Quadratic QUBO term: J_x * x_i * x_j
            # → Ising linear on Z_i:     −J_x / 4
            # → Ising linear on Z_j:     −J_x / 4
            # → Ising quadratic Z_i*Z_j: +J_x / 4
            # (constant +J_x/4 dropped)
            (cell_a, site_a) = vars_in_key[0]
            (cell_b, site_b) = vars_in_key[1]
            qi = variable_to_qubit_index(cell_a, site_a)
            qj = variable_to_qubit_index(cell_b, site_b)
            _accum_h(qi, -coeff / 4.0)
            _accum_h(qj, -coeff / 4.0)
            _accum_J(qi, qj, coeff / 4.0)

        else:
            raise ValueError(
                f"QUBO key has {len(vars_in_key)} variables (expected 1 or 2): {key}"
            )

    return h_ising, J_ising


def build_cost_unitary(qubo: QUBODict, gamma: float) -> QuantumCircuit:
    """Build the QAOA cost unitary exp(−i·γ·H_C) for the given QUBO.

    The QUBO is first converted from {0,1} variables to {+1,−1} Ising
    spins via x_i = (1 − Z_i)/2, then decomposed into RZ and CX-RZ-CX
    gates.  See the module docstring for the full algebraic derivation.

    Parameters
    ----------
    qubo : QUBODict
        QUBO dict from ``build_qubo()``.
    gamma : float
        QAOA cost-layer angle parameter.

    Returns
    -------
    QuantumCircuit
        A ``TOTAL_QUBITS``-qubit circuit implementing the cost unitary.
    """
    h_ising, J_ising = _qubo_to_ising(qubo)

    qc = QuantumCircuit(TOTAL_QUBITS, name="CostUnitary")

    # Single-qubit Z rotations: exp(−i*gamma*h*Z) = RZ(2*gamma*h)
    for qubit, h in sorted(h_ising.items()):
        angle = 2.0 * gamma * h
        if abs(angle) > 1e-15:  # skip truly zero rotations
            qc.rz(angle, qubit)

    # Two-qubit ZZ interactions: CX-RZ-CX decomposition
    # exp(−i*gamma*J*Z_i⊗Z_j) via CX(i,j), RZ(2*gamma*J, j), CX(i,j)
    for (qi, qj), J in sorted(J_ising.items()):
        angle = 2.0 * gamma * J
        if abs(angle) > 1e-15:  # skip truly zero rotations
            qc.cx(qi, qj)
            qc.rz(angle, qj)
            qc.cx(qi, qj)

    return qc


def build_mixer_unitary(n_qubits: int, beta: float) -> QuantumCircuit:
    """Build the standard transverse-field mixer unitary.

    Applies RX(2·β) on every qubit:
        exp(−i·β·Σ_i X_i) = ⊗_i RX(2·β)

    Parameters
    ----------
    n_qubits : int
        Number of qubits.
    beta : float
        QAOA mixer-layer angle parameter.

    Returns
    -------
    QuantumCircuit
        An ``n_qubits``-qubit circuit implementing the mixer unitary.
    """
    qc = QuantumCircuit(n_qubits, name="MixerUnitary")
    for i in range(n_qubits):
        qc.rx(2.0 * beta, i)
    return qc


def build_qaoa_circuit(
    qubo: QUBODict,
    gammas: list[float],
    betas: list[float],
    n_qubits: int = TOTAL_QUBITS,
) -> QuantumCircuit:
    """Build a complete p-layer QAOA circuit with measurement.

    Structure:
      1. Hadamard on all qubits (uniform superposition initialisation)
      2. For each layer k = 0, ..., p−1:
         a. Cost unitary with gamma[k]
         b. Mixer unitary with beta[k]
      3. Measure all qubits

    Parameters
    ----------
    qubo : QUBODict
        QUBO dict from ``build_qubo()``.
    gammas : list[float]
        Cost-layer angles, one per layer.
    betas : list[float]
        Mixer-layer angles, one per layer.
    n_qubits : int
        Number of qubits (default 28).

    Returns
    -------
    QuantumCircuit
        The full QAOA circuit with classical register for measurement.

    Raises
    ------
    ValueError
        If ``len(gammas) != len(betas)`` (layer count mismatch).
    """
    p = len(gammas)
    if len(betas) != p:
        raise ValueError(
            f"gammas and betas must have the same length, "
            f"got {len(gammas)} and {len(betas)}"
        )

    qc = QuantumCircuit(n_qubits, n_qubits, name="QAOA")

    # Step 1: Uniform superposition initialisation
    for i in range(n_qubits):
        qc.h(i)

    # Step 2: Alternating cost/mixer layers
    for k in range(p):
        # Cost unitary
        cost_layer = build_cost_unitary(qubo, gammas[k])
        qc.compose(cost_layer, qubits=range(n_qubits), inplace=True)
        qc.barrier()

        # Mixer unitary
        mixer_layer = build_mixer_unitary(n_qubits, betas[k])
        qc.compose(mixer_layer, qubits=range(n_qubits), inplace=True)
        qc.barrier()

    # Step 3: Measurement
    qc.measure(range(n_qubits), range(n_qubits))

    # Project convention: hard assert on qubit count
    assert qc.num_qubits == n_qubits, (
        f"QAOA circuit qubit count {qc.num_qubits} != expected {n_qubits}. "
        f"A compose/append call likely changed the qubit count."
    )

    return qc
