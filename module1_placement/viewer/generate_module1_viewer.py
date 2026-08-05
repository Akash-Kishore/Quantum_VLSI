"""
Module 1 Viewer Data Generator
================================

Generates a self-contained HTML file that visualizes the Phase 3b Grover
search for Module 1 as an animated 4×7 (cell × site) marginal-probability
heatmap, swept across iterations 0 through 9.

Data source: exact statevectors via AerSimulator (not sampled counts).

Usage::

    python module1_placement/viewer/generate_module1_viewer.py
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

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator, AerError

from shared_framework.diffusion import diffusion_operator
from module1_placement.placement_oracle import (
    build_placement_oracle,
    CELL_QUBITS,
    TOTAL_QUBITS,
)
from module1_placement.classical_baseline import (
    enumerate_valid_placements_with_adjacency,
)


# ── Constants ────────────────────────────────────────────────────────
N_SEARCH: int = 12  # search register qubits (q0–q11)
N_ITERATIONS: int = 10  # k = 0..9
SEARCH_SPACE_SIZE: int = 2 ** N_SEARCH  # 4096
NUM_CELLS: int = 4
NUM_SITES: int = 7
TOP_K: int = 8  # number of top placements to report per frame


def decode_index(i: int) -> tuple[int, int, int, int]:
    """Decode a 12-bit search-register index to a 4-cell placement tuple.

    Uses direct bit-shift extraction consistent with the little-endian
    convention in ``encoding.py``: for cell *c*, the 3-bit code is stored
    at bits ``3c``, ``3c+1``, ``3c+2`` of the index.

    Parameters
    ----------
    i : int
        Search-register basis-state index (0–4095).

    Returns
    -------
    tuple[int, int, int, int]
        ``(site0, site1, site2, site3)`` where each value is 0–7.

    Examples
    --------
    >>> decode_index(0)
    (0, 0, 0, 0)
    >>> decode_index(1925)
    (5, 0, 6, 3)
    >>> decode_index(3584)
    (0, 0, 0, 7)
    """
    return (
        (i >> 0) & 0b111,
        (i >> 3) & 0b111,
        (i >> 6) & 0b111,
        (i >> 9) & 0b111,
    )


def generate_frames() -> list[dict[str, Any]]:
    """Generate 10 frames of viewer data (k = 0..9).

    For each iteration count, builds and simulates the Grover circuit
    using exact statevector simulation, then extracts:

    - A 4×7 marginal probability matrix (cell × site).
    - The total success probability (fraction of amplitude on the 96
      valid adjacency-constrained placements).
    - The top 8 highest-probability placements.

    Returns
    -------
    list[dict]
        A list of 10 frame dictionaries, one per iteration count.
    """
    print("[generate_frames] Building oracle...")
    oracle: QuantumCircuit = build_placement_oracle()
    assert oracle.num_qubits == TOTAL_QUBITS

    diffusion: QuantumCircuit = diffusion_operator(N_SEARCH)

    # Pre-compute ground truth (once, not per-frame).
    valid_placements: set[tuple[int, int, int, int]] = set(
        enumerate_valid_placements_with_adjacency()
    )
    assert len(valid_placements) == 96, (
        f"Expected 96 valid adjacency placements, got {len(valid_placements)}"
    )

    # Pre-compute which search-register indices are valid placements.
    valid_indices: set[int] = set()
    for i in range(SEARCH_SPACE_SIZE):
        placement = decode_index(i)
        if placement in valid_placements:
            valid_indices.add(i)
    assert len(valid_indices) == 96

    frames: list[dict[str, Any]] = []

    for k in range(N_ITERATIONS):
        print(f"[generate_frames] Running k={k}...")

        # Build fresh circuit for this iteration count.
        qc = QuantumCircuit(TOTAL_QUBITS)

        # Initial H on search register only.
        search_qubits = list(range(N_SEARCH))
        qc.h(search_qubits)

        # k Grover iterations.
        for _ in range(k):
            qc.compose(oracle, inplace=True)
            qc.compose(diffusion, qubits=search_qubits, inplace=True)

        assert qc.num_qubits == TOTAL_QUBITS, (
            f"Circuit at k={k} has {qc.num_qubits} qubits, expected {TOTAL_QUBITS}"
        )

        # Statevector simulation.
        qc.save_statevector()

        try:
            sim = AerSimulator(method="statevector", device="GPU")
            transpiled = transpile(qc, sim)
            result = sim.run(transpiled).result()
        except (AerError, RuntimeError) as exc:
            print(f"  GPU unavailable ({exc}), falling back to CPU.")
            sim = AerSimulator(method="statevector", device="CPU")
            transpiled = transpile(qc, sim)
            result = sim.run(transpiled).result()

        full_sv = result.get_statevector(qc).data  # numpy array of complex128

        # Extract search-register amplitudes (ancillas guaranteed |0⟩).
        search_amplitudes: np.ndarray = full_sv[:SEARCH_SPACE_SIZE].copy()

        # Memory discipline: discard the full statevector immediately.
        del full_sv
        del result

        # Probabilities over the 4096 search-register basis states.
        probs: np.ndarray = np.abs(search_amplitudes) ** 2
        del search_amplitudes

        # Build 4×7 marginal matrix.
        marginal: list[list[float]] = [
            [0.0 for _ in range(NUM_SITES)] for _ in range(NUM_CELLS)
        ]
        for idx in range(SEARCH_SPACE_SIZE):
            p = probs[idx]
            if p <= 0:
                continue
            cell_codes = decode_index(idx)
            for c in range(NUM_CELLS):
                code = cell_codes[c]
                if code <= 6:
                    marginal[c][code] += float(p)

        # Success probability.
        success_prob: float = float(sum(probs[i] for i in valid_indices))

        # Top 8 placements.
        top_indices = np.argsort(probs)[-TOP_K:][::-1]
        top_placements: list[dict[str, Any]] = []
        for ti in top_indices:
            placement = decode_index(int(ti))
            top_placements.append({
                "cells": list(placement),
                "probability": float(probs[int(ti)]),
                "valid": placement in valid_placements,
            })

        del probs

        frame: dict[str, Any] = {
            "iteration": k,
            "success_probability": success_prob,
            "marginal": marginal,
            "top_placements": top_placements,
        }
        frames.append(frame)
        print(f"  k={k}: success_probability={success_prob:.6f}")

    return frames


# ── HTML Template ────────────────────────────────────────────────────

_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Module 1 — Cell×Site Probability Heatmap</title>
<meta name="description" content="Animated heatmap of Grover search marginal probabilities for quantum VLSI placement (4 cells × 7 sites).">
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
    --border-subtle: rgba(255,255,255,0.06);
    --border-accent: rgba(59,130,246,0.3);
    --glow-blue: 0 0 20px rgba(59,130,246,0.15);
    --glow-purple: 0 0 20px rgba(139,92,246,0.15);
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 16px;
    --radius-xl: 20px;
  }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    overflow-x: hidden;
    -webkit-font-smoothing: antialiased;
  }

  /* Background ambient effect */
  body::before {
    content: '';
    position: fixed;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 20%, rgba(59,130,246,0.04) 0%, transparent 50%),
                radial-gradient(circle at 70% 80%, rgba(139,92,246,0.04) 0%, transparent 50%);
    z-index: -1;
    animation: ambientDrift 30s ease-in-out infinite alternate;
  }

  @keyframes ambientDrift {
    0% { transform: translate(0, 0) rotate(0deg); }
    100% { transform: translate(-3%, 3%) rotate(5deg); }
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 32px 24px;
  }

  /* ── Header ─────────────────────────────────────── */
  .header {
    text-align: center;
    margin-bottom: 32px;
  }

  .header h1 {
    font-size: 1.8rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple), var(--accent-cyan));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 6px;
  }

  .header .subtitle {
    font-size: 0.85rem;
    color: var(--text-muted);
    font-weight: 400;
  }

  /* ── Stats Bar ──────────────────────────────────── */
  .stats-bar {
    display: flex;
    gap: 16px;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 28px;
  }

  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    padding: 16px 24px;
    text-align: center;
    min-width: 160px;
    transition: all 0.3s ease;
  }

  .stat-card:hover {
    border-color: var(--border-accent);
    box-shadow: var(--glow-blue);
    transform: translateY(-2px);
  }

  .stat-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-bottom: 4px;
  }

  .stat-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--text-primary);
    transition: all 0.4s ease;
  }

  .stat-value.success {
    font-variant-numeric: tabular-nums;
  }

  /* Colour coding for success probability */
  .stat-value.low { color: var(--accent-red); }
  .stat-value.mid { color: var(--accent-amber); }
  .stat-value.high { color: var(--accent-green); }

  /* ── Main Layout ────────────────────────────────── */
  .main-grid {
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 24px;
    align-items: start;
  }

  @media (max-width: 900px) {
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
    font-size: 0.75rem;
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
    background: var(--accent-blue);
    box-shadow: 0 0 6px var(--accent-blue);
  }

  .panel-body {
    padding: 20px;
  }

  /* ── Heatmap ────────────────────────────────────── */
  .heatmap-container {
    position: relative;
  }

  .heatmap-grid {
    display: grid;
    grid-template-columns: 72px repeat(7, 1fr);
    gap: 3px;
  }

  .heatmap-corner {
    /* empty top-left corner */
  }

  .heatmap-col-label {
    text-align: center;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--text-muted);
    padding: 6px 0;
    letter-spacing: 0.04em;
  }

  .heatmap-row-label {
    display: flex;
    align-items: center;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--text-muted);
    padding-right: 8px;
    letter-spacing: 0.04em;
    justify-content: flex-end;
  }

  .heatmap-cell {
    aspect-ratio: 1;
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: rgba(255,255,255,0.9);
    cursor: default;
    position: relative;
    transition: background-color 0.5s cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 0.5s cubic-bezier(0.4, 0, 0.2, 1),
                transform 0.2s ease;
    border: 1px solid transparent;
    min-height: 56px;
  }

  .heatmap-cell:hover {
    transform: scale(1.08);
    z-index: 2;
    border-color: rgba(255,255,255,0.2);
  }

  .heatmap-cell .prob-text {
    text-shadow: 0 1px 3px rgba(0,0,0,0.6);
    transition: opacity 0.3s ease;
  }

  /* ── Color Legend ───────────────────────────────── */
  .legend {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 16px;
    justify-content: center;
  }

  .legend-label {
    font-size: 0.65rem;
    color: var(--text-muted);
    font-weight: 500;
  }

  .legend-bar {
    width: 200px;
    height: 10px;
    border-radius: 5px;
    background: linear-gradient(90deg,
      hsl(220, 30%, 14%) 0%,
      hsl(220, 60%, 35%) 25%,
      hsl(250, 70%, 50%) 50%,
      hsl(280, 80%, 55%) 75%,
      hsl(330, 90%, 60%) 100%);
    border: 1px solid var(--border-subtle);
  }

  /* ── Top Placements Table ───────────────────────── */
  .placements-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.72rem;
  }

  .placements-table th {
    text-align: left;
    padding: 8px 10px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.62rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .placements-table td {
    padding: 7px 10px;
    border-bottom: 1px solid var(--border-subtle);
    font-variant-numeric: tabular-nums;
    transition: background-color 0.3s ease;
  }

  .placements-table tr:last-child td {
    border-bottom: none;
  }

  .placements-table tr:hover td {
    background: var(--bg-card-hover);
  }

  .placement-tuple {
    font-family: 'Inter', monospace;
    font-weight: 500;
    color: var(--text-primary);
  }

  .placement-prob {
    color: var(--accent-cyan);
    font-weight: 600;
  }

  .badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.58rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .badge.valid {
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent-green);
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .badge.invalid {
    background: rgba(239, 68, 68, 0.12);
    color: var(--accent-red);
    border: 1px solid rgba(239, 68, 68, 0.25);
  }

  /* ── Controls ───────────────────────────────────── */
  .controls {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 18px 24px;
    margin-top: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    justify-content: center;
  }

  .btn {
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
    border: none;
    color: #fff;
    padding: 9px 22px;
    border-radius: var(--radius-sm);
    font-family: 'Inter', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.25s ease;
    letter-spacing: 0.03em;
    min-width: 100px;
  }

  .btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(59,130,246,0.3);
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
    background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
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
    box-shadow: 0 0 6px rgba(59,130,246,0.5);
    cursor: pointer;
    transition: box-shadow 0.2s ease;
  }

  input[type="range"]::-webkit-slider-thumb:hover {
    box-shadow: 0 0 12px rgba(59,130,246,0.7);
  }

  input[type="range"]::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 0 6px rgba(59,130,246,0.5);
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
    background: var(--accent-blue);
    box-shadow: 0 0 8px var(--accent-blue);
    transform: scale(1.3);
  }

  /* ── Footer ─────────────────────────────────────── */
  .footer {
    text-align: center;
    margin-top: 32px;
    font-size: 0.65rem;
    color: var(--text-muted);
  }
</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div class="header">
    <h1>Module 1 — Grover Placement Heatmap</h1>
    <div class="subtitle">4 Cells × 7 Sites · Marginal Probability Sweep · Iterations 0–9</div>
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
      <div class="stat-label">Marked States</div>
      <div class="stat-value">96</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Search Space</div>
      <div class="stat-value">4096</div>
    </div>
  </div>

  <!-- Main Layout -->
  <div class="main-grid">
    <!-- Heatmap Panel -->
    <div class="panel">
      <div class="panel-header"><span class="dot"></span> Marginal Probability Heatmap</div>
      <div class="panel-body">
        <div class="heatmap-container">
          <div class="heatmap-grid" id="heatmap-grid">
            <!-- Populated by JS -->
          </div>
        </div>
        <div class="legend">
          <span class="legend-label">0.0</span>
          <div class="legend-bar"></div>
          <span class="legend-label">1.0</span>
        </div>
      </div>
    </div>

    <!-- Top Placements Panel -->
    <div class="panel">
      <div class="panel-header"><span class="dot"></span> Top 8 Placements</div>
      <div class="panel-body" style="padding: 8px 0;">
        <table class="placements-table" id="placements-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Placement (c0,c1,c2,c3)</th>
              <th>Prob</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody id="placements-body">
            <!-- Populated by JS -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Controls -->
  <div class="controls">
    <button class="btn" id="btn-play" onclick="togglePlay()">▶ Play</button>
    <div class="slider-group">
      <label for="slider-frame">Iteration</label>
      <input type="range" id="slider-frame" min="0" max="9" value="0" step="1">
      <span class="speed-label" id="slider-val">k = 0</span>
    </div>
  </div>

  <!-- Iteration dots -->
  <div class="iter-dots" id="iter-dots"></div>

  <!-- Footer -->
  <div class="footer">
    Quantum VLSI Placement — Phase 3b Grover Search Visualization · Exact Statevector Data
  </div>
</div>

<script>
const FRAMES = __FRAMES_JSON__;

let currentFrame = 0;
let playing = false;
let playInterval = null;
const PLAY_SPEED_MS = 1200;

// ── Heatmap colour mapping ───────────────────────────────
function probToColor(p) {
  // Fixed linear scale 0 → 1.
  // Maps through a cool-to-warm gradient:
  //   0.0 → deep dark blue-grey
  //   0.5 → vivid purple
  //   1.0 → hot magenta/pink
  const t = Math.max(0, Math.min(1, p));
  const h = 220 - t * 170;               // 220 → 50  (blue → warm)
  const s = 20 + t * 70;                 // 20% → 90%
  const l = 12 + t * 50;                 // 12% → 62%
  return 'hsl(' + h + ',' + s + '%,' + l + '%)';
}

function probToGlow(p) {
  if (p < 0.3) return 'none';
  const intensity = Math.min(1, (p - 0.3) / 0.7);
  const alpha = (intensity * 0.5).toFixed(2);
  return '0 0 ' + Math.round(8 + intensity * 16) + 'px hsla(280, 80%, 55%, ' + alpha + ')';
}

// ── Build static grid structure ──────────────────────────
function buildGrid() {
  const grid = document.getElementById('heatmap-grid');
  grid.innerHTML = '';

  // Corner cell
  const corner = document.createElement('div');
  corner.className = 'heatmap-corner';
  grid.appendChild(corner);

  // Column headers
  for (let s = 0; s < 7; s++) {
    const lbl = document.createElement('div');
    lbl.className = 'heatmap-col-label';
    lbl.textContent = 'Site ' + s;
    grid.appendChild(lbl);
  }

  // Rows
  for (let c = 0; c < 4; c++) {
    const rowLabel = document.createElement('div');
    rowLabel.className = 'heatmap-row-label';
    rowLabel.textContent = 'Cell ' + c;
    grid.appendChild(rowLabel);

    for (let s = 0; s < 7; s++) {
      const cell = document.createElement('div');
      cell.className = 'heatmap-cell';
      cell.id = 'hm-' + c + '-' + s;
      cell.innerHTML = '<span class="prob-text"></span>';
      grid.appendChild(cell);
    }
  }
}

// ── Build iteration dots ─────────────────────────────────
function buildDots() {
  const container = document.getElementById('iter-dots');
  for (let i = 0; i < FRAMES.length; i++) {
    const dot = document.createElement('div');
    dot.className = 'iter-dot';
    dot.dataset.frame = i;
    dot.addEventListener('click', function() { goToFrame(i); });
    container.appendChild(dot);
  }
}

// ── Render a frame ───────────────────────────────────────
function renderFrame(idx) {
  const frame = FRAMES[idx];

  // Stats
  document.getElementById('stat-iteration').textContent = frame.iteration;
  const sp = frame.success_probability;
  const spEl = document.getElementById('stat-success');
  spEl.textContent = (sp * 100).toFixed(2) + '%';
  spEl.className = 'stat-value success ' + (sp < 0.1 ? 'low' : sp < 0.7 ? 'mid' : 'high');

  // Heatmap cells
  for (let c = 0; c < 4; c++) {
    for (let s = 0; s < 7; s++) {
      const p = frame.marginal[c][s];
      const cell = document.getElementById('hm-' + c + '-' + s);
      cell.style.backgroundColor = probToColor(p);
      cell.style.boxShadow = probToGlow(p);
      cell.querySelector('.prob-text').textContent = p < 0.0005 ? '' : p.toFixed(3);
      cell.title = 'Cell ' + c + ' → Site ' + s + ': ' + p.toFixed(6);
    }
  }

  // Top placements
  const tbody = document.getElementById('placements-body');
  tbody.innerHTML = '';
  frame.top_placements.forEach(function(tp, i) {
    const tr = document.createElement('tr');
    const rank = document.createElement('td');
    rank.textContent = (i + 1);
    rank.style.color = 'var(--text-muted)';

    const tuple = document.createElement('td');
    tuple.className = 'placement-tuple';
    tuple.textContent = '(' + tp.cells.join(', ') + ')';

    const prob = document.createElement('td');
    prob.className = 'placement-prob';
    prob.textContent = (tp.probability * 100).toFixed(4) + '%';

    const status = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = 'badge ' + (tp.valid ? 'valid' : 'invalid');
    badge.textContent = tp.valid ? '✓ valid' : '✗ invalid';
    status.appendChild(badge);

    tr.appendChild(rank);
    tr.appendChild(tuple);
    tr.appendChild(prob);
    tr.appendChild(status);
    tbody.appendChild(tr);
  });

  // Slider
  document.getElementById('slider-frame').value = idx;
  document.getElementById('slider-val').textContent = 'k = ' + idx;

  // Dots
  const dots = document.querySelectorAll('.iter-dot');
  dots.forEach(function(d, i) {
    d.className = 'iter-dot' + (i === idx ? ' active' : '');
  });
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
  document.getElementById('btn-play').textContent = '⏸ Pause';
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
  document.getElementById('btn-play').textContent = '▶ Play';
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
buildGrid();
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
        The 10 frame dictionaries from ``generate_frames()``.

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

    output_path = os.path.join(_SCRIPT_DIR, "module1_viewer.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n[generate_module1_viewer] Wrote {len(html_content):,} bytes to:")
    print(f"  {output_path}")
    print(f"\n  Frames generated: {len(frames)}")
    for frame in frames:
        k = frame["iteration"]
        sp = frame["success_probability"]
        print(f"    k={k}: success_probability={sp:.6f} ({sp*100:.4f}%)")

    print("\n  No packages were changed, upgraded, or installed.")


if __name__ == "__main__":
    main()
