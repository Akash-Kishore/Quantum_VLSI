"""
STAGE 1 — Encoding Unit Tests (Pure Python)
=============================================

Validates the bitstring decode logic and validity checking with no
quantum simulation at all. Must pass before proceeding to stage 2.
"""

from __future__ import annotations

import sys
import os

# Ensure project root is on sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from module1_placement.encoding import (
    decode_bitstring_to_placement,
    is_valid_collision_free,
)


def main() -> None:
    """Run all stage-1 encoding tests."""

    passed = True

    # ------------------------------------------------------------------
    # Test 1: Three worked examples from the bit-weight convention
    # ------------------------------------------------------------------
    print("[STAGE 1] Testing decode_bitstring_to_placement worked examples...")

    result_1 = decode_bitstring_to_placement("000000000000")
    expected_1 = (0, 0, 0, 0)
    assert result_1 == expected_1, (
        f"Example 1 FAILED: decode('000000000000') = {result_1}, expected {expected_1}"
    )
    print(f"  decode('000000000000') = {result_1}  ✓")

    result_2 = decode_bitstring_to_placement("011110000101")
    expected_2 = (5, 0, 6, 3)
    assert result_2 == expected_2, (
        f"Example 2 FAILED: decode('011110000101') = {result_2}, expected {expected_2}"
    )
    print(f"  decode('011110000101') = {result_2}  ✓")

    result_3 = decode_bitstring_to_placement("111000000000")
    expected_3 = (0, 0, 0, 7)
    assert result_3 == expected_3, (
        f"Example 3 FAILED: decode('111000000000') = {result_3}, expected {expected_3}"
    )
    print(f"  decode('111000000000') = {result_3}  ✓")

    # ------------------------------------------------------------------
    # Test 2: is_valid_collision_free — valid case
    # ------------------------------------------------------------------
    print("\n[STAGE 1] Testing is_valid_collision_free...")

    valid_placement = (0, 1, 2, 3)
    assert is_valid_collision_free(valid_placement) is True, (
        f"FAILED: is_valid_collision_free({valid_placement}) should be True"
    )
    print(f"  is_valid_collision_free({valid_placement}) = True  ✓")

    valid_placement_2 = (6, 5, 4, 3)
    assert is_valid_collision_free(valid_placement_2) is True, (
        f"FAILED: is_valid_collision_free({valid_placement_2}) should be True"
    )
    print(f"  is_valid_collision_free({valid_placement_2}) = True  ✓")

    # ------------------------------------------------------------------
    # Test 3: is_valid_collision_free — collision case
    # ------------------------------------------------------------------
    collision_placement = (0, 0, 1, 2)
    assert is_valid_collision_free(collision_placement) is False, (
        f"FAILED: is_valid_collision_free({collision_placement}) should be False"
    )
    print(f"  is_valid_collision_free({collision_placement}) = False  ✓")

    collision_placement_2 = (1, 2, 3, 1)
    assert is_valid_collision_free(collision_placement_2) is False, (
        f"FAILED: is_valid_collision_free({collision_placement_2}) should be False"
    )
    print(f"  is_valid_collision_free({collision_placement_2}) = False  ✓")

    # ------------------------------------------------------------------
    # Test 4: is_valid_collision_free — out of range
    # ------------------------------------------------------------------
    invalid_range = (0, 1, 2, 7)
    assert is_valid_collision_free(invalid_range) is False, (
        f"FAILED: is_valid_collision_free({invalid_range}) should be False"
    )
    print(f"  is_valid_collision_free({invalid_range}) = False  ✓")

    invalid_range_2 = (7, 7, 7, 7)
    assert is_valid_collision_free(invalid_range_2) is False, (
        f"FAILED: is_valid_collision_free({invalid_range_2}) should be False"
    )
    print(f"  is_valid_collision_free({invalid_range_2}) = False  ✓")

    # ------------------------------------------------------------------
    # Test 5: Round-trip decode → validate for third worked example
    # ------------------------------------------------------------------
    print("\n[STAGE 1] Testing round-trip decode → validate...")
    # "111000000000" decodes to (0, 0, 0, 7) — invalid (code 7)
    decoded = decode_bitstring_to_placement("111000000000")
    assert is_valid_collision_free(decoded) is False, (
        f"FAILED: decode('111000000000') = {decoded} should be invalid"
    )
    print(f"  decode('111000000000') = {decoded} → valid={is_valid_collision_free(decoded)}  ✓")

    # "000000000000" decodes to (0, 0, 0, 0) — collision (all same)
    decoded2 = decode_bitstring_to_placement("000000000000")
    assert is_valid_collision_free(decoded2) is False, (
        f"FAILED: decode('000000000000') = {decoded2} should be invalid (collision)"
    )
    print(f"  decode('000000000000') = {decoded2} → valid={is_valid_collision_free(decoded2)}  ✓")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    print("=" * 50)
    print("  STAGE 1: PASS")
    print("=" * 50)


if __name__ == "__main__":
    main()
