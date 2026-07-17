"""
Oracle Construction for Grover's Algorithm
===========================================

Provides two oracle-building functions:

1. ``bitstring_oracle`` — marks one or more known bitstrings via
   multi-controlled-Z logic (X on 0-bits, MCZ, X to uncompute).

2. ``constraint_oracle`` — lower-level helper that accepts an arbitrary
   condition sub-circuit plus an ancilla qubit. It composes:
   compute → phase-kickback via CZ → uncompute, enabling constraint-based
   oracles needed by Module 1 (placement) and Module 2 (ATPG).

All oracles implement the phase-flip convention:
    O|x⟩ = (-1)^{f(x)} |x⟩
"""

from __future__ import annotations

from typing import List, Union

from qiskit import QuantumCircuit


def _mcz(circuit: QuantumCircuit, qubits: List[int]) -> None:
    """Apply a multi-controlled-Z gate on *qubits* (last qubit is the target).

    Decomposition: H(target) → MCX(controls, target) → H(target).

    Parameters
    ----------
    circuit : QuantumCircuit
        The circuit to append the MCZ to (in-place).
    qubits : list[int]
        Qubit indices; all but the last are controls, the last is the target.
    """
    if len(qubits) < 2:
        # Single-qubit "MCZ" is just a Z gate.
        circuit.z(qubits[0])
        return
    target = qubits[-1]
    controls = qubits[:-1]
    circuit.h(target)
    circuit.mcx(controls, target)
    circuit.h(target)


def bitstring_oracle(
    n_qubits: int,
    marked_states: Union[str, List[str]],
) -> QuantumCircuit:
    """Build a phase-flip oracle for one or more marked bitstrings.

    For each marked bitstring the oracle applies:
      1. X gates on every qubit whose bit value is 0 in the bitstring.
      2. Multi-controlled-Z across all qubits.
      3. X gates again to uncompute step 1.

    Parameters
    ----------
    n_qubits : int
        Number of qubits in the search space.
    marked_states : str or list[str]
        Target bitstring(s), e.g. ``"11"`` or ``["01", "10"]``.
        Each string must have length ``n_qubits``.  Bit ordering is
        big-endian: the leftmost character is qubit ``n_qubits - 1``.

    Returns
    -------
    QuantumCircuit
        A circuit on ``n_qubits`` qubits implementing the phase oracle.

    Raises
    ------
    ValueError
        If any bitstring length does not match ``n_qubits``.
    """
    if isinstance(marked_states, str):
        marked_states = [marked_states]

    oracle = QuantumCircuit(n_qubits, name="Oracle")

    for bitstring in marked_states:
        if len(bitstring) != n_qubits:
            raise ValueError(
                f"Bitstring '{bitstring}' has length {len(bitstring)}, "
                f"expected {n_qubits}."
            )

        # --- flip 0-bits so that |bitstring⟩ maps to |11...1⟩ ----------
        for i, bit in enumerate(reversed(bitstring)):
            if bit == "0":
                oracle.x(i)

        # --- multi-controlled-Z on |11...1⟩ ----------------------------
        _mcz(oracle, list(range(n_qubits)))

        # --- uncompute the X gates ------------------------------------
        for i, bit in enumerate(reversed(bitstring)):
            if bit == "0":
                oracle.x(i)

    return oracle


def constraint_oracle(
    n_qubits: int,
    condition_circuit: QuantumCircuit,
    ancilla_index: int,
) -> QuantumCircuit:
    """Build a phase-flip oracle from an arbitrary condition sub-circuit.

    The pattern is:
      1. Apply *condition_circuit* (computes f(x) into the ancilla qubit).
      2. Apply a Z gate on the ancilla (phase-kickback: |1⟩ → -|1⟩).
      3. Apply the inverse of *condition_circuit* (uncompute the ancilla).

    This gives O|x⟩|0⟩ = (-1)^{f(x)} |x⟩|0⟩, matching the standard
    Grover phase oracle convention, provided the condition circuit flips
    the ancilla to |1⟩ exactly when x satisfies the constraint.

    Parameters
    ----------
    n_qubits : int
        Total number of qubits (data + ancilla) in *condition_circuit*.
    condition_circuit : QuantumCircuit
        A circuit on ``n_qubits`` qubits that computes the Boolean
        constraint into the ancilla qubit at index ``ancilla_index``.
        Must be unitary so that its inverse exists.
    ancilla_index : int
        Index of the ancilla qubit that the condition circuit writes to.

    Returns
    -------
    QuantumCircuit
        A circuit on ``n_qubits`` qubits implementing the phase oracle.
    """
    oracle = QuantumCircuit(n_qubits, name="ConstraintOracle")

    # 1. Compute the constraint into the ancilla.
    oracle.compose(condition_circuit, inplace=True)

    # 2. Phase-kickback: Z on the ancilla flips the phase of |1⟩ states.
    oracle.z(ancilla_index)

    # 3. Uncompute the ancilla.
    oracle.compose(condition_circuit.inverse(), inplace=True)

    return oracle
