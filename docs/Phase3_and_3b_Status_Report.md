# Status Report — Phase 3 and Phase 3b
### Grover's Algorithm for VLSI Design & Test — Module 1 (Placement)

---

## 1. Where things stand

| Phase | Task | Status |
|---|---|---|
| 1 | Shared Grover framework | Complete, verified, committed |
| 2 | Module 2 — ATPG | Complete, verified, committed |
| **3** | **Module 1 — Placement (no-collision + validity)** | **Complete, verified, committed** |
| **3b** | **Module 1 — Placement (+ adjacency constraint)** | **Complete, verified, committed** |
| 4 | Documentation & write-up | Not started |
| 5 (stretch) | Sequential pipeline (Module 1 -> Module 2) | Not started |

Separately, still open and not yet started: a standalone HTML/JS visual UI for Module 1
(cell x site probability heatmap animating across Grover iterations), decided on earlier
but never built.

---

## 2. Phase 3 — Placement (no-collision + validity)

**Problem**: assign 4 logic cells to 7 physical sites, encoded as 12 search qubits
(3 qubits/cell, binary-encoded site index 0-6, code 7 invalid).

**Qubit budget (25 total)**:

| Range | Purpose |
|---|---|
| q0-q11 | Search register — 4 cells x 3 qubits [LSB, mid, MSB] |
| q12-q14 | Reusable scratch register (pairwise collision XOR) |
| q15-q20 | 6 collision-flag ancillas (one per cell pair) |
| q21-q24 | 4 validity-flag ancillas (one per cell) |

**Classical ground truth**: M = 840 = 7x6x5x4 (permutations of 7 sites taken 4 at a time),
confirmed by brute force.

**Result**: `optimal_iterations(12, 840)` = 2 (approximate formula), 1 (exact/arcsin mode) —
the approximate formula overshoots by one iteration, consistent with the pattern first seen
in Phase 1's trivial 2-qubit case. At the true optimum (k=1, exact mode), measured success
probability was 97.4%.

All three test stages (pure-Python encoding/logic checks, deterministic Aer-statevector
oracle sanity checks on hand-picked inputs, full sampled Grover run cross-checked against
classical brute force) passed. Committed and pushed to `main`.

---

## 3. Phase 3b — Adjacency constraint

**Design decisions locked in this phase**:

- **Site topology**: the 7 sites sit in a 2-row x 4-column grid, with one corner unused
  (only 7 real sites exist):

  ```
  Row 0:  [0] [1] [2] [3]
  Row 1:  [4] [5] [6] [ . ]
  ```

  Adjacency = orthogonal (Manhattan-distance-1) neighbors only, no diagonals. This gives
  exactly 8 undirected edges: `(0,1) (1,2) (2,3) (4,5) (5,6) (0,4) (1,5) (2,6)`.

  *(Side note: site code 7 — the code the Phase 3 validity flag already excludes — happens
  to decode to the same unused grid corner (row=1, col=3) under this 3-bit scheme. A
  coincidence of the encoding, not load-bearing.)*

- **Required adjacency ("chain") constraint**: cell 0 adjacent to cell 1, AND cell 1
  adjacent to cell 2. Cell 3 has no adjacency requirement. (Chosen over a non-overlapping
  cell0-cell1/cell2-cell3 alternative, which was also computed: chain gives a better
  narrative — a 3-cell signal path — for the same implementation cost.)

- **New classical ground truth**: filtering the 840 by the chain constraint gives
  **M = 96** (confirmed by brute force). N is unchanged at 4096 (still 12 search qubits;
  the new qubits are ancillas only).

**New qubit budget (27 total, +2 over Phase 3)**:

| Range | Purpose |
|---|---|
| q0-q24 | Unchanged from Phase 3 |
| q25-q26 | 2 new adjacency-flag ancillas, index-matched to `ADJACENCY_PAIRS = [(0,1), (1,2)]` |

**Oracle construction**: `_append_adjacency_flag` enumerates all 16 ordered site-code pairs
matching the 8 undirected edges (both directions), using an X-mask + 6-control-MCX +
undo-X-mask block per term, followed by a single inverting X to match the existing
"1 = problem" flag polarity. The whole block is self-inverse (XOR-into-the-same-target
operations always commute), so uncompute is simply calling the same function a second time
— no manually-reversed variant needed. The final phase kick extends Phase 3's 10-flag
H-MCX-H trick to 12 flags (11-control MCX, qubits 15-25 as controls, q26 as target).

**Iteration count — a genuine deviation from every prior phase's pattern**:
`optimal_iterations(12, 96)` gives **k=5 for both the approximate and exact formulas** —
they agree this time, unlike the "approximate overshoots by exactly one" pattern seen in
every phase so far (2-qubit trivial case, Module 2, Phase 3 above). Theoretical success at
k=5: ~98.57%.

### 3.1 Code review findings and fixes

Full review (including actually installing the pinned `qiskit`/`qiskit-aer` stack in a
sandbox and running/exhaustively testing the code, not just reading it) found:

- `placement_oracle.py`, `classical_baseline.py`, Stage 1 (`test_encoding.py`), and Stage 2
  (`test_oracle_sanity.py`) were all correct as submitted — verified via direct execution
  and, for the new adjacency-flag logic, exhaustive testing of all 42 possible
  `(cell_a_code, cell_b_code)` combinations plus the self-inverse uncompute property, on an
  isolated 7-qubit circuit.
- Stage 3 (`test_placement.py`) had two real bugs, both since fixed and reconfirmed on the
  real machine:
  1. Leftover Phase-3-era regression tests (`Test 1`/`Test 2`) asserted >90% success against
     the *old* 840-member ground truth at k=1 — but the oracle now marks only the 96-member
     adjacency set, so the actual value was ~34.7%, not >90%. **Fix**: removed both tests
     entirely (the assertion could not be satisfied once the same oracle function's output
     fundamentally changed) — the classical `count_valid_placements() == 840` check was kept
     since it doesn't depend on the oracle and remains valid.
  2. A "flag unexpected marked states" safety check had a vacuous/tautological assertion
     (`placement not in ground_truth_adj_set` inside a branch only reachable when that was
     already guaranteed true) that could never fail, providing zero actual protection.
     **Fix**: rewritten to collect genuine offenders during the loop and assert the
     collected list is empty.
  3. Minor: two stale docstrings referencing the old 25-qubit/q12-q24 layout, updated to
     27-qubit/q12-q26.

### 3.2 Final confirmed results (real machine run, post-fix)

```
STAGE 1: PASS  (all encoding + classical adjacency-count checks correct)
STAGE 2: PASS  (all 6 statevector sanity cases — A, B, C, A3b, B3b, C3b — correct;
                oracle: 27 qubits, 779 gates, 909 gates decomposed)
STAGE 3: PASS
  optimal_iterations(12, 840)             = 2   (approx)
  optimal_iterations(12, 840, exact=True) = 1   (exact)
  optimal_iterations(12, 96)              = 5   (approx)
  optimal_iterations(12, 96, exact=True)  = 5   (exact — agrees with approx, no overshoot)
  Observed adjacency-Grover success rate: 98.60%  (theoretical prediction: 98.57%)
  Distinct valid+adjacent placements observed: 96 / 96 (full coverage across 1000 shots)
  unexpected_marks check: 0 offenders (real confirmation the rewritten Stage 3 safety
  check is both correct and clean on actual hardware data)
```

The 98.60% observed vs. 98.57% theoretical match is a strong independent confirmation that
the oracle, the manually-scoped diffusion, and the iteration count are all correctly wired
together end to end, not just individually correct in isolation.

**Git status**: committed and pushed to `github.com:Akash-Kishore/Quantum_VLSI.git`,
branch `main`. Commit message: `"Phase 3b: Module 1 adjacency constraint (2x4 grid, chain
cell0-cell1-cell2, M=96)"`.

---

## 4. Established conventions carried forward (for future phases)

- No `pytest`, ever — every test file uses plain `assert` statements inside a `main()`,
  run directly via `python path/to/test_file.py`.
- "Manual Grover loop" pattern: when the oracle is wider than the search register (true for
  both Module 1 and Module 2), the oracle spans all qubits but diffusion is manually scoped
  via `compose()` to only the search-register qubits — `shared_framework`'s
  `build_grover_circuit` (which assumes same-width oracle/diffusion) is never modified.
- `qc.mcx(...)` calls never use `ancilla_qubits`/v-chain modes — every control must be a
  real, already-allocated qubit; every oracle-builder ends with an `assert
  qc.num_qubits == TOTAL_QUBITS` to catch ancilla drift.
- Exact/deterministic statevector checks use `AerSimulator(method="statevector")` +
  `save_statevector()`, never `qiskit.quantum_info.Statevector` (shown in Phase 3 to hang
  for minutes at 25+ qubits).
- Self-inverse "compute" helpers (collision flags, validity flags, and now adjacency flags)
  are uncomputed by calling the same construction function a second time with identical
  arguments, rather than writing a separately-reversed variant.
- Three-stage testing methodology: pure-Python logic test -> deterministic exact-statevector
  oracle sanity check on hand-picked inputs -> full sampled Grover run cross-checked against
  classical brute force.
- `optimal_iterations(n_qubits, n_marked, exact=False)` — the approximate formula has
  overshot the true optimum by exactly one iteration in every case tested except Phase 3b's
  M=96 case, where they agree. Not a rule, just tracked as a recurring (mostly) pattern.

---

## 5. Open items

1. **Phase 4 — documentation & write-up.** Per the original build plan, this is meant to be
   locked in before attempting Phase 5, to guarantee a complete deliverable regardless of
   what happens next. Not started.
2. **Module 1 visual UI.** Decided earlier (standalone self-contained HTML/JS viewer, not
   ipywidgets, showing a full cell x site probability heatmap animating across Grover
   iterations) but never built.
3. **Phase 5 (stretch) — sequential pipeline.** Feeds Module 1's measured placement into
   Module 2's fault-testing oracle. Explicitly scoped as attempted only after Phases 1-4 are
   complete, so as not to risk the guaranteed deliverable.
4. **Module 1's own second design gap, noted since Phase 1** and still unaddressed: none
   remaining — the adjacency constraint (the one open design question from Phase 1/3) is
   now fully resolved by Phase 3b.
