"""
Module 2 Viewer Data Generator
================================

Generates a self-contained HTML file that visualizes the ATPG Grover
search for Module 2 as an animated 8-bar probability chart (one bar
per 3-bit input state) plus a static fault-circuit diagram, swept
across Grover iterations k = 0 through k = 6.

Data source: exact statevectors via AerSimulator (CPU statevector,
no GPU — 6 qubits / 64 amplitudes is trivially fast on CPU and the
project's hardware-requirements doc already notes GPU kernel-launch
overhead can make small circuits slower on GPU).

Usage::

    python module2_atpg/viewer/generate_module2_viewer.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import numpy as np

# ── Ensure project root is on sys.path ───────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from shared_framework.diffusion import diffusion_operator
from module2_atpg.atpg_oracle import build_atpg_oracle


# ── Constants ────────────────────────────────────────────────────────
N_TOTAL: int = 6          # total qubits in the ATPG oracle
N_SEARCH: int = 3         # search register qubits (q0=A, q1=B, q2=Cin)
N_ITERATIONS: int = 7     # k = 0..6
N_INPUT_STATES: int = 8   # 2^3

# Detecting-state indices in the statevector.
# Bit-j of index = qubit-j value.  Detecting iff A=1 AND B=1.
#   Index 3 (binary 011): A=1, B=1, Cin=0
#   Index 7 (binary 111): A=1, B=1, Cin=1
DETECTING_INDICES: set[int] = {3, 7}


def index_to_bitstring(i: int) -> str:
    """Convert a 3-bit statevector index to a Qiskit little-endian bitstring.

    Qiskit convention: character position 0 is the highest-numbered qubit.
    For 3 qubits ``format(i, '03b')`` already yields this.

    Parameters
    ----------
    i : int
        Statevector index (0–7).

    Returns
    -------
    str
        3-character Qiskit bitstring (e.g. ``'011'`` for index 3).
    """
    return format(i, "03b")


def index_to_label(i: int) -> str:
    """Convert a 3-bit statevector index to a human-readable A·B·Cin label.

    Bit 0 = A, bit 1 = B, bit 2 = Cin (Qiskit little-endian convention
    with q0 as LSB).

    Parameters
    ----------
    i : int
        Statevector index (0–7).

    Returns
    -------
    str
        Label string, e.g. ``'A=1,B=1,Cin=0'``.
    """
    a = (i >> 0) & 1
    b = (i >> 1) & 1
    cin = (i >> 2) & 1
    return f"A={a},B={b},Cin={cin}"


def generate_frames() -> list[dict[str, Any]]:
    """Generate 7 frames of viewer data (k = 0..6).

    For each iteration count, builds and simulates the Grover circuit
    using exact statevector simulation, then extracts:

    - 8 probabilities, one per 3-bit input state.
    - Which states are fault-detecting (indices 3 and 7).
    - The total success probability.

    A residual check verifies that ancillas return to ``|0⟩`` every
    frame (i.e. the first 8 amplitudes account for all probability).

    Returns
    -------
    list[dict]
        A list of 7 frame dictionaries, one per iteration count.

    Raises
    ------
    AssertionError
        If the ancilla residual exceeds 1e-9 at any frame.
    """
    print("[generate_frames] Building oracle...")
    oracle: QuantumCircuit = build_atpg_oracle()
    assert oracle.num_qubits == N_TOTAL, (
        f"Oracle has {oracle.num_qubits} qubits, expected {N_TOTAL}"
    )

    diffusion: QuantumCircuit = diffusion_operator(N_SEARCH)

    sim = AerSimulator(method="statevector")

    frames: list[dict[str, Any]] = []

    for k in range(N_ITERATIONS):
        print(f"[generate_frames] Running k={k}...")

        # Build fresh circuit for this iteration count.
        qc = QuantumCircuit(N_TOTAL)

        # Initial H on search register only (q0=A, q1=B, q2=Cin).
        search_qubits = list(range(N_SEARCH))
        qc.h(search_qubits)

        # k Grover iterations.
        for _ in range(k):
            # Full 6-qubit oracle.
            qc.compose(oracle, inplace=True)
            # Diffusion on q0–q2 only.
            qc.compose(diffusion, qubits=search_qubits, inplace=True)

        qc.save_statevector()

        result = sim.run(qc).result()
        full_sv: np.ndarray = result.get_statevector(qc).data

        # Slice the first 8 amplitudes (ancillas guaranteed |0⟩).
        input_amplitudes: np.ndarray = full_sv[:N_INPUT_STATES].copy()

        # ── Residual check ────────────────────────────────────────
        residual: float = 1.0 - float(np.sum(np.abs(input_amplitudes) ** 2))
        assert abs(residual) < 1e-9, (
            f"FAIL: Ancilla residual at k={k} is {residual:.2e} "
            f"(exceeds 1e-9). Some ancilla is NOT returning to |0⟩."
        )
        print(f"  k={k}: residual = {residual:.2e}  ✓")

        # Probabilities.
        probs: np.ndarray = np.abs(input_amplitudes) ** 2

        # Memory discipline.
        del full_sv
        del result
        del input_amplitudes

        # Build per-state records.
        states: list[dict[str, Any]] = []
        for i in range(N_INPUT_STATES):
            states.append({
                "index": i,
                "bitstring": index_to_bitstring(i),
                "label": index_to_label(i),
                "probability": float(probs[i]),
                "detecting": i in DETECTING_INDICES,
            })

        # Success probability.
        success_prob: float = float(
            sum(probs[i] for i in DETECTING_INDICES)
        )

        frame: dict[str, Any] = {
            "iteration": k,
            "success_probability": success_prob,
            "states": states,
        }
        frames.append(frame)
        print(f"  k={k}: success_probability={success_prob:.6f}")

        del probs

    return frames


# ── HTML Template ────────────────────────────────────────────────────

_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Module 2 — ATPG Fault Detection Probability Viewer</title>
<meta name="description" content="Animated bar chart of Grover ATPG search input-state probabilities and static fault-circuit diagram for a 1-bit full adder stuck-at-0 fault.">
<style>

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg-primary: #0a0e1a;
    --bg-secondary: #111827;
    --bg-card: #1a1f35;
    --bg-card-hover: #222842;
    --text-primary: #e8ecf4;
    --text-secondary: #8892a8;
    --text-muted: #5a6478;
    --accent-blue: #3b82f6;
    --accent-cyan: #06b6d4;
    --accent-purple: #8b5cf6;
    --accent-green: #10b981;
    --accent-red: #ef4444;
    --accent-amber: #f59e0b;
    --accent-teal: #14b8a6;
    --border-subtle: rgba(255,255,255,0.06);
    --border-accent: rgba(59,130,246,0.3);
    --glow-blue: 0 0 20px rgba(59,130,246,0.15);
    --glow-purple: 0 0 20px rgba(139,92,246,0.15);
    --glow-teal: 0 0 20px rgba(20,184,166,0.25);
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --radius-xl: 20px;
    --bar-non-detect: #3b4f7a;
    --bar-non-detect-bright: #4a6399;
    --bar-detect: #0ea5a9;
    --bar-detect-bright: #14d4c8;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    overflow-x: hidden;
    -webkit-font-smoothing: antialiased;
  }

  body::before {
    content: '';
    position: fixed;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 20%, rgba(6,182,212,0.04) 0%, transparent 50%),
                radial-gradient(circle at 70% 80%, rgba(139,92,246,0.04) 0%, transparent 50%);
    z-index: -1;
    animation: ambientDrift 30s ease-in-out infinite alternate;
  }

  @keyframes ambientDrift {
    0% { transform: translate(0, 0) rotate(0deg); }
    100% { transform: translate(-3%, 3%) rotate(5deg); }
  }

  .container {
    max-width: 1280px;
    margin: 0 auto;
    padding: 28px 24px;
  }

  /* ── Header ─────────────────────────────────────── */
  .header {
    text-align: center;
    margin-bottom: 28px;
  }

  .header h1 {
    font-size: 1.7rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple), var(--accent-blue));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 6px;
  }

  .header .subtitle {
    font-size: 0.82rem;
    color: var(--text-muted);
    font-weight: 400;
  }

  /* ── Stats Bar ──────────────────────────────────── */
  .stats-bar {
    display: flex;
    gap: 14px;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 24px;
  }

  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 14px 22px;
    text-align: center;
    min-width: 140px;
    transition: all 0.3s ease;
  }

  .stat-card:hover {
    border-color: var(--border-accent);
    box-shadow: var(--glow-blue);
    transform: translateY(-2px);
  }

  .stat-label {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-bottom: 4px;
  }

  .stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    transition: all 0.4s ease;
  }

  .stat-value.success {
    font-variant-numeric: tabular-nums;
  }

  .stat-value.low { color: var(--accent-red); }
  .stat-value.mid { color: var(--accent-amber); }
  .stat-value.high { color: var(--accent-green); }

  /* ── Status line ────────────────────────────────── */
  .status-line {
    text-align: center;
    margin-bottom: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 10px 20px;
    border-radius: var(--radius-md);
    transition: all 0.4s ease;
  }

  .status-line.detected {
    background: rgba(16, 185, 129, 0.12);
    color: var(--accent-green);
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .status-line.masked {
    background: rgba(239, 68, 68, 0.10);
    color: var(--accent-red);
    border: 1px solid rgba(239, 68, 68, 0.25);
  }

  /* ── Main Layout ────────────────────────────────── */
  .main-grid {
    display: grid;
    grid-template-columns: 1fr 420px;
    gap: 24px;
    align-items: start;
  }

  @media (max-width: 960px) {
    .main-grid { grid-template-columns: 1fr; }
  }

  .panel {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    overflow: hidden;
  }

  .panel-header {
    padding: 14px 20px;
    border-bottom: 1px solid var(--border-subtle);
    font-size: 0.73rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .panel-header .dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--accent-cyan);
    box-shadow: 0 0 6px var(--accent-cyan);
  }

  .panel-body {
    padding: 20px;
  }

  /* ── Bar Chart ──────────────────────────────────── */
  .bar-chart {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    height: 320px;
    padding: 0 8px;
    position: relative;
  }

  .bar-column {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    position: relative;
  }

  .bar-track {
    flex: 1;
    width: 100%;
    display: flex;
    align-items: flex-end;
    position: relative;
  }

  .bar-fill {
    width: 100%;
    border-radius: 4px 4px 0 0;
    transition: height 0.5s cubic-bezier(0.4, 0, 0.2, 1),
                background 0.5s cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    min-height: 2px;
  }

  .bar-fill.non-detecting {
    background: linear-gradient(to top, var(--bar-non-detect), var(--bar-non-detect-bright));
  }

  .bar-fill.detecting {
    background: linear-gradient(to top, var(--bar-detect), var(--bar-detect-bright));
    box-shadow: 0 0 12px rgba(14, 165, 169, 0.3);
  }

  .bar-prob {
    position: absolute;
    top: -22px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.62rem;
    font-weight: 600;
    color: var(--text-secondary);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    transition: opacity 0.3s ease;
  }

  .bar-label {
    margin-top: 8px;
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--text-muted);
    font-family: monospace;
    letter-spacing: 0.04em;
  }

  .bar-sublabel {
    font-size: 0.55rem;
    color: var(--text-muted);
    opacity: 0.7;
    margin-top: 2px;
  }

  /* Y-axis */
  .y-axis {
    position: absolute;
    left: -6px;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--border-subtle);
  }

  .y-axis-labels {
    position: absolute;
    left: -42px;
    top: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    pointer-events: none;
  }

  .y-axis-label {
    font-size: 0.58rem;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
    transform: translateY(4px);
  }

  .y-axis-label:first-child {
    transform: translateY(-2px);
  }

  /* Reference line at 12.5% */
  .ref-line {
    position: absolute;
    left: 0; right: 0;
    border-top: 1px dashed rgba(255,255,255,0.1);
    pointer-events: none;
  }

  .ref-line-label {
    position: absolute;
    right: 4px;
    top: -14px;
    font-size: 0.52rem;
    color: var(--text-muted);
    opacity: 0.7;
  }

  /* Legend */
  .chart-legend {
    display: flex;
    gap: 20px;
    justify-content: center;
    margin-top: 18px;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.68rem;
    color: var(--text-secondary);
  }

  .legend-swatch {
    width: 12px;
    height: 12px;
    border-radius: 3px;
  }

  .legend-swatch.detect {
    background: linear-gradient(135deg, var(--bar-detect), var(--bar-detect-bright));
    box-shadow: 0 0 6px rgba(14, 165, 169, 0.3);
  }

  .legend-swatch.non-detect {
    background: linear-gradient(135deg, var(--bar-non-detect), var(--bar-non-detect-bright));
  }

  /* ── Fault Diagram ──────────────────────────────── */
  .fault-diagram {
    padding: 8px 0;
  }

  .fault-diagram svg {
    width: 100%;
    height: auto;
  }

  .diagram-note {
    font-size: 0.65rem;
    color: var(--text-muted);
    margin-top: 14px;
    padding: 10px 14px;
    background: rgba(255,255,255,0.02);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-subtle);
    line-height: 1.5;
  }

  .diagram-note strong {
    color: var(--text-secondary);
  }

  /* ── Controls ───────────────────────────────────── */
  .controls {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 16px 24px;
    margin-top: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    justify-content: center;
  }

  .btn {
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
    border: none;
    color: #fff;
    padding: 9px 22px;
    border-radius: var(--radius-sm);
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.25s ease;
    letter-spacing: 0.03em;
    min-width: 100px;
  }

  .btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(6,182,212,0.3);
  }

  .btn:active {
    transform: translateY(0);
  }

  .slider-group {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 200px;
  }

  .slider-group label {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--text-muted);
    white-space: nowrap;
  }

  input[type="range"] {
    -webkit-appearance: none;
    appearance: none;
    flex: 1;
    height: 4px;
    border-radius: 2px;
    background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
    outline: none;
    cursor: pointer;
  }

  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 0 6px rgba(6,182,212,0.5);
    cursor: pointer;
    transition: box-shadow 0.2s ease;
  }

  input[type="range"]::-webkit-slider-thumb:hover {
    box-shadow: 0 0 12px rgba(6,182,212,0.7);
  }

  input[type="range"]::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 0 6px rgba(6,182,212,0.5);
    border: none;
    cursor: pointer;
  }

  .speed-label {
    font-size: 0.65rem;
    color: var(--text-muted);
    font-weight: 500;
    min-width: 42px;
    text-align: right;
  }

  /* ── Iteration dots ─────────────────────────────── */
  .iter-dots {
    display: flex;
    gap: 6px;
    justify-content: center;
    margin-top: 4px;
  }

  .iter-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--text-muted);
    opacity: 0.3;
    transition: all 0.3s ease;
    cursor: pointer;
  }

  .iter-dot.active {
    opacity: 1;
    background: var(--accent-cyan);
    box-shadow: 0 0 8px var(--accent-cyan);
    transform: scale(1.3);
  }

  /* ── Footer ─────────────────────────────────────── */
  .footer {
    text-align: center;
    margin-top: 28px;
    font-size: 0.63rem;
    color: var(--text-muted);
  }

  /* ── Chart wrapper with y-axis space ────────────── */
  .chart-wrapper {
    position: relative;
    margin-left: 48px;
  }

</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div class="header">
    <h1>Module 2 — ATPG Fault Detection Viewer</h1>
    <div class="subtitle">8 Input States · Stuck-at-0 Fault on AB Term · Grover Iterations 0–6</div>
  </div>

  <!-- Stats Bar -->
  <div class="stats-bar">
    <div class="stat-card">
      <div class="stat-label">Iteration</div>
      <div class="stat-value" id="stat-iteration">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Success Probability</div>
      <div class="stat-value success" id="stat-success">0.00%</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Detecting States</div>
      <div class="stat-value">2 / 8</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Fault Model</div>
      <div class="stat-value" style="font-size:0.85rem;">AB stuck-at-0</div>
    </div>
  </div>

  <!-- Status Line -->
  <div class="status-line" id="status-line">—</div>

  <!-- Main Layout -->
  <div class="main-grid">
    <!-- Bar Chart Panel -->
    <div class="panel">
      <div class="panel-header"><span class="dot"></span> Input-State Probabilities</div>
      <div class="panel-body">
        <div class="chart-wrapper">
          <div class="y-axis-labels" id="y-axis-labels">
            <span class="y-axis-label">1.0</span>
            <span class="y-axis-label">0.75</span>
            <span class="y-axis-label">0.50</span>
            <span class="y-axis-label">0.25</span>
            <span class="y-axis-label">0.0</span>
          </div>
          <div class="bar-chart" id="bar-chart">
            <div class="y-axis"></div>
            <!-- Reference line at 12.5% (1/8, uniform baseline) -->
            <div class="ref-line" id="ref-line" style="bottom: 12.5%;">
              <span class="ref-line-label">12.5% baseline</span>
            </div>
            <!-- 8 bar columns populated by JS -->
          </div>
        </div>
        <div class="chart-legend">
          <div class="legend-item">
            <div class="legend-swatch detect"></div>
            Fault-detecting (A=1, B=1)
          </div>
          <div class="legend-item">
            <div class="legend-swatch non-detect"></div>
            Non-detecting
          </div>
        </div>
      </div>
    </div>

    <!-- Fault Diagram Panel -->
    <div class="panel">
      <div class="panel-header"><span class="dot"></span> Reversible Full-Adder Carry-Out Circuit</div>
      <div class="panel-body fault-diagram">
        <svg viewBox="0 0 380 310" xmlns="http://www.w3.org/2000/svg">
          <!-- Background -->
          <rect width="380" height="310" fill="transparent"/>

          <!-- Wire labels (inputs) -->
          <text x="12" y="60" fill="#8892a8" font-size="11" font-weight="600" font-family="monospace">A</text>
          <text x="12" y="120" fill="#8892a8" font-size="11" font-weight="600" font-family="monospace">B</text>
          <text x="10" y="180" fill="#8892a8" font-size="11" font-weight="600" font-family="monospace">Cin</text>

          <!-- Input wires -->
          <line x1="32" y1="57" x2="340" y2="57" stroke="#3b4f7a" stroke-width="1.5"/>
          <line x1="32" y1="117" x2="340" y2="117" stroke="#3b4f7a" stroke-width="1.5"/>
          <line x1="32" y1="177" x2="340" y2="177" stroke="#3b4f7a" stroke-width="1.5"/>

          <!-- Cout accumulator wire -->
          <line x1="80" y1="245" x2="340" y2="245" stroke="#06b6d4" stroke-width="2" opacity="0.7"/>
          <text x="345" y="249" fill="#06b6d4" font-size="10" font-weight="600" font-family="monospace">Cout</text>
          <text x="80" y="268" fill="#5a6478" font-size="8" font-family="sans-serif">(XOR accumulator, not OR)</text>

          <!-- Gate 1: AB Toffoli — FAULTY (stuck-at-0) -->
          <g opacity="0.35">
            <!-- Control dots on A, B -->
            <circle cx="105" cy="57" r="4" fill="#5a6478"/>
            <circle cx="105" cy="117" r="4" fill="#5a6478"/>
            <!-- Vertical line to target -->
            <line x1="105" y1="61" x2="105" y2="241" stroke="#5a6478" stroke-width="1" stroke-dasharray="3,2"/>
            <!-- Target (XOR symbol) -->
            <circle cx="105" cy="245" r="10" fill="none" stroke="#5a6478" stroke-width="1.5"/>
            <line x1="95" y1="245" x2="115" y2="245" stroke="#5a6478" stroke-width="1.5"/>
            <line x1="105" y1="235" x2="105" y2="255" stroke="#5a6478" stroke-width="1.5"/>
          </g>
          <!-- Fault overlay on Gate 1 -->
          <line x1="88" y1="40" x2="122" y2="262" stroke="#ef4444" stroke-width="2.5" opacity="0.7"/>
          <line x1="122" y1="40" x2="88" y2="262" stroke="#ef4444" stroke-width="2.5" opacity="0.7"/>
          <rect x="65" y="280" width="80" height="20" rx="4" fill="rgba(239,68,68,0.15)" stroke="#ef4444" stroke-width="1"/>
          <text x="105" y="294" fill="#ef4444" font-size="8.5" font-weight="600" text-anchor="middle" font-family="sans-serif">stuck-at-0</text>
          <!-- Gate label -->
          <text x="105" y="30" fill="#5a6478" font-size="8" text-anchor="middle" font-family="sans-serif">AB term</text>

          <!-- Gate 2: BC Toffoli — healthy -->
          <g>
            <!-- Control dots on B, Cin -->
            <circle cx="200" cy="117" r="4" fill="#10b981"/>
            <circle cx="200" cy="177" r="4" fill="#10b981"/>
            <!-- Vertical line to target -->
            <line x1="200" y1="121" x2="200" y2="241" stroke="#10b981" stroke-width="1" opacity="0.5"/>
            <!-- Target (XOR symbol) -->
            <circle cx="200" cy="245" r="10" fill="none" stroke="#10b981" stroke-width="1.5"/>
            <line x1="190" y1="245" x2="210" y2="245" stroke="#10b981" stroke-width="1.5"/>
            <line x1="200" y1="235" x2="200" y2="255" stroke="#10b981" stroke-width="1.5"/>
          </g>
          <text x="200" y="30" fill="#8892a8" font-size="8" text-anchor="middle" font-family="sans-serif">BC term</text>

          <!-- Gate 3: AC Toffoli — healthy -->
          <g>
            <!-- Control dots on A, Cin -->
            <circle cx="290" cy="57" r="4" fill="#10b981"/>
            <circle cx="290" cy="177" r="4" fill="#10b981"/>
            <!-- Vertical line to target -->
            <line x1="290" y1="61" x2="290" y2="241" stroke="#10b981" stroke-width="1" opacity="0.5"/>
            <!-- Target (XOR symbol) -->
            <circle cx="290" cy="245" r="10" fill="none" stroke="#10b981" stroke-width="1.5"/>
            <line x1="280" y1="245" x2="300" y2="245" stroke="#10b981" stroke-width="1.5"/>
            <line x1="290" y1="235" x2="290" y2="255" stroke="#10b981" stroke-width="1.5"/>
          </g>
          <text x="290" y="30" fill="#8892a8" font-size="8" text-anchor="middle" font-family="sans-serif">AC term</text>

        </svg>

        <div class="diagram-note">
          <strong>Fault model:</strong> The AB-term Toffoli gate is stuck-at-0 — its
          contribution never reaches the Cout XOR accumulator. The faulty circuit
          computes Cout = BC ⊕ AC instead of the correct AB ⊕ BC ⊕ AC.<br><br>
          <strong>Detection:</strong> The fault is detected whenever the true AB
          product is 1, i.e. whenever A=1 AND B=1, regardless of Cin. This gives
          exactly 2 fault-detecting inputs out of 8.<br><br>
          <strong>Note:</strong> Sum is not computed in this circuit — the fault does
          not affect Sum, so including it would add ancillas for zero benefit.
          This was a deliberate design decision, not an omission.
        </div>
      </div>
    </div>
  </div>

  <!-- Controls -->
  <div class="controls">
    <button class="btn" id="btn-play" onclick="togglePlay()">&#9654; Play</button>
    <div class="slider-group">
      <label for="slider-frame">Iteration</label>
      <input type="range" id="slider-frame" min="0" max="6" value="0" step="1">
      <span class="speed-label" id="slider-val">k = 0</span>
    </div>
  </div>

  <!-- Iteration dots -->
  <div class="iter-dots" id="iter-dots"></div>

  <!-- Footer -->
  <div class="footer">
    Quantum VLSI — Module 2 ATPG Stuck-at-0 Fault Detection · Exact Statevector Data · Grover Iterations 0–6
  </div>
</div>

<script>
var FRAMES = __FRAMES_JSON__;

var currentFrame = 0;
var playing = false;
var playInterval = null;
var PLAY_SPEED_MS = 1200;

// ── Build bar chart ──────────────────────────────────────
function buildBars() {
  var chart = document.getElementById('bar-chart');
  for (var i = 0; i < 8; i++) {
    var state = FRAMES[0].states[i];
    var col = document.createElement('div');
    col.className = 'bar-column';

    var track = document.createElement('div');
    track.className = 'bar-track';

    var fill = document.createElement('div');
    fill.className = 'bar-fill ' + (state.detecting ? 'detecting' : 'non-detecting');
    fill.id = 'bar-' + i;

    var probLabel = document.createElement('span');
    probLabel.className = 'bar-prob';
    probLabel.id = 'bar-prob-' + i;
    fill.appendChild(probLabel);

    track.appendChild(fill);
    col.appendChild(track);

    var label = document.createElement('div');
    label.className = 'bar-label';
    label.textContent = state.bitstring;
    col.appendChild(label);

    var sub = document.createElement('div');
    sub.className = 'bar-sublabel';
    var a = (i >> 0) & 1;
    var b = (i >> 1) & 1;
    var c = (i >> 2) & 1;
    sub.textContent = a + ',' + b + ',' + c;
    col.appendChild(sub);

    chart.appendChild(col);
  }
}

// ── Build iteration dots ─────────────────────────────────
function buildDots() {
  var container = document.getElementById('iter-dots');
  for (var i = 0; i < FRAMES.length; i++) {
    var dot = document.createElement('div');
    dot.className = 'iter-dot';
    dot.dataset.frame = i;
    (function(idx) {
      dot.addEventListener('click', function() { goToFrame(idx); });
    })(i);
    container.appendChild(dot);
  }
}

// ── Render a frame ───────────────────────────────────────
function renderFrame(idx) {
  var frame = FRAMES[idx];

  // Stats
  document.getElementById('stat-iteration').textContent = frame.iteration;
  var sp = frame.success_probability;
  var spEl = document.getElementById('stat-success');
  spEl.textContent = (sp * 100).toFixed(2) + '%';
  spEl.className = 'stat-value success ' + (sp < 0.15 ? 'low' : sp < 0.7 ? 'mid' : 'high');

  // Find highest-probability state
  var maxProb = -1;
  var maxDetecting = false;
  for (var i = 0; i < 8; i++) {
    if (frame.states[i].probability > maxProb) {
      maxProb = frame.states[i].probability;
      maxDetecting = frame.states[i].detecting;
    }
  }

  // Status line
  var statusEl = document.getElementById('status-line');
  if (maxDetecting) {
    statusEl.textContent = '\u2714 Fault detected \u2014 highest-probability state detects the stuck-at-0 fault';
    statusEl.className = 'status-line detected';
  } else {
    statusEl.textContent = '\u2718 Fault masked \u2014 highest-probability state does NOT detect the fault';
    statusEl.className = 'status-line masked';
  }

  // Bars
  for (var i = 0; i < 8; i++) {
    var s = frame.states[i];
    var bar = document.getElementById('bar-' + i);
    var pct = (s.probability * 100).toFixed(1);
    bar.style.height = (s.probability * 100) + '%';
    bar.className = 'bar-fill ' + (s.detecting ? 'detecting' : 'non-detecting');

    var probLabel = document.getElementById('bar-prob-' + i);
    probLabel.textContent = s.probability < 0.005 ? '' : pct + '%';
  }

  // Slider
  document.getElementById('slider-frame').value = idx;
  document.getElementById('slider-val').textContent = 'k = ' + frame.iteration;

  // Dots
  var dots = document.querySelectorAll('.iter-dot');
  for (var d = 0; d < dots.length; d++) {
    dots[d].className = 'iter-dot' + (d === idx ? ' active' : '');
  }
}

// ── Playback ─────────────────────────────────────────────
function togglePlay() {
  if (playing) {
    stopPlay();
  } else {
    startPlay();
  }
}

function startPlay() {
  playing = true;
  document.getElementById('btn-play').innerHTML = '&#9208; Pause';
  playInterval = setInterval(function() {
    currentFrame++;
    if (currentFrame >= FRAMES.length) {
      currentFrame = 0;
    }
    renderFrame(currentFrame);
  }, PLAY_SPEED_MS);
}

function stopPlay() {
  playing = false;
  document.getElementById('btn-play').innerHTML = '&#9654; Play';
  if (playInterval) {
    clearInterval(playInterval);
    playInterval = null;
  }
}

function goToFrame(idx) {
  stopPlay();
  currentFrame = idx;
  renderFrame(currentFrame);
}

// ── Slider binding ───────────────────────────────────────
document.getElementById('slider-frame').addEventListener('input', function(e) {
  goToFrame(parseInt(e.target.value, 10));
});

// ── Init ─────────────────────────────────────────────────
buildBars();
buildDots();
renderFrame(0);
</script>
</body>
</html>"""


def build_html(frames: list[dict[str, Any]]) -> str:
    """Build the complete self-contained HTML string.

    Substitutes the frame data as inline JSON into the HTML template.

    Parameters
    ----------
    frames : list[dict]
        The 7 frame dictionaries from ``generate_frames()``.

    Returns
    -------
    str
        Complete HTML document as a string.
    """
    frames_json = json.dumps(frames, indent=None, separators=(",", ":"))
    return _HTML_TEMPLATE.replace("__FRAMES_JSON__", frames_json)


def main() -> None:
    """Generate the viewer HTML file."""
    frames = generate_frames()

    html_content = build_html(frames)

    output_path = os.path.join(_SCRIPT_DIR, "module2_viewer.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n[generate_module2_viewer] Wrote {len(html_content):,} bytes to:")
    print(f"  {output_path}")
    print(f"\n  Frames generated: {len(frames)}")
    for frame in frames:
        k = frame["iteration"]
        sp = frame["success_probability"]
        print(f"    k={k}: success_probability={sp:.6f} ({sp*100:.4f}%)")

    print("\n  No packages were changed, upgraded, or installed.")


if __name__ == "__main__":
    main()
