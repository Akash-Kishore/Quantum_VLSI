# Publication Roadmap — Phase 6 Onward
### From Demonstration Project to Conference Paper: Grover's Algorithm for VLSI Design & Test

---

## 0. Executive Summary

**Central claim of the paper:** Decision-oracle quantum search (Grover's algorithm) and
cost-based hybrid quantum-classical optimization (QAOA) are usually treated as
interchangeable "quantum speedup" tools for combinatorial problems. They are not
interchangeable near a problem's feasibility boundary. Grover's success probability is a
function of M/N (marked states / total states); as a constraint set tightens toward
infeasibility, M → 0, the rotation angle collapses, and the algorithm's output becomes
uninformative — not just weak, but literally undefined by its own governing formula.
QAOA has no such discontinuity: its cost function is graded by construction and continues
to return a meaningful "least bad" answer arbitrarily close to and past the infeasibility
boundary. **This paper characterizes that structural gap concretely** using a matched pair
of case studies from the VLSI design-and-test lifecycle — cell placement (Module 1) and
automatic test pattern generation (Module 2) — each solved four ways (quantum-decision,
classical-decision, quantum-optimization, classical-optimization) across a swept tightness
parameter, with the M=0/infeasible boundary as the paper's central, deliberately-engineered
data point rather than an edge case to avoid.

**What is and isn't novel here, stated plainly:**
- Grover-for-ATPG: **not novel** (see §11, prior art exists — cite it, don't compete with it)
- Grover-for-placement-as-CSP: **not novel as a technique** (toy CSP-via-Grover is standard
  teaching material); what's new is using it as one arm of a controlled comparison
- QAOA-for-placement: **not novel as a technique** (active research area, cite it)
- **What is novel**: the paired, controlled, four-method experimental design itself; the
  M=0/infeasibility-boundary behavior characterized as a *structural* property with a
  proof, not an anecdote; the cross-domain replication (placement AND ATPG show the same
  effect); and the finding (to be confirmed experimentally, see §5.3) that Grover's failure
  mode at the boundary may be *less* informative than even a naive classical exhaustive
  search, which returns a clean "no such input exists" rather than a silent flat
  distribution.

---

## 1. Relationship to Existing Work (Phases 1–5)

| Existing asset | Status | Role going forward |
|---|---|---|
| `shared_framework/` | Complete, trusted | Reused as-is for all new Grover-based experiments |
| Module 2 ATPG (single AB-term fault) | Complete, trusted | Becomes the base case of a *generalized fault family* (§5) |
| Module 1 Placement (no-collision, validity, adjacency) | Complete, trusted | Becomes the *Grover-decision* arm of a 4-method comparison (§4) |
| Module 1 & 2 visual UIs | Complete | Extended, not replaced (§4.6, §5.6) |
| Phase 4 documentation (`Grover_VLSI_Project_Report.docx`) | Substantially complete | Superseded by the paper itself; original report remains valid as a standalone artifact/advocate content |
| Phase 5 pipeline (site→fault mapping table, M=0/2/6 design) | Designed, not yet built | **Absorbed into this roadmap** — the 7-scenario fault family from that design becomes Module 2's fault family below (§5.1), so that work is not wasted |

**Do not re-litigate or rebuild anything in the first row.** This roadmap is additive.

---

## 2. Contributions (for the paper's introduction)

1. A controlled, four-method (quantum-decision / classical-decision / quantum-optimization
   / classical-optimization) experimental framework for comparing decision-oracle and
   cost-based quantum approaches to combinatorial VLSI subproblems.
2. A proof that Grover-oracle success probability is discontinuous at the feasibility
   boundary (M=0), with the diffusion operator's fixed-point property as the mechanism,
   generalized beyond the single N=8 case already checked.
3. A generalized, provable fault-class taxonomy for reversible-arithmetic-circuit ATPG
   (product-term stuck-at-0/1, XOR-chain stuck-at-0/1, fault-free control), with derived
   M/N ratios rather than measured-only ones, validated across 1-, 2-, and 3-bit adders.
4. Empirical replication of the graceful-vs-non-graceful degradation effect in **two
   independent domains** (placement, ATPG) — a single case study is an anecdote; two
   matched domains showing the same structural effect is evidence of generality.
5. A comparison, not previously made explicit in the literature reviewed, between Grover's
   failure mode at infeasibility and classical exhaustive search's failure mode at the same
   boundary — the classical case is arguably more informative, which is a stronger and more
   surprising claim than "QAOA degrades better than Grover" alone.

---

## 3. Experimental Design: The 2×2 Framework

Every comparison in this paper follows the same factorial structure, applied twice (once
per module):

| | **Decision** (does a solution exist / find one) | **Optimization** (find the best-scoring assignment, graded) |
|---|---|---|
| **Quantum** | Grover oracle search (existing) | QAOA on a cost Hamiltonian (**new**) |
| **Classical** | Backtracking / constraint-propagation solver (**new**) | Simulated annealing (**new**) |

Both modules are run across a swept **tightness parameter** α, from clearly-feasible
through the feasibility boundary to clearly-infeasible (definitions below, module-specific).
For each α and each of the four methods, record a normalized **solution-quality score**:

- Decision methods report a **binary-flavored** score: success probability (Grover) or
  solve/no-solve + wall-clock (backtracking). Past the feasibility boundary this score is
  either undefined (Grover, formula breaks) or a clean "provably no solution" (backtracking).
- Optimization methods report a **continuous** score: best cost found, normalized as an
  approximation ratio against the classical-optimal or brute-force-optimal cost. This score
  remains well-defined and informative on both sides of the boundary.

**The central figure of the paper** is solution-quality vs. tightness α, all four curves
overlaid, once for Module 1 and once for Module 2. The expected (to be confirmed, not
assumed) shape: decision-paradigm curves show a cliff/discontinuity at α = boundary;
optimization-paradigm curves degrade smoothly through it.

---

## 4. Module 1 (Placement) — Detailed Changes

### 4.1 Open design decision: encoding for the QUBO/QAOA arm

The existing Grover oracle uses **binary (log) encoding**: 3 qubits/cell, site index 0–6
as a 3-bit integer, code 7 excluded via an explicit validity ancilla. This is efficient for
an oracle (12 qubits total) because Grover's oracle just needs a Boolean circuit — it can
use comparators/arithmetic on the binary-encoded integer directly.

QAOA needs a **QUBO** (quadratic unconstrained binary optimization) cost function. Binary
(log) encoding makes "cell i and cell j occupy the same site" and "cell i and cell j are
adjacent" naturally **higher-than-quadratic** polynomial expressions over the encoded bits
(comparing two 3-bit integers for equality/adjacency is not a quadratic function of the
bits) — expressing this as a true QUBO requires auxiliary-variable order reduction, adding
real complexity and qubit overhead.

**Two paths, pick one before building (do not silently default):**

- **Path A — One-hot encoding for the QAOA arm only (recommended default).** Each cell
  gets 7 binary variables (one per site), exactly one of which should be 1. Collision and
  adjacency penalties become natural quadratic terms (e.g. collision penalty
  `Σ_s x_{i,s}·x_{j,s}` for cells i,j). Cost: 7 × 4 = 28 qubits for QAOA vs. 12 for Grover
  — **the qubit-count mismatch is itself a reportable finding**: the encoding that's
  efficient for a decision oracle is not the encoding that's efficient for a QUBO cost
  function, and switching quantum paradigms is not encoding-neutral. Report this explicitly
  in the paper rather than treating it as an inconvenience to hide.
- **Path B — Match Grover's binary encoding exactly, do the order reduction.** Keeps qubit
  count identical (12) for the cleanest possible "same resource budget" comparison, at the
  cost of building and validating a nontrivial quadratization procedure (extra ancilla
  variables per higher-order term, standard technique but real implementation/verification
  work). More rigorous if reviewers push on "you changed two variables at once
  (encoding *and* method)."

**Recommendation:** implement Path A first (faster, defensible, and the qubit-mismatch
finding is genuinely interesting), keep Path B as a documented option-B appendix if time
allows — this mirrors how Phase 3b's topology decision was made (state the tradeoff, pick
one, document why).

### 4.2 Tightness parameter α

Define α as **number of required adjacency edges in the chain constraint**, sweepable from
0 (no adjacency requirement — reduces to Phase 3's M=840 case) up through the existing
2-edge chain (M=96) and beyond to a 3-edge or over-constrained variant that is
**provably infeasible on the fixed 2×4 grid** (e.g. requiring cell3 to also be adjacent to
cell0 in addition to the existing chain, which — depending on the specific site assignment
—may have zero satisfying assignments; verify by brute force before building the oracle for
it, per the project's established classical-ground-truth-first convention).

At minimum, sweep across: α ∈ {0 edges (M=840), 1 edge (compute M), 2 edges (M=96,
existing), 3 edges (compute M, expected small or possibly 0), over-constrained (M=0,
engineered)}.

### 4.3 QAOA implementation

- Build manually, **not** via `qiskit-optimization`/`qiskit-algorithms` — construct the
  cost-Hamiltonian phase-separator and mixer layers directly as `QuantumCircuit` objects,
  consistent with this project's existing "build from primitives" convention and avoiding
  new package risk (see §7).
- Classical outer loop: `scipy.optimize.minimize` with COBYLA or SPSA (gradient-free,
  standard for QAOA at this circuit depth). **`scipy` needs an explicit compatibility check
  against the pinned stack before use** — flag per the package barrier protocol even though
  it likely ships as a transitive dependency already.
- Sweep circuit depth p ∈ {1, 2, 3} at minimum; report how approximation ratio scales with
  p (standard QAOA result to include, expected but must be measured not assumed).
- Multiple random optimizer seeds per (α, p) combination — QAOA landscapes are seed-sensitive
  at shallow depth; report mean and variance, not a single lucky run (see §6).

### 4.4 Classical decision baseline: backtracking / constraint propagation

- Simple recursive backtracking CSP solver over the same 4-cell/7-site problem: assign
  cells in order, prune on collision/validity/adjacency violation, backtrack on dead end.
- Report: solve/no-solve, wall-clock time, and node-expansion count (the classical analog
  of "query count") across the same α sweep.
- This is the fair classical counterpart to Grover specifically because both are
  **decision** procedures with no graded notion of partial credit — this is what makes the
  boundary behavior a fair comparison (§3).

### 4.5 Classical optimization baseline: simulated annealing

- Standard Metropolis-criterion SA on the same one-hot QUBO cost function used for QAOA
  (Path A) — same objective, different (classical) search strategy, so QAOA-vs-SA isolates
  "does the quantum optimizer help," separately from "does optimization beat decision."
- Cite Mallela & Grover's 1988 clustering-based SA placement paper as the historical
  baseline this technique descends from — a nice, honest touch for an EDA-adjacent reviewer.
- Multiple random seeds and temperature schedules; report best-of and average-of, both.

### 4.6 Visualization changes

- Extend the existing Module 1 heatmap viewer with a **tightness-sweep panel**: α on one
  axis, all four methods' solution-quality score on the other, live-updating alongside the
  existing per-iteration heatmap (which stays as-is for the α=2-edges case already built).

### 4.7 New file layout

```
module1_placement/
├── (existing files, untouched)
├── qaoa/
│   ├── __init__.py
│   ├── onehot_encoding.py        # one-hot variable layout, decode/encode helpers
│   ├── qubo_cost.py              # cost Hamiltonian construction (collision + adjacency)
│   ├── qaoa_circuit.py           # phase-separator + mixer layer construction
│   ├── qaoa_optimizer.py         # scipy classical outer loop
│   └── tests/
│       └── test_qaoa.py
├── classical_baselines/
│   ├── __init__.py
│   ├── backtracking.py           # decision-paradigm classical solver
│   ├── simulated_annealing.py    # optimization-paradigm classical solver
│   └── tests/
│       └── test_classical_baselines.py
├── tightness_sweep.py            # orchestrates all 4 methods across α, collects results
└── tests/
    └── test_tightness_sweep.py   # includes the engineered-infeasible (M=0) case explicitly
```

---

## 5. Module 2 (ATPG) — Detailed Changes

### 5.1 Generalized, provable fault family

Absorb the Phase 5 design work already done. Formalize as a lemma-driven family rather than
seven independently-measured numbers:

| Fault class | Definition | M/N (derived) |
|---|---|---|
| Product-term stuck-at-0 (AB, BC, or AC) | Term forced to always contribute 0 | N/4 |
| Product-term stuck-at-1 (AB, BC, or AC) | Term forced to always contribute 1 | 3N/4 |
| XOR-chain stuck-at (any Sum-chain line) | One XOR-accumulation term dropped | N/2 |
| Fault-free (control) | No fault injected; compares circuit to itself | 0 |

**Task:** prove these ratios algebraically for the general reversible-accumulator
construction (not just verify by brute force for N=8), then verify the proof empirically at
N=8 (1-bit adder, existing) and extend to 2-bit and 3-bit ripple-carry adders to check
whether the ratios hold as bit-width grows or need a correction term from carry-chain
interaction between slices — **this is a real, falsifiable extension**, not guaranteed to
come out clean, and should be reported honestly either way.

### 5.2 M=0 fixed-point lemma (generalize existing argument)

Prove, for general n (not just n=3 inputs / N=8): with the fault-free control circuit, the
oracle is the identity operation, the uniform superposition is a fixed point of the
diffusion operator, and therefore measured success probability is exactly 0.0 for **any**
iteration count k. State this as a formal lemma with proof, then verify it holds
empirically at each tested bit-width — this becomes one of the paper's citable technical
contributions (§2, item 2).

### 5.3 Classical baseline: exhaustive/random test-pattern generation

- For each fault class, run classical exhaustive search over all N inputs (trivial at these
  sizes, but the point is the **query count and the failure signature**, not raw speed).
- Central comparison point: at the fault-free (M=0) boundary, **what does each method
  report?**
  - Classical exhaustive search: after N queries, correctly and informatively reports "no
    detecting input exists" — a clean negative result.
  - Grover: returns a flat, uniform measurement distribution with no explicit "undetectable"
    signal — a practitioner who doesn't already know to check for this could misread it as
    an implementation bug rather than a correct null result.
- **This is the sharper, more surprising version of the paper's thesis** (see §0,
  contribution 5) — write it up explicitly as its own subsection, not folded into the
  placement discussion.
- Also report classical random-sampling ATPG (draw inputs at random without replacement,
  expected queries to find a detecting input) as the realistic industrial baseline —
  connects to weighted random pattern testing (WRPT) framing for fault-coverage-percentage
  metrics if extending Module 2 to multi-fault coverage experiments (optional stretch,
  see §5.5).

### 5.4 Hardware execution

- Run the 1-bit adder case (all 7 fault classes) on real IBM Quantum hardware via the
  Advocate account, not just the pinned local Aer simulator stack.
- Report measured vs. theoretical success probability, with hardware noise as an explicit,
  discussed source of deviation — reviewers expect at least one real-hardware data point in
  a Grover-application paper at this scale; the pinned local environment (§7) is simulator-only
  by design, so this is a deliberate, scoped exception, not a change to the core pipeline.
- Requires a **separate, unpinned environment** (e.g. `qiskit-ibm-runtime`, explicitly out
  of scope for the `grover-vlsi` conda env) — do not add this to the pinned local stack;
  keep it as an isolated script/notebook that only touches hardware-submission code.

### 5.5 Optional stretch: multi-fault coverage framing

If time allows, extend the single-fault-at-a-time experiments into a **fault coverage**
experiment: given a query budget, what fraction of the 6 real (non-control) fault classes
does each method successfully find a detecting vector for? This reframes the comparison in
terms recognizable to real ATPG practice (industrial ATPG is scored on fault coverage
percentage, not single-fault detection), strengthening the "genuinely relevant to VLSI test
practice" framing from the original project's motivation section.

### 5.6 New file layout

```
module2_atpg/
├── (existing files, untouched — becomes the AB-term-stuck-at-0, N=8 special case)
├── generalized_faults/
│   ├── __init__.py
│   ├── fault_family.py           # parameterized fault injection (term × stuck-at type)
│   ├── nbit_adder.py             # 2-bit, 3-bit ripple-carry generalization
│   └── tests/
│       └── test_fault_family.py  # validates derived M/N ratios against brute force
├── classical_baselines/
│   ├── __init__.py
│   ├── exhaustive_search.py
│   ├── random_sampling.py
│   └── tests/
│       └── test_classical_baselines.py
├── hardware/                      # ISOLATED — not part of the pinned grover-vlsi env
│   ├── README.md                  # explicit note: separate environment, see §7
│   └── run_on_hardware.py
└── tests/
    └── test_m0_lemma_general_n.py # verifies the fixed-point lemma across bit-widths
```

---

## 6. Statistical Methodology (applies to both modules)

- Every reported success probability / approximation ratio gets a confidence interval
  (Wilson score interval for binomial success probabilities is more defensible at small
  shot counts than a naive normal approximation).
- Shot counts: increase from the existing project convention of 1000 shots to a
  publication-appropriate count justified by a target CI half-width (e.g. solve for shots
  needed for ±1% at 95% confidence) — compute and state this, don't just pick a round number.
- QAOA and SA: report across ≥10 random seeds per configuration; report mean, standard
  deviation, and best-of, not a single run.
- Every classical brute-force ground truth is computed fresh for each new α / fault-class /
  bit-width — never assumed to generalize from the existing N=8, M=96 cases.

---

## 7. Package & Environment Considerations

**The existing non-negotiable barrier still applies to everything in `shared_framework/`,
existing Module 1, and existing Module 2 code — repeated here verbatim per project
convention:**

| Package | Version — DO NOT CHANGE |
|---|---|
| Python | 3.10 |
| qiskit | 1.2.4 |
| qiskit-aer-gpu-cu11 | 0.15.1 |
| numpy | 1.26.4 |
| matplotlib | 3.8.4 |
| CUDA Toolkit (inside WSL2) | 11.8 |

**New for this roadmap, needs explicit sign-off before any Antigravity prompt uses it:**

| Addition | Where used | Risk | Recommendation |
|---|---|---|---|
| `scipy` | QAOA classical optimizer (§4.3), possibly SA | Low — likely already present transitively via numpy/matplotlib install; must be explicitly verified, not assumed | Verify version in the existing `grover-vlsi` env first; only add explicitly if genuinely absent |
| `qiskit-ibm-runtime` | Hardware execution only (§5.4) | Real, but fully isolated | **Separate environment**, never added to `grover-vlsi`; hardware scripts live in an isolated folder with their own README |
| Anything else | — | — | Default answer is no; QAOA, backtracking, and SA are all implementable in plain Python + existing pinned Qiskit |

---

## 8. Phased Build Plan

Continuing the existing Phase 1–5 numbering. Same workflow as before (you write nothing
directly; I write the Antigravity/Opus 4.6 prompt, you paste code back, I review file by
file, package-lock check first).

| Phase | Task | Depends on |
|---|---|---|
| 6 | Module 2 generalized fault family (§5.1) + M=0 lemma at N=8 (§5.2) | None — pure extension of existing, trusted code |
| 7 | Module 2 classical baselines (§5.3) | Phase 6 |
| 8 | Module 2 n-bit generalization (2-bit, 3-bit adders) (§5.1 extended) | Phase 6 |
| 9 | Module 1: resolve encoding decision (§4.1), build QAOA arm (§4.3) | None — independent of Module 2 work |
| 10 | Module 1: classical baselines, backtracking + SA (§4.4, §4.5) | Phase 9 (shares the QUBO cost function with SA) |
| 11 | Module 1: tightness sweep orchestration incl. engineered-infeasible case (§4.2) | Phases 9–10 |
| 12 | Statistical methodology pass across all of Module 1 + Module 2 (§6) | Phases 6–11 |
| 13 | Module 2 hardware execution (§5.4) | Phase 6 (needs the fault family built) |
| 14 | Visualization extensions (§4.6) | Phase 11 |
| 15 | Paper writing (§9) | Everything above |
| 16 (optional) | Multi-fault coverage stretch (§5.5) | Phase 8 |
| 17 (optional) | Module 1 Path B: encoding-matched QAOA (§4.1) | Phase 9 |

Phases 6–8 (Module 2) and 9–11 (Module 1) are independent of each other and can be
pursued in either order or interleaved.

---

## 9. Paper Structure

1. **Abstract**
2. **Introduction** — lead with the structural question (§0), not "two demos"
3. **Background** — Grover's algorithm, QAOA, VLSI placement, ATPG
4. **Related Work** — position honestly against QuSAF, the 2021 SAT-ATPG paper, and the
   QAOA/quantum-annealing placement literature (§11); state precisely what's shared and
   what's new relative to each
5. **Problem Formulations** — Module 1's dual encoding (binary for Grover, one-hot for
   QAOA, with the mismatch discussed as a finding); Module 2's generalized fault taxonomy
6. **Theoretical Results** — the M/N derivation for the fault family; the general-n M=0
   fixed-point lemma
7. **Experimental Setup** — simulator + hardware configuration, the 2×2 framework, α
   sweep definitions, statistical methodology
8. **Results**
   - 8.1 Module 1: solution quality vs. tightness, all four methods
   - 8.2 Module 2: fault family validation across bit-widths; hardware vs. simulator
   - 8.3 The M=0 boundary, compared across all methods in both modules, including the
     classical-exhaustive-search-is-more-informative-than-Grover finding (§5.3)
9. **Discussion** — when should an EDA practitioner reach for decision-oracle vs.
   cost-based quantum methods; what the encoding mismatch (§4.1) implies for anyone porting
   a CSP formulation into a QUBO formulation
10. **Limitations** — toy problem scale, simulator-dominant results, no integration with
    real EDA toolchains, single circuit family (adders) for Module 2
11. **Conclusion & Future Work**

---

## 10. Venue Targets (broad, worldwide, no tier assumed)

| Venue | Type | Fit |
|---|---|---|
| IEEE Quantum Week (QCE) | Research track / workshop | Strong fit — quantum-algorithm-application papers are exactly its scope |
| ISQED (Intl. Symposium on Quality Electronic Design) | Research track / poster | Strong fit — EDA-adjacent, values the placement/ATPG framing directly |
| DATE (Design, Automation & Test in Europe) | Special session / workshop | Good fit if positioned as an EDA methods paper with a quantum angle |
| *Quantum Science and Technology* (IOP journal) | Journal, if a paper track is preferred over conference | Good fit for the theoretical (M/N derivation, fixed-point lemma) contributions |
| Regional/national IEEE conferences (many countries hold these) | Research or student track | Realistic, lower-barrier options if the above are too competitive; still legitimate peer review |
| IEEE Quantum Week Education/Workforce track | Fallback | If the comparative study doesn't fully land, the well-documented methodology alone is strong content here |

---

## 11. Related Work to Cite Honestly

- **QuSAF** (IEEE, 2023) — SAT-based Grover ATPG for stuck-at faults. Cite as the closest
  prior work to Module 2; differentiate on the generalized fault family, the n-bit scaling
  study, and the M=0 boundary analysis, none of which QuSAF addresses.
- **"Automatic Test Pattern Generation using Grover's Algorithm"** (2021, IBM Quantum
  Experience implementation) — earlier SAT-based Grover ATPG. Cite alongside QuSAF.
- **Mallela & Grover, "Clustering Based Simulated Annealing for Std Cell Placement"** (DAC,
  1988) — historical baseline for the SA arm of Module 1's comparison.
- **QAOA/quantum-annealing VLSI placement papers** (several found: FPGA placement via
  quantum annealing; QAOA-based bisectional placement; general quantum-EDA survey work) —
  cite as the established quantum-optimization-for-placement literature that Module 1's
  QAOA arm draws its formulation style from.
- **Any Grover-for-general-CSP educational material** (e.g. IBM Quantum Learning's
  Minesweeper module) — cite as the pedagogical genre Module 1's Grover arm belongs to,
  to be upfront that the technique itself isn't the contribution.

*(A full literature search pass should be done again immediately before submission — this
list reflects what was found during roadmap planning, not a complete systematic review.)*

---

## 12. Open Design Decisions Requiring Sign-off Before Any Code Is Written

1. **Module 1 encoding for QAOA**: Path A (one-hot, report qubit mismatch) vs. Path B
   (match binary encoding, do order reduction) — §4.1. Recommendation: Path A first.
2. **Tightness parameter definition**: adjacency-edge count (as sketched, §4.2) vs. an
   alternative like shrinking the available site set — pick one before building the sweep
   orchestration.
3. **Engineered-infeasible instance**: needs a specific, verified-by-brute-force-first
   constraint configuration that actually yields M=0 — this must be confirmed classically
   before any oracle or QUBO is built around it (same convention as every prior phase).
4. **Bit-widths for Module 2's n-bit generalization**: 2-bit and 3-bit proposed (§5.1) —
   confirm this is the right stopping point given qubit counts grow fast (each additional
   bit roughly doubles both search-register size and gate count).
5. **Hardware execution scope**: 1-bit case only (§5.4), or extend to 2-bit if the queue
   time/qubit budget allows — decide once Phase 6–8 numbers are in hand.
6. **scipy addition**: verify actual necessity and current environment status before
   treating it as approved (§7).

---

## 13. Risks & Limitations to Address Preemptively in the Paper

- All results are simulator-based except the scoped Module 2 hardware run (§5.4) — state
  this plainly rather than letting a reviewer discover it.
- Toy problem sizes throughout (≤28 qubits) — standard for this literature, but should be
  stated as a limitation, not implied to be a stepping stone to production scale without
  qualification.
- QAOA at shallow depth (p ≤ 3) is not guaranteed to reach a good approximation ratio;
  report this honestly if the numbers come out mediocre rather than only reporting favorable
  depths.
- The classical baselines (backtracking, SA, exhaustive/random search) are simple,
  intentionally not state-of-the-art industrial implementations — appropriate for isolating
  the paradigm-level effect this paper studies, but not a claim that quantum methods beat
  best-in-class classical EDA tools.
- The Module 1 / Module 2 "pipeline" framing from the original Phase 5 design is now
  secondary to this comparative study — if kept in the paper at all, position it as a
  systems-integration illustration, not a load-bearing contribution.
