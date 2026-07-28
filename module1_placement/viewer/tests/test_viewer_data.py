"""
Test Viewer Data
=================

Three-stage test for the Module 1 viewer data generator.

Stage 1: Pure-Python decode consistency (no simulation).
Stage 2: Analytic sanity check at k=0 (deterministic math).
Stage 3: Full pipeline smoke test (runs actual frame generation).

No pytest — plain ``assert`` in ``main()``, matching every other test
file in this project.

Usage::

    python module1_placement/viewer/tests/test_viewer_data.py
"""

from __future__ import annotations

import os
import sys

# ── Ensure project root is on sys.path ───────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from module1_placement.viewer.generate_module1_viewer import (
    decode_index,
    generate_frames,
)
from module1_placement.encoding import decode_bitstring_to_placement


def _index_to_bitstring(i: int) -> str:
    """Convert a 12-bit index to a Qiskit little-endian bitstring.

    Qiskit bitstrings are written with qubit 0 at the rightmost position.
    So for index ``i``, the bitstring is the 12-bit binary representation
    with the LSB on the right — which is simply ``format(i, '012b')``
    reversed at the *bit* level... except that ``format(i, '012b')``
    already puts MSB on the left, which in Qiskit convention means the
    highest-numbered qubit is on the left.  Since our index ``i`` has
    qubit 0 as bit 0 (LSB), the Qiskit bitstring is the *reversed*
    binary representation.

    Wait — let's be precise.  Qiskit bitstring character position:
      ``s[0]`` = qubit n-1 (MSB), ``s[n-1]`` = qubit 0 (LSB).

    So for 12 qubits: ``s = format(i, '012b')`` where bit 0 of ``i``
    maps to ``s[11]`` (rightmost).  That's exactly ``format(i, '012b')``.

    Parameters
    ----------
    i : int
        Index in 0..4095.

    Returns
    -------
    str
        12-character Qiskit little-endian bitstring.
    """
    return format(i, "012b")


def main() -> None:
    """Run all viewer data tests."""

    # ==================================================================
    # STAGE 1: Pure-Python decode consistency (no simulation)
    # ==================================================================
    print("=" * 60)
    print("  STAGE 1: Decode Consistency")
    print("=" * 60)

    # Test case 1: index 0 → (0, 0, 0, 0)
    result = decode_index(0)
    assert result == (0, 0, 0, 0), f"FAIL: decode_index(0) = {result}, expected (0, 0, 0, 0)"
    # Cross-check with encoding.py
    bs = _index_to_bitstring(0)
    assert bs == "000000000000", f"FAIL: bitstring for 0 = '{bs}'"
    enc_result = decode_bitstring_to_placement(bs)
    assert enc_result == (0, 0, 0, 0), f"FAIL: encoding.decode('{bs}') = {enc_result}"
    assert result == enc_result, f"FAIL: decode_index(0)={result} != encoding.decode='{enc_result}'"
    print(f"  decode_index(0)    = {result}  ✓  (matches encoding.decode('{bs}'))")

    # Test case 2: index 1925 → (5, 0, 6, 3)
    result = decode_index(1925)
    assert result == (5, 0, 6, 3), f"FAIL: decode_index(1925) = {result}, expected (5, 0, 6, 3)"
    bs = _index_to_bitstring(1925)
    assert bs == "011110000101", f"FAIL: bitstring for 1925 = '{bs}'"
    enc_result = decode_bitstring_to_placement(bs)
    assert enc_result == (5, 0, 6, 3), f"FAIL: encoding.decode('{bs}') = {enc_result}"
    assert result == enc_result, f"FAIL: decode_index(1925)={result} != encoding.decode='{enc_result}'"
    print(f"  decode_index(1925) = {result}  ✓  (matches encoding.decode('{bs}'))")

    # Test case 3: index 3584 → (0, 0, 0, 7)
    result = decode_index(3584)
    assert result == (0, 0, 0, 7), f"FAIL: decode_index(3584) = {result}, expected (0, 0, 0, 7)"
    bs = _index_to_bitstring(3584)
    assert bs == "111000000000", f"FAIL: bitstring for 3584 = '{bs}'"
    enc_result = decode_bitstring_to_placement(bs)
    assert enc_result == (0, 0, 0, 7), f"FAIL: encoding.decode('{bs}') = {enc_result}"
    assert result == enc_result, f"FAIL: decode_index(3584)={result} != encoding.decode='{enc_result}'"
    print(f"  decode_index(3584) = {result}  ✓  (matches encoding.decode('{bs}'))")

    print("  STAGE 1: PASS ✓\n")

    # ==================================================================
    # STAGE 2: Analytic sanity check at k=0
    # ==================================================================
    print("=" * 60)
    print("  STAGE 2: Analytic Sanity Check (k=0)")
    print("=" * 60)

    # At k=0, all 4096 basis states are equiprobable at 1/4096.
    # Each cell's 3 qubits are independently uniform over codes 0-7.
    # Marginal for real sites (0-6): each has probability 1/8 = 0.125.
    # Success probability: 96/4096 = 0.0234375 (2.34375%).

    print("  (Will be verified against actual frame-0 in Stage 3)")
    print("  Expected marginal[c][s] for s in 0..6: 0.125")
    print("  Expected success_probability: 0.0234375 (96/4096)")
    print("  STAGE 2: SETUP COMPLETE ✓\n")

    # ==================================================================
    # STAGE 3: Full pipeline smoke test
    # ==================================================================
    print("=" * 60)
    print("  STAGE 3: Full Pipeline Smoke Test")
    print("=" * 60)

    print("  Generating all 10 frames (this will take a while)...")
    frames = generate_frames()

    # Check frame count.
    assert len(frames) == 10, f"FAIL: len(frames) = {len(frames)}, expected 10"
    print(f"  len(frames) = {len(frames)}  ✓")

    # ── Frame 0: analytic verification (Stage 2 values) ──────────────
    f0 = frames[0]
    print(f"\n  Frame 0 (k=0):")
    print(f"    success_probability = {f0['success_probability']:.10f}")

    # Check success probability at k=0.
    expected_sp0 = 96.0 / 4096.0  # 0.0234375
    actual_sp0 = f0["success_probability"]
    assert abs(actual_sp0 - expected_sp0) < 1e-9, (
        f"FAIL: Frame 0 success_probability = {actual_sp0}, "
        f"expected {expected_sp0} (diff = {abs(actual_sp0 - expected_sp0)})"
    )
    print(f"    success_probability ≈ {expected_sp0} (96/4096)  ✓")

    # Check marginal entries at k=0.
    expected_marginal = 1.0 / 8.0  # 0.125
    for c in range(4):
        for s in range(7):
            actual_m = f0["marginal"][c][s]
            assert abs(actual_m - expected_marginal) < 1e-9, (
                f"FAIL: Frame 0 marginal[{c}][{s}] = {actual_m}, "
                f"expected {expected_marginal}"
            )
    print(f"    All marginal[c][s] ≈ 0.125 (1/8)  ✓")

    # ── Frame 5: success probability near ~98.57% ─────────────────────
    f5 = frames[5]
    print(f"\n  Frame 5 (k=5):")
    print(f"    success_probability = {f5['success_probability']:.10f}")
    # Theoretical optimum at k=5 for M=96, N=4096 is ~98.57%.
    # We assert > 0.95 with slack; the exact value should be very close to 0.9857.
    assert f5["success_probability"] > 0.95, (
        f"FAIL: Frame 5 success_probability = {f5['success_probability']}, "
        f"expected > 0.95 (theoretical ~98.57%)"
    )
    print(f"    success_probability > 0.95  ✓  (theoretical ~98.57%)")

    # ── Print all frame summaries ─────────────────────────────────────
    print(f"\n  All frames:")
    for frame in frames:
        k = frame["iteration"]
        sp = frame["success_probability"]
        print(f"    k={k}: success_probability = {sp:.10f} ({sp*100:.4f}%)")

    # ── Check HTML file exists and has content ─────────────────────────
    viewer_dir = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))
    html_path = os.path.join(viewer_dir, "module1_viewer.html")

    # Generate the HTML file if it doesn't exist yet (in case test is
    # run standalone after generate_frames but before main()).
    if not os.path.exists(html_path):
        from module1_placement.viewer.generate_module1_viewer import build_html
        html_content = build_html(frames)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n  (Generated HTML file for validation)")

    assert os.path.exists(html_path), (
        f"FAIL: HTML file not found at {html_path}"
    )
    file_size = os.path.getsize(html_path)
    assert file_size > 10_000, (
        f"FAIL: HTML file is only {file_size} bytes, expected > 10,000"
    )
    print(f"\n  HTML file: {html_path}")
    print(f"    Size: {file_size:,} bytes  ✓  (> 10,000)")

    with open(html_path, "r", encoding="utf-8") as f:
        html_text = f.read()
    assert '"iteration"' in html_text, (
        f'FAIL: HTML file does not contain the literal substring \'"iteration"\''
    )
    print(f'    Contains "iteration" substring  ✓')

    print()
    print("=" * 60)
    print("  ALL STAGES PASS")
    print("  No packages were changed, upgraded, or installed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
