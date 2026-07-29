"""
Test Viewer Data — Module 2 ATPG
==================================

Three-stage test for the Module 2 viewer data generator.

Stage 1: Detecting-set consistency (no simulation).
Stage 2: Analytic sanity check at k=0 (deterministic math).
Stage 3: Full pipeline smoke test (runs actual frame generation).

No pytest — plain ``assert`` in ``main()``, matching every other test
file in this project.

Usage::

    python module2_atpg/viewer/tests/test_viewer_data.py
"""

from __future__ import annotations

import os
import sys

# ── Ensure project root is on sys.path ───────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from module2_atpg.viewer.generate_module2_viewer import (
    DETECTING_INDICES,
    N_INPUT_STATES,
    index_to_bitstring,
    index_to_label,
    generate_frames,
    build_html,
)


def main() -> None:
    """Run all viewer data tests."""

    # ==================================================================
    # STAGE 1: Detecting-set consistency (no simulation)
    # ==================================================================
    print("=" * 60)
    print("  STAGE 1: Detecting-Set Consistency")
    print("=" * 60)

    # The two detecting indices must decode to A=1, B=1 with both
    # values of Cin.
    assert DETECTING_INDICES == {3, 7}, (
        f"FAIL: DETECTING_INDICES = {DETECTING_INDICES}, expected {{3, 7}}"
    )
    print(f"  DETECTING_INDICES = {DETECTING_INDICES}  ✓")

    # Index 3: bit0(A)=1, bit1(B)=1, bit2(Cin)=0
    label_3 = index_to_label(3)
    assert label_3 == "A=1,B=1,Cin=0", (
        f"FAIL: index_to_label(3) = '{label_3}', expected 'A=1,B=1,Cin=0'"
    )
    print(f"  index_to_label(3) = '{label_3}'  ✓")

    # Index 7: bit0(A)=1, bit1(B)=1, bit2(Cin)=1
    label_7 = index_to_label(7)
    assert label_7 == "A=1,B=1,Cin=1", (
        f"FAIL: index_to_label(7) = '{label_7}', expected 'A=1,B=1,Cin=1'"
    )
    print(f"  index_to_label(7) = '{label_7}'  ✓")

    # Cross-check Qiskit-convention bitstrings against the
    # already-established MARKED_RAW = {"011", "111"} from
    # module2_atpg/tests/test_atpg.py.
    bs_3 = index_to_bitstring(3)
    bs_7 = index_to_bitstring(7)
    assert bs_3 == "011", (
        f"FAIL: index_to_bitstring(3) = '{bs_3}', expected '011'"
    )
    assert bs_7 == "111", (
        f"FAIL: index_to_bitstring(7) = '{bs_7}', expected '111'"
    )
    bitstring_set = {bs_3, bs_7}
    expected_marked_raw = {"011", "111"}
    assert bitstring_set == expected_marked_raw, (
        f"FAIL: detecting bitstrings = {bitstring_set}, "
        f"expected {expected_marked_raw} (from test_atpg.py MARKED_RAW)"
    )
    print(f"  Detecting bitstrings = {bitstring_set}  ✓  (matches MARKED_RAW)")

    # Verify both have A=1, B=1 (the fault-detecting condition)
    for idx in DETECTING_INDICES:
        a = (idx >> 0) & 1
        b = (idx >> 1) & 1
        assert a == 1 and b == 1, (
            f"FAIL: index {idx} decodes to A={a},B={b} — "
            f"expected A=1,B=1 for fault detection"
        )
    print("  All detecting states have A=1, B=1  ✓")

    print("  STAGE 1: PASS ✓\n")

    # ==================================================================
    # STAGE 2: Analytic sanity check at k=0
    # ==================================================================
    print("=" * 60)
    print("  STAGE 2: Analytic Sanity Check (k=0)")
    print("=" * 60)

    # At k=0, uniform superposition over 8 states.
    # Every prob = 1/8 = 0.125.
    # success_probability = 2/8 = 0.25 (25%, the random-guess baseline).
    expected_uniform_prob = 1.0 / N_INPUT_STATES  # 0.125
    expected_success_prob_k0 = 2.0 / N_INPUT_STATES  # 0.25

    print(f"  Expected per-state probability at k=0: {expected_uniform_prob}")
    print(f"  Expected success_probability at k=0:   {expected_success_prob_k0}")
    print("  (Will be verified against actual frame 0 in Stage 3)")
    print("  STAGE 2: SETUP COMPLETE ✓\n")

    # ==================================================================
    # STAGE 3: Full pipeline smoke test
    # ==================================================================
    print("=" * 60)
    print("  STAGE 3: Full Pipeline Smoke Test")
    print("=" * 60)

    print("  Generating all 7 frames...")
    frames = generate_frames()

    # ── Check frame count ─────────────────────────────────────────────
    assert len(frames) == 7, (
        f"FAIL: len(frames) = {len(frames)}, expected 7"
    )
    print(f"  len(frames) = {len(frames)}  ✓")

    # ── Frame 0: analytic verification (Stage 2 values) ──────────────
    f0 = frames[0]
    print(f"\n  Frame 0 (k=0):")
    print(f"    success_probability = {f0['success_probability']:.10f}")

    # Check success probability at k=0.
    actual_sp0 = f0["success_probability"]
    assert abs(actual_sp0 - expected_success_prob_k0) < 1e-9, (
        f"FAIL: Frame 0 success_probability = {actual_sp0}, "
        f"expected {expected_success_prob_k0} "
        f"(diff = {abs(actual_sp0 - expected_success_prob_k0)})"
    )
    print(f"    success_probability ≈ {expected_success_prob_k0} (2/8)  ✓")

    # Check all 8 per-state probabilities at k=0.
    for state in f0["states"]:
        actual_p = state["probability"]
        assert abs(actual_p - expected_uniform_prob) < 1e-9, (
            f"FAIL: Frame 0 state {state['bitstring']} "
            f"probability = {actual_p}, expected {expected_uniform_prob}"
        )
    print(f"    All 8 per-state probabilities ≈ 0.125 (1/8)  ✓")

    # ── Frame 1: first Grover optimum ─────────────────────────────────
    f1 = frames[1]
    print(f"\n  Frame 1 (k=1):")
    print(f"    success_probability = {f1['success_probability']:.10f}")
    assert f1["success_probability"] > 0.99, (
        f"FAIL: Frame 1 success_probability = {f1['success_probability']}, "
        f"expected > 0.99 (first peak)"
    )
    print(f"    success_probability > 0.99  ✓  (first peak)")

    # ── Frame 4: second peak from periodicity ─────────────────────────
    f4 = frames[4]
    print(f"\n  Frame 4 (k=4):")
    print(f"    success_probability = {f4['success_probability']:.10f}")
    # The second peak: with θ = 30°, sin²((2·4+1)·30°) = sin²(270°) = 1.
    assert f4["success_probability"] > 0.99, (
        f"FAIL: Frame 4 success_probability = {f4['success_probability']}, "
        f"expected > 0.99 (second peak)"
    )
    print(f"    success_probability > 0.99  ✓  (second peak)")

    # ── Print all frame summaries ─────────────────────────────────────
    print(f"\n  All frames:")
    for frame in frames:
        k = frame["iteration"]
        sp = frame["success_probability"]
        print(f"    k={k}: success_probability = {sp:.10f} ({sp*100:.4f}%)")

    # ── Check HTML file exists and has content ────────────────────────
    viewer_dir = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))
    html_path = os.path.join(viewer_dir, "module2_viewer.html")

    # Generate the HTML file if it doesn't exist yet.
    if not os.path.exists(html_path):
        html_content = build_html(frames)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n  (Generated HTML file for validation)")

    assert os.path.exists(html_path), (
        f"FAIL: HTML file not found at {html_path}"
    )
    file_size = os.path.getsize(html_path)
    assert file_size > 5_000, (
        f"FAIL: HTML file is only {file_size} bytes, expected > 5,000"
    )
    print(f"\n  HTML file: {html_path}")
    print(f"    Size: {file_size:,} bytes  ✓  (> 5,000)")

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
