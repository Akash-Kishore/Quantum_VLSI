# Publication Roadmap: Phase 8 Onward
### Grover's Algorithm for VLSI Design & Test — Publication Track, Post-Literature-Review Update

This document supersedes `Publication_Roadmap_Phase6_Onward.md` for everything from Phase 8
forward. Phases 1–7 are complete, verified, and should not be re-litigated. This document
folds in the results of a literature-review checkpoint conducted after Phase 7, which
confirmed the core thesis still appears novel and identified a small set of low-cost
additions worth making, while explicitly rejecting several scope-creep proposals.

---

## 1. Status Summary — Phases 1–7 (all complete, independently verified)

| Phase | Task | Status |
|---|---|---|
| 1 | Shared Grover framework | Complete |
| 2 | Module 2 — ATPG (single AB-term stuck-at-0 fault) | Complete |
| 3 | Module 1 — Placement (no-collision + validity) | Complete |
| 3b | Module 1 — Placement (+ adjacency constraint) | Complete |
| 4 | Documentation & write-up (`Grover_VLSI_Project_Report.docx`) | Substantially complete |
| — | Module 1 & Module 2 visual UIs | Complete |
| 5 | Sequential pipeline (original stretch-goal design) | Superseded — absorbed into Phase 6's fault family, not built as a literal pipeline |
| 6 | Module 2 generalized fault family (11 sites) + M=0 lemma | **Complete, independently verified** |
| 7 | Module 2 classical baselines (exhaustive + random sampling) | **Complete, independently verified** |

### 1.1 Phase 6 — what was built and confirmed

- `module2_atpg/generalized_faults/fault_family.py` — pure-Python Boolean model, 11
  enumerated fault sites (6 product-term: AB/BC/AC × stuck-at-{0,1}; 4 XOR-chain: line1/line2
  × stuck-at-{0,1}; 1 fault-free control). Algebraic M/N proofs for each, validated by brute
  force. Note: informal planning language said "six real fault classes plus control" — the
  correct, fully-enumerated count is **11**, not 7. This was flagged explicitly in code
  comments rather than silently reconciled.
- `module2_atpg/generalized_faults/generalized_oracle.py` — unified 10-qubit oracle
  (q0–2 search: A,B,Cin; q3=t_good; q4=Cout_good; q5=Sum_good; q6=t_faulty; q7=Cout_faulty;
  q8=Sum_faulty; q9=flag). **A real ancilla-uncomputation bug was caught and fixed during
  review**: Sum depends on T within the same block, so the established "call the same
  compute function twice to uncompute" convention (safe for every prior phase's
  independent ancillas) silently corrupted Sum's uncompute. Fixed by splitting each block
  into independently-callable sub-steps (T, Cout, Sum) and uncomputing in strict reverse
  dependency order. **New convention going forward**: any oracle where one ancilla's
  computation reads another ancilla's value must use this granular-uncompute pattern, not
  the simple "call twice" pattern.
- Stage 2 (exhaustive statevector + uncompute check, 88 cases): all pass, independently
  re-run and confirmed after the fix.
- Stage 3 Part A (sampled Grover, 10 real fault sites): matches theory exactly —
  M=2 → ~100% at k=1; M=6 → ~75% at k=2 (k=1 would hit exact destructive interference,
  sin²(π)=0 — the exact-mode iteration search correctly avoids this); **M=4 is a genuine
  secondary finding**: at M/N=0.5 exactly, success probability is mathematically fixed at
  50% for *every* iteration count k (θ=π/4 makes the geometric picture perfectly
  symmetric) — this is a defined, smooth optimum-plateau, distinct from the M=0
  discontinuity, and worth a sentence in the paper distinguishing the two.
- Stage 3 Part B (M=0 lemma): empirically confirmed — `optimal_iterations(3, 0)` raises
  `ZeroDivisionError` in both approximate and exact modes; measured success probability is
  exactly 0.0 for k=0–8. A missing assertion (the test only *observed* this rather than
  *enforcing* it) was caught and fixed — the check is now load-bearing, confirmed via a
  simulated-regression test.

### 1.2 Phase 7 — what was built and confirmed

- `module2_atpg/generalized_faults/classical_baseline.py` — exhaustive search (canonical
  order, stops at first hit, `queries_used=8` on failure = certified negative), random
  sampling without replacement (same semantics, randomized order), closed-form expected
  queries `(N+1)/(M+1)` (proven and confirmed exact against independent brute-force
  enumeration over all 8! permutations — not a wrapper, a true independent check), and a
  Monte Carlo trial runner (2000 trials, seed 42).
- Confirmed E[Q] values: M=2 → 3.0, M=4 → 1.8, M=6 → 1.286 (exact matches, brute-force vs.
  closed-form agree to `<1e-9`).
- **The M=0 "failure signature" contrast is built and verified**: classical exhaustive and
  random-sampling both correctly report "NO DETECTING INPUT EXISTS" as a certified
  negative (8/8 queries, 100% of 2000 trials); Grover (restated from Phase 6 Stage 3 Part
  B) returns a uniform distribution with no such signal. This is written up as its own
  printable section, ready to drop into the paper's discussion.

---

## 2. Literature Review Checkpoint (conducted after Phase 7)

A third-party (ChatGPT-generated) literature survey and set of "novelty extension"
proposals was reviewed. Findings:

- **Core thesis appears to remain novel.** Targeted search found real, adjacent literature
  (Grover-mixer QAOA / G-QAOA — a *hybrid* operator combining Grover-style mixers inside
  QAOA, benchmarked against plain Grover on 3-SAT) but nothing addressing this project's
  specific question: the *separately-run*, paradigm-selection comparison between
  decision-oracle search and cost-based optimization, specifically at the M=0 feasibility
  boundary, specifically VLSI-framed. This must be stated as "not found in a handful of
  targeted searches," not "confirmed absent" — a full systematic review has not been done.
- **One genuinely useful new citation confirmed real**: Akshay, Philathong, Zacharov,
  Biamonte, "Reachability Deficits in Quantum Approximate Optimization" (Phys. Rev. Lett.
  124, 090504, 2020; expanded as "...of Graph Problems," Quantum 5, 532, 2021). Shows QAOA
  performance depends strongly on constraint-to-variable density. This is independent,
  peer-reviewed support for the tightness parameter α's relevance — add to related work.
- **Must explicitly distinguish from the Grover-mixer/G-QAOA literature** (e.g. Zhang et
  al., "Grover-QAOA for 3-SAT," arXiv:2402.02585 / Quantum Sci. Technol. 2024) in the
  related-work section, since a reviewer familiar with that line of work will otherwise
  wonder if this project is reinventing it. It is not — that literature builds one hybrid
  algorithm; this project compares two separately-run paradigms.
- **Ten "extension" proposals were triaged** — see §3 below for what was accepted (folded
  into existing phases, no new phase numbers) vs. rejected (real scope creep).

### 2.1 Accepted, folded into existing phases — no new phase numbers

| Idea | Folded into | Why |
|---|---|---|
| Present results as a phase-transition curve across multiple M/N ratios, not just M=0 | Phase 11 (sweep) + Phase 15 (writing) | Data already exists — Phase 6 gave M/N = 0, 0.25, 0.5, 0.75; Phase 11 already plans a Module 1 sweep. Free — a framing choice, not new work. |
| Oracle complexity table (ancilla/gate counts vs. constraint count) | Phase 15 (writing) | Already-measured data sitting in old status reports (Phase 3: 259 gates/25 qubits; Phase 3b: 909 gates/27 qubits; Phase 6: 10-qubit oracle). Tabulate, don't re-simulate. |
| Analytical scaling law (pen-and-paper extrapolation) | Phase 15 (writing) | Cheap — derived from the same already-collected data points as above, no new simulation needed. |
| Entropy / KL-divergence metric between uniform and Grover output distributions | Phase 12 (statistical methodology) | Post-processing on distributions already computed and verified in Phase 6. One more metric alongside success probability. |
| Noise-aware feasibility boundary (does hardware noise move the apparent M=0 boundary?) | Phase 13 (hardware execution) | Not separate work — Phase 13 already puts the control (M=0) fault site on real hardware. This is the specific analysis question to ask once that data exists. |
| Reframe research question as paradigm-selection ("which computational paradigm fits which problem class") | Phase 15 (writing) | Wording upgrade only — this is already substantively the roadmap's thesis. |

### 2.2 Rejected for this paper (explicitly out of scope)

| Idea | Why rejected |
|---|---|
| Generalize beyond placement + ATPG to routing, clock-tree, cell legalization | Each new VLSI subdomain has historically needed its own from-scratch design-decision process and fresh brute-force verification (see Phase 3b's adjacency topology decision as the template). Three more subdomains ≈ three more Phase-3b-sized efforts. Would risk the "guaranteed complete deliverable" principle this project has protected since Phase 1. |
| Universal oracle compiler (constraint spec → automatic oracle synthesis) | A different paper's contribution — substantial, unscoped software-engineering complexity disproportionate to an empirical comparative-methodology paper. |
| Constraint topology sweep (sparse → dense → disconnected) as a separate axis | Redundant with the phase-transition idea above and with Phase 11's already-planned tightness sweep (α is already a constraint-density parameter). |

---

## 3. Six Open Design Decisions — Current Status

Carried forward from the original Phase 6 handoff. **None have been resolved yet** — Phases
6 and 7 didn't require any of them. Decision #1 is now the immediate blocker for Phase 9.

1. **Module 1's QAOA encoding — STILL OPEN, next immediate task.** One-hot (Path A, 28
   qubits, simpler penalty terms, no order reduction needed) vs. binary-matched (Path B, 12
   qubits, qubit-parity with Grover's encoding, needs order reduction for higher-order
   penalty terms). Roadmap default is Path A first, with Path B explicitly scoped as
   optional Phase 17 if Path A ships. A tradeoff discussion was started but not finished —
   pick this up first in the new chat.
2. **Tightness parameter α's definition** — still open. Adjacency-edge count is the
   sketched default, never formally confirmed.
3. **The engineered-infeasible (M=0) placement instance** — still needs to be constructed
   and brute-force-verified. This is Phase 11 work.
4. **Module 2's n-bit generalization bit-widths** — still open. 2-bit and 3-bit adders
   proposed but not confirmed. This is Phase 8's first decision to make.
5. **Hardware execution scope** — still open (1-bit ATPG only, or extend to 2-bit).
6. **scipy's actual presence/version in `grover-vlsi`** — still not verified. This blocks
   Phase 9's QAOA classical-optimizer loop; verify before writing any QAOA code, do not
   assume it's installed just because it's on the pinned-package "needs sign-off" list.

---

## 4. Updated Phase 8–17 Roadmap

| Phase | Task | Depends on | Status |
|---|---|---|---|
| 8 | Module 2 n-bit generalization (2-bit, 3-bit adders) | Phase 6 | Not started |
| 9 | Module 1: resolve encoding decision (§3.1), verify scipy (§3.6), build QAOA arm | None | **Not started — encoding decision unresolved, this is the immediate next step** |
| 10 | Module 1 classical baselines: backtracking + simulated annealing (shares the QUBO cost function with Phase 9's SA-adjacent QAOA cost) | Phase 9 | Not started |
| 11 | Module 1 tightness sweep incl. the engineered-infeasible M=0 case; present results as an explicit phase-transition curve (§2.1) | Phases 9–10 | Not started |
| 12 | Statistical methodology pass across all of Module 1 + Module 2, including an entropy/KL-divergence metric alongside success probability (§2.1) | Phases 6–11 | Not started |
| 13 | Module 2 hardware execution (isolated `qiskit-ibm-runtime` environment, never added to `grover-vlsi`), including the noise-vs-boundary analysis question (§2.1) | Phase 6 | Not started |
| 14 | Visualization extensions | Phase 11 | Not started |
| 15 | Paper writing: results write-up, oracle-complexity table + analytical scaling law, paradigm-selection framing, phase-transition presentation, new related-work citations (reachability-deficits paper; explicit distinction from Grover-mixer/G-QAOA literature) | Everything above | Not started |
| 16 (optional stretch) | Multi-fault coverage framing (query budget vs. fraction of fault classes found) | Phase 8 | Not started |
| 17 (optional stretch) | Module 1 Path B — binary-matched, encoding-parity QAOA | Phase 9 | Not started |

---

## 5. Technical Reference

### 5.1 Module 1 — Placement

- **Qubit layout (27 total)**: `CELL_QUBITS = [[0,1,2],[3,4,5],[6,7,8],[9,10,11]]` (4 cells
  × 3 qubits, binary-encoded site index 0–6, code 7 invalid), q12–14 scratch, q15–20
  collision flags, q21–24 validity flags, q25–26 adjacency flags.
- **Site topology**: 2-row × 4-column grid, position (1,3) unused. Required adjacency:
  cell0↔cell1 AND cell1↔cell2 (chain; cell3 unconstrained).
- **Oracle**: `module1_placement/placement_oracle.py`, `build_placement_oracle()`.
- **Classical ground truth**: `module1_placement/classical_baseline.py`,
  `enumerate_valid_placements_with_adjacency()` → 96-member set.
- **Result**: M=96, N=4096, k=5 optimal (approx and exact agree — the only phase where they
  do), 98.57% theoretical / 98.60% observed success.
- **Gate counts**: Phase 3 (no adjacency) — 25 qubits, 259 gates. Phase 3b (+adjacency) —
  27 qubits, 779 gates (909 decomposed).
- **Visual UI**: `module1_placement/viewer/` — 4×7 cell×site heatmap, k=0–9, exact
  statevector data, committed.

### 5.2 Module 2 — ATPG

- **Original single-fault (Phase 2)**: q0=A, q1=B, q2=Cin, q3=fault-free Cout, q4=faulty
  Cout, q5=flag. M=2/N=8, period-3 pattern (100% at k=1 and k=4).
- **Generalized fault family (Phase 6)**: `module2_atpg/generalized_faults/`
  — `fault_family.py` (11 sites, pure Python, algebraic M/N proofs), `generalized_oracle.py`
  (10-qubit unified oracle: q0–2 search, q3=t_good, q4=Cout_good, q5=Sum_good, q6=t_faulty,
  q7=Cout_faulty, q8=Sum_faulty, q9=flag; granular sub-step uncompute per §1.1).
- **Classical baselines (Phase 7)**: `classical_baseline.py` — exhaustive, random sampling,
  closed-form + brute-force expected queries, Monte Carlo trials.

### 5.3 Established conventions (carried forward, updated)

- No `pytest`, ever — plain `assert` inside `main()`.
- "Manual Grover loop" pattern: oracle spans all qubits, diffusion scoped to search-register
  qubits only via `compose()`.
- `qc.mcx(...)` never uses ancilla_qubits/v-chain modes; every oracle-builder ends with
  `assert qc.num_qubits == <total>`.
- Exact/deterministic checks use `AerSimulator(method="statevector")` +
  `save_statevector()` — never `qiskit.quantum_info.Statevector`.
- **Updated self-inverse convention**: "call the same compute function twice to uncompute"
  is only safe when a block's ancillas are mutually independent (true for every phase
  before Phase 6). Where one ancilla's computation reads another ancilla already written in
  the same block (e.g. Sum reading T), split into independently-callable sub-steps and
  uncompute in strict reverse dependency order instead.
- Three-stage testing methodology: pure-Python logic → deterministic exact-statevector
  sanity check → full sampled/pipeline run cross-checked against classical ground truth.
- Classical ground truth is computed fresh, by brute force, before any oracle/QUBO is built
  around a new constraint configuration — never assumed to generalize.
- **Review discipline (reinforced by Phase 6/7 experience)**: independently rebuild and run
  every piece of agent-submitted code rather than trusting the agent's self-reported test
  output alone. This caught a real ancilla-uncomputation bug and a real missing-assertion
  gap in Phase 6 that the agent's own "ALL TESTS PASSED" reports did not catch. Where
  feasible, also run a quick mutation check (deliberately break a value and confirm the
  relevant assertion actually fires) before signing off on a correctness claim.
- `optimal_iterations(n_qubits, n_marked, exact=False)`: raises `ZeroDivisionError` in both
  modes at `n_marked=0` — this is the concrete, load-bearing demonstration of the paper's
  M=0 discontinuity claim, not just a theoretical aside.

---

## 6. Recommended Immediate Next Step

Resolve decision #1 (§3) — Module 1's QAOA encoding, one-hot (Path A) vs. binary-matched
(Path B) — as a short design conversation before any Phase 9 code is written, same pattern
as the Phase 3b adjacency-topology decision. Verify scipy's actual presence in `grover-vlsi`
(§3.6) in the same conversation, since Phase 9's QAOA optimizer loop needs it. Only then
write the first Phase 9 Antigravity prompt.
