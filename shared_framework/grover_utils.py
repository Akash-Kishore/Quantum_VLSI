"""
Grover Algorithm Utilities
==========================

Helper functions for building and running Grover circuits:

- ``optimal_iterations`` — compute the number of Grover iterations,
  with both an approximate (small-angle) and exact mode.
- ``build_grover_circuit`` — assemble a complete Grover circuit from
  an oracle, diffusion operator, and iteration count.
- ``run_circuit`` — execute a circuit on AerSimulator with GPU→CPU
  fallback.
"""

from __future__ import annotations

import math
from typing import Dict

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator, AerError

from shared_framework.diffusion import diffusion_operator


def optimal_iterations(
    n_qubits: int,
    n_marked: int = 1,
    exact: bool = False,
) -> int:
    """Compute the optimal number of Grover iterations.

    Parameters
    ----------
    n_qubits : int
        Number of qubits in the search space.
    n_marked : int, optional
        Number of marked (solution) states.  Default is 1.
    exact : bool, optional
        If ``False`` (default), use the standard small-angle
        approximation: ``k = round((π/4) · √(N/M))``, floored to 1.
        Note: ``round`` may slightly overshoot the true optimum for
        small qubit counts (e.g. returns 2 for ``n=2, M=1`` where the
        true optimum is 1); use ``exact=True`` for precision.
        If ``True``, compute the exact optimum by finding the integer
        ``k ≥ 1`` that maximizes ``sin²((2k+1)·θ)`` where
        ``θ = arcsin(√(M/N))``.

    Returns
    -------
    int
        The optimal iteration count (always ≥ 1).
    """
    N = 2 ** n_qubits
    M = n_marked

    if not exact:
        # Standard small-angle approximation.
        k = round((math.pi / 4.0) * math.sqrt(N / M))
        return max(1, k)

    # Exact mode: sweep k and pick the best.
    theta = math.asin(math.sqrt(M / N))
    # Upper bound on useful iterations: half-period is π/(2θ).
    k_max = math.ceil(math.pi / (2.0 * theta))

    best_k = 1
    best_prob = 0.0
    for k in range(1, k_max + 1):
        prob = math.sin((2 * k + 1) * theta) ** 2
        if prob > best_prob:
            best_prob = prob
            best_k = k

    return best_k


def build_grover_circuit(
    n_qubits: int,
    oracle_circuit: QuantumCircuit,
    iterations: int,
) -> QuantumCircuit:
    """Assemble a complete Grover search circuit.

    Structure::

        |0⟩⊗n → H⊗n → [Oracle · Diffusion] × iterations → Measure

    Parameters
    ----------
    n_qubits : int
        Number of qubits.
    oracle_circuit : QuantumCircuit
        The phase-flip oracle circuit (must act on ``n_qubits`` qubits).
    iterations : int
        Number of Grover iterations to apply.

    Returns
    -------
    QuantumCircuit
        The complete circuit with classical measurement registers.
    """
    circuit = QuantumCircuit(n_qubits, n_qubits)

    # Initial superposition.
    circuit.h(range(n_qubits))

    # Grover iterations.
    diffusion = diffusion_operator(n_qubits)
    for _ in range(iterations):
        circuit.compose(oracle_circuit, inplace=True)
        circuit.compose(diffusion, inplace=True)

    # Measurement.
    circuit.measure(range(n_qubits), range(n_qubits))

    return circuit


def run_circuit(
    circuit: QuantumCircuit,
    shots: int = 1000,
    device: str = "GPU",
) -> Dict[str, int]:
    """Run a circuit on AerSimulator with GPU→CPU fallback.

    Parameters
    ----------
    circuit : QuantumCircuit
        The circuit to execute.
    shots : int, optional
        Number of measurement shots.  Default is 1000.
    device : str, optional
        Preferred Aer device (``"GPU"`` or ``"CPU"``).  Default is
        ``"GPU"``.  If the GPU device raises ``AerError``, the circuit
        is automatically re-run on ``"CPU"``.

    Returns
    -------
    dict[str, int]
        Measurement counts, e.g. ``{"11": 950, "00": 50}``.
    """
    try:
        sim = AerSimulator(method="statevector", device=device)
        transpiled = transpile(circuit, sim)
        result = sim.run(transpiled, shots=shots).result()
        return result.get_counts()
    except AerError as exc:
        if device.upper() != "CPU":
            print(f"[grover_utils] GPU unavailable ({exc}), falling back to CPU.")
            sim_cpu = AerSimulator(method="statevector", device="CPU")
            transpiled = transpile(circuit, sim_cpu)
            result = sim_cpu.run(transpiled, shots=shots).result()
            return result.get_counts()
        raise
