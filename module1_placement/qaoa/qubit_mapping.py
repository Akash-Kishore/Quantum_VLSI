"""
Qubit Mapping for One-Hot QAOA Encoding
========================================

Defines a deterministic, bijective mapping between the (cell, site) QUBO
variables from ``one_hot_qubo.py`` and qubit indices in the QAOA circuit.

Mapping rule: qubit_index = cell * NUM_SITES + site
  cell ∈ {0, 1, 2, 3}, site ∈ {0, 1, 2, 3, 4, 5, 6}
  → qubit_index ∈ {0, 1, ..., 27}

This mapping is intentionally simple and deterministic.  Every other module
(circuit builder, measurement decoder) must use these functions — never
inline the arithmetic.
"""

from __future__ import annotations

from module1_placement.qaoa.one_hot_qubo import NUM_CELLS, NUM_SITES


TOTAL_QUBITS: int = NUM_CELLS * NUM_SITES   # 4 × 7 = 28


def variable_to_qubit_index(cell: int, site: int) -> int:
    """Map a (cell, site) QUBO variable to its qubit index.

    Parameters
    ----------
    cell : int
        Cell index, 0–3.
    site : int
        Site index, 0–6.

    Returns
    -------
    int
        Qubit index in the range [0, TOTAL_QUBITS).

    Raises
    ------
    ValueError
        If ``cell`` or ``site`` is out of range.
    """
    if not (0 <= cell < NUM_CELLS):
        raise ValueError(f"cell must be 0–{NUM_CELLS - 1}, got {cell}")
    if not (0 <= site < NUM_SITES):
        raise ValueError(f"site must be 0–{NUM_SITES - 1}, got {site}")
    return cell * NUM_SITES + site


def qubit_index_to_variable(index: int) -> tuple[int, int]:
    """Map a qubit index back to its (cell, site) QUBO variable.

    Parameters
    ----------
    index : int
        Qubit index in the range [0, TOTAL_QUBITS).

    Returns
    -------
    tuple[int, int]
        ``(cell, site)`` pair.

    Raises
    ------
    ValueError
        If ``index`` is out of range.
    """
    if not (0 <= index < TOTAL_QUBITS):
        raise ValueError(
            f"qubit index must be 0–{TOTAL_QUBITS - 1}, got {index}"
        )
    cell = index // NUM_SITES
    site = index % NUM_SITES
    return (cell, site)
