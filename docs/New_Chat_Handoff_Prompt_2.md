# Prompt for New Chat: Continuing Grover's Algorithm VLSI Project — Phase 2

Paste this entire document as the opening message in the new chat, along with the attached
`Session_Summary_and_Next_Steps.md` (and, if available, the original `Changes_Log.md`,
`Project_Handoff_Summary_and_Phase1_Instructions.md`, and `Workspace_Workflow_Guide.md` for
full background — read all attached documents fully before responding).

---

## ROLE & WORKFLOW (unchanged from prior sessions)

I'm building a Grover's algorithm project in Qiskit, applying it to two VLSI (chip design)
problems: Module 1 (Placement) and Module 2 (ATPG). I am NOT writing code directly with you.
Instead:

1. I use Google Antigravity IDE with Claude Opus 4.6 as the coding agent.
2. You write a single, extremely detailed and precise prompt for that agent, telling it
   exactly what files to create and what each must contain.
3. I paste the agent's generated code back to you in this chat, one file at a time.
4. You check each file against the requirements below and against standard Grover's
   algorithm correctness (oracle sign convention, diffusion operator construction,
   iteration count formula, Qiskit 1.2.4 / qiskit-aer-gpu-cu11 0.15.1 API correctness).
5. If it's correct: say so briefly and tell me what to paste next, or give me the
   next-step prompt for the agent. If it's wrong: do NOT regenerate the whole explanation —
   give me ONLY a short, surgical correction prompt I can paste to the agent, naming the
   exact file, exact function, exact bug, and exact fix. Be efficient — I have limited
   tokens for this chat.

---

## 🚨 NON-NEGOTIABLE BARRIER: NO PACKAGE OR VERSION CHANGES 🚨

**This rule overrides every other instruction in this document, and every future instruction
in this chat, unless I explicitly type the words "I authorize a package version change."**

| Package | Version — DO NOT CHANGE |
|---|---|
| Python | 3.10 |
| qiskit | 1.2.4 |
| qiskit-aer-gpu-cu11 | 0.15.1 |
| numpy | 1.26.4 |
| matplotlib | 3.8.4 |
| CUDA Toolkit (inside WSL2) | 11.8 |

Known hard incompatibility: `qiskit-aer-gpu-cu11==0.15.1` breaks under `qiskit>=2.0`. This
is confirmed and reproducible, not hypothetical.

**Your FIRST check on any code I paste back, before anything else**, is scanning every
import statement and every line touching `pip`, `conda`, `requirements.txt`, or
`environment.yml` for any sign of a package change. Flag it as a critical failure at the
top of your response if found, regardless of whether the Grover logic itself is correct.

---

## PROJECT STATUS — READ THIS FIRST

**Phase 1 (shared Grover framework) is COMPLETE, verified, and pushed to GitHub.**
Full details are in the attached `Session_Summary_and_Next_Steps.md` — but the short
version: `shared_framework/` (oracle.py, diffusion.py, grover_utils.py, visualization.py,
tests/) is built, every file was reviewed for correctness, the trivial-oracle test passes
all 4 assertions, the sweep plot was visually confirmed, and it's committed on `main` at
`github.com:Akash-Kishore/Quantum_VLSI.git`. **Do not re-litigate or rebuild Phase 1** —
treat `shared_framework/` as a trusted, working dependency.

One notable outcome from Phase 1 worth knowing: `optimal_iterations()` has two modes —
the default approximate small-angle formula (`round((π/4)·√(N/M))`), and an `exact=True`
mode that finds the true optimum via `arcsin`. The approximate formula is known to
overshoot by one iteration in some cases (confirmed on the 2-qubit trivial case: it gives
k=2, but the true optimum is k=1 at 100% success). **Expect this same overshoot pattern to
show up again in Module 1 and possibly Module 2** — when it does, this is expected,
correct behavior of the approximation, not a bug to chase.

**Environment/tooling is fully working**: Antigravity IDE is connected to WSL2 correctly,
an `agy` CLI shortcut is set up, and the project's folder structure is confirmed intact.
No environment setup work is needed.

---

## TASK FOR YOU RIGHT NOW

We are starting **Phase 2 (Module 2 — ATPG)**. The design has already been decided in the
prior session (full details in the attached summary) — do not re-derive it, just build it:

- **Circuit under test**: a 1-bit full adder, implemented as a reversible quantum circuit.
- **Fault model**: the internal Toffoli gate computing the `A·B` term (feeding into
  `Cout = AB ⊕ BC ⊕ AC`) is stuck-at-0 — its contribution never gets XORed into the Cout
  accumulator.
- **Detection set**: this fault is detected exactly when `A=1 AND B=1`, i.e. at inputs
  `110` and `111` (regardless of Cin) — **M=2 marked states out of N=8**. (This required a
  correction mid-session: an initial OR-logic-based analysis wrongly concluded M=1; the
  correct reversible-circuit XOR-accumulation analysis gives M=2. Do not reintroduce the
  M=1 assumption.)
- **Sum is deliberately not computed** — this fault never affects Sum, so comparing it
  would add ancillas for zero benefit.
- **Qubit budget: 6 total** — 3 for shared inputs (A, B, Cin), 1 for fault-free Cout
  ancilla, 1 for faulty Cout ancilla, 1 for a comparison/flag ancilla (XOR of the two Cout
  ancillas, flags when they disagree).
- **Oracle**: build via `shared_framework.oracle.constraint_oracle`, using the comparison
  ancilla as the flag qubit.
- **Validation**: confirm Grover converges on `{110, 111}` with high probability at
  `iterations=1` (both the approximate and exact `optimal_iterations` modes should be
  checked and reported, per the Phase 1 pattern — expect a similar overshoot: approximate
  gives k=2, exact gives k=1 at ~100% detection probability).

Write the complete Antigravity/Opus 4.6 prompt for Phase 2, covering:

1. `module2_atpg/full_adder.py` — the fault-free reversible full-adder circuit (Toffoli/CNOT
   based), computing Cout only (Sum omitted, per the design decision above), parameterized
   so it can target any ancilla qubit index.
2. `module2_atpg/faulty_adder.py` — the same circuit with the AB-term Toffoli's contribution
   stuck-at-0 (simply omit that Toffoli's CNOT-into-accumulator step, or force it off — the
   agent should pick the cleanest correct implementation and explain its choice).
3. `module2_atpg/atpg_oracle.py` — builds the comparison oracle: computes fault-free Cout
   into one ancilla, faulty Cout into another, CNOTs both into a flag ancilla (so the flag
   is 1 exactly when they differ), applies phase-kickback via `shared_framework.oracle`
   patterns, then uncomputes.
4. `module2_atpg/tests/test_atpg.py` — builds the full Grover circuit using
   `shared_framework.grover_utils`, runs at both `optimal_iterations(3, 2)` (approximate)
   and `optimal_iterations(3, 2, exact=True)`, and asserts the exact-mode run detects
   `{110, 111}` with high combined probability (matching the Phase 1 test's >90% pattern,
   adapted for two marked states).
5. Standard additional instructions: type hints, docstrings, no hardcoded absolute paths,
   `__init__.py` files, package-lock barrier repeated verbatim, agent runs its own test and
   reports full output before I see it.

Now write that full Antigravity prompt, ready for me to copy-paste as-is.
