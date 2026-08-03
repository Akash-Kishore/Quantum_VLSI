# Stage 2 Walkthrough — Generalized Oracle + Quantum Verification

## Discovery Findings

### `constraint_oracle` (shared_framework/oracle.py)
- Signature: `constraint_oracle(n_qubits, condition_circuit, ancilla_index)`
- Pattern: `compose(condition) → Z(ancilla) → compose(condition.inverse())`
- The existing `atpg_oracle.py` does NOT use it — builds compute→Z→uncompute manually for gate-ordering control

### Diffusion Scoping (test_atpg.py, L114–119)
- `diffusion_operator(3)` composed onto q0–q2 only via `compose(diffusion, qubits=[0,1,2])`
- Oracle spans all 6 qubits via full `compose(oracle)`

### `optimal_iterations(3, 0)` Behavior
- **Approximate mode**: `ZeroDivisionError: division by zero` (N/M = 8/0)
- **Exact mode**: `ZeroDivisionError: float division by zero` (π/(2·0))
- Both modes are **undefined** at M=0 — this is the feasibility boundary singularity

## Files Created

| File | Purpose |
|---|---|
| [generalized_oracle.py](file:///mnt/c/Quantum_VLSI/module2_atpg/generalized_faults/generalized_oracle.py) | 10-qubit unified oracle template for all 11 fault sites |
| [test_generalized_oracle_sanity.py](file:///mnt/c/Quantum_VLSI/module2_atpg/generalized_faults/tests/test_generalized_oracle_sanity.py) | Stage 2: exhaustive statevector verification (88 cases) |
| [test_generalized_atpg.py](file:///mnt/c/Quantum_VLSI/module2_atpg/generalized_faults/tests/test_generalized_atpg.py) | Stage 3: full sampled Grover runs + M=0 lemma verification |

## Bug Fixed During Development

**Uncomputation ordering bug in the oracle:** The initial implementation used monolithic `_append_good_block` / `_append_faulty_block` functions. Since Sum depends on T (`Sum = T ⊕ Cin`), calling the block function a second time to uncompute would reset T *before* Sum got uncomputed, leaving Sum stuck. Fix: split into 6 granular sub-steps (`_compute_t_good`, `_compute_cout_good`, `_compute_sum_good`, `_compute_t_faulty`, `_compute_cout_faulty`, `_compute_sum_faulty`) and uncompute in strict reverse order.

## Test Results

### Stage 2 — Statevector Sanity (88/88 pass)
- Phase correctness verified for all 11 fault sites × 8 inputs
- Ancilla uncomputation verified (zero residual outside q0–q2)

### Stage 3 — Sampled Grover

**Part A — 10 real fault sites:**

| Fault | M | k | P(detect) | Theoretical max | Threshold |
|---|---|---|---|---|---|
| AB SA0 | 2 | 1 | 1.000 | 1.00 | >90% |
| AB SA1 | 6 | 2 | 0.751 | 0.75 | >60% |
| BC SA0 | 2 | 1 | 1.000 | 1.00 | >90% |
| BC SA1 | 6 | 2 | 0.750 | 0.75 | >60% |
| AC SA0 | 2 | 1 | 1.000 | 1.00 | >90% |
| AC SA1 | 6 | 2 | 0.727 | 0.75 | >60% |
| line1 SA0 | 4 | 2 | 0.497 | 0.50 | >40% |
| line1 SA1 | 4 | 2 | 0.475 | 0.50 | >40% |
| line2 SA0 | 4 | 2 | 0.516 | 0.50 | >40% |
| line2 SA1 | 4 | 2 | 0.498 | 0.50 | >40% |

> [!IMPORTANT]
> M=4 and M=6 cases have theoretical ceilings well below 90% at n=3. This is not a bug — it's Grover's algorithm operating in the small-N regime where the rotation angle θ is too large for the small-angle approximation.

**Part B — Control fault (M=0) — Fixed-point lemma confirmed:**

| k | P(detect) |
|---|---|
| 0 | 0.0000 |
| 1 | 0.0000 |
| 2 | 0.0000 |
| 3 | 0.0000 |
| 4 | 0.0000 |
| 5 | 0.0000 |
| 6 | 0.0000 |
| 7 | 0.0000 |
| 8 | 0.0000 |

Success probability is **exactly 0.0** for all k=0..8, confirming the M=0 fixed-point lemma empirically.

## Package-Lock Barrier Confirmation
No packages were changed, upgraded, or installed. No existing files were modified.
