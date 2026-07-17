"""
Visualization Helpers for Grover's Algorithm
=============================================

- ``plot_counts`` — histogram of measurement counts.
- ``sweep_iterations`` — success probability vs. iteration count plot.

All figures are saved to files (relative to the caller's directory)
rather than relying solely on ``plt.show()``.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Union

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend; safe in headless WSL2.
import matplotlib.pyplot as plt
from qiskit.visualization import plot_histogram

from shared_framework.grover_utils import build_grover_circuit, run_circuit
from shared_framework.oracle import bitstring_oracle


def plot_counts(
    counts: Dict[str, int],
    title: str = "Measurement Counts",
    save_path: Optional[str] = None,
) -> str:
    """Plot a histogram of measurement counts and save to a file.

    Parameters
    ----------
    counts : dict[str, int]
        Measurement results, e.g. ``{"11": 950, "00": 50}``.
    title : str, optional
        Plot title.
    save_path : str or None, optional
        Absolute or relative path for the saved figure.  If ``None``,
        defaults to ``counts_histogram.png`` in the directory of the
        calling script.

    Returns
    -------
    str
        The path the figure was saved to.
    """
    if save_path is None:
        save_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "counts_histogram.png",
        )

    fig = plot_histogram(counts, title=title)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[visualization] Histogram saved to {save_path}")
    return save_path


def sweep_iterations(
    n_qubits: int,
    oracle_circuit,
    max_iterations: int,
    shots: int = 1000,
    marked_states: Optional[Union[str, List[str]]] = None,
    save_path: Optional[str] = None,
) -> List[float]:
    """Sweep Grover iteration counts and plot success probability.

    Runs Grover's algorithm for iteration counts ``0, 1, ...,
    max_iterations``, computes the success probability at each
    (fraction of shots measuring a marked state), and produces a
    matplotlib line plot saved to a file.

    Parameters
    ----------
    n_qubits : int
        Number of qubits.
    oracle_circuit : QuantumCircuit
        The phase-flip oracle circuit.
    max_iterations : int
        Maximum number of Grover iterations to test.
    shots : int, optional
        Shots per run.  Default is 1000.
    marked_states : str or list[str] or None, optional
        The marked bitstring(s) used to compute success probability.
        If ``None``, the success probability cannot be computed and
        raw counts are printed instead.
    save_path : str or None, optional
        Path for the saved figure.  Defaults to
        ``sweep_iterations.png`` in this module's directory.

    Returns
    -------
    list[float]
        Success probabilities for iterations ``0..max_iterations``.
    """
    if save_path is None:
        save_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "sweep_iterations.png",
        )

    if isinstance(marked_states, str):
        marked_states = [marked_states]

    probabilities: List[float] = []
    iteration_range = list(range(max_iterations + 1))

    for iters in iteration_range:
        circuit = build_grover_circuit(n_qubits, oracle_circuit, iters)
        counts = run_circuit(circuit, shots=shots)

        if marked_states is not None:
            # Sum counts for all marked states.
            success_count = sum(counts.get(s, 0) for s in marked_states)
            prob = success_count / shots
        else:
            # If marked_states unknown, report max-count state probability.
            prob = max(counts.values()) / shots

        probabilities.append(prob)
        print(
            f"  iterations={iters:2d}  |  "
            f"success_prob={prob:.4f}  |  counts={counts}"
        )

    # --- Plot ---------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(iteration_range, probabilities, "o-", linewidth=2, markersize=8)
    ax.set_xlabel("Number of Grover Iterations", fontsize=12)
    ax.set_ylabel("Success Probability", fontsize=12)
    ax.set_title(
        f"Grover Success Probability vs Iterations  (n={n_qubits} qubits)",
        fontsize=13,
    )
    ax.set_xticks(iteration_range)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"[visualization] Sweep plot saved to {save_path}")

    return probabilities
