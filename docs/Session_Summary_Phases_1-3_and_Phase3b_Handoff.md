# Session Summary & Handoff — Grover's Algorithm VLSI Project
### Phases 1–3 Complete. Phase 3b (Adjacency) Next.

**How to use this document**: Paste this entire document as the opening message in a new
chat, along with (if available) the original project docs —
`Project_Handoff_Summary_and_Phase1_Instructions.md`, `Workspace_Workflow_Guide.md`,
`Grovers_Algorithm_VLSI_Project.docx`, and the corrected `Hardware_Software_Requirements.docx`
(see §5 below — the old version is stale, use the corrected one). This document is written
to be fully self-contained on the technical details that matter, so a new chat can continue
without needing the original long conversation history.

---

## 1. Project Overview (unchanged, recap)

**Goal**: A simulated Qiskit project applying **Grover's algorithm** to two VLSI problems:

- **Module 1 — Placement**: assign 4 logic cells to 7 physical sites, satisfying
  no-collision + validity constraints (built), with adjacency constraints as a follow-up
  (**Phase 3b, not yet started**).
- **Module 2 — ATPG**: find input vectors that detect a manufacturing fault in a 1-bit
  full adder (**complete**).

**Role/context**: The user is an IBM Quantum Qiskit Advocate. This is a demonstration of
Grover's algorithm on genuinely industry-relevant hardware problems, not a generic demo.

**Build order (5 phases, unchanged)**:
| Phase | Task | Status |
|---|---|---|
| 1 | Shared Grover framework | ✅ Complete |
| 2 | Module 2 — ATPG | ✅ Complete |
| 3 | Module 1 — Placement (no-collision + validity) | ✅ Complete |
| 3b | Module 1 — Placement (+ adjacency) | 🔜 Next |
| 4 | Documentation & write-up | Not started |
| 5 (stretch) | Sequential pipeline (Module 1 → Module 2) | Not started |

---

## 2. Environment — Unchanged, Confirmed Working Across All Phases

| Package | Version — DO NOT CHANGE |
|---|---|
| Python | 3.10 |
| qiskit | 1.2.4 |
| qiskit-aer-gpu-cu11 | 0.15.1 |
| numpy | 1.26.4 |
| matplotlib | 3.8.4 |
| CUDA Toolkit (inside WSL2) | 11.8 |

- OS: WSL2 Ubuntu 24.04, project files at `C:\Quantum_VLSI` (`/mnt/c/Quantum_VLSI` in WSL)
- Conda env: `grover-vlsi`, Python 3.10
- GPU: NVIDIA RTX 3050, confirmed working via `AerSimulator(device="GPU")`
- Known hard incompatibility (still applies, never violated across 3 phases):
  `qiskit-aer-gpu-cu11==0.15.1` breaks under `qiskit>=2.0`
  (`ImportError: cannot import name 'convert_to_target' from 'qiskit.providers'`)
- Antigravity IDE + WSL2 remote connection, `agy` CLI shortcut — all confirmed working,
  no further setup needed.
- **No `pytest` or any other test framework has been introduced.** All tests across all
  phases are plain Python scripts using `assert` inside a `main()` function, run directly
  via `python path/to/test_file.py`. This convention must continue.

---

## 3. Phase 1 — Shared Grover Framework: COMPLETE ✅ (recap, unchanged from before)

`shared_framework/` — `oracle.py`, `diffusion.py`, `grover_utils.py`, `visualization.py`,
`tests/test_trivial_oracle.py` — all built, reviewed, tested, committed. Key exports used
throughout Phases 2 and 3:

- `optimal_iterations(n_qubits, n_marked, exact=False)` — approximate formula
  `round((π/4)·√(N/M))` by default, or the true analytical optimum via `exact=True`.
- `run_circuit(circuit, shots, device="GPU")` — GPU execution with automatic CPU fallback.
- `diffusion_operator(n)` — standard H→X→MCZ→X→H inversion-about-the-mean, returns a
  circuit/gate that can be `compose()`d onto a subset of qubits in a larger circuit.

**Recurring pattern, confirmed in every phase since**: the approximate iteration formula
tends to overshoot by exactly one iteration relative to the true optimum. This is expected
behavior of the approximation, not a bug — seen in the 2-qubit trivial case, Module 2, and
Module 1 (see tables below).

**Treat `shared_framework/` as a trusted, unmodified dependency. It has never been changed
since Phase 1 and should not be, for any reason, in any future phase.**

---

## 4. Phase 2 — Module 2 (ATPG): COMPLETE ✅

**Files**: `module2_atpg/__init__.py`, `full_adder.py`, `faulty_adder.py`,
`atpg_oracle.py`, `tests/__init__.py`, `tests/test_atpg.py`. All reviewed file-by-file,
all correct, all committed.

**Fault model**: 1-bit full adder, `Cout = AB ⊕ BC ⊕ AC` computed via three XOR-accumulating
Toffolis onto a shared `Cout` ancilla. Fault: the `AB`-term Toffoli is stuck-at-0 (simply
omitted from the faulty version). Algebraically, `Cout_good ⊕ Cout_faulty` reduces exactly
to `AB` — confirmed by hand, not just by the test passing. **Marked states: `{110, 111}`
(A=1, B=1, any Cin) — M=2 out of N=8.**

**Qubit layout (6 total)**: q0=A, q1=B, q2=Cin (search register), q3=fault-free Cout,
q4=faulty Cout, q5=flag (XOR of q3,q4). Oracle spans all 6 qubits; diffusion applies only
to q0–q2. **This is where the "manual Grover loop" architecture was first established**,
because `shared_framework.grover_utils.build_grover_circuit` assumes oracle and diffusion
share the same qubit count, which doesn't hold once ancillas are introduced. The pattern —
build a wider oracle circuit, apply diffusion only to the search-register sub-range via
`circuit.compose(diffusion, qubits=list(range(n_search)), inplace=True)`, measure only the
search register — was reused verbatim in Phase 3 and should be reused again in Phase 3b.

**Test results** (`test_atpg.py`, all confirmed):
| Metric | Value |
|---|---|
| `optimal_iterations(3, 2)` (approx) | 2 |
| `optimal_iterations(3, 2, exact=True)` | 1 |
| Detection probability @ iterations=1 | 100% (1000/1000 shots) — matches theoretical `sin²(90°)=1.0` exactly |
| Detection probability @ iterations=2 | 21.6% (comparison only) — theoretical is 25%, within normal shot noise |

**Git status**: committed and pushed to `github.com:Akash-Kishore/Quantum_VLSI.git`,
branch `main`, commit message `"Phase 2: Module 2 ATPG"`.

---

## 5. Hardware_Software_Requirements.docx — CORRECTED ✅

The original version of this file was stale — written before the GPU/CUDA decision was
locked in, and contradicted every other project doc (it claimed GPU/CUDA were "not
required" and gave an unpinned `pip install qiskit qiskit-aer numpy matplotlib` command).

**This has been fixed.** The corrected version now:
- Lists the actual pinned stack (`qiskit-aer-gpu-cu11==0.15.1`, CUDA 11.8 in WSL2) in its
  requirements table.
- Gives the real install sequence (conda env + pinned pip installs), including the
  `convert_to_target` incompatibility warning.
- States plainly that GPU is in active use, with the actual verification result
  (`AerSimulator().available_devices()` returned `('CPU', 'GPU')`).
- Reframes (rather than deletes) the "GPU not strictly necessary at this qubit count"
  section — the reasoning is correct in general, it's just honest now about GPU being used
  anyway because the environment was built around it early on.

**This was committed together with Phase 2** (commit message covered both). If a new chat
is started and only has the *old* `Hardware_Software_Requirements.docx` on hand, flag that
it's stale and the corrected version should be used from the repo instead.

---

## 6. Phase 3 — Module 1 (Placement, no-collision + validity): COMPLETE ✅

**Scope**: this phase deliberately excludes adjacency constraints (that's Phase 3b).
It covers only: (1) every cell has a valid site code, (2) no two cells share a site.

### 6.1 Design — locked, unchanged going into Phase 3b

- 4 logic cells, 7 placement sites. Each cell = 3 qubits, encoding site index 0–6 (code 7
  is the one invalid, unused value).
- Search register: 12 qubits (cell 0 = q0–q2, cell 1 = q3–q5, cell 2 = q6–q8, cell 3 =
  q9–q11). N = 2¹² = 4096.
- Classical ground truth: **M = 840** (= 7×6×5×4), computed via
  `itertools.permutations(range(7), 4)` in `classical_baseline.py` — not hardcoded
  anywhere else in the codebase.

### 6.2 Qubit layout (25 total) — the single source of truth, defined as constants in
`placement_oracle.py`, reused everywhere:

```python
CELL_QUBITS = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]  # [LSB, mid, MSB] per cell
DIFF_QUBITS = [12, 13, 14]
COLLISION_PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
COLLISION_FLAG_QUBITS = [15, 16, 17, 18, 19, 20]  # index-matched to COLLISION_PAIRS
VALIDITY_FLAG_QUBITS = [21, 22, 23, 24]  # index-matched to cell order 0,1,2,3
TOTAL_QUBITS = 25
```

| Index range | Role |
|---|---|
| q0–q11 | Search register (4 cells × 3 qubits) — diffusion applies here only |
| q12–q14 | Reusable "diff" scratch register (one pair at a time, returns to `\|0⟩` between pairs) |
| q15–q20 | 6 collision-flag ancillas |
| q21–q24 | 4 validity-flag ancillas |

**⚠️ Ancilla budget discipline**: `qc.mcx(controls, target)` was called throughout without
an `ancilla_qubits` argument and without `v-chain`/`recursion` modes, specifically to avoid
silently consuming extra qubits beyond this fixed 25-qubit budget.
`build_placement_oracle()` ends with a hard `assert qc.num_qubits == TOTAL_QUBITS` for
exactly this reason — **this same discipline must be followed in Phase 3b**, and any new
ancillas needed for adjacency should extend this qubit layout table explicitly, not be
added ad hoc.

### 6.3 Bit-weight convention for decoding (in `encoding.py`)

For cell *k* (qubits `3k`, `3k+1`, `3k+2`): qubit `3k` = LSB (weight 1), `3k+1` = mid
(weight 2), `3k+2` = MSB (weight 4). Combined with Qiskit's little-endian measurement
strings (rightmost char = q0), the decode formula is:

```
lsb_char = s[11 - 3*k]; mid_char = s[10 - 3*k]; msb_char = s[9 - 3*k]
code_k = int(lsb_char) + 2*int(mid_char) + 4*int(msb_char)
```

**Hand-verified worked examples** (also embedded as doctests in `encoding.py` and as
executable assertions in `test_encoding.py`):
```
decode_bitstring_to_placement("000000000000") == (0, 0, 0, 0)
decode_bitstring_to_placement("011110000101") == (5, 0, 6, 3)
decode_bitstring_to_placement("111000000000") == (0, 0, 0, 7)
```

This convention does not affect oracle correctness (the oracle only checks "all bits
equal 1" and "corresponding bits equal," both weight-invariant) — it only matters for
`encoding.py`'s decode function and must stay consistent if Phase 3b adds any new
decode/interpretation logic.

### 6.4 Oracle construction (`placement_oracle.py`)

- `_append_pairwise_collision_flag`: XORs cell_a and cell_b into the shared diff register
  via position-matched CNOTs, flags via X-sandwich + 3-input MCX (want-all-zero →
  positive-control AND), uncomputes diff immediately after each pair. Self-inverse.
- `_append_cell_validity_flag`: plain 3-input MCX (positive controls) flags code=7.
  Self-inverse.
- `build_placement_oracle()`: computes all 6 collision + 4 validity flags → X-sandwiches
  all 10 flags → multi-controlled-Z via H→MCX(9 controls)→H on the 10 flags → undoes the
  X-sandwich → uncomputes everything in exact LIFO order (validity flags reverse, then
  collision flags reverse) → asserts `num_qubits == 25`.
- Algebraically confirmed (same style of check as Module 2's `FLAG = AB` reduction): the
  oracle phase-flips a basis state iff all 10 flags were 0 before the X-sandwich, i.e.
  exactly "no collision AND no invalid code" — the 840-member ground truth set, by
  construction.

### 6.5 Three-stage testing methodology — established this phase, should be reused for
Phase 3b's adjacency oracle

This was a deliberate departure from Phase 2's single-test approach, because this oracle
is more complex (compound AND of 10 conditions vs. Module 2's single condition). Each
stage gates the next — if one fails, stop, don't proceed:

**Stage 1 — `test_encoding.py`** (pure Python, no quantum simulation): validates
`decode_bitstring_to_placement` and `is_valid_collision_free` against hand-computed
examples. Fast, catches decode bugs before they can be confused with oracle bugs.

**Stage 2 — `test_oracle_sanity.py`** (deterministic exact statevector, no sampling): three
hand-picked classical inputs, prepared via X gates only (no Hadamards), oracle applied
once, then the resulting statevector inspected directly for the exact expected amplitude
sign and confirmation that ALL other probability mass is zero (proving ancilla
uncomputation). Test vectors:

| Case | Meaning | X gates applied | Statevector index | Expected amplitude |
|---|---|---|---|---|
| A | Sites (0,1,2,3) — valid | X(3), X(7), X(9), X(10) | 1672 | ≈ **-1+0j** (marked) |
| B | Sites (0,0,1,2) — collision | X(6), X(10) | 1088 | ≈ **+1+0j** (unmarked) |
| C | Sites (0,1,2,7) — invalid code | X(3), X(7), X(9), X(10), X(11) | 3720 | ≈ **+1+0j** (unmarked) |

**⚠️ Important technical lesson from this stage, applies to Phase 3b too**: the first
implementation used `qiskit.quantum_info.Statevector.from_instruction(circuit)` (pure
Python/NumPy gate-by-gate evolution) and it hung for several minutes on this 25-qubit,
261-gate circuit. Switching to `AerSimulator(method="statevector")` with
`circuit.save_statevector()` — Aer's compiled backend, still exact, still deterministic,
no new package (same `qiskit-aer-gpu-cu11` already pinned) — fixed it, running in seconds.
**For any future exact/deterministic statevector check (Phase 3b's adjacency oracle sanity
check will need one), use the Aer compiled-backend method from the start, not
`qiskit.quantum_info.Statevector`.**

**Stage 3 — `test_placement.py`** (full Grover circuit, 1000 shots via `run_circuit`,
GPU): builds the manual Grover loop (25-qubit oracle, 12-qubit diffusion on q0–q11 only,
measure q0–q11 only), decodes every measured result, cross-checks each valid result
against `enumerate_valid_placements()`'s actual output (not just internal consistency).

### 6.6 Test results — all three stages, confirmed

**Stage 1**: all three decode examples correct; `is_valid_collision_free` correct on
valid/collision/out-of-range cases. PASS.

**Stage 2**: oracle decomposed gate count 261. All three cases: exact ±1 amplitude as
predicted, zero residual probability (full ancilla uncomputation confirmed). PASS.

**Stage 3**:
| Metric | Value |
|---|---|
| `count_valid_placements()` | 840 (confirmed = 7×6×5×4) |
| `optimal_iterations(12, 840)` (approx) | 2 |
| `optimal_iterations(12, 840, exact=True)` | 1 |
| Oracle: qubits / gates | 25 / 259 |
| Valid-placement probability @ iterations=1 | **97.4%** (theoretical ≈97.5%) |
| Distinct valid placements observed @ iter=1 | 580 (coupon-collector expectation ≈577 — confirms uniform amplitude spread across all 840 marked states, not clumping) |
| Valid-placement probability @ iterations=2 | **50.2%** (theoretical ≈50.5%, comparison only) |
| Distinct valid placements observed @ iter=2 | 392 (expectation ≈378) |

All numbers land within normal statistical noise of theory. PASS on all three stages.

### 6.7 Git status

Committed and pushed: `"Phase 3: Module 1 Placement (no-collision + validity)"`, branch
`main`.

### 6.8 Files created this phase

```
module1_placement/
├── __init__.py
├── classical_baseline.py    # enumerate_valid_placements(), count_valid_placements()
├── encoding.py               # decode_bitstring_to_placement(), is_valid_collision_free()
├── placement_oracle.py       # build_placement_oracle() + qubit-layout constants
└── tests/
    ├── __init__.py
    ├── test_encoding.py       # Stage 1
    ├── test_oracle_sanity.py  # Stage 2 (Aer-based)
    └── test_placement.py      # Stage 3
```

---

## 7. Current Full Project File Structure

```
C:\Quantum_VLSI\
├── shared_framework\              # Phase 1 — trusted, do not modify
│   ├── __init__.py
│   ├── oracle.py
│   ├── diffusion.py
│   ├── grover_utils.py
│   ├── visualization.py
│   └── tests\
│       ├── gpu_test.py
│       └── test_trivial_oracle.py
├── module2_atpg\                  # Phase 2 — complete, do not modify
│   ├── __init__.py
│   ├── full_adder.py
│   ├── faulty_adder.py
│   ├── atpg_oracle.py
│   └── tests\
│       ├── __init__.py
│       └── test_atpg.py
├── module1_placement\             # Phase 3 — complete (no-collision + validity)
│   ├── __init__.py                # Phase 3b will extend this module for adjacency
│   ├── classical_baseline.py
│   ├── encoding.py
│   ├── placement_oracle.py
│   └── tests\
│       ├── __init__.py
│       ├── test_encoding.py
│       ├── test_oracle_sanity.py
│       └── test_placement.py
├── notebooks\
├── docs\
├── requirements.txt
├── environment.yml
├── .gitignore
└── README.md
```

---

## 8. Key Learnings & Principles Carried Forward (applies to all future phases)

- **Package barrier is absolute**: `qiskit==1.2.4` / `qiskit-aer-gpu-cu11==0.15.1` /
  `numpy==1.26.4` / `matplotlib==3.8.4`, never touched across 3 phases. Any code review
  starts with scanning for accidental version drift before checking logic.
- **No pytest, ever** — plain `assert` + `main()` scripts throughout, run directly.
- **Manual Grover loop pattern** (established Phase 2, reused Phase 3): whenever an oracle
  needs ancillas beyond the search register, diffusion must be manually scoped to the
  search-register qubit range via `circuit.compose(diffusion, qubits=list(range(n)),
  inplace=True)` — `shared_framework.grover_utils.build_grover_circuit` assumes same-width
  oracle/diffusion and has never needed to be (and should not be) modified to handle this.
- **Approximate-formula overshoot by exactly one iteration** is a recurring, expected
  pattern (2-qubit trivial case, Module 2, Module 1) — not a bug when it recurs again.
- **Little-endian bitstring decoding** is a recurring risk (flagged originally in the
  Changes Log for the Module 1 viewer, then actually encountered and correctly handled in
  both Module 2's and Module 1's tests). Any new decode logic in Phase 3b must restate and
  hand-verify its own convention the same way, don't assume it carries over silently.
- **Ancilla budget discipline**: `qc.mcx(...)` calls must never be given `ancilla_qubits`
  or `v-chain`/`recursion` modes, to avoid silently growing the qubit count beyond a
  documented, fixed layout. Always assert `num_qubits` equals the expected total after
  building any oracle.
- **Layered testing for complex oracles** (established Phase 3): isolate pure-Python logic
  tests, then a deterministic exact-statevector oracle sanity check on hand-picked inputs,
  then the full sampled Grover run — in that order, each gating the next. Phase 3b's
  adjacency oracle is more complex than Phase 3's, so this methodology should be applied
  again, likely with new hand-picked test vectors for adjacency-specific cases.
- **Exact statevector checks must use `AerSimulator(method="statevector")` +
  `save_statevector()`, not `qiskit.quantum_info.Statevector`** — the latter is pure
  Python/NumPy and becomes impractically slow even for moderately-gated 25+ qubit circuits;
  the former is Aer's compiled backend, equally exact, much faster.
- **Algebraic verification, not just test-passing**: for both Module 2 (`FLAG = AB`
  reduction) and Module 1 (10-flag AND reduces to exactly the 840-member ground truth),
  correctness was confirmed by hand-deriving what the flag logic reduces to algebraically,
  not just by trusting that assertions passed. Worth doing the same for adjacency's flag
  logic once designed.

---

## 9. Role & Workflow (unchanged from all prior sessions)

1. User uses Google Antigravity IDE with Claude Opus 4.6 as the coding agent — not writing
   code directly with the assistant in this chat.
2. The assistant (Claude, in this chat) writes a single, extremely detailed and precise
   prompt for that agent, specifying exactly what files to create and what each must
   contain — matching the level of detail in the Phase 2 and Phase 3 prompts (explicit
   qubit-index constants, explicit bit-weight conventions with hand-verified worked
   examples, explicit test vectors with expected outputs, explicit LIFO uncompute order,
   explicit "no extra ancilla" warnings).
3. The user pastes the agent's generated code back file by file.
4. The assistant checks it: package-lock compliance FIRST (scan every import and any
   pip/conda/requirements touch), then algorithmic/circuit correctness (oracle sign
   convention, diffusion construction, iteration formula, qubit indexing, Qiskit 1.2.4 API
   correctness).
5. If correct: say so briefly, confirm what's next. If wrong: a short, surgical correction
   prompt naming the exact file, function, bug, and fix — not a full re-explanation.
6. When something is slow or behaves unexpectedly, the assistant should diagnose the
   actual cause (e.g. checking what `Statevector` vs `AerSimulator` actually do under the
   hood) rather than accepting the agent's first self-diagnosis at face value — this
   mattered concretely in Phase 3's Stage 2 slowdown, where the agent's first proposed fix
   (`Statevector.from_instruction` → `Statevector`) was a same-engine, no-op change, and
   the actual fix required switching to a different execution backend entirely.

---

## 10. Phase 3b — Adjacency Constraints: NOT YET STARTED

**This is the next task.** Open questions, not yet decided, that must be resolved before
an Antigravity prompt can be written for this phase:

- **Site-adjacency topology**: no structure (line / grid / ring / other) has been chosen
  for how the 7 placement sites relate to each other spatially. This determines which
  pairs of sites count as "adjacent."
- **Which cell pairs require adjacency**: no specific pair(s) of the 4 cells have been
  declared as needing a required connection (this is presumably meant to model a subset of
  cells with a netlist/wiring dependency, but the exact pair(s) haven't been chosen).
- **Qubit budget impact**: adjacency will need its own constraint-checking ancillas
  (likely a per-required-pair "is-adjacent" flag, ANDed into the existing 10-flag
  structure or combined into an 11th+ flag), extending the 25-qubit layout — this needs to
  be designed before writing the Antigravity prompt, following the same "define constants,
  document the layout table, assert num_qubits" discipline as Phase 3.
- **New M**: adding an adjacency constraint will shrink the valid-placement count below
  840 — the new M must be computed via an extended classical brute-force enumeration
  (filter `enumerate_valid_placements()`'s existing 840 results by the adjacency
  condition, rather than re-deriving from scratch), and iteration counts recalculated from
  that new M.

**Recommended approach**: resolve the topology and cell-pair decisions first (in
conversation, before writing any agent prompt), then follow the same structure as the
Phase 3 prompt — locked design section, qubit layout constants, worked examples for any
new encode/decode logic, three-stage testing methodology with hand-picked oracle sanity
test vectors, LIFO uncompute ordering, ancilla-budget warnings.

---

## 11. Phase 4 — Documentation: NOT STARTED

Per the original build plan, this locks in the guaranteed deliverable (write-up covering
background theory, architecture, design decisions, and results) before Phase 5 (stretch
pipeline) is attempted. Not yet begun — should follow Phase 3b.

---

## 12. Recommended Next Steps, In Order

1. Resolve the two open Phase 3b design questions (site-adjacency topology; which cell
   pair(s) require adjacency) in conversation.
2. Design the qubit-budget extension and new classical ground-truth (M) for the
   adjacency-constrained version.
3. Write the Phase 3b Antigravity prompt, following the Phase 3 prompt's level of rigor
   (explicit constants, worked examples, hand-picked oracle sanity test vectors, LIFO
   uncompute order, ancilla-budget assertions, three-stage testing).
4. Review the agent's output file by file: package-lock first, then algebraic/circuit
   correctness.
5. Confirm all three test stages pass with results consistent with theory (as in §6.6).
6. Commit and push Phase 3b.
7. Move to Phase 4 (documentation).
