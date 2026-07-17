# Project Handoff Summary & Phase 1 Instructions
### Grover's Algorithm for VLSI Design & Test

**Purpose of this document**: A self-contained summary of everything decided and built so far, plus detailed instructions for Phase 1, written so you can paste this into a **new chat** and continue seamlessly without needing the full history of the original (very long) conversation.

---

## 1. Project Overview

**Goal**: Build a simulated quantum computing project (using Qiskit) that applies **Grover's algorithm** to two real hardware-design problems from the VLSI (chip design) lifecycle:

- **Module 1 — Placement**: Assign logic cells to physical sites on a chip while satisfying no-collision and adjacency constraints (design-time problem).
- **Module 2 — ATPG (Automatic Test Pattern Generation)**: Find an input vector that detects a manufacturing fault in a fabricated logic circuit — specifically, a 1-bit full adder with an injected stuck-at fault (post-fabrication testing problem).

These two modules represent two different stages of the VLSI lifecycle (design vs. test), giving the project a coherent narrative arc. An optional stretch goal (Phase 5) chains the two modules into a single pipeline.

**Role/context**: The user is an IBM Quantum Qiskit Advocate, building this as a demonstration of Grover's algorithm applied to genuinely industry-relevant hardware problems, not just a generic textbook demo.

---

## 2. Key Design Decisions Already Made

### 2.1 Architecture: Option A (chosen over Option B)
- **Option A** = build and fully verify both modules (Placement, ATPG) as independent, self-contained demos first.
- **Option B** = chain them into one sequential pipeline (Module 1's output feeds Module 2).
- **Decision**: Do Option A first, completely, with full validation. Only *then*, if time/energy allows, attempt Option B as a stretch goal (Phase 5) — never let the pipeline attempt put the core deliverable at risk.

### 2.2 Build Order (5 Phases)
| Phase | Task |
|---|---|
| **1** | Shared Grover framework (oracle wrapper, diffusion operator, iteration-count calculator, measurement/plotting) — validate on a trivial oracle first |
| **2** | Module 2 — ATPG (built before Module 1, since the full-adder logic is well-defined and easier to reason about) |
| **3** | Module 1 — Placement (validated against a classical brute-force ground truth) |
| **4** | Documentation & write-up (lock in the guaranteed deliverable) |
| **5 (stretch)** | Sequential pipeline connecting Module 1 → Module 2 |

**We are about to start Phase 1.**

---

## 3. Environment — Fully Set Up and Verified

Everything below has already been built, tested, and confirmed working. No further setup is needed before starting Phase 1 code.

### 3.1 Hardware
- Machine: Lenovo LOQ, hostname `AkashLOQ`
- CPU: Intel i5-13450HX
- RAM: 12 GB
- GPU: NVIDIA RTX 3050 (6GB VRAM), Ampere architecture

### 3.2 Software Stack (pinned, verified, zero dependency conflicts)
| Package | Version |
|---|---|
| Python | 3.10 |
| qiskit | 1.2.4 |
| qiskit-aer-gpu-cu11 | 0.15.1 |
| numpy | 1.26.4 |
| matplotlib | 3.8.4 |
| CUDA Toolkit (inside WSL2) | 11.8 |

**Important compatibility note**: `qiskit-aer-gpu` (and `-cu11`) version 0.15.1 breaks under Qiskit 2.0+ (a `convert_to_target` import error). This is why the versions above are pinned exactly — do not upgrade qiskit past the 1.x line without also verifying qiskit-aer compatibility.

### 3.3 System Setup
- **WSL2 Ubuntu 24.04 ("noble")** running on Windows, with GPU passthrough from the Windows NVIDIA driver (confirmed via `nvidia-smi` inside WSL).
- **CUDA Toolkit 11.8** installed inside WSL using a *targeted* package install (`cuda-nvcc-11-8 cuda-cudart-11-8 cuda-cudart-dev-11-8 cuda-libraries-11-8 cuda-libraries-dev-11-8 cuda-cccl-11-8`) — deliberately skipping the full `cuda-toolkit-11-8` metapackage, because it pulls in `nsight-systems`, which depends on `libtinfo5` — a package Ubuntu 24.04 no longer provides. The targeted install avoids this conflict entirely and installs everything actually needed for Qiskit Aer's GPU backend.
- **Conda environment**: `grover-vlsi` (Python 3.10), created and activated via `conda activate grover-vlsi`.
- **Jupyter** installed and kernel registered as "Python (grover-vlsi)".
- **GPU verification test PASSED**: `AerSimulator().available_devices()` returned `('CPU', 'GPU')`, and a 3-qubit GHZ circuit run on `device="GPU"` returned a correct ~50/50 split between `'000'` and `'111'` (501/499 out of 1000 shots).

### 3.4 File Location Strategy
- Project files live on the **Windows C: drive** at `C:\Quantum_VLSI`.
- Code is **executed via the WSL terminal** (`cd /mnt/c/Quantum_VLSI`), using the `grover-vlsi` conda environment — never via a native Windows Python (the GPU-enabled Aer package is Linux-only).
- A shell alias `qvlsi` was set up to `cd` into the project and activate the environment in one command.
- (See the companion document "Workspace & Workflow Guide" for full detail on this.)

### 3.5 Git & GitHub
- SSH key generated and linked to GitHub account `Akash-Kishore`.
- Repository created and pushed: **`github.com/Akash-Kishore/Quantum_VLSI`**, branch `main`.
- `.gitignore`, `README.md`, `requirements.txt`, `environment.yml` are all committed.

### 3.6 Current Folder Structure
```
C:\Quantum_VLSI\
├── shared_framework\
│   └── tests\
│       └── gpu_test.py        # GPU verification script (passing)
├── module1_placement\          # empty, to be filled in Phase 3
├── module2_atpg\               # empty, to be filled in Phase 2
├── notebooks\
├── docs\
├── requirements.txt
├── environment.yml
├── .gitignore
└── README.md
```

---

## 4. What Has NOT Been Started Yet

- No Grover framework code has been written yet.
- No oracle circuits (for either module) have been designed yet.
- No classical brute-force baseline code has been written yet.

**Phase 1 is the very next step.**

---

## 5. Phase 1 — Detailed Instructions: Shared Grover Framework

### 5.1 Goal
Build a small, reusable set of components that both Module 1 (Placement) and Module 2 (ATPG) will import and build on top of. Validate this framework on a **trivial oracle** before either module touches it, so any bugs are caught here rather than being confused with problem-specific oracle bugs later.

### 5.2 Components to Build

1. **Oracle wrapper**
   - A function/class that takes a marked state (or a Boolean condition) and constructs the corresponding phase-flip circuit: `O|x⟩ = (-1)^f(x)|x⟩`.
   - Should be generic enough to accept an arbitrary sub-circuit representing the condition `f(x)`, plus ancilla-based phase kickback (the standard "compute condition into an ancilla, flip phase, uncompute" pattern), so it can later host non-trivial constraint logic for both modules.

2. **Diffusion operator**
   - Standard inversion-about-the-mean: `D = 2|ψ⟩⟨ψ| - I`.
   - Implemented as: Hadamards on all qubits → multi-controlled phase flip about `|0⟩^⊗n` → Hadamards again.

3. **Iteration count calculator**
   - Implements `k ≈ (π/4)√(N/M)`, where `N = 2^n` is the search space size and `M` is the number of marked states (default `M=1`).
   - Should round to the nearest integer and handle the edge case where the calculated iteration count is 0 (round up to 1).

4. **Measurement & visualization helpers**
   - A thin wrapper around running a circuit on `AerSimulator` (CPU or GPU device, selectable) and returning counts.
   - A helper to plot histograms (`plot_histogram` from `qiskit.visualization`) and, ideally, a helper to sweep iteration count from 0 to ~2-3× optimal and plot success probability vs. iteration count (to visually confirm the expected rise-and-fall periodicity).

### 5.3 Validation Step (Do This Before Moving to Module 2)

Test the entire framework on a **trivial oracle**: a 2-qubit system where the marked state is `|11⟩`.

- Build the oracle for `|11⟩` (this is just a controlled-Z gate, the simplest possible case).
- Compute the optimal iteration count using the formula above (`N=4`, `M=1` → should come out to 1 iteration).
- Run the full Grover circuit (superposition → oracle → diffusion, repeated the calculated number of times) on `AerSimulator(device="GPU")`.
- Confirm the measurement result returns `'11'` with very high probability (should be at or near 100% for this trivial case).
- Additionally, sweep iteration counts 0, 1, 2, 3 and confirm the success probability rises to a peak at 1 iteration and then falls — this confirms the diffusion operator and oracle are both implemented correctly (a common bug is a sign error in the oracle, which shows up as the periodicity being wrong or absent).

### 5.4 Suggested File Layout for Phase 1

```
shared_framework/
├── __init__.py
├── oracle.py              # Oracle wrapper / phase-flip construction helpers
├── diffusion.py           # Diffusion operator construction
├── grover_utils.py        # Iteration count calculator, circuit assembly helper
├── visualization.py       # Histogram plotting, success-probability sweep plotting
└── tests/
    ├── gpu_test.py         # (already exists — basic GPU smoke test)
    └── test_trivial_oracle.py   # Validates the framework end-to-end on |11⟩
```

### 5.5 Definition of "Phase 1 Done"

- [ ] `oracle.py`, `diffusion.py`, `grover_utils.py`, `visualization.py` written and importable
- [ ] `test_trivial_oracle.py` runs successfully on the GPU backend
- [ ] Measurement result correctly returns `'11'` with high probability at the calculated optimal iteration count
- [ ] Success-probability-vs-iteration-count sweep plotted and shows the expected rise-and-fall pattern
- [ ] Code committed and pushed to GitHub (`git add . && git commit -m "Phase 1: shared Grover framework" && git push`)

Once all of the above are checked off, Phase 1 is complete, and the next step is **Phase 2 (Module 2 — ATPG)**: building a 1-bit full adder as a reversible circuit, injecting a stuck-at fault, and constructing the fault-detection oracle on top of this same shared framework.

---

## 6. How to Use This Document in a New Chat

Paste this entire document as your first message in a new conversation, optionally followed by something like:

> "This is where I left off on my Grover's algorithm VLSI project. Let's start Phase 1 — walk me through building the shared Grover framework."

This gives a fresh conversation everything it needs — project goals, prior decisions, verified environment, and exact next steps — without needing the full original conversation history.
