"""
ATPG Comparison Oracle (6 Qubits)
==================================

Builds the Grover phase-flip oracle that marks input states (A, B, Cin)
for which the fault-free and faulty carry-out values **disagree** — i.e.,
states that detect the stuck-at-0 fault on the AB term.

Qubit layout (6 total):

    q0 — A   (search register)
    q1 — B   (search register)
    q2 — Cin (search register)
    q3 — Fault-free Cout ancilla
    q4 — Faulty Cout ancilla
    q5 — Flag ancilla (1 iff q3 ⊕ q4, i.e. fault detected)

The oracle uses ``shared_framework.oracle.constraint_oracle``'s
compute → Z-kickback → uncompute pattern.  However, since
``constraint_oracle`` performs its own compose + Z + inverse
internally, and the ATPG comparison circuit's uncomputation requires
a specific ordering (reverse of the forward pass, respecting the
self-inverse property of the adder functions), we replicate the
identical pattern manually here for full control over the gate
ordering.

Oracle structure:
  1. Compute fault-free Cout into q3.
  2. Compute faulty Cout into q4.
  3. CNOT q3 → q5, CNOT q4 → q5  (q5 = Cout_good ⊕ Cout_faulty).
  4. Z on q5 — phase-kickback: (-1)^{flag}.
  5. Uncompute: CNOT q4 → q5, CNOT q3 → q5, faulty adder on
     (q0,q1,q2,q4), fault-free adder on (q0,q1,q2,q3).
     All ancillas return to |0⟩.
"""

from __future__ import annotations

from qiskit import QuantumCircuit

from module2_atpg.full_adder import append_fault_free_cout
from module2_atpg.faulty_adder import append_faulty_cout


def build_atpg_oracle() -> QuantumCircuit:
    """Build the 6-qubit ATPG comparison oracle.

    Returns a ``QuantumCircuit`` on 6 qubits that applies the phase flip
    ``(-1)^{f(A,B,Cin)}`` where ``f=1`` exactly when the fault-free and
    faulty carry-out values disagree (i.e. when ``A=1, B=1``).

    All ancilla qubits (q3–q5) are guaranteed to start and end at
    ``|0⟩``, so the oracle can be applied repeatedly inside a Grover
    loop without ancilla contamination.

    Returns
    -------
    QuantumCircuit
        The 6-qubit phase-flip oracle circuit.
    """
    oracle = QuantumCircuit(6, name="ATPG_Oracle")

    # Qubit assignments
    A, B, Cin = 0, 1, 2
    COUT_GOOD = 3
    COUT_FAULTY = 4
    FLAG = 5

    # --- Forward pass: compute the comparison flag ---

    # 1. Fault-free Cout → q3
    append_fault_free_cout(oracle, A, B, Cin, COUT_GOOD)

    # 2. Faulty Cout → q4
    append_faulty_cout(oracle, A, B, Cin, COUT_FAULTY)

    # 3. XOR the two carry-outs into the flag qubit
    #    q5 = q3 ⊕ q4 (1 exactly when they disagree)
    oracle.cx(COUT_GOOD, FLAG)
    oracle.cx(COUT_FAULTY, FLAG)

    # --- Phase kickback ---

    # 4. Z on the flag qubit: |1⟩ → -|1⟩, |0⟩ → |0⟩
    #    This is the same compute→Z→uncompute pattern used by
    #    shared_framework.oracle.constraint_oracle.
    oracle.z(FLAG)

    # --- Reverse pass: uncompute all ancillas ---

    # 5. Undo the XOR (CNOT is self-inverse, reverse order)
    oracle.cx(COUT_FAULTY, FLAG)
    oracle.cx(COUT_GOOD, FLAG)

    # 6. Undo faulty Cout (self-inverse)
    append_faulty_cout(oracle, A, B, Cin, COUT_FAULTY)

    # 7. Undo fault-free Cout (self-inverse)
    append_fault_free_cout(oracle, A, B, Cin, COUT_GOOD)

    return oracle
