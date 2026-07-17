"""
Fault-Free 1-Bit Full Adder — Carry-Out Only (Reversible)
==========================================================

Computes carry-out as ``Cout = AB ⊕ BC ⊕ AC`` using three Toffoli gates
that XOR-accumulate their AND terms into a single ``cout_ancilla`` qubit.

This is a reversible implementation: calling the function twice on the
same qubits uncomputes the result (each Toffoli XORs, and XOR is its
own inverse), restoring ``cout_ancilla`` to its original state.

Sum is intentionally not computed — the ATPG stuck-at fault in this
module only affects carry-out, so Sum logic would add ancillas for
zero benefit.
"""

from __future__ import annotations

from qiskit import QuantumCircuit


def append_fault_free_cout(
    qc: QuantumCircuit,
    a: int,
    b: int,
    cin: int,
    cout_ancilla: int,
) -> None:
    """Append the fault-free carry-out computation onto *qc*.

    Applies three Toffoli gates to XOR-accumulate the carry terms::

        cout_ancilla ^= A·B   (via ccx(a, b, cout_ancilla))
        cout_ancilla ^= B·Cin (via ccx(b, cin, cout_ancilla))
        cout_ancilla ^= A·Cin (via ccx(a, cin, cout_ancilla))

    After this, ``cout_ancilla`` holds ``AB ⊕ BC ⊕ AC`` (assuming it
    started at ``|0⟩``).

    **Self-inverse property**: calling this function again on the same
    qubits uncomputes the result, returning ``cout_ancilla`` to ``|0⟩``.

    Parameters
    ----------
    qc : QuantumCircuit
        The circuit to append to (modified in-place).
    a : int
        Qubit index for input A.
    b : int
        Qubit index for input B.
    cin : int
        Qubit index for carry-in (Cin).
    cout_ancilla : int
        Qubit index for the carry-out ancilla (must start at ``|0⟩``).
    """
    qc.ccx(a, b, cout_ancilla)      # AB term
    qc.ccx(b, cin, cout_ancilla)    # BC term
    qc.ccx(a, cin, cout_ancilla)    # AC term
