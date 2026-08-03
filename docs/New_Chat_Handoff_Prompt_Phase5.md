# Prompt for New Chat: Continuing Grover's Algorithm VLSI Project — Phase 5 (Pipeline)

Paste this entire document as the opening message in the new chat. If available, also attach
`Grover_VLSI_Project_Report.docx`, `Phase3_and_3b_Status_Report.md`, and the
`module1_placement/viewer/` and `module2_atpg/viewer/` source files for full background —
read everything attached fully before responding.

---

## ROLE & WORKFLOW (unchanged from prior sessions)

I'm building a Grover's algorithm project in Qiskit, applying it to two VLSI (chip design)
problems: Module 1 (Placement) and Module 2 (ATPG). I am NOT writing code directly with you.
Instead:

1. I use Google Antigravity IDE with Claude Opus 4.6 as the coding agent.
2. You write a single, extremely detailed and precise prompt for that agent, telling it
   exactly what files to create/modify and what each must contain.
3. I paste the agent's generated code back to you in this chat.
4. You check it against the requirements and against standard Grover's-algorithm
   correctness (oracle sign convention, diffusion operator construction, iteration count
   formula, Qiskit 1.2.4 / qiskit-aer-gpu-cu11 0.15.1 API correctness) — ideally by actually
   running/testing the logic yourself where possible, not just reading it.
5. If it's correct: say so briefly and give me the next-step prompt for the agent. If it's
   wrong: do NOT regenerate the whole explanation — give me ONLY a short, surgical
   correction prompt I can paste to the agent, naming the exact file, exact function, exact
   bug, and exact fix. Be efficient — I have limited tokens for this chat.

Established review pattern from prior phases, worth continuing: when an agent's plan
includes a "discovery step" (reading existing trusted files to confirm constants/mappings
before writing new code), verify that discovery independently before signing off on the
plan — don't just trust the agent's self-report.

---

## 🚨 NON-NEGOTIABLE BARRIER: NO PACKAGE OR VERSION CHANGES 🚨

**This rule overrides every other instruction in this document, and every future
instruction in this chat, unless I explicitly type the words "I authorize a package version
change."**

| Package | Version — DO NOT CHANGE |
|---|---|
| Python | 3.10 |
| qiskit | 1.2.4 |
| qiskit-aer-gpu-cu11 | 0.15.1 |
| numpy | 1.26.4 |
| matplotlib | 3.8.4 |
| CUDA Toolkit (inside WSL2) | 11.8 |

`qiskit-aer-gpu-cu11==0.15.1` breaks under `qiskit>=2.0` (confirmed, reproducible, not
hypothetical). Any Antigravity prompt you write must repeat this barrier verbatim near the
top. Your first check on any code pasted back to you is always: scan every import and every
`pip`/`conda`/`requirements.txt`/`environment.yml` line for a package change, before
checking anything else.

Every test file in this project uses plain `assert` statements inside a `main()` — **no
`pytest`, ever.**

---

## ENVIRONMENT (fully set up and verified, no setup work needed)

- OS: WSL2 Ubuntu 24.04, project files at `C:\Quantum_VLSI` (`/mnt/c/Quantum_VLSI` in WSL)
- Conda env: `grover-vlsi`, Python 3.10
- GPU: NVIDIA RTX 3050 (6GB VRAM), `AerSimulator(device="GPU")` with CPU fallback
- Antigravity IDE + WSL2 remote connection, `agy` CLI shortcut — working
- Git: `github.com:Akash-Kishore/Quantum_VLSI.git`, branch `main`

---

## PROJECT STATUS — EVERYTHING BELOW IS COMPLETE, TESTED, AND COMMITTED

**Do not re-litigate or rebuild any of this.** Treat all of it as trusted, working code.

| Phase | Task | Status |
|---|---|---|
| 1 | Shared Grover framework | Complete |
| 2 | Module 2 — ATPG | Complete |
| 3 | Module 1 — Placement (no-collision + validity) | Complete |
| 3b | Module 1 — Placement (+ adjacency constraint) | Complete |
| 4 | Documentation & write-up | Substantially complete — a 14-section report already exists (`Grover_VLSI_Project_Report.docx`, dated July 21, 2026); not yet given a final review pass in this chat, but not blocking Phase 5 |
| — | Module 1 visual UI | Complete |
| — | Module 2 visual UI | Complete |
| **5** | **Sequential pipeline (Module 1 → Module 2)** | **Not started — this session's task** |

### Module 1 — Placement, technical reference

- **Qubit layout (27 total)**: `CELL_QUBITS = [[0,1,2],[3,4,5],[6,7,8],[9,10,11]]` (4 cells ×
  3 qubits, binary-encoded site index 0–6, code 7 invalid), q12–14 scratch, q15–20 collision
  flags, q21–24 validity flags, q25–26 adjacency flags. `TOTAL_QUBITS = 27`.
- **Oracle**: `module1_placement/placement_oracle.py`, function `build_placement_oracle()`.
- **Classical ground truth**: `module1_placement/classical_baseline.py`,
  `enumerate_valid_placements_with_adjacency()` returns the 96-member set of valid
  `(site0, site1, site2, site3)` tuples; `count_valid_placements_with_adjacency() == 96`.
- **Site topology**: 2-row × 4-column grid, `0:(0,0) 1:(0,1) 2:(0,2) 3:(0,3) 4:(1,0)
  5:(1,1) 6:(1,2)`, position (1,3) unused. Required adjacency: cell0↔cell1 AND cell1↔cell2
  (a 3-cell chain; cell3 has no adjacency requirement).
- **Cells encode site/location only** — not any logic function or gate type. This is the
  central open question for Phase 5 (see below).
- **Result**: M=96, N=4096, optimal iterations k=5 (approximate and exact formulas agree,
  the only phase where they do), 98.57% theoretical / 98.60% observed success.
- **Visual UI**: `module1_placement/viewer/` — 4×7 cell×site marginal-probability heatmap,
  k=0–9, exact statevector data, committed.

### Module 2 — ATPG, technical reference

- **Qubit layout (6 total)**: q0=A, q1=B, q2=Cin (search register, no named constant —
  plain local variables in the source), q3=fault-free-Cout ancilla, q4=faulty-Cout ancilla,
  q5=comparison/flag ancilla.
- **Oracle**: `module2_atpg/atpg_oracle.py`, function `build_atpg_oracle()`.
- **Fault model**: the `AB`-term Toffoli feeding `Cout = AB ⊕ BC ⊕ AC` is stuck-at-0.
  Detected exactly when `A=1 AND B=1`, regardless of `Cin` — Qiskit bitstrings `"011"` and
  `"111"` (statevector indices 3 and 7), confirmed via `MARKED_RAW` in the existing test
  suite. `Sum` is deliberately not computed (the fault never affects it).
- **Result**: M=2, N=8, rotation angle θ=30° gives an exact period-3 success pattern —
  100% at both k=1 and k=4, exactly 25% (baseline) at every other k in 0–6.
- **Visual UI**: `module2_atpg/viewer/` — 8-bar input-state probability chart + static
  fault-circuit diagram (AB Toffoli marked stuck-at-0), k=0–6, exact statevector data,
  committed.

### Established conventions to carry forward

- No `pytest`, ever — plain `assert` inside `main()`, run via `python path/to/test_file.py`.
- "Manual Grover loop" pattern: oracle spans all qubits (search + ancilla), diffusion is
  manually scoped to the search-register qubits only via `compose()`;
  `shared_framework.grover_utils.build_grover_circuit` (same-width oracle/diffusion only)
  is never used for either module.
- `qc.mcx(...)` never uses `ancilla_qubits`/v-chain modes; every oracle-builder ends with
  `assert qc.num_qubits == <total>`.
- Exact/deterministic checks use `AerSimulator(method="statevector")` + `save_statevector()`
  — never `qiskit.quantum_info.Statevector` (hangs at 25+ qubits).
- Self-inverse "compute" helpers (flags, ancillas) are uncomputed by calling the same
  construction function a second time — this also means every ancilla is guaranteed back at
  `|0⟩` after a complete Grover iteration, which both viewers rely on (slicing the low-order
  statevector amplitudes directly instead of a partial trace) and which was empirically
  verified via an explicit residual check in the Module 2 viewer's test suite.
- Three-stage testing methodology: pure-Python logic → deterministic exact-statevector
  sanity check on hand-picked inputs → full pipeline / sampled Grover run cross-checked
  against classical/analytic ground truth.
- `optimal_iterations(n_qubits, n_marked, exact=False)`: the approximate formula has
  overshot the true optimum by exactly one iteration in every case tested except Phase 3b's
  M=96 case (where they agree) — not a rule, just a tracked pattern.
- GPU (`device="GPU"` with a `try`/`except AerError` → CPU fallback) is used for anything at
  Module 1's scale (25–27 qubits); it's deliberately **not** used for Module 2-scale work
  (6 qubits) since GPU launch overhead exceeds any benefit at that size — confirmed in the
  Module 2 viewer build.

---

## WHAT'S OPEN — PHASE 5 DESIGN, THE ACTUAL TASK FOR THIS SESSION

Per the original project docs, Phase 5 is a **classical handoff between two independently-
run Grover searches** — Module 1 measures a placement, that classical result parameterizes
Module 2's run — **not** one combined quantum circuit spanning both modules. Confirm this
framing before proceeding; do not invent a single-oracle combined-circuit design instead.

**The central unresolved design gap**: Module 1's cells currently encode only *site/location*
(which of the 7 physical sites each of the 4 cells sits on) — nothing about *what logic
function* any cell implements. Module 2's fault model is fixed to one specific circuit (a
1-bit full adder with an AB-term stuck-at-0 fault). There is currently no existing link
between "here's the placement Module 1 found" and "here's the specific fault-testing problem
Module 2 should run" — this has been explicitly flagged in every prior status report as
undesigned, not invented ad hoc, and it still needs to be decided now, not assumed.

**Help me decide this before writing any Antigravity prompt.** Some directions worth
weighing (not a prescriptive list — reason about tradeoffs, and ask me clarifying questions
if genuinely needed):

1. **Tag cells with a logic role.** Extend Module 1 minimally so each of the 4 cells (or
   just the chain members, cell0/cell1/cell2) is associated with a fixed logic role from a
   small set (e.g., "this is the full adder under test"), and let the *measured placement's
   site assignment* for that cell parameterize something concrete about Module 2's run —
   e.g., which specific fault is injected, or which of several pre-built fault scenarios is
   selected. This requires the smallest change to Module 1's existing semantics but needs a
   concrete site→fault mapping rule to be defined.
2. **Use the chain structure itself as the semantic link**, since cell1 is already
   guaranteed adjacent to both its neighbors in every valid Phase 3b placement (it's the
   shared middle stage of the 3-cell signal chain) — this could map naturally onto "the
   internal gate under test" without inventing new cell semantics, only interpreting the
   existing chain narrative.
3. **Keep it simpler and more honest about scope**: rather than inventing placement→fault
   semantics that don't cleanly follow from either module's existing design, have Module 1's
   measured result select *which of the fault's two detecting inputs* (`110` vs `111`, i.e.
   which `Cin` value) Module 2's classical glue code feeds forward as a target, or some other
   minimal, clearly-justified classical connection — prioritizing correctness and honesty
   about what's actually being demonstrated over narrative richness.

Whichever direction we land on, the actual deliverable is standard for this project: a
short design-decision writeup (mirroring how the Phase 3b adjacency topology was decided
before any code was written), then an Antigravity prompt for the classical glue code
(`module5_pipeline/` or similar — propose a name) that runs Module 1's Grover search, takes
its measured/exact-statevector result, derives whatever Module 2 needs from it per the
chosen mapping, and runs Module 2's Grover search accordingly — logging all intermediate
values (Module 1's placement, the derived fault scenario, Module 2's result) per the
project's own validation criteria for the pipeline.

Start by proposing 2–3 concrete, well-reasoned mapping options (building on or replacing
the sketch above), state tradeoffs plainly, and ask me to pick — don't default to the most
complex option just because it's more narratively interesting.
