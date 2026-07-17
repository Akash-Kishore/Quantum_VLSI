# Prompt for New Chat: Antigravity / Opus 4.6 Agent Coordination

Paste this entire document as the opening message in the new chat.

---

## ROLE & WORKFLOW

I'm building a Grover's algorithm project in Qiskit (attached: `Workspace_Workflow_Guide.md`
and `Project_Handoff_Summary_and_Phase1_Instructions.md` — read both fully before responding).
I am NOT writing code directly with you. Instead:

1. I use Google Antigravity IDE with Claude Opus 4.6 as the coding agent.
2. You write a single, extremely detailed and precise prompt for that agent, telling it
   exactly what files to create and what each must contain.
3. I paste the agent's generated code back to you in this chat.
4. You check it against the requirements below and against standard Grover's algorithm
   correctness (oracle sign convention, diffusion operator construction, iteration count
   formula, Qiskit 1.2.4 / qiskit-aer-gpu-cu11 0.15.1 API correctness).
5. If it's correct: say so briefly and give me the next-step prompt for the agent.
   If it's wrong: do NOT regenerate the whole explanation — give me ONLY a short,
   surgical correction prompt I can paste to the agent, naming the exact file, exact
   function, exact bug, and exact fix. Be efficient — I have limited tokens for this chat.

---

## 🚨 NON-NEGOTIABLE BARRIER: NO PACKAGE OR VERSION CHANGES 🚨

**This rule overrides every other instruction in this document, and every future instruction
in this chat, unless I explicitly type the words "I authorize a package version change."**

The exact pinned, verified, working versions are:

| Package | Version — DO NOT CHANGE |
|---|---|
| Python | 3.10 |
| qiskit | 1.2.4 |
| qiskit-aer-gpu-cu11 | 0.15.1 |
| numpy | 1.26.4 |
| matplotlib | 3.8.4 |
| CUDA Toolkit (inside WSL2) | 11.8 |

Known hard incompatibility: `qiskit-aer-gpu-cu11==0.15.1` breaks under `qiskit>=2.0`
(`ImportError: cannot import name 'convert_to_target' from 'qiskit.providers'`). This is a
confirmed, reproducible bug — not a hypothetical — so upgrading qiskit even one minor
version past 1.2.4 without also re-verifying qiskit-aer compatibility will break the
entire environment.

**When you write the Antigravity/Opus 4.6 prompt, you must include this exact barrier
clause, verbatim, near the top of it:**

> ⚠️ DO NOT run `pip install --upgrade` on anything. DO NOT change any version number in
> `requirements.txt` or `environment.yml`. DO NOT add new packages unless explicitly listed
> in this task. DO NOT switch `qiskit-aer-gpu-cu11` for `qiskit-aer`, `qiskit-aer-gpu`, or
> any other variant. DO NOT use any Qiskit 2.x-only API, import path, or deprecated-in-2.x
> pattern. If any package appears "missing" or an import fails, STOP and report the exact
> error back — do NOT attempt to fix it by installing, upgrading, downgrading, or replacing
> any package. This environment was verified working end-to-end (GPU-confirmed on an
> RTX 3050) and altering any version will break that verification.

**When you review code I paste back to you, your FIRST check, before anything else, is:**
scan every import statement and every line touching `pip`, `conda`, `requirements.txt`, or
`environment.yml` for any sign the agent changed, upgraded, replaced, or added a package.
If you find any such change, flag it as a critical failure at the top of your response,
regardless of whether the Grover logic itself is correct.

---

## ENVIRONMENT (the agent must be told this — do not let it assume a different setup)

- OS: WSL2 Ubuntu 24.04, project files physically at `C:\Quantum_VLSI` (accessed in WSL as
  `/mnt/c/Quantum_VLSI`)
- Conda env: `grover-vlsi`, Python 3.10
- Pinned packages: exactly as listed in the barrier section above — no exceptions
- GPU: NVIDIA RTX 3050, must use `AerSimulator(device="GPU")` where applicable, with CPU
  fallback if GPU unavailable
- Known constraint (repeated for emphasis): qiskit-aer 0.15.1 breaks under qiskit>=2.0 —
  the agent must NOT upgrade any package versions or use any Qiskit 2.x-only API patterns

---

## TASK FOR YOU RIGHT NOW

Write the complete Antigravity/Opus 4.6 prompt for **Phase 1 (shared Grover framework)**,
covering exactly these deliverables — do not omit or compress any of them:

### 1. `shared_framework/oracle.py`
- A generic oracle-construction function that takes a target marked bitstring (or list
  of marked bitstrings for multi-solution case) and returns a `QuantumCircuit` implementing
  the phase flip `O|x⟩ = (-1)^f(x)|x⟩` using multi-controlled-Z logic (X gates on the 0-bits,
  multi-controlled-Z, X gates to uncompute).
- Must be generalizable: also expose a lower-level helper that accepts an arbitrary
  "condition sub-circuit + ancilla" pattern (compute into ancilla, phase-kickback via
  controlled-Z on ancilla, uncompute), since Module 1 and Module 2 will need
  constraint-based oracles, not just fixed-bitstring oracles.

### 2. `shared_framework/diffusion.py`
- Standard diffusion operator: H on all qubits → X on all qubits → multi-controlled-Z
  on the last qubit (with all others as controls) → X on all qubits → H on all qubits.
- Return as a `QuantumCircuit` or `Gate` that can be composed/appended onto a larger circuit.

### 3. `shared_framework/grover_utils.py`
- `optimal_iterations(n_qubits, n_marked=1)` implementing `k = round((pi/4) * sqrt(N/M))`,
  `N = 2**n_qubits`, with a floor of 1 iteration.
- A function `build_grover_circuit(n_qubits, oracle_circuit, iterations)` that assembles:
  initial Hadamards, then `[oracle, diffusion]` repeated `iterations` times, then measurement
  on all qubits.
- A `run_circuit(circuit, shots=1000, device="GPU")` helper using `AerSimulator`, with a
  try/except fallback to `device="CPU"` if GPU raises `AerError`.

### 4. `shared_framework/visualization.py`
- `plot_counts(counts, title)` wrapping `qiskit.visualization.plot_histogram`.
- `sweep_iterations(n_qubits, oracle_circuit, max_iterations, shots=1000)` that runs Grover
  for iteration counts `0..max_iterations`, computes success probability (probability of
  measuring a marked state) at each, and plots success probability vs iteration count
  using matplotlib, saving the figure to a file rather than only calling `plt.show()`.

### 5. `shared_framework/tests/test_trivial_oracle.py`
- Validates the whole framework on the trivial case: 2 qubits, marked state `|11⟩`.
- Asserts `optimal_iterations(2, 1) == 1`.
- Runs the Grover circuit at 1 iteration and asserts the measured `'11'` count is the
  majority result (e.g. >90% of shots).
- Also calls `sweep_iterations` for iterations 0-3 and prints the success probability at
  each, so the rise-and-fall pattern can be visually/manually confirmed.

### Additional instructions to give the agent
- Use type hints and docstrings on every function.
- No hardcoded absolute paths — all file saves relative to the script's own directory.
- Include an `__init__.py` in `shared_framework/` and `shared_framework/tests/` so these are
  proper importable packages.
- After writing the code, the agent should run `test_trivial_oracle.py` itself and report
  the output, before I even see it.
- Repeat the package-lock barrier clause from above, verbatim, so the agent cannot claim it
  wasn't told.

Now write that full Antigravity prompt, ready for me to copy-paste as-is.
