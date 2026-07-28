# Prompt for New Chat: Continuing Grover's Algorithm VLSI Project — Post-Phase 3b

Paste this entire document as the opening message in the new chat, along with the attached
`Phase3_and_3b_Status_Report.md` (and, if available, the original `Changes_Log.md`,
`Workspace_Workflow_Guide.md`, `Grovers_Algorithm_VLSI_Project.docx`, and
`Hardware_Software_Requirements.docx` for full background — read all attached documents
fully before responding).

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

---

## NON-NEGOTIABLE BARRIER: NO PACKAGE OR VERSION CHANGES

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

## PROJECT STATUS — READ THE ATTACHED STATUS REPORT FOR FULL DETAIL

**Phases 1, 2, 3, and 3b are all complete, tested, and committed.** Short version:

- **Phase 1** (`shared_framework/`): oracle/diffusion/iteration-count/visualization helpers,
  validated on a trivial 2-qubit oracle.
- **Phase 2** (`module2_atpg/`): 1-bit full adder with an AB-term stuck-at-0 fault,
  M=2/N=8, 100% detection at k=1 (exact).
- **Phase 3** (`module1_placement/`): 4 cells onto 7 sites, no-collision + validity only,
  25 qubits, M=840, 97.4% success at k=1 (exact).
- **Phase 3b** (`module1_placement/`, extended): added a chain adjacency constraint
  (cell0-cell1-cell2 on a 2x4 grid), 27 qubits, M=96, both approximate and exact iteration
  formulas agree at k=5, observed success 98.60% vs. 98.57% theoretical — confirmed on the
  real machine, all 3 test stages passing. A code review round caught and fixed two bugs in
  the Stage-3 test file (stale regression assertions, a vacuous safety-check assertion) —
  both fixed and reconfirmed; full detail in the attached status report.

**Do not re-litigate or rebuild any of this** — treat `shared_framework/`,
`module2_atpg/`, and `module1_placement/` as trusted, working code.

---

## WHAT'S OPEN — HELP ME DECIDE THE NEXT STEP

Three things are still outstanding, and I haven't picked which to do next:

1. **Phase 4 — documentation & write-up.** Per the original build plan, this is meant to be
   locked in before attempting Phase 5, to guarantee a complete deliverable regardless of
   what happens next. This is a *writing* task (background theory, architecture, design
   decisions, results) — probably something you draft directly rather than something that
   goes through the Antigravity coding-agent workflow above.
2. **Module 1 visual UI.** Decided earlier in the project (standalone self-contained
   HTML/JS viewer, not ipywidgets, showing a full cell x site probability heatmap animating
   across Grover iterations) but never actually built. This WOULD go through the Antigravity
   workflow.
3. **Phase 5 (stretch) — sequential pipeline.** Feed Module 1's measured placement into
   Module 2's fault-testing oracle as a chained demo. Explicitly scoped as attempted only
   after Phases 1-4 are complete, specifically so it doesn't put the guaranteed deliverable
   at risk — so per the original plan, this should probably wait for #1 first.

Ask me which one I want to do first (or suggest an order, if you think one is clearly right
given the plan above), and then proceed accordingly — writing the doc directly, or writing
the next Antigravity prompt.
