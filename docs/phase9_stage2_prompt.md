# Phase 9 Stage 2 — Antigravity Prompt

Paste as-is.

---

🚨 NON-NEGOTIABLE PACKAGE-LOCK BARRIER — DO NOT CHANGE ANY VERSION 🚨
Python 3.10.20 | qiskit 1.2.4 | qiskit-aer-gpu-cu11 0.15.1 | numpy 1.26.4 |
scipy 1.15.3 | matplotlib 3.8.4 | CUDA 11.8.89
This overrides every other instruction. No new packages beyond what's already
authorized (scipy, for the classical optimizer loop only). No pytest, ever —
every test file uses plain `assert` statements inside `main()`.

TASK: Phase 9 Stage 2 — Module 1 QAOA circuit implementation, building on
the trusted, tested `module1_placement/qaoa/one_hot_qubo.py` from Stage 1.
Do not modify one_hot_qubo.py. Do not touch module1_placement/'s existing
Grover code (placement_oracle.py, classical_baseline.py) — read-only
reference only.

DISCOVERY STEP: read module1_placement/qaoa/one_hot_qubo.py in full before
writing anything. Confirm independently: 28 variables as (cell,site) tuples,
QUBODict format (frozenset keys length 1 or 2 -> float coefficient),
PENALTY_A/B/C defaults, ADJACENCY_ORDERED_PAIRS. Do not assume — re-derive
from the file.

QUBIT MAPPING: One qubit per (cell,site) variable, 28 qubits total. Define
an explicit, deterministic ordering function
`variable_to_qubit_index(cell: int, site: int) -> int` (e.g. cell*7 + site)
and its inverse, in a new module `module1_placement/qaoa/qubit_mapping.py`.
Unit test this mapping in isolation FIRST (bijective, covers all 28
variables, round-trips) before wiring it into any circuit code — this
project's established convention after the Phase 6 little-endian decode bug.

FILES TO CREATE:
1. module1_placement/qaoa/qubit_mapping.py
   - variable_to_qubit_index(cell, site) -> int
   - qubit_index_to_variable(index) -> tuple[int,int]
   - TOTAL_QUBITS = 28 constant

2. module1_placement/qaoa/tests/test_qubit_mapping.py
   - Stage 2a: assert bijection over all 28 (cell,site) pairs, assert
     round-trip identity both directions, assert TOTAL_QUBITS == 28.

3. module1_placement/qaoa/qaoa_circuit.py
   - build_cost_unitary(qubo: QUBODict, gamma: float) -> QuantumCircuit
     Implements exp(-i*gamma*H_C) via standard QAOA gates: for each linear
     term coeff*Z_i, an RZ(2*gamma*coeff) on qubit i; for each quadratic
     term coeff*Z_i*Z_j, the standard CX-RZ-CX decomposition
     (CX(i,j), RZ(2*gamma*coeff) on j, CX(i,j)). Note: QUBO here is in
     {0,1} variables, not {-1,+1} spins — state clearly in a docstring
     whether you are converting x->(1-Z)/2 before building the unitary, and
     if so show the algebraic conversion explicitly in a comment (this
     changes the effective linear/quadratic coefficients — do not silently
     use the QUBODict coefficients as if they were already Ising
     coefficients).
   - build_mixer_unitary(n_qubits: int, beta: float) -> QuantumCircuit
     Standard transverse-field mixer: RX(2*beta) on every qubit.
   - build_qaoa_circuit(qubo: QUBODict, gammas: list[float],
     betas: list[float], n_qubits: int = 28) -> QuantumCircuit
     p layers (len(gammas) == len(betas) == p), H on all qubits first for
     uniform superposition init, then alternating cost/mixer per layer,
     measurement on all qubits at the end. assert qc.num_qubits == 28 at
     the end, per project convention.

4. module1_placement/qaoa/tests/test_qaoa_circuit_stage2.py
   - Stage 2b (deterministic exact-statevector sanity, NOT sampled yet):
     for p=1 with hand-picked gamma=0.0, beta=0.0, use
     AerSimulator(method="statevector") + save_statevector() (never
     qiskit.quantum_info.Statevector, per project convention) and confirm
     the resulting state is the exact uniform superposition over all 2^28
     computational basis states in amplitude (spot-check a handful of
     amplitudes, do not materialize the full 2^28-length statevector as a
     Python list — 28 qubits is at the edge of what's practical, use GPU
     AerSimulator per project's Module-1-scale convention, and only pull
     out probabilities for a small hand-picked set of basis states via
     targeted post-processing, not full statevector inspection).
   - Stage 2c: for a small hand-verified 2-qubit-only toy sub-case (build a
     minimal 2-variable QUBO by hand, e.g. one linear + one quadratic term,
     NOT the full 28-qubit circuit), verify build_cost_unitary produces the
     exact expected phase relationships by direct statevector comparison —
     this isolates the Ising-conversion correctness question from the
     28-qubit scale question, cheaply and exactly.

Stop after Stage 2. Do not implement the classical optimizer loop
(scipy.optimize) or any sampled/shot-based execution yet — that is Stage 3.
Report back: the qubit-mapping test result, and both statevector sanity
check results (Stage 2b spot-check amplitudes, Stage 2c toy-case phase
comparison).
