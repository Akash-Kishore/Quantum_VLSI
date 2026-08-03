"""
Generalized ATPG Oracle — 10-Qubit Unified Template
=====================================================

Builds a Grover phase-flip oracle for **any** member of the 11-site
generalized fault family defined in ``fault_family.py``.

Qubit layout (10 total):

======  ================================================
Qubit   Purpose
======  ================================================
q0–q2   Search register: A, B, Cin
q3      t_good ancilla  — always computes A ⊕ B
q4      Cout_good ancilla — always computes AB ⊕ BC ⊕ AC
q5      Sum_good ancilla  — always computes t_good ⊕ Cin
q6      t_faulty ancilla  — per fault site
q7      Cout_faulty ancilla — per fault site
q8      Sum_faulty ancilla — per fault site
q9      flag ancilla — (Cout_good⊕Cout_faulty) ⊕ (Sum_good⊕Sum_faulty)
======  ================================================

The oracle follows the established compute→Z→uncompute pattern,
building both good and faulty blocks as a single condition subcircuit,
XOR-ing results into the flag qubit, then uncomputing in **strict
reverse order** of the forward pass.

**Critical design note on uncomputation ordering:**

Sum depends on T (Sum = T ⊕ Cin), so T must still hold its forward-pass
value when Sum is being uncomputed.  This means each computation
sub-step (T, Cout, Sum) must be individually callable so the reverse
pass can undo them in exact reverse order:

    Forward:  T_good → Cout_good → Sum_good → T_faulty → Cout_faulty → Sum_faulty → flag
    Reverse:  flag → Sum_faulty → Cout_faulty → T_faulty → Sum_good → Cout_good → T_good

If Sum were uncomputed after T has already been reset, the CX(T→Sum)
gate would XOR 0 instead of the forward-pass value, leaving Sum stuck.

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

from qiskit import QuantumCircuit

from module2_atpg.generalized_faults.fault_family import FaultSite


# ---------------------------------------------------------------------------
# Qubit index constants
# ---------------------------------------------------------------------------
A, B, CIN = 0, 1, 2
T_GOOD = 3
COUT_GOOD = 4
SUM_GOOD = 5
T_FAULTY = 6
COUT_FAULTY = 7
SUM_FAULTY = 8
FLAG = 9

NUM_QUBITS = 10


# ---------------------------------------------------------------------------
# Good block — split into three independently-callable sub-steps
# ---------------------------------------------------------------------------

def _compute_t_good(qc: QuantumCircuit) -> None:
    """Compute t_good = A ⊕ B into q3.  Self-inverse.

    Parameters
    ----------
    qc : QuantumCircuit
        Circuit to append to (modified in-place).
    """
    qc.cx(A, T_GOOD)
    qc.cx(B, T_GOOD)


def _compute_cout_good(qc: QuantumCircuit) -> None:
    """Compute Cout_good = AB ⊕ BC ⊕ AC into q4.  Self-inverse.

    Parameters
    ----------
    qc : QuantumCircuit
        Circuit to append to (modified in-place).
    """
    qc.ccx(A, B, COUT_GOOD)
    qc.ccx(B, CIN, COUT_GOOD)
    qc.ccx(A, CIN, COUT_GOOD)


def _compute_sum_good(qc: QuantumCircuit) -> None:
    """Compute Sum_good = t_good ⊕ Cin into q5.  Self-inverse.

    Requires t_good (q3) to already hold its forward-pass value.

    Parameters
    ----------
    qc : QuantumCircuit
        Circuit to append to (modified in-place).
    """
    qc.cx(T_GOOD, SUM_GOOD)
    qc.cx(CIN, SUM_GOOD)


# ---------------------------------------------------------------------------
# Faulty block — split into three independently-callable sub-steps
# ---------------------------------------------------------------------------

def _compute_t_faulty(qc: QuantumCircuit, fault_site: FaultSite) -> None:
    """Compute t_faulty into q6, per fault site.  Self-inverse.

    - xor_chain/line1: forced to stuck_at constant (X if 1, nothing if 0).
    - All others: identical to good block (t_faulty = A ⊕ B).

    Parameters
    ----------
    qc : QuantumCircuit
        Circuit to append to (modified in-place).
    fault_site : FaultSite
        The fault to inject.
    """
    if (fault_site.fault_class == "xor_chain"
            and fault_site.identifier == "line1"):
        if fault_site.stuck_at == 1:
            qc.x(T_FAULTY)
    else:
        qc.cx(A, T_FAULTY)
        qc.cx(B, T_FAULTY)


def _compute_cout_faulty(qc: QuantumCircuit, fault_site: FaultSite) -> None:
    """Compute Cout_faulty into q7, per fault site.  Self-inverse.

    - product_term: three Toffolis with the matching term replaced by
      X (SA1) or omitted (SA0).
    - All others: identical to good block.

    Parameters
    ----------
    qc : QuantumCircuit
        Circuit to append to (modified in-place).
    fault_site : FaultSite
        The fault to inject.
    """
    if fault_site.fault_class == "product_term":
        term_controls = {"AB": (A, B), "BC": (B, CIN), "AC": (A, CIN)}
        for term, (c1, c2) in term_controls.items():
            if term == fault_site.identifier:
                if fault_site.stuck_at == 1:
                    qc.x(COUT_FAULTY)
            else:
                qc.ccx(c1, c2, COUT_FAULTY)
    else:
        qc.ccx(A, B, COUT_FAULTY)
        qc.ccx(B, CIN, COUT_FAULTY)
        qc.ccx(A, CIN, COUT_FAULTY)


def _compute_sum_faulty(qc: QuantumCircuit, fault_site: FaultSite) -> None:
    """Compute Sum_faulty into q8, per fault site.  Self-inverse.

    - xor_chain/line2: forced to stuck_at constant (X if 1, nothing if 0).
    - All others: Sum_faulty = t_faulty ⊕ Cin.  For xor_chain/line1,
      t_faulty is already wrong, correctly propagating the fault.

    Requires t_faulty (q6) to already hold its forward-pass value.

    Parameters
    ----------
    qc : QuantumCircuit
        Circuit to append to (modified in-place).
    fault_site : FaultSite
        The fault to inject.
    """
    if (fault_site.fault_class == "xor_chain"
            and fault_site.identifier == "line2"):
        if fault_site.stuck_at == 1:
            qc.x(SUM_FAULTY)
    else:
        qc.cx(T_FAULTY, SUM_FAULTY)
        qc.cx(CIN, SUM_FAULTY)


# ---------------------------------------------------------------------------
# Flag computation
# ---------------------------------------------------------------------------

def _append_flag_xor(qc: QuantumCircuit) -> None:
    """XOR good/faulty outputs into the flag ancilla.

    flag = (Cout_good ⊕ Cout_faulty) ⊕ (Sum_good ⊕ Sum_faulty)

    Since product-term faults never affect Sum and XOR-chain faults
    never affect Cout, at most one of the two XOR-difference terms is
    ever nonzero, so this XOR serves as an implicit OR.

    Self-inverse: calling twice uncomputes.

    Parameters
    ----------
    qc : QuantumCircuit
        Circuit to append to (modified in-place).
    """
    qc.cx(COUT_GOOD, FLAG)
    qc.cx(COUT_FAULTY, FLAG)
    qc.cx(SUM_GOOD, FLAG)
    qc.cx(SUM_FAULTY, FLAG)


# ---------------------------------------------------------------------------
# Full oracle builder
# ---------------------------------------------------------------------------

def build_generalized_atpg_oracle(fault_site: FaultSite) -> QuantumCircuit:
    """Build the 10-qubit ATPG comparison oracle for a given fault site.

    Implements the unified oracle template with granular uncomputation:

    Forward pass::

        T_good → Cout_good → Sum_good →
        T_faulty → Cout_faulty → Sum_faulty →
        flag XOR → Z(flag)

    Reverse pass (strict reverse order)::

        flag XOR →
        Sum_faulty → Cout_faulty → T_faulty →
        Sum_good → Cout_good → T_good

    Each sub-step is self-inverse, so calling it again uncomputes it.
    The reverse ordering ensures Sum is uncomputed while T still holds
    its forward-pass value (since Sum = T ⊕ Cin depends on T).

    For the **control** (fault-free) fault site, the faulty block is
    byte-for-byte identical to the good block — no gate differs.  This
    means the flag qubit is never flipped, so the Z gate has no effect,
    and the oracle reduces to the identity on the search register's
    phase.  This is the concrete circuit-level demonstration of the
    M=0 fixed-point lemma.

    Parameters
    ----------
    fault_site : FaultSite
        The fault to inject (from ``enumerate_fault_sites()``).

    Returns
    -------
    QuantumCircuit
        The 10-qubit phase-flip oracle circuit.
    """
    oracle = QuantumCircuit(NUM_QUBITS, name=f"GenATEG_{fault_site.identifier}")

    # --- Forward pass: compute the comparison flag ---
    _compute_t_good(oracle)
    _compute_cout_good(oracle)
    _compute_sum_good(oracle)

    _compute_t_faulty(oracle, fault_site)
    _compute_cout_faulty(oracle, fault_site)
    _compute_sum_faulty(oracle, fault_site)

    _append_flag_xor(oracle)

    # --- Phase kickback ---
    oracle.z(FLAG)

    # --- Reverse pass: uncompute in strict reverse order ---
    _append_flag_xor(oracle)

    _compute_sum_faulty(oracle, fault_site)
    _compute_cout_faulty(oracle, fault_site)
    _compute_t_faulty(oracle, fault_site)

    _compute_sum_good(oracle)
    _compute_cout_good(oracle)
    _compute_t_good(oracle)

    assert oracle.num_qubits == NUM_QUBITS, (
        f"Oracle should have {NUM_QUBITS} qubits, got {oracle.num_qubits}"
    )
    return oracle
