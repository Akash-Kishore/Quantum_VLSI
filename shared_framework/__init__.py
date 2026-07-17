"""
Shared Grover Framework
=======================

A reusable framework for Grover's search algorithm, providing oracle
construction, diffusion operators, circuit building utilities, and
visualization tools.

Built for Qiskit 1.2.4 + qiskit-aer-gpu-cu11 0.15.1.
"""

from shared_framework.oracle import bitstring_oracle, constraint_oracle
from shared_framework.diffusion import diffusion_operator
from shared_framework.grover_utils import (
    optimal_iterations,
    build_grover_circuit,
    run_circuit,
)
from shared_framework.visualization import plot_counts, sweep_iterations

__all__ = [
    "bitstring_oracle",
    "constraint_oracle",
    "diffusion_operator",
    "optimal_iterations",
    "build_grover_circuit",
    "run_circuit",
    "plot_counts",
    "sweep_iterations",
]
