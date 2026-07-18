"""
Placement Oracle for Grover's Algorithm
=========================================

Builds a 25-qubit phase-flip oracle that marks valid, collision-free
placements of 4 logic cells onto 7 physical sites.

The oracle spans 25 qubits:

- q0–q11:  search register (4 cells × 3 qubits each)
- q12–q14: reusable diff scratch register
- q15–q20: 6 collision-flag ancillas
- q21–q24: 4 validity-flag ancillas

Diffusion must be applied only to q0–q11 (12-qubit search register)
by the caller — the oracle does not include diffusion.

Constraints checked:

1. **Validity**: each cell's 3-bit code ≠ 111 (decimal 7).
2. **No-collision**: all 6 pairs of cells have distinct site codes.

Adjacency constraints are out of scope for this phase.
"""

from __future__ import annotations

from qiskit import QuantumCircuit


# ── Qubit layout constants (single source of truth) ─────────────────

CELL_QUBITS = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]  # [LSB, mid, MSB] per cell
DIFF_QUBITS = [12, 13, 14]
COLLISION_PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]  # (cell_i, cell_j)
COLLISION_FLAG_QUBITS = [15, 16, 17, 18, 19, 20]  # index-matched to COLLISION_PAIRS
VALIDITY_FLAG_QUBITS = [21, 22, 23, 24]  # index-matched to cell order 0,1,2,3
TOTAL_QUBITS = 25


def _append_pairwise_collision_flag(
    qc: QuantumCircuit,
    cell_a_qubits: list[int],
    cell_b_qubits: list[int],
    diff_qubits: list[int],
    flag_qubit: int,
) -> None:
    """Compute and flag whether two cells share the same site code.

    Steps:

    1. XOR cell_a into diff_qubits (CNOT from cell_a[i] to diff[i]).
    2. XOR cell_b into diff_qubits (CNOT from cell_b[i] to diff[i]).
       Now diff[i] = cell_a[i] ⊕ cell_b[i].
    3. If all diff bits are 0 (cells collide), set flag_qubit = 1:
       X-sandwich the diff qubits, MCX(diff → flag), X-sandwich again.
    4. Uncompute diff (reverse CNOTs from step 2, then step 1).

    The flag_qubit is left set (not uncomputed here) — it is uncomputed
    at the end of build_placement_oracle via the reverse call.

    This function is self-inverse: calling it twice with the same
    arguments restores all qubits to their original state.

    Parameters
    ----------
    qc : QuantumCircuit
        Circuit to append to (in-place).
    cell_a_qubits : list[int]
        3 qubit indices for cell A (position-matched).
    cell_b_qubits : list[int]
        3 qubit indices for cell B (position-matched).
    diff_qubits : list[int]
        3 scratch qubit indices (must start at |0⟩).
    flag_qubit : int
        Ancilla qubit to set if cells collide.
    """
    # Step 1: XOR cell_a into diff
    for i in range(3):
        qc.cx(cell_a_qubits[i], diff_qubits[i])

    # Step 2: XOR cell_b into diff  →  diff = cell_a ⊕ cell_b
    for i in range(3):
        qc.cx(cell_b_qubits[i], diff_qubits[i])

    # Step 3: Flag if all diff bits are 0 (collision)
    # X-sandwich: "all-zero" → "all-one" for positive-control MCX
    for d in diff_qubits:
        qc.x(d)
    qc.mcx(diff_qubits, flag_qubit)
    for d in diff_qubits:
        qc.x(d)

    # Step 4: Uncompute diff (reverse of steps 2, 1)
    for i in range(2, -1, -1):
        qc.cx(cell_b_qubits[i], diff_qubits[i])
    for i in range(2, -1, -1):
        qc.cx(cell_a_qubits[i], diff_qubits[i])


def _append_cell_validity_flag(
    qc: QuantumCircuit,
    cell_qubits: list[int],
    flag_qubit: int,
) -> None:
    """Flag whether a cell's 3-bit code equals 111 (invalid code 7).

    Sets ``flag_qubit = 1`` iff all 3 cell qubits are 1, using a plain
    3-input MCX with positive controls (no X-sandwich needed since we
    detect the all-ones pattern directly).

    This function is self-inverse: calling it twice restores the flag
    qubit to its original state.

    Parameters
    ----------
    qc : QuantumCircuit
        Circuit to append to (in-place).
    cell_qubits : list[int]
        3 qubit indices for the cell [LSB, mid, MSB].
    flag_qubit : int
        Ancilla qubit to set if the code is invalid (7).
    """
    qc.mcx(cell_qubits, flag_qubit)


def build_placement_oracle() -> QuantumCircuit:
    """Build the 25-qubit placement oracle circuit.

    The oracle phase-flips exactly those basis states in the search
    register (q0–q11) that encode valid, collision-free placements:

    - All 4 cell codes in range 0–6 (not 7).
    - All 6 cell pairs have distinct codes.

    The oracle's compute-phase-uncompute structure ensures that all
    ancilla qubits (q12–q24) return to |0⟩ after each application.

    Returns
    -------
    QuantumCircuit
        A 25-qubit oracle circuit (no classical register).
    """
    qc = QuantumCircuit(TOTAL_QUBITS, name="PlacementOracle")

    # ── Step 1: Compute collision flags ──────────────────────────────
    for pair_idx, (ci, cj) in enumerate(COLLISION_PAIRS):
        _append_pairwise_collision_flag(
            qc,
            cell_a_qubits=CELL_QUBITS[ci],
            cell_b_qubits=CELL_QUBITS[cj],
            diff_qubits=DIFF_QUBITS,
            flag_qubit=COLLISION_FLAG_QUBITS[pair_idx],
        )

    # ── Step 2: Compute validity flags ───────────────────────────────
    for cell_idx in range(4):
        _append_cell_validity_flag(
            qc,
            cell_qubits=CELL_QUBITS[cell_idx],
            flag_qubit=VALIDITY_FLAG_QUBITS[cell_idx],
        )

    # ── Step 3: X all 10 flag qubits ─────────────────────────────────
    # Convert "bad condition = 1" → "good condition = 1":
    #   collision flags: 1 means collision → after X, 1 means no collision
    #   validity flags:  1 means code=7   → after X, 1 means code≠7
    all_flags = COLLISION_FLAG_QUBITS + VALIDITY_FLAG_QUBITS
    for f in all_flags:
        qc.x(f)

    # ── Step 4: Multi-controlled-Z across all 10 flags ───────────────
    # H → MCX → H on the last flag as target, other 9 as controls.
    target = all_flags[-1]
    controls = all_flags[:-1]
    qc.h(target)
    qc.mcx(controls, target)
    qc.h(target)

    # ── Step 5: Undo X on all 10 flag qubits ─────────────────────────
    for f in all_flags:
        qc.x(f)

    # ── Step 6: Uncompute in exact reverse (LIFO) order ──────────────
    # First: validity flags in reverse cell order (3, 2, 1, 0)
    for cell_idx in range(3, -1, -1):
        _append_cell_validity_flag(
            qc,
            cell_qubits=CELL_QUBITS[cell_idx],
            flag_qubit=VALIDITY_FLAG_QUBITS[cell_idx],
        )

    # Then: collision flags in reverse pair order
    for pair_idx in range(len(COLLISION_PAIRS) - 1, -1, -1):
        ci, cj = COLLISION_PAIRS[pair_idx]
        _append_pairwise_collision_flag(
            qc,
            cell_a_qubits=CELL_QUBITS[ci],
            cell_b_qubits=CELL_QUBITS[cj],
            diff_qubits=DIFF_QUBITS,
            flag_qubit=COLLISION_FLAG_QUBITS[pair_idx],
        )

    # ── Step 7: Hard assertion — no ancilla drift from mcx ───────────
    assert qc.num_qubits == TOTAL_QUBITS, (
        f"Oracle qubit count {qc.num_qubits} != expected {TOTAL_QUBITS}. "
        f"An mcx call likely requested extra ancillas."
    )

    return qc
