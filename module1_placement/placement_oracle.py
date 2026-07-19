"""
Placement Oracle for Grover's Algorithm
=========================================

Builds a 27-qubit phase-flip oracle that marks valid, collision-free,
adjacency-satisfying placements of 4 logic cells onto 7 physical sites.

The oracle spans 27 qubits:

- q0–q11:  search register (4 cells × 3 qubits each)
- q12–q14: reusable diff scratch register
- q15–q20: 6 collision-flag ancillas
- q21–q24: 4 validity-flag ancillas
- q25–q26: 2 adjacency-flag ancillas

Diffusion must be applied only to q0–q11 (12-qubit search register)
by the caller — the oracle does not include diffusion.

Constraints checked:

1. **Validity**: each cell's 3-bit code ≠ 111 (decimal 7).
2. **No-collision**: all 6 pairs of cells have distinct site codes.
3. **Adjacency (chain)**: cell 0 adjacent to cell 1, AND cell 1
   adjacent to cell 2. Cell 3 has no adjacency requirement.
"""

from __future__ import annotations

from qiskit import QuantumCircuit


# ── Qubit layout constants (single source of truth) ─────────────────

CELL_QUBITS = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]  # [LSB, mid, MSB] per cell
DIFF_QUBITS = [12, 13, 14]
COLLISION_PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]  # (cell_i, cell_j)
COLLISION_FLAG_QUBITS = [15, 16, 17, 18, 19, 20]  # index-matched to COLLISION_PAIRS
VALIDITY_FLAG_QUBITS = [21, 22, 23, 24]  # index-matched to cell order 0,1,2,3
ADJACENCY_PAIRS = [(0, 1), (1, 2)]           # (cell_a, cell_b) index pairs
ADJACENCY_FLAG_QUBITS = [25, 26]             # index-matched to ADJACENCY_PAIRS
TOTAL_QUBITS = 27


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


# ── Site-adjacency topology ──────────────────────────────────────────
#
# 7 sites in a 2×4 grid (row=1,col=3 is unused):
#   Row 0:  [0] [1] [2] [3]
#   Row 1:  [4] [5] [6] [ . ]
#
# 8 undirected adjacency edges (Manhattan distance = 1):
_ADJACENCY_EDGES = frozenset({
    (0, 1), (1, 2), (2, 3), (4, 5), (5, 6),
    (0, 4), (1, 5), (2, 6),
})

# 16 ordered pairs (both directions of each edge):
_ADJACENCY_ORDERED_PAIRS = [
    (0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2),
    (4, 5), (5, 4), (5, 6), (6, 5),
    (0, 4), (4, 0), (1, 5), (5, 1), (2, 6), (6, 2),
]

# Bit patterns for site codes 0-6, as (LSB, mid, MSB):
_CODE_BITS = {
    0: (0, 0, 0), 1: (1, 0, 0), 2: (0, 1, 0), 3: (1, 1, 0),
    4: (0, 0, 1), 5: (1, 0, 1), 6: (0, 1, 1),
}


def _append_adjacency_flag(
    qc: QuantumCircuit,
    cell_a_qubits: list[int],
    cell_b_qubits: list[int],
    flag_qubit: int,
) -> None:
    """Compute and flag whether two cells are NOT adjacent.

    After this function completes, ``flag_qubit`` = 1 means the cells
    are NOT adjacent (chain constraint violated), 0 means they ARE
    adjacent (constraint satisfied). This matches the polarity of all
    other flags (1 = problem exists).

    **Construction**: enumerates all 16 ordered (site_a, site_b) pairs
    that ARE adjacent. For each pair, an X-mask + 6-control MCX +
    undo-X-mask block conditionally toggles ``flag_qubit``. After all
    16 terms, ``flag_qubit`` = 1 iff the cells ARE adjacent. A final
    X gate inverts this to the "problem" polarity.

    **Self-inverse property**: the entire block is a pure sequence of
    XOR-into-``flag_qubit`` operations (each MCX toggles flag_qubit
    conditionally) plus a single trailing X. Calling this function
    twice with the same arguments restores ``flag_qubit`` to its
    original state, with zero net effect on the cell qubits.

    **Worked example** for ordered pair (x=1, y=0):
    code 1 = (1,0,0), code 0 = (0,0,0). X-mask: X on cell_a[1],
    cell_a[2] (the 0-bits of code 1), X on cell_b[0], cell_b[1],
    cell_b[2] (all bits of code 0 are 0). The 6-control MCX fires
    exactly when cell_a=1 and cell_b=0 — correctly flagging adjacency,
    since (1,0) is in the edge set.

    Parameters
    ----------
    qc : QuantumCircuit
        Circuit to append to (in-place).
    cell_a_qubits : list[int]
        3 qubit indices for cell A [LSB, mid, MSB].
    cell_b_qubits : list[int]
        3 qubit indices for cell B [LSB, mid, MSB].
    flag_qubit : int
        Ancilla qubit to set if cells are NOT adjacent.
    """
    # Part A: 16-term adjacency lookup
    for (code_a, code_b) in _ADJACENCY_ORDERED_PAIRS:
        bits_a = _CODE_BITS[code_a]
        bits_b = _CODE_BITS[code_b]

        # Step 1: X-mask — apply X where the target bit is 0
        x_positions = []  # track which qubits get X'd, for undo
        for i in range(3):
            if bits_a[i] == 0:
                qc.x(cell_a_qubits[i])
                x_positions.append(cell_a_qubits[i])
            if bits_b[i] == 0:
                qc.x(cell_b_qubits[i])
                x_positions.append(cell_b_qubits[i])

        # Step 2: 6-control MCX
        qc.mcx(cell_a_qubits + cell_b_qubits, flag_qubit)

        # Step 3: Undo X-mask
        for pos in x_positions:
            qc.x(pos)

    # Part B: Invert to "problem" polarity (1 = NOT adjacent)
    qc.x(flag_qubit)


def build_placement_oracle() -> QuantumCircuit:
    """Build the 27-qubit placement oracle circuit.

    The oracle phase-flips exactly those basis states in the search
    register (q0–q11) that encode valid, collision-free, chain-adjacent
    placements:

    - All 4 cell codes in range 0–6 (not 7).
    - All 6 cell pairs have distinct codes.
    - Cell 0 is adjacent to cell 1, and cell 1 is adjacent to cell 2.

    The oracle's compute-phase-uncompute structure ensures that all
    ancilla qubits (q12–q26) return to |0⟩ after each application.

    Returns
    -------
    QuantumCircuit
        A 27-qubit oracle circuit (no classical register).
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

    # ── Step 3: Compute adjacency flags ──────────────────────────────
    for adj_idx, (ca, cb) in enumerate(ADJACENCY_PAIRS):
        _append_adjacency_flag(
            qc,
            cell_a_qubits=CELL_QUBITS[ca],
            cell_b_qubits=CELL_QUBITS[cb],
            flag_qubit=ADJACENCY_FLAG_QUBITS[adj_idx],
        )

    # ── Step 4: X all 12 flag qubits ─────────────────────────────────
    # Convert "bad condition = 1" → "good condition = 1":
    #   collision flags:  1 means collision     → after X, 1 means no collision
    #   validity flags:   1 means code=7        → after X, 1 means code≠7
    #   adjacency flags:  1 means NOT adjacent  → after X, 1 means adjacent
    all_flags = COLLISION_FLAG_QUBITS + VALIDITY_FLAG_QUBITS + ADJACENCY_FLAG_QUBITS
    for f in all_flags:
        qc.x(f)

    # ── Step 5: Multi-controlled-Z across all 12 flags ───────────────
    # H → MCX → H on qubit 26 (last flag) as target, qubits 15-25 as controls.
    target = all_flags[-1]    # qubit 26
    controls = all_flags[:-1]  # qubits 15-25 (11 controls)
    qc.h(target)
    qc.mcx(controls, target)
    qc.h(target)

    # ── Step 6: Undo X on all 12 flag qubits ─────────────────────────
    for f in all_flags:
        qc.x(f)

    # ── Step 7: Uncompute in exact reverse (LIFO) order ──────────────
    # First: adjacency flags in reverse order (computed last, undone first)
    for adj_idx in range(len(ADJACENCY_PAIRS) - 1, -1, -1):
        ca, cb = ADJACENCY_PAIRS[adj_idx]
        _append_adjacency_flag(
            qc,
            cell_a_qubits=CELL_QUBITS[ca],
            cell_b_qubits=CELL_QUBITS[cb],
            flag_qubit=ADJACENCY_FLAG_QUBITS[adj_idx],
        )

    # Then: validity flags in reverse cell order (3, 2, 1, 0)
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

    # ── Step 8: Hard assertion — no ancilla drift from mcx ───────────
    assert qc.num_qubits == TOTAL_QUBITS, (
        f"Oracle qubit count {qc.num_qubits} != expected {TOTAL_QUBITS}. "
        f"An mcx call likely requested extra ancillas."
    )

    return qc
