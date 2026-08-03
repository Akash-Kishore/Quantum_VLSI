"""
Test suite for the generalized fault family — Stage 1 (pure Python).
====================================================================

Validates every one of the 11 enumerated fault sites by checking that
the algebraically derived M matches the brute-force count, then
performs a cross-check against the existing trusted Phase 2 code
(AB stuck-at-0 detecting set).

Uses plain ``assert`` in ``main()`` — no pytest, per project convention.

Package-lock barrier (repeated per project convention):

==========  ============================
Package     Version — DO NOT CHANGE
==========  ============================
Python      3.10
qiskit      1.2.4
qiskit-aer  0.15.1 (gpu-cu11)
numpy       1.26.4
matplotlib  3.8.4
CUDA (WSL2) 11.8
==========  ============================

No Qiskit import appears anywhere in this file.
No scipy import appears anywhere in this file.
"""

from __future__ import annotations

import sys
import os

# Ensure the project root is on sys.path so that module2_atpg is importable
# regardless of the working directory.
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from module2_atpg.generalized_faults.fault_family import (
    FaultSite,
    count_detecting_inputs,
    enumerate_fault_sites,
    evaluate_faulty,
    evaluate_full_adder,
    get_detecting_inputs,
)


def main() -> None:
    """Run all Stage-1 fault-family validation tests."""

    sites = enumerate_fault_sites()

    # ------------------------------------------------------------------
    # 1. Confirm total count is 11
    # ------------------------------------------------------------------
    assert len(sites) == 11, f"Expected 11 fault sites, got {len(sites)}"
    print(f"Total enumerated fault sites: {len(sites)}")
    print()

    # ------------------------------------------------------------------
    # 2. For every fault site: derived M must match brute-force M
    # ------------------------------------------------------------------
    header = (
        f"{'Fault Class':15s}  {'ID':6s}  {'SA':5s}  "
        f"{'Derived M':>9s}  {'Brute M':>7s}  {'Result':6s}"
    )
    print(header)
    print("-" * len(header))

    all_pass = True
    for site in sites:
        brute_m = count_detecting_inputs(site)
        match = brute_m == site.derived_m
        status = "PASS" if match else "FAIL"
        if not match:
            all_pass = False
        sa_str = f"SA{site.stuck_at}" if site.stuck_at is not None else "none"
        print(
            f"{site.fault_class:15s}  {site.identifier:6s}  {sa_str:5s}  "
            f"{site.derived_m:9d}  {brute_m:7d}  {status:6s}"
        )
        assert match, (
            f"MISMATCH for {site.fault_class} {site.identifier} SA{site.stuck_at}: "
            f"derived_m={site.derived_m}, brute_force={brute_m}"
        )

    print()
    print(f"All 11 fault sites: {'ALL PASS' if all_pass else 'SOME FAILED'}")
    print()

    # ------------------------------------------------------------------
    # 3. Explicit check: control fault site has M = 0
    # ------------------------------------------------------------------
    control_sites = [s for s in sites if s.fault_class == "control"]
    assert len(control_sites) == 1, "Expected exactly 1 control fault site"
    control = control_sites[0]
    assert count_detecting_inputs(control) == 0, (
        f"Control fault site should have M=0, got {count_detecting_inputs(control)}"
    )
    print("Control fault site M=0 check: PASS")

    # ------------------------------------------------------------------
    # 4. Cross-check: AB stuck-at-0 detecting set matches Phase 2
    # ------------------------------------------------------------------
    # The existing Phase 2 module2_atpg code establishes that the AB
    # stuck-at-0 fault is detected by exactly {(1,1,0), (1,1,1)}.
    ab_sa0_sites = [
        s for s in sites
        if s.fault_class == "product_term"
        and s.identifier == "AB"
        and s.stuck_at == 0
    ]
    assert len(ab_sa0_sites) == 1, "Expected exactly 1 AB-SA0 fault site"
    ab_sa0 = ab_sa0_sites[0]

    detecting_set = set(get_detecting_inputs(ab_sa0))
    expected_set = {(1, 1, 0), (1, 1, 1)}

    assert detecting_set == expected_set, (
        f"AB stuck-at-0 detecting set mismatch:\n"
        f"  got:      {detecting_set}\n"
        f"  expected: {expected_set}"
    )
    print(
        f"AB stuck-at-0 cross-check vs Phase 2: PASS  "
        f"(detecting set = {sorted(detecting_set)})"
    )
    print()

    # ------------------------------------------------------------------
    # 5. Verify evaluate_full_adder is self-consistent
    # ------------------------------------------------------------------
    # Quick sanity: Cout should be the majority function, Sum the XOR.
    for a in range(2):
        for b in range(2):
            for cin in range(2):
                cout, sum_ = evaluate_full_adder(a, b, cin)
                expected_sum = a ^ b ^ cin
                expected_cout = (a & b) ^ (b & cin) ^ (a & cin)
                assert cout == expected_cout, (
                    f"Cout mismatch at ({a},{b},{cin}): "
                    f"got {cout}, expected {expected_cout}"
                )
                assert sum_ == expected_sum, (
                    f"Sum mismatch at ({a},{b},{cin}): "
                    f"got {sum_}, expected {expected_sum}"
                )
    print("evaluate_full_adder sanity check: PASS")

    # ------------------------------------------------------------------
    # 6. Verify fault-free control produces identical outputs everywhere
    # ------------------------------------------------------------------
    for a in range(2):
        for b in range(2):
            for cin in range(2):
                good = evaluate_full_adder(a, b, cin)
                faulty = evaluate_faulty(control, a, b, cin)
                assert good == faulty, (
                    f"Control fault should match fault-free at ({a},{b},{cin}): "
                    f"good={good}, faulty={faulty}"
                )
    print("Control fault identity check: PASS")

    print()
    print("=" * 50)
    print("ALL TESTS PASSED")
    print("=" * 50)


if __name__ == "__main__":
    main()
