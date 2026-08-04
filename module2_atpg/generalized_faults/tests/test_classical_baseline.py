"""
Test suite for classical ATPG baselines — Phase 7
====================================================

Validates exhaustive search, random sampling, and expected-query
computations against ``fault_family.py``'s ground truth for all 11
fault sites.

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

# Ensure project root is on sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from module2_atpg.generalized_faults.fault_family import (
    enumerate_fault_sites,
    get_detecting_inputs,
)
from module2_atpg.generalized_faults.classical_baseline import (
    ExhaustiveResult,
    TrialStats,
    exhaustive_search,
    expected_queries_bruteforce,
    expected_queries_formula,
    run_random_trials,
)


N_TRIALS = 2000
SEED = 42


def main() -> None:
    """Run all classical baseline validation tests."""

    sites = enumerate_fault_sites()
    assert len(sites) == 11

    # ==================================================================
    # 1. Exhaustive correctness, all 11 sites
    # ==================================================================
    print("=" * 78)
    print("1. Exhaustive search correctness (all 11 fault sites)")
    print("=" * 78)
    print()

    for site in sites:
        detecting = get_detecting_inputs(site)
        detecting_set = set(detecting)
        result = exhaustive_search(site)
        sa_str = f"SA{site.stuck_at}" if site.stuck_at is not None else "none"
        label = f"{site.fault_class} {site.identifier} {sa_str}"

        if len(detecting_set) > 0:
            assert result.found, (
                f"{label}: expected found=True (M={site.derived_m}), got False"
            )
            assert result.first_detecting_input in detecting_set, (
                f"{label}: first_detecting_input "
                f"{result.first_detecting_input} not in detecting set "
                f"{detecting_set}"
            )
        else:
            assert not result.found, (
                f"{label}: expected found=False (M=0), got True"
            )
            assert result.queries_used == 8, (
                f"{label}: control site queries_used={result.queries_used}, "
                f"expected 8"
            )

    print("  All 11 exhaustive searches: PASS")
    print()

    # ==================================================================
    # 2. Brute-force vs. closed-form cross-check, all 11 sites
    # ==================================================================
    print("=" * 78)
    print("2. Expected queries: brute-force vs. closed-form (all 11 sites)")
    print("=" * 78)
    print()

    header = (
        f"  {'Fault Class':15s}  {'ID':6s}  {'SA':5s}  {'M':>3s}  "
        f"{'Formula':>10s}  {'BruteForce':>10s}  {'Match':>6s}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))

    for site in sites:
        formula_val = expected_queries_formula(8, site.derived_m)
        brute_val = expected_queries_bruteforce(site)
        sa_str = f"SA{site.stuck_at}" if site.stuck_at is not None else "none"

        if site.derived_m == 0:
            assert formula_val is None, (
                f"Formula should return None for M=0, got {formula_val}"
            )
            assert brute_val is None, (
                f"Bruteforce should return None for M=0, got {brute_val}"
            )
            print(
                f"  {site.fault_class:15s}  {site.identifier:6s}  "
                f"{sa_str:5s}  {site.derived_m:3d}  "
                f"{'None':>10s}  {'None':>10s}  {'PASS':>6s}"
            )
        else:
            assert formula_val is not None
            assert brute_val is not None
            assert abs(formula_val - brute_val) < 1e-9, (
                f"Mismatch for {site.fault_class} {site.identifier} "
                f"{sa_str}: formula={formula_val}, brute={brute_val}"
            )
            print(
                f"  {site.fault_class:15s}  {site.identifier:6s}  "
                f"{sa_str:5s}  {site.derived_m:3d}  "
                f"{formula_val:10.4f}  {brute_val:10.4f}  {'PASS':>6s}"
            )

    print()
    print("  All 11 cross-checks: PASS")
    print()

    # ==================================================================
    # 3. Random-trial statistics, all 11 sites
    # ==================================================================
    print("=" * 78)
    print(f"3. Random sampling trials (n_trials={N_TRIALS}, seed={SEED})")
    print("=" * 78)
    print()

    for site in sites:
        stats = run_random_trials(site, n_trials=N_TRIALS, seed=SEED)
        sa_str = f"SA{site.stuck_at}" if site.stuck_at is not None else "none"
        label = f"{site.fault_class} {site.identifier} {sa_str}"

        if site.derived_m > 0:
            assert stats.success_rate == 1.0, (
                f"{label}: success_rate={stats.success_rate}, expected 1.0 "
                f"(M={site.derived_m} > 0, sampling without replacement)"
            )

            expected = expected_queries_bruteforce(site)
            assert expected is not None
            # Monte Carlo tolerance: mean_queries within 15% of exact
            # expected value. This is a provisional tolerance, not
            # rigorous — formal statistical methodology is deferred to
            # Phase 12 per the project roadmap.
            tolerance = 0.15
            assert abs(stats.mean_queries - expected) / expected <= tolerance, (
                f"{label}: mean_queries={stats.mean_queries:.4f}, "
                f"expected={expected:.4f}, "
                f"deviation={abs(stats.mean_queries - expected) / expected:.4f} "
                f"> {tolerance}"
            )
        else:
            assert stats.success_rate == 0.0, (
                f"{label}: success_rate={stats.success_rate}, expected 0.0"
            )
            assert stats.min_queries == 8, (
                f"{label}: min_queries={stats.min_queries}, expected 8"
            )
            assert stats.max_queries == 8, (
                f"{label}: max_queries={stats.max_queries}, expected 8"
            )

    print("  All 11 random-trial checks: PASS")
    print()

    # ==================================================================
    # 4a. Summary table
    # ==================================================================
    print("=" * 78)
    print("SUMMARY TABLE: Classical ATPG Baselines (all 11 fault sites)")
    print("=" * 78)
    print()

    hdr = (
        f"{'Fault Class':15s}  {'ID':6s}  {'SA':5s}  {'M':>3s}  "
        f"{'Exh.Found':>9s}  {'Exh.Q':>5s}  "
        f"{'Rnd.SR':>6s}  {'Rnd.MeanQ':>9s}  {'E[Q] exact':>10s}"
    )
    print(hdr)
    print("-" * len(hdr))

    for site in sites:
        exh = exhaustive_search(site)
        stats = run_random_trials(site, n_trials=N_TRIALS, seed=SEED)
        eq_brute = expected_queries_bruteforce(site)
        sa_str = f"SA{site.stuck_at}" if site.stuck_at is not None else "none"

        found_str = "YES" if exh.found else "NO"
        eq_str = f"{eq_brute:.4f}" if eq_brute is not None else "N/A"

        print(
            f"{site.fault_class:15s}  {site.identifier:6s}  {sa_str:5s}  "
            f"{site.derived_m:3d}  "
            f"{found_str:>9s}  {exh.queries_used:5d}  "
            f"{stats.success_rate:6.2f}  {stats.mean_queries:9.4f}  "
            f"{eq_str:>10s}"
        )

    print()

    # ==================================================================
    # 4b. M=0 failure signature section
    # ==================================================================
    print("=" * 78)
    print("M=0 FAILURE SIGNATURE — Classical vs. Quantum")
    print("=" * 78)
    print()

    control_site = [s for s in sites if s.fault_class == "control"][0]
    exh_control = exhaustive_search(control_site)
    stats_control = run_random_trials(
        control_site, n_trials=N_TRIALS, seed=SEED
    )

    print("CLASSICAL EXHAUSTIVE SEARCH:")
    print(f"  Result: NO DETECTING INPUT EXISTS (certified negative)")
    print(f"  Queries used: {exh_control.queries_used}/8 (all inputs tested)")
    print(f"  The exhaustive search's 8/8 query count is itself the")
    print(f"  unambiguous failure certificate: by testing every possible")
    print(f"  input and finding no disagreement between fault-free and")
    print(f"  faulty circuits, the classical method certifies that no")
    print(f"  detecting input exists.")
    print()
    print("CLASSICAL RANDOM SAMPLING:")
    print(f"  Result: NO DETECTING INPUT EXISTS in {N_TRIALS}/{N_TRIALS} trials")
    print(f"  Queries used: exactly 8 in every trial "
          f"(min={stats_control.min_queries}, max={stats_control.max_queries})")
    print(f"  Success rate: {stats_control.success_rate:.1%}")
    print(f"  The random sampling search produces the same certified")
    print(f"  negative in 100% of trials, always after exhausting all 8")
    print(f"  inputs. The sampling-without-replacement guarantee ensures")
    print(f"  this is exact, not probabilistic.")
    print()
    print("GROVER (quantum, from Phase 6 Stage 3 Part B — restated here,")
    print("        not recomputed):")
    print(f"  The Grover oracle for the control fault site is the identity")
    print(f"  (no phase is ever flipped), making the uniform superposition")
    print(f"  a fixed point of the Grover iteration. The measured")
    print(f"  distribution is uniform across all 8 outcomes (~12.5% each)")
    print(f"  at every iteration count k=0–8, with P(detect)=0.0 at all k.")
    print()
    print(f"  CRITICAL CONTRAST: While both classical methods provide an")
    print(f"  explicit, unambiguous signal that no detecting input exists")
    print(f"  (the 8/8 exhaustion certificate), the Grover output at M=0")
    print(f"  is a uniform distribution — indistinguishable, from the")
    print(f"  output alone, from a poorly-tuned Grover search where a")
    print(f"  detecting input DOES exist but the iteration count is wrong.")
    print(f"  A practitioner without prior knowledge of the M=0 boundary")
    print(f"  has no way to tell, from the Grover measurement outcomes")
    print(f"  alone, that no detecting input exists at all. This is the")
    print(f"  fundamental observability gap at the feasibility boundary.")
    print()

    # ==================================================================
    # Final summary
    # ==================================================================
    print("=" * 78)
    print("ALL TESTS PASSED")
    print("No packages were changed, upgraded, or installed.")
    print("=" * 78)


if __name__ == "__main__":
    main()
