# Prompt for New Chat: Continuing Grover's Algorithm VLSI Project — Publication Track (Phase 6+)

Paste this entire document as the opening message in the new chat, **along with the
attached `Publication_Roadmap_Phase6_Onward.md`** (this is the authoritative source of
truth for all technical detail below — read it fully before responding). If available,
also attach `Phase3_and_3b_Status_Report.md`, `Grover_VLSI_Project_Report.docx`,
`Hardware_Software_Requirements.docx`, and `Grovers_Algorithm_VLSI_Project.docx` for full
background.

---

## ROLE & WORKFLOW (unchanged from prior sessions)

I'm building a Grover's algorithm project in Qiskit, applying it to VLSI (chip design)
problems, now being extended into a publication-track comparative study. I am NOT writing
code directly with you. Instead:

1. I use Google Antigravity IDE with Claude Opus 4.6 as the coding agent.
2. You write a single, extremely detailed and precise prompt for that agent, telling it
   exactly what files to create/modify and what each must contain.
3. I paste the agent's generated code back to you in this chat.
4. You check it against the requirements and against standard correctness (oracle sign
   convention, diffusion operator construction, iteration count formula, QAOA
   phase-separator/mixer construction, Qiskit 1.2.4 / qiskit-aer-gpu-cu11 0.15.1 API
   correctness) — ideally by actually running/testing the logic yourself, not just reading it.
5. If it's correct: say so briefly and give me the next-step prompt for the agent. If it's
   wrong: do NOT regenerate the whole explanation — give me ONLY a short, surgical
   correction prompt naming the exact file, exact function, exact bug, and exact fix. Be
   efficient — I have limited tokens for this chat.

Established review pattern, worth continuing: when an agent's plan includes a "discovery
step" (reading existing trusted files to confirm constants/mappings before writing new
code), verify that discovery independently before signing off on the plan — don't just
trust the agent's self-report.

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

`qiskit-aer-gpu-cu11==0.15.1` breaks under `qiskit>=2.0` (confirmed, reproducible). Any
Antigravity prompt you write must repeat this barrier verbatim near the top. Your first
check on any code pasted back to you is always: scan every import and every
`pip`/`conda`/`requirements.txt`/`environment.yml` line for a package change, before
checking anything else.

**New for this phase, needs explicit sign-off before use, not blanket-approved:**
- `scipy` — needed for QAOA's classical optimizer loop. Must be verified as actually
  present/compatible in the existing `grover-vlsi` env before use, not assumed.
- `qiskit-ibm-runtime` — needed only for the scoped real-hardware ATPG run. Must live in a
  **fully separate environment**, never added to `grover-vlsi`.
- Default answer to anything else is no. QAOA, backtracking, and simulated annealing are
  all implementable in plain Python plus the existing pinned Qiskit — that's the intended
  approach (see Publication_Roadmap §7).

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

## PROJECT STATUS — WHAT'S ALREADY COMPLETE AND TRUSTED

**Do not re-litigate or rebuild any of this.**

| Phase | Task | Status |
|---|---|---|
| 1 | Shared Grover framework | Complete |
| 2 | Module 2 — ATPG (single AB-term stuck-at-0 fault) | Complete |
| 3 | Module 1 — Placement (no-collision + validity) | Complete |
| 3b | Module 1 — Placement (+ adjacency constraint) | Complete |
| 4 | Documentation & write-up (`Grover_VLSI_Project_Report.docx`) | Substantially complete — now superseded in intent by the paper itself, but remains valid as standalone content |
| — | Module 1 & Module 2 visual UIs | Complete |
| 5 | Sequential pipeline (site→fault mapping, M=0/2/6 design) | **Designed but not built** — absorbed into Phase 6+ below, not wasted, see next section |

### Module 1 — Placement, technical reference
- **Qubit layout (27 total)**: `CELL_QUBITS = [[0,1,2],[3,4,5],[6,7,8],[9,10,11]]` (4 cells
  × 3 qubits, binary-encoded site index 0–6, code 7 invalid), q12–14 scratch, q15–20
  collision flags, q21–24 validity flags, q25–26 adjacency flags.
- **Site topology**: 2-row × 4-column grid, position (1,3) unused. Required adjacency:
  cell0↔cell1 AND cell1↔cell2 (chain; cell3 unconstrained).
- **Result**: M=96, N=4096, k=5 optimal (approx and exact agree — the only phase where
  they do), 98.57% theoretical / 98.60% observed success.

### Module 2 — ATPG, technical reference
- **Qubit layout (6 total)**: q0=A, q1=B, q2=Cin, q3=fault-free-Cout ancilla,
  q4=faulty-Cout ancilla, q5=comparison/flag ancilla.
- **Fault model**: AB-term Toffoli stuck-at-0. Detected exactly when A=1 AND B=1 (Qiskit
  bitstrings `"011"`/`"111"`). M=2, N=8, period-3 pattern: 100% at k=1 and k=4.

### Established conventions to carry forward
- No `pytest`, ever — plain `assert` inside `main()`.
- "Manual Grover loop" pattern: oracle spans all qubits, diffusion manually scoped to
  search-register qubits via `compose()`.
- `qc.mcx(...)` never uses ancilla_qubits/v-chain modes; every oracle-builder ends with
  `assert qc.num_qubits == <total>`.
- Exact/deterministic checks use `AerSimulator(method="statevector")` +
  `save_statevector()` — never `qiskit.quantum_info.Statevector` (hangs at 25+ qubits).
- Self-inverse "compute" helpers are uncomputed by calling the same construction function
  a second time.
- Three-stage testing methodology: pure-Python logic → deterministic exact-statevector
  sanity check → full sampled/pipeline run cross-checked against classical ground truth.
- Classical ground truth is computed fresh, by brute force, **before** any oracle or QUBO
  is built around a new constraint configuration — never assumed to generalize.

---

## THE PIVOT: WHY THIS CHAT EXISTS

The original project (Phases 1–5) is a well-executed, correct demonstration, but a search
of the literature confirmed it is **not novel enough on its own for a conference paper**:
Grover-for-ATPG-via-stuck-at-faults has published prior art (QuSAF, IEEE 2023; an earlier
2021 SAT-based Grover ATPG paper on real IBM hardware), and Grover-for-placement-as-CSP is
standard pedagogical material, while real placement research uses QAOA/quantum-annealing
cost-based methods instead (because real placement is optimization, not pure decision).

**The novel angle we landed on**: Grover-style decision-oracle search and QAOA-style
cost-based optimization are usually treated as interchangeable "quantum speedup" tools, but
they are structurally different near a problem's feasibility boundary. Grover's success
probability is a function of M/N; as constraints tighten toward infeasibility, M→0 and the
governing formula itself breaks down (division by zero / undefined rotation angle) — not
just weak performance, an actual discontinuity. QAOA's cost function has no such
discontinuity — it degrades gracefully and keeps returning a graded "least bad" answer past
the same boundary. **This is the paper's central, provable, testable claim.**

Full detail — the 2×2 experimental framework, module-by-module changes, theoretical lemmas
to prove, statistical methodology, phased build plan (Phase 6–17), paper structure, venue
targets, and related work to cite — is in the attached `Publication_Roadmap_Phase6_Onward.md`.
**Read that file in full before doing anything else in this chat.** This handoff document
is a summary and orientation layer on top of it, not a replacement for it.

---

## SIX OPEN DESIGN DECISIONS — RESOLVE BEFORE WRITING ANY NEW CODE

Per this project's established convention (same pattern as Phase 3b's adjacency topology
decision), these need explicit resolution first, not silent defaults:

1. **Module 1's QAOA encoding**: one-hot (28 qubits, report the qubit-count mismatch with
   Grover's 12-qubit binary encoding as a finding) vs. binary-matched (12 qubits, requires
   building order-reduction for the higher-order penalty terms). Roadmap recommends
   one-hot first.
2. **Tightness parameter α's definition** for Module 1's sweep (adjacency-edge count is the
   sketched default — confirm or replace).
3. **The engineered-infeasible (M=0) placement instance** — must be verified by brute force
   before any oracle/QUBO is built around it.
4. **Bit-widths for Module 2's n-bit generalization** — 2-bit and 3-bit adders proposed;
   confirm this is the right stopping point given qubit/gate-count growth.
5. **Hardware execution scope** — 1-bit ATPG case only, or extend to 2-bit; decide once
   Phase 6–8 numbers exist.
6. **`scipy` status** — verify actual presence/version in `grover-vlsi` before treating it
   as available.

---

## RECOMMENDED STARTING POINT

**Phase 6: Module 2's generalized fault family** (product-term stuck-at-0/1, XOR-chain
stuck-at, fault-free control — six real fault classes plus the control, replacing the
single AB-term fault with a provable family; derive the M/N ratios algebraically, then
verify by brute force at N=8). This is the best place to start because:

- It's fully independent of Module 1's still-open encoding decision (#1 above), so no time
  is lost waiting on that.
- It builds directly on trusted, complete code (`module2_atpg/`) with no new package risk.
- It absorbs and completes the Phase 5 fault-family design work already done in the prior
  chat, so nothing from that session is wasted.

Ask me to confirm this starting point (or propose a different order from the Phase 6–17
table in the roadmap), then write the first Antigravity prompt — covering the parameterized
fault-injection framework (`module2_atpg/generalized_faults/fault_family.py`), the derived
M/N ratio proofs stated as code comments/docstrings referencing the lemma, and a Stage-1
pure-Python test validating the derived ratios against brute-force enumeration for all six
fault classes plus the control, before any circuit-level work begins.
