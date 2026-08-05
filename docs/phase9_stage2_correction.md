Fix a package-convention violation in
module1_placement/qaoa/tests/test_qaoa_circuit_stage2.py.

Both `_stage_2b()` and `_stage_2c()` currently do:

    sim = AerSimulator(method="statevector", device="GPU")

This has no CPU fallback, breaking the project's established convention
(GPU with try/except AerError -> CPU fallback, used since the Module 1
viewer work) — a CUDA/driver hiccup would hard-crash instead of degrading
gracefully, which matters more once this circuit gets rerun repeatedly by
the Stage 3 optimizer loop.

FIX 1 — _stage_2b() (28 qubits, GPU is the correct choice, just needs the
fallback):

    from qiskit_aer import AerSimulator
    from qiskit_aer.backends.aer_simulator import AerError

    try:
        sim = AerSimulator(method="statevector", device="GPU")
    except AerError:
        sim = AerSimulator(method="statevector", device="CPU")

(Adjust the AerError import path if qiskit-aer-gpu-cu11 0.15.1 exposes it
elsewhere — verify by checking `python -c "from qiskit_aer import AerError"`
in the grover-vlsi env first; use whichever import path actually resolves,
do not guess.)

FIX 2 — _stage_2c() (2-qubit toy case): remove GPU entirely, this is
Module-2 scale where GPU launch overhead exceeds any benefit per project
convention. Change to:

    sim = AerSimulator(method="statevector")

(CPU is the AerSimulator default when no device is specified — no GPU
device kwarg at all for this function.)

Re-run both stages after the fix and confirm STAGE 2b/2c: PASS still
prints. Report back the full output.
