# Antigravity/Opus 4.6 Prompt: Phase 3b — Module 1 Adjacency Constraint

Paste this entire document as the opening message to the Antigravity/Opus 4.6 coding agent.

---

## ROLE & WORKFLOW (unchanged from all prior phases)

You are extending an existing, working Qiskit project. Phases 1–3 are complete, tested,
and committed — **treat every existing file as a trusted dependency and do not modify
anything outside `module1_placement/` unless explicitly instructed below.**

---

## 🚨 NON-NEGOTIABLE BARRIER: NO PACKAGE OR VERSION CHANGES 🚨

**This rule overrides every other instruction in this document, unless the user explicitly
types the words "I authorize a package version change."**

| Package | Version — DO NOT CHANGE |
|---|---|
| Python | 3.10 |
| qiskit | 1.2.4 |
| qiskit-aer-gpu-cu11 | 0.15.1 |
| numpy | 1.26.4 |
| matplotlib | 3.8.4 |
| CUDA Toolkit (inside WSL2) | 11.8 |

`qiskit-aer-gpu-cu11==0.15.1` breaks under `qiskit>=2.0`
(`ImportError: cannot import name 'convert_to_target' from 'qiskit.providers'`) — confirmed,
reproducible, not hypothetical.

⚠️ DO NOT run `pip install --upgrade` on anything. DO NOT change any version number in
`requirements.txt` or `environment.yml`. DO NOT add new packages, including any test
framework — **no `pytest`, ever; every test file in this project uses plain `assert`
statements inside a `main()` function, run directly via `python path/to/test_file.py`, and
this must continue.** DO NOT use any Qiskit 2.x-only API. If any import fails or a package
appears missing, STOP and report the exact error — do not attempt to fix it by installing,
upgrading, or replacing any package.

---

## ENVIRONMENT (unchanged, already verified working across 3 phases)

- OS: WSL2 Ubuntu 24.04, project files at `C:\Quantum_VLSI` (`/mnt/c/Quantum_VLSI` in WSL)
- Conda env: `grover-vlsi`, Python 3.10
- GPU: NVIDIA RTX 3050, use `AerSimulator(device="GPU")` with automatic CPU fallback
- Antigravity IDE + WSL2 remote connection, `agy` CLI shortcut — already working, no setup needed

---

## PROJECT STATUS

| Phase | Task | Status |
|---|---|---|
| 1 | Shared Grover framework (`shared_framework/`) | ✅ Complete — trusted, do not modify |
| 2 | Module 2 — ATPG (`module2_atpg/`) | ✅ Complete — trusted, do not modify |
| 3 | Module 1 — Placement, no-collision + validity (`module1_placement/`) | ✅ Complete |
| **3b** | **Module 1 — Placement, + adjacency constraint** | **🔨 This task** |

`module1_placement/` currently contains `classical_baseline.py`, `encoding.py`,
`placement_oracle.py`, and `tests/` (`test_encoding.py`, `test_oracle_sanity.py`,
`test_placement.py`). **You are extending these files, not replacing them** — every
existing constant, function, and test from Phase 3 must remain intact and continue to pass.

### Existing Phase 3 design (unchanged — do not modify)

- 4 logic cells, 7 placement sites, 3 qubits/cell, codes 0–6 valid, code 7 invalid.
- Search register: 12 qubits. `CELL_QUBITS = [[0,1,2],[3,4,5],[6,7,8],[9,10,11]]` — per
  cell, `[LSB, mid, MSB]` (weights 1, 2, 4).
- `DIFF_QUBITS = [12,13,14]` — reusable scratch register for pairwise collision XOR.
- `COLLISION_PAIRS = [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]`,
  `COLLISION_FLAG_QUBITS = [15,16,17,18,19,20]`.
- `VALIDITY_FLAG_QUBITS = [21,22,23,24]`.
- `TOTAL_QUBITS = 25` (Phase 3).
- Existing oracle logic: compute 6 collision flags + 4 validity flags (flag=1 means
  "problem exists" — collision flag=1 means the pair collides, validity flag=1 means the
  code is invalid) → X-sandwich all 10 flags → 9-control MCX (`H`→`MCX`→`H` trick) realizes
  a 10-qubit MCZ → undo X-sandwich → uncompute everything in exact LIFO order.
- Bit-weight/decode convention (`encoding.py`): for cell `k`, qubit `3k`=LSB(weight 1),
  `3k+1`=mid(weight 2), `3k+2`=MSB(weight 4). Combined with Qiskit's little-endian
  measurement strings (qubit 0 = rightmost character): `lsb_char = s[11-3k]`,
  `mid_char = s[10-3k]`, `msb_char = s[9-3k]`.

---

## TASK: PHASE 3b — ADJACENCY CONSTRAINT

### 1. Locked design (do not re-derive or change any of this)

**Site-adjacency topology**: the 7 sites are arranged in a 2-row × 4-column grid, with one
corner position unused (only 7 real sites exist):

```
Row 0:  [0] [1] [2] [3]
Row 1:  [4] [5] [6] [ · ]   <- (row=1, col=3) is NOT a real site
```

Site → (row, col) coordinates: `0:(0,0) 1:(0,1) 2:(0,2) 3:(0,3) 4:(1,0) 5:(1,1) 6:(1,2)`.
Adjacency = orthogonal neighbors only (Manhattan distance exactly 1 — no diagonals).

**This gives exactly 8 undirected adjacency edges** (hand-verified, do not recompute a
different set):

```
(0,1) (1,2) (2,3) (4,5) (5,6) (0,4) (1,5) (2,6)
```

*(Side note, not required for implementation but useful for your own sanity-checking: code
7's bit pattern is `row=1, col=3` under this scheme too — i.e. the one invalid site code
already excluded by the Phase 3 validity flag lands exactly on the grid's unused corner.
This is a coincidence of the encoding, not something you need to build logic around.)*

**Required adjacency (the "chain" constraint)**: cell 0 must be adjacent to cell 1, **AND**
cell 1 must be adjacent to cell 2. Cell 3 has no adjacency requirement. (This models a
3-cell signal chain: cell0 → cell1 → cell2, with cell1 as a shared middle stage.)

**New classical ground truth**: filtering the existing 840 collision-free+valid placements
by this chain constraint gives **M = 96** (confirmed by brute force: iterate
`itertools.permutations(range(7), 4)`, keep placements where `(sites[0],sites[1])` and
`(sites[1],sites[2])` are both in the 8-edge set above, count = 96). **N is unchanged at
4096** (still 12 search qubits) — the new qubits are ancillas only, they don't affect N.

### 2. New qubit layout — extend `placement_oracle.py`'s constants

```python
ADJACENCY_PAIRS = [(0, 1), (1, 2)]           # (cell_a, cell_b) index pairs, in this order
ADJACENCY_FLAG_QUBITS = [25, 26]             # index-matched to ADJACENCY_PAIRS
TOTAL_QUBITS = 27                             # was 25 in Phase 3
```

All Phase 3 constants (`CELL_QUBITS`, `DIFF_QUBITS`, `COLLISION_PAIRS`,
`COLLISION_FLAG_QUBITS`, `VALIDITY_FLAG_QUBITS`) stay exactly as they are. You are adding
two new ancilla qubits (25, 26), nothing else changes about the existing qubit ranges.

⚠️ **Statevector memory note**: 27 qubits means `2^27` complex128 amplitudes ≈ **2.15 GB**
for any exact-statevector check. This still comfortably fits the RTX 3050's 6GB VRAM and
the machine's 12GB system RAM, but it's a real jump from Phase 3's ~500MB — if a statevector
sanity check runs noticeably slower than Phase 3's did, that is expected from the qubit
count increase, not necessarily a bug. Continue using `AerSimulator(method="statevector")`
+ `circuit.save_statevector()` for any exact/deterministic check — **never**
`qiskit.quantum_info.Statevector`, which was already shown in Phase 3 to hang for minutes
at 25 qubits and will be worse at 27.

### 3. Oracle construction — new helper function in `placement_oracle.py`

Add `_append_adjacency_flag(qc, cell_a_qubits, cell_b_qubits, flag_qubit)`:

**Semantics**: like the existing collision and validity flags, this flag must end up **1
when there is a problem** (cells NOT adjacent — chain broken) and **0 when the constraint
is satisfied** (cells ARE adjacent), so it plugs into the existing "X-sandwich all flags,
then MCZ" logic with the same polarity as every other flag, with no special-casing needed
at the top level.

**Implementation — enumerate the 16 ordered edge pairs directly** (both directions of each
of the 8 edges, since either cell could hold either endpoint's code):

```
(0,1) (1,0) (1,2) (2,1) (2,3) (3,2) (4,5) (5,4) (5,6) (6,5) (0,4) (4,0) (1,5) (5,1) (2,6) (6,2)
```

For each ordered pair `(x, y)` in this list:
1. Apply X gates to `cell_a_qubits` and `cell_b_qubits` on exactly the bit positions where
   code `x` (for cell_a) and code `y` (for cell_b) have a 0 bit — this makes "cell_a holds
   code x AND cell_b holds code y" readable as an all-positive-control condition.
2. Apply a 6-control MCX: controls = `cell_a_qubits + cell_b_qubits` (all 6), target =
   `flag_qubit`.
3. Undo the X gates from step 1 (mirror of step 1, same qubits).

Because any specific `(cell_a_code, cell_b_code)` pair can match **at most one** of the 16
enumerated terms, these 16 MCX-into-flag operations are safe to apply sequentially — there
is no double-toggling risk. After all 16 terms, `flag_qubit` holds 1 if the pair IS
adjacent, 0 otherwise.

4. **Apply one final X gate to `flag_qubit`** to invert this into the required "problem"
   polarity: now `flag_qubit` = 1 means NOT adjacent (violates the chain), 0 means adjacent
   (satisfies it) — matching the polarity of every other flag in the circuit.

**Bit-pattern reference** (codes 0–6, as `(LSB, mid, MSB)`, same convention as `encoding.py`):
```
0=(0,0,0)  1=(1,0,0)  2=(0,1,0)  3=(1,1,0)  4=(0,0,1)  5=(1,0,1)  6=(0,1,1)
```

**Hand-verified worked example** — include this as a comment or doctest in the new
function: for the ordered pair `(x=1, y=0)` (cell_a holds code 1, cell_b holds code 0),
code 1 = `(1,0,0)` and code 0 = `(0,0,0)`. So step 1 applies X to `cell_a_qubits[1]` (the
mid qubit, since code 1's mid bit is 0) and `cell_a_qubits[2]` (MSB, also 0) — cell_a's LSB
bit is already 1, no X needed there — and X to all three of `cell_b_qubits` (code 0 is all
zeros, so all three bits need inverting to read as positive controls). This term's MCX
fires (and correctly signals "adjacent", since `(1,0)` is in the edge list) exactly when
cell_a=1 and cell_b=0.

**Uncompute (LIFO order) — extend the existing pattern**: after the final phase kick, undo
the 12 flags in exact reverse order of computation:
1. Undo the 2 adjacency flags (reverse of their computation: undo the final inversion X,
   then undo the 16 enumerated terms in reverse order) — **these were computed last, so
   they must be undone first.**
2. Then undo the 4 validity flags (as in Phase 3).
3. Then undo the 6 collision flags (as in Phase 3).

### 4. Update `build_placement_oracle()`

- Compute collision flags (unchanged) → compute validity flags (unchanged) → **compute the
  2 adjacency flags** via `_append_adjacency_flag` for each pair in `ADJACENCY_PAIRS` (using
  `CELL_QUBITS[a]` and `CELL_QUBITS[b]` for each `(a,b)` in the list) → X-sandwich **all 12
  flags** (6 collision + 4 validity + 2 adjacency) → realize the 12-qubit MCZ via
  `H` on the 12th flag qubit → 11-control MCX (first 11 flags as controls, 12th as target)
  → `H` again → undo the 12-flag X-sandwich → uncompute in LIFO order per §3 above.
- End with `assert qc.num_qubits == TOTAL_QUBITS` (now 27) — same discipline as Phase 3.
- ⚠️ Same ancilla-budget rule as Phase 3: no `qc.mcx(...)` call anywhere in this function
  may use an `ancilla_qubits` argument or `v-chain`/`recursion` mode. Every control must be
  a real, already-allocated qubit from the fixed 27-qubit layout.

### 5. Update `classical_baseline.py`

Add a new function, e.g. `enumerate_valid_placements_with_adjacency()`, that filters the
existing `enumerate_valid_placements()` output (or re-derives via the same
`itertools.permutations(range(7), 4)` approach) by the chain condition: both
`(sites[0], sites[1])` and `(sites[1], sites[2])` must be in the 8-edge adjacency set
(define the edge set as a module-level constant, both directions, matching the 16-pair list
in §3). Add `count_valid_placements_with_adjacency()` analogously to the existing
`count_valid_placements()`. **Do not hardcode `96`** anywhere — it must be computed by this
function, matching how `840` was never hardcoded in Phase 3.

### 6. Testing — reuse the three-stage methodology from Phase 3, extended for adjacency

**Stage 1 — extend `test_encoding.py`** (or add `test_classical_baseline.py` if cleaner):
assert `count_valid_placements_with_adjacency() == 96`. Also assert a few hand-checked
individual placements' chain-validity directly (e.g. `(0,1,2,3)` → chain-valid;
`(0,1,3,2)` → chain-invalid), matching the worked cases in Stage 2 below so the pure-Python
logic is confirmed before any quantum circuit is involved.

**Stage 2 — extend `test_oracle_sanity.py`**: three new hand-picked deterministic
statevector cases (prepared via X gates only, oracle applied once, inspect the resulting
statevector at the exact predicted index, confirm all other probability mass is zero):

| Case | Meaning | X gates applied | Statevector index | Expected amplitude |
|---|---|---|---|---|
| A | Sites (0,1,2,3) — collision-free, valid, chain-adjacent (0↔1 and 1↔2 both edges) | X(3), X(7), X(9), X(10) | 1672 | ≈ **-1+0j** (marked) |
| B | Sites (0,1,3,2) — collision-free, valid, chain **broken** (1↔3 is not an edge) | X(3), X(6), X(7), X(10) | 1224 | ≈ **+1+0j** (unmarked) |
| C | Sites (0,0,1,2) — collision (regression check: still correctly rejected with the new 12-flag oracle) | X(6), X(10) | 1088 | ≈ **+1+0j** (unmarked) |

Note Case C reuses the exact same qubit pattern and index as Phase 3's collision test case —
this is expected, since the two new ancilla qubits (25, 26) default to `\|0⟩` and don't
change the numeric value of a statevector index that only has bits set below qubit 25.
Use `AerSimulator(method="statevector")` + `save_statevector()`, per the memory-note warning
in §2.

**Stage 3 — extend `test_placement.py`**: build the manual Grover loop (27-qubit oracle,
12-qubit diffusion on q0–q11 only — unchanged pattern from Phase 2/3 — measure q0–q11 only),
compute `optimal_iterations(12, 96)` (approximate) and `optimal_iterations(12, 96,
exact=True)`, run at both, decode every measured result, cross-check each accepted result
against `enumerate_valid_placements_with_adjacency()`'s actual output (not just internal
consistency). Report the observed success probability at both iteration counts.

⚠️ **Heads up on this phase's iteration numbers — different pattern than every prior
phase**: the approximate and exact formulas **agree this time** (`k=5` both ways, ~98.57%
theoretical success), unlike the "approximate overshoots exact by exactly one iteration"
pattern seen in every phase so far (2-qubit trivial case, Module 2, Phase 3). This is
expected — the overshoot pattern is a coincidence of the earlier ratios, not a rule — but
flag it explicitly in your test output so it isn't mistaken for a miscalculation.

### 7. Deliverables checklist

- [ ] `placement_oracle.py` extended: new constants, `_append_adjacency_flag`, updated
      `build_placement_oracle()` (12-flag AND, 27-qubit assert), all existing Phase 3
      functions/constants untouched.
- [ ] `classical_baseline.py` extended: new enumeration/count functions for the
      adjacency-constrained set, `96` never hardcoded.
- [ ] All three test stages extended and passing, including full Phase 3 regression (every
      existing Phase 3 assertion still passes unmodified).
- [ ] No `pytest`, no new dependencies, no touched version numbers anywhere.
- [ ] Run every test file yourself and report full output before the user sees it.
- [ ] `git add . && git commit -m "Phase 3b: Module 1 adjacency constraint" && git push`

Now build Phase 3b exactly as specified above.
