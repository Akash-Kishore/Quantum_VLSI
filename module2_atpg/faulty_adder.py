"""
Faulty 1-Bit Full Adder — Carry-Out Only (Stuck-at-0 on AB Term)
=================================================================

Identical to the fault-free carry-out computation, **except the first
Toffoli gate** (``ccx(a, b, cout_ancilla)`` — the AB term) **is
omitted entirely**.

This models a **stuck-at-0 fault** on the AB contribution: the gate
that would normally XOR the AB term into the carry-out accumulator
never fires, so that term is permanently 0 regardless of A and B.
The remaining two terms (BC, AC) are computed normally.

As a result::

    Cout_faulty = BC ⊕ AC     (missing the AB term)

The fault is detected whenever the true AB product is 1, i.e. whenever
``A=1 AND B=1``, regardless of Cin.  This gives two fault-detecting
inputs: ``(A,B,Cin) = (1,1,0)`` and ``(1,1,1)``.

**Self-inverse property**: calling this function again on the same
qubits uncomputes the result, restoring ``cout_ancilla`` to ``|0⟩``.
"""

from __future__ import annotations

from qiskit import QuantumCircuit


def append_faulty_cout(
    qc: QuantumCircuit,
    a: int,
    b: int,
    cin: int,
    cout_ancilla: int,
) -> None:
    """Append the faulty carry-out computation onto *qc*.

    Applies only two of the three Toffoli gates — the AB term is
    stuck-at-0 (omitted)::

        # ccx(a, b, cout_ancilla) — OMITTED (stuck-at-0)
        cout_ancilla ^= B·Cin (via ccx(b, cin, cout_ancilla))
        cout_ancilla ^= A·Cin (via ccx(a, cin, cout_ancilla))

    After this, ``cout_ancilla`` holds ``BC ⊕ AC`` (assuming it started
    at ``|0⟩``), **not** the correct ``AB ⊕ BC ⊕ AC``.

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
        Qubit index for the faulty carry-out ancilla (must start at
        ``|0⟩``).
    """
    # AB term OMITTED — stuck-at-0 fault
    qc.ccx(b, cin, cout_ancilla)    # BC term
    qc.ccx(a, cin, cout_ancilla)    # AC term
