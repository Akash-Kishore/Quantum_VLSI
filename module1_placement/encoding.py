"""
Bitstring Encoding / Decoding for Placement
=============================================

Converts between Qiskit little-endian measurement bitstrings (12-bit,
qubits q0–q11) and 4-tuples of site indices (cell 0–3).

Bit-weight convention
---------------------
For cell *k* (qubits ``3k``, ``3k+1``, ``3k+2``):

- qubit ``3k``   → LSB (weight 1)
- qubit ``3k+1`` → mid (weight 2)
- qubit ``3k+2`` → MSB (weight 4)

Little-endian Qiskit bitstring ``s`` of length 12 (rightmost = q0):

    lsb_char = s[11 - 3*k]
    mid_char = s[10 - 3*k]
    msb_char = s[9  - 3*k]
    code_k   = int(lsb_char) + 2*int(mid_char) + 4*int(msb_char)

Worked examples (hand-verified)::

    >>> decode_bitstring_to_placement("000000000000") == (0, 0, 0, 0)
    True
    >>> decode_bitstring_to_placement("011110000101") == (5, 0, 6, 3)
    True
    >>> decode_bitstring_to_placement("111000000000") == (0, 0, 0, 7)
    True
"""

from __future__ import annotations

from typing import Tuple


def decode_bitstring_to_placement(bitstring: str) -> Tuple[int, int, int, int]:
    """Decode a 12-bit Qiskit measurement bitstring to a 4-cell placement.

    Parameters
    ----------
    bitstring : str
        A 12-character string of ``'0'`` and ``'1'``, in Qiskit
        little-endian order (rightmost character = qubit 0).

    Returns
    -------
    tuple[int, int, int, int]
        ``(site0, site1, site2, site3)`` where each value is 0–7.

    Raises
    ------
    ValueError
        If the bitstring is not exactly 12 characters long.
    """
    if len(bitstring) != 12:
        raise ValueError(
            f"Expected 12-character bitstring, got length {len(bitstring)}: "
            f"'{bitstring}'"
        )

    sites = []
    for k in range(4):
        lsb_char = bitstring[11 - 3 * k]
        mid_char = bitstring[10 - 3 * k]
        msb_char = bitstring[9 - 3 * k]
        code = int(lsb_char) + 2 * int(mid_char) + 4 * int(msb_char)
        sites.append(code)
    return tuple(sites)  # type: ignore[return-value]


def is_valid_collision_free(placement: Tuple[int, int, int, int]) -> bool:
    """Check whether a 4-cell placement is valid and collision-free.

    A placement is valid iff:

    1. Every site code is in the range 0–6 (code 7 is invalid).
    2. All four site codes are pairwise distinct (no collisions).

    Parameters
    ----------
    placement : tuple[int, int, int, int]
        ``(site0, site1, site2, site3)``.

    Returns
    -------
    bool
        ``True`` if the placement is valid and collision-free.
    """
    # Check range: all codes must be 0–6
    for code in placement:
        if code < 0 or code > 6:
            return False
    # Check pairwise distinct
    if len(set(placement)) != 4:
        return False
    return True
