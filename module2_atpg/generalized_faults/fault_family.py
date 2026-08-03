"""
Generalized Fault Family — Pure-Python Boolean Model
=====================================================

Pure-Python (no Qiskit) Boolean model of the 1-bit full adder with
parameterised fault injection for any member of the following fault
family:

1. **Product-term stuck-at faults** on Cout  (AB, BC, AC × {0, 1} = 6 instances)
2. **XOR-chain stuck-at faults** on Sum    (line1, line2 × {0, 1} = 4 instances)
3. **Fault-free control**                   (1 instance)

Total enumerated fault sites: **11**.

.. note::

   The informal Phase-6 planning language described "six real fault
   classes plus control = 7".  That count pre-dates the explicit
   per-line / per-direction enumeration worked out here.  The correct
   count after full enumeration is 6 + 4 + 1 = **11**, not 7.  This
   discrepancy is intentional and expected.

This module does NOT import Qiskit.  It is a pure-Python reference
implementation used to:

* algebraically derive M (number of detecting inputs out of N = 8)
  for each fault site,
* brute-force validate those derivations, and
* serve as a ground-truth specification for the quantum oracle
  circuits that will be built in Stage 2.

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

No Qiskit import appears anywhere in this file.
No scipy import appears anywhere in this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FaultSite:
    """Description of a single injectable fault in the 1-bit full adder.

    Attributes
    ----------
    fault_class : str
        One of ``"product_term"``, ``"xor_chain"``, or ``"control"``.
    identifier : str
        Which term or line is affected.
        - For product-term faults: ``"AB"``, ``"BC"``, or ``"AC"``.
        - For XOR-chain faults: ``"line1"`` (t = A ⊕ B) or ``"line2"``
          (Sum = t ⊕ Cin).
        - For control: ``"none"``.
    stuck_at : Optional[int]
        ``0`` or ``1`` for real faults; ``None`` for the fault-free control.
    derived_m : int
        Analytically derived number of detecting inputs (out of N = 8).
    proof : str
        Human-readable algebraic derivation of ``derived_m``.
    """

    fault_class: str
    identifier: str
    stuck_at: Optional[int]
    derived_m: int
    proof: str

    def __str__(self) -> str:
        """Human-readable one-line summary."""
        sa = f"SA{self.stuck_at}" if self.stuck_at is not None else "none"
        return (
            f"{self.fault_class:13s}  {self.identifier:6s}  "
            f"{sa:5s}  M={self.derived_m}"
        )


# ---------------------------------------------------------------------------
# Fault-free reference evaluation
# ---------------------------------------------------------------------------

def evaluate_full_adder(a: int, b: int, cin: int) -> Tuple[int, int]:
    """Evaluate the fault-free 1-bit full adder.

    Parameters
    ----------
    a, b, cin : int
        Single-bit inputs (0 or 1).

    Returns
    -------
    (cout, sum_) : tuple[int, int]
        ``cout = AB ⊕ BC ⊕ AC``
        ``sum_ = A ⊕ B ⊕ Cin``
    """
    ab = a & b
    bc = b & cin
    ac = a & cin
    cout = ab ^ bc ^ ac
    sum_ = a ^ b ^ cin
    return (cout, sum_)


# ---------------------------------------------------------------------------
# Faulty evaluation
# ---------------------------------------------------------------------------

def evaluate_faulty(fault_site: FaultSite, a: int, b: int, cin: int) -> Tuple[int, int]:
    """Evaluate the 1-bit full adder with a single fault injected.

    For ``"product_term"`` faults, only Cout is affected (Sum is
    computed identically to the fault-free case).  For ``"xor_chain"``
    faults, only Sum is affected (Cout is computed identically to the
    fault-free case).  For ``"control"``, both outputs match the
    fault-free reference.

    Parameters
    ----------
    fault_site : FaultSite
        The fault to inject.
    a, b, cin : int
        Single-bit inputs (0 or 1).

    Returns
    -------
    (cout, sum_) : tuple[int, int]
        The (possibly faulty) carry-out and sum.
    """
    # --- Cout computation (affected only by product-term faults) ---
    ab = a & b
    bc = b & cin
    ac = a & cin

    if fault_site.fault_class == "product_term":
        term_map = {"AB": 0, "BC": 1, "AC": 2}
        terms = [ab, bc, ac]
        idx = term_map[fault_site.identifier]
        # Override the identified term with the stuck-at value
        terms[idx] = fault_site.stuck_at  # type: ignore[assignment]
        cout = terms[0] ^ terms[1] ^ terms[2]
    else:
        cout = ab ^ bc ^ ac  # fault-free

    # --- Sum computation (affected only by XOR-chain faults) ---
    if fault_site.fault_class == "xor_chain":
        if fault_site.identifier == "line1":
            # Line 1 computes t = A ⊕ B.
            # Stuck-at forces the output of this gate.
            t = fault_site.stuck_at  # type: ignore[assignment]
            sum_ = t ^ cin
        else:  # line2
            # Line 2 computes Sum = t ⊕ Cin, where t = A ⊕ B (computed correctly).
            # Stuck-at forces the output of this gate.
            t = a ^ b
            # The output of the line-2 gate is forced.
            sum_ = fault_site.stuck_at  # type: ignore[assignment]
    else:
        sum_ = a ^ b ^ cin  # fault-free

    return (cout, sum_)


# ---------------------------------------------------------------------------
# Brute-force detecting-input counter
# ---------------------------------------------------------------------------

def count_detecting_inputs(fault_site: FaultSite) -> int:
    """Count the number of inputs that detect the given fault, by brute force.

    An input ``(a, b, cin)`` is *detecting* if and only if:

    - For ``"product_term"`` faults: the faulty Cout differs from the
      fault-free Cout.
    - For ``"xor_chain"`` faults: the faulty Sum differs from the
      fault-free Sum.
    - For ``"control"``: there is never a disagreement (by definition).

    Parameters
    ----------
    fault_site : FaultSite
        The fault to test.

    Returns
    -------
    int
        Number of detecting inputs out of N = 8.
    """
    count = 0
    for a in range(2):
        for b in range(2):
            for cin in range(2):
                good_cout, good_sum = evaluate_full_adder(a, b, cin)
                bad_cout, bad_sum = evaluate_faulty(fault_site, a, b, cin)

                if fault_site.fault_class == "product_term":
                    if bad_cout != good_cout:
                        count += 1
                elif fault_site.fault_class == "xor_chain":
                    if bad_sum != good_sum:
                        count += 1
                # control: never detected
    return count


def get_detecting_inputs(fault_site: FaultSite) -> List[Tuple[int, int, int]]:
    """Return the set of detecting input tuples for the given fault.

    Parameters
    ----------
    fault_site : FaultSite
        The fault to test.

    Returns
    -------
    list[tuple[int, int, int]]
        Each element is ``(a, b, cin)`` that detects the fault.
    """
    result: List[Tuple[int, int, int]] = []
    for a in range(2):
        for b in range(2):
            for cin in range(2):
                good_cout, good_sum = evaluate_full_adder(a, b, cin)
                bad_cout, bad_sum = evaluate_faulty(fault_site, a, b, cin)

                if fault_site.fault_class == "product_term":
                    if bad_cout != good_cout:
                        result.append((a, b, cin))
                elif fault_site.fault_class == "xor_chain":
                    if bad_sum != good_sum:
                        result.append((a, b, cin))
    return result


# ---------------------------------------------------------------------------
# Algebraic proofs (as strings) for each fault site
# ---------------------------------------------------------------------------

_PRODUCT_TERM_SA0_PROOF_TEMPLATE = """\
Product-term {term} stuck-at-0 on Cout.

Cout_good = AB ⊕ BC ⊕ AC.
Cout_faulty = Cout_good with {term}'s contribution forced to 0.

Since XOR is associative/commutative and the three product terms are
accumulated via XOR, forcing one term T to 0 changes the accumulated
result exactly when the true value of T is 1 (because 0 ⊕ rest ≠
1 ⊕ rest iff and only iff the removed contribution is 1).

The term {term} = {var1}·{var2}.  Over 3 independent uniform bits
(A, B, Cin), each pair of distinct variables is independent, and
{var1}·{var2} = 1 for exactly 1 of 4 assignments to ({var1}, {var2}).
Since the third variable {var3} is free (0 or 1), the number of
inputs where {term} = 1 is 1 × 2 = 2 out of 8.

Therefore M = 2 = N/4.

Symmetry note: the same argument applies identically to all three
terms (AB, BC, AC) because A, B, Cin enter the full-adder carry
equation symmetrically — any permutation of (A, B, Cin) merely
relabels the three product terms without changing the XOR structure.\
"""

_PRODUCT_TERM_SA1_PROOF_TEMPLATE = """\
Product-term {term} stuck-at-1 on Cout.

Cout_good = AB ⊕ BC ⊕ AC.
Cout_faulty = Cout_good with {term}'s contribution forced to 1.

Forcing T to 1 changes the accumulated XOR result exactly when the
true value of T is 0 (because 1 ⊕ rest ≠ 0 ⊕ rest iff and only iff
the forced contribution differs from the true one, which happens when
T = 0).

The term {term} = {var1}·{var2} is 0 for exactly 3 of 4 assignments
to ({var1}, {var2}).  With the third variable {var3} free (0 or 1),
the number of inputs where {term} = 0 is 3 × 2 = 6 out of 8.

Therefore M = 6 = 3N/4.

Symmetry note: the same argument applies identically to all three
terms (AB, BC, AC) because A, B, Cin enter the full-adder carry
equation symmetrically — any permutation of (A, B, Cin) merely
relabels the three product terms without changing the XOR structure.\
"""


def _product_term_proof(term: str, stuck_at: int) -> str:
    """Generate the algebraic proof string for a product-term fault.

    Parameters
    ----------
    term : str
        One of ``"AB"``, ``"BC"``, ``"AC"``.
    stuck_at : int
        0 or 1.

    Returns
    -------
    str
        Multi-line proof string.
    """
    var_map = {"AB": ("A", "B", "Cin"), "BC": ("B", "Cin", "A"), "AC": ("A", "Cin", "B")}
    var1, var2, var3 = var_map[term]
    template = (
        _PRODUCT_TERM_SA0_PROOF_TEMPLATE if stuck_at == 0
        else _PRODUCT_TERM_SA1_PROOF_TEMPLATE
    )
    return template.format(term=term, var1=var1, var2=var2, var3=var3)


_XOR_LINE1_SA0_PROOF = """\
XOR-chain line 1 stuck-at-0 on Sum.

Sum is computed as a 2-gate XOR chain:
  Line 1: t = A ⊕ B
  Line 2: Sum = t ⊕ Cin

Fault: the output of line 1 is forced to 0 (t_faulty = 0).
Sum_faulty = 0 ⊕ Cin = Cin.
Sum_good   = A ⊕ B ⊕ Cin = t ⊕ Cin.

Detection: Sum_faulty ≠ Sum_good iff Cin ≠ t ⊕ Cin, i.e. iff t ≠ 0,
i.e. iff A ⊕ B = 1.

A ⊕ B = 1 for exactly 2 of 4 assignments to (A, B): namely (0,1)
and (1,0).  With Cin free (0 or 1), the detecting count is 2 × 2 = 4.

Therefore M = 4 = N/2.

Equivalently: the "other operand" feeding the line-1 XOR gate is the
pair (A, B) producing t = A ⊕ B, which is balanced (equal probability
of 0 and 1 across uniform inputs).  Forcing t to 0 disagrees with the
true value exactly when t = 1, which happens for half the inputs.\
"""

_XOR_LINE1_SA1_PROOF = """\
XOR-chain line 1 stuck-at-1 on Sum.

Sum is computed as a 2-gate XOR chain:
  Line 1: t = A ⊕ B
  Line 2: Sum = t ⊕ Cin

Fault: the output of line 1 is forced to 1 (t_faulty = 1).
Sum_faulty = 1 ⊕ Cin = NOT(Cin).
Sum_good   = A ⊕ B ⊕ Cin = t ⊕ Cin.

Detection: Sum_faulty ≠ Sum_good iff NOT(Cin) ≠ t ⊕ Cin,
i.e. iff 1 ⊕ Cin ≠ t ⊕ Cin, i.e. iff t ≠ 1,
i.e. iff A ⊕ B = 0.

A ⊕ B = 0 for exactly 2 of 4 assignments to (A, B): namely (0,0)
and (1,1).  With Cin free (0 or 1), the detecting count is 2 × 2 = 4.

Therefore M = 4 = N/2.

Equivalently: forcing t to 1 disagrees with the true value exactly
when t = 0, which happens for half the inputs because A ⊕ B is
balanced.\
"""

_XOR_LINE2_SA0_PROOF = """\
XOR-chain line 2 stuck-at-0 on Sum.

Sum is computed as a 2-gate XOR chain:
  Line 1: t = A ⊕ B
  Line 2: Sum = t ⊕ Cin

Fault: the output of line 2 is forced to 0 (Sum_faulty = 0).
Sum_good = A ⊕ B ⊕ Cin = t ⊕ Cin.

Detection: Sum_faulty ≠ Sum_good iff 0 ≠ t ⊕ Cin,
i.e. iff t ⊕ Cin = 1, i.e. iff Sum_good = 1.

Sum_good = A ⊕ B ⊕ Cin is a balanced function of 3 independent
uniform bits: it equals 1 for exactly 4 of 8 inputs (the XOR of any
number of independent uniform bits is itself uniform).

Therefore M = 4 = N/2.

Equivalently: the "other operand" feeding the line-2 XOR gate is Cin,
which takes each value {0, 1} for exactly half the inputs.  But more
precisely, forcing the gate output to 0 detects whenever the true
output is 1, and the 3-input XOR is balanced, giving M = 4.\
"""

_XOR_LINE2_SA1_PROOF = """\
XOR-chain line 2 stuck-at-1 on Sum.

Sum is computed as a 2-gate XOR chain:
  Line 1: t = A ⊕ B
  Line 2: Sum = t ⊕ Cin

Fault: the output of line 2 is forced to 1 (Sum_faulty = 1).
Sum_good = A ⊕ B ⊕ Cin = t ⊕ Cin.

Detection: Sum_faulty ≠ Sum_good iff 1 ≠ t ⊕ Cin,
i.e. iff t ⊕ Cin = 0, i.e. iff Sum_good = 0.

Sum_good = A ⊕ B ⊕ Cin is balanced: it equals 0 for exactly 4 of 8
inputs.

Therefore M = 4 = N/2.

Equivalently: forcing the gate output to 1 detects whenever the true
output is 0, and the 3-input XOR is balanced, giving M = 4.\
"""

_CONTROL_PROOF = """\
Fault-free control — no fault injected.

Both outputs (Cout and Sum) are computed identically to the fault-free
reference for every input.  Therefore Cout_faulty ≡ Cout_good and
Sum_faulty ≡ Sum_good for all 8 inputs.

M = 0 by construction.

**Lemma (M=0 fixed point).** For the fault-free control fault class
at any input width n, the faulty circuit is functionally identical to
the fault-free circuit, so the comparison flag is 0 for all 2^n inputs
and M=0 regardless of n.  Consequently the corresponding Grover oracle
reduces to the identity operation (no phase is ever flipped).  Since
the uniform superposition |ψ⟩ satisfies D|ψ⟩ = |ψ⟩ for the diffusion
operator D = 2|ψ⟩⟨ψ| − I (as ⟨ψ|ψ⟩ = 1), |ψ⟩ is a fixed point of
the Grover iteration when the oracle is the identity.  Therefore
measured success probability is exactly 0.0 for **any** iteration
count k ≥ 0 — not merely low, but provably, permanently zero.
(Empirical quantum-circuit verification of this lemma is deferred to
the follow-up Stage 2 prompt.)\
"""


# ---------------------------------------------------------------------------
# Enumeration of all 11 fault sites
# ---------------------------------------------------------------------------

def enumerate_fault_sites() -> List[FaultSite]:
    """Return the complete list of 11 fault sites in the generalized family.

    The list contains:
    - 6 product-term Cout faults (AB, BC, AC × stuck-at-{0, 1})
    - 4 XOR-chain Sum faults (line1, line2 × stuck-at-{0, 1})
    - 1 fault-free control

    Total: **11** fault sites.

    Returns
    -------
    list[FaultSite]
        All 11 fault sites, ordered as described above.
    """
    sites: List[FaultSite] = []

    # --- 6 product-term faults on Cout ---
    for term in ("AB", "BC", "AC"):
        for sa in (0, 1):
            derived_m = 2 if sa == 0 else 6
            proof = _product_term_proof(term, sa)
            sites.append(FaultSite(
                fault_class="product_term",
                identifier=term,
                stuck_at=sa,
                derived_m=derived_m,
                proof=proof,
            ))

    # --- 4 XOR-chain faults on Sum ---
    xor_proofs = {
        ("line1", 0): _XOR_LINE1_SA0_PROOF,
        ("line1", 1): _XOR_LINE1_SA1_PROOF,
        ("line2", 0): _XOR_LINE2_SA0_PROOF,
        ("line2", 1): _XOR_LINE2_SA1_PROOF,
    }
    for line in ("line1", "line2"):
        for sa in (0, 1):
            sites.append(FaultSite(
                fault_class="xor_chain",
                identifier=line,
                stuck_at=sa,
                derived_m=4,
                proof=xor_proofs[(line, sa)],
            ))

    # --- 1 fault-free control ---
    sites.append(FaultSite(
        fault_class="control",
        identifier="none",
        stuck_at=None,
        derived_m=0,
        proof=_CONTROL_PROOF,
    ))

    assert len(sites) == 11, f"Expected 11 fault sites, got {len(sites)}"
    return sites
