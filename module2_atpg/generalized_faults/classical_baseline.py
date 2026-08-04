"""
Classical ATPG Search Baselines — Pure Python
===============================================

Implements classical search strategies for finding fault-detecting inputs
in the 1-bit full adder, for direct comparison against Grover-based
quantum search (Phase 6).

Strategies:

1. **Exhaustive search** — deterministic, canonical-order walk.
2. **Random sampling search** — uniformly random permutation walk
   (without replacement).
3. **Expected queries (closed-form)** — order-statistics formula.
4. **Expected queries (brute-force)** — exact average over all 8!
   permutations.
5. **Random trial runner** — Monte Carlo statistics over many
   random-sampling runs.

All functions build on ``fault_family.py``'s ground truth
(``evaluate_full_adder``, ``evaluate_faulty``, ``get_detecting_inputs``)
and do NOT reimplement fault logic.

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

import itertools
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from module2_atpg.generalized_faults.fault_family import (
    FaultSite,
    evaluate_faulty,
    evaluate_full_adder,
    get_detecting_inputs,
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExhaustiveResult:
    """Result of a single exhaustive or random-sampling search.

    Attributes
    ----------
    found : bool
        Whether a detecting input was found.
    first_detecting_input : Optional[Tuple[int, int, int]]
        The first detecting ``(a, b, cin)`` found, or ``None`` if not found.
    queries_used : int
        Number of inputs tested before either finding a detecting input
        (1-indexed position of the hit) or exhausting the space (exactly
        N=8 when no detecting input exists).
    """

    found: bool
    first_detecting_input: Optional[Tuple[int, int, int]]
    queries_used: int


@dataclass(frozen=True)
class TrialStats:
    """Aggregate statistics from multiple random-sampling trials.

    Attributes
    ----------
    mean_queries : float
        Mean queries used across all trials.
    median_queries : float
        Median queries used across all trials.
    min_queries : int
        Minimum queries used in any single trial.
    max_queries : int
        Maximum queries used in any single trial.
    success_rate : float
        Fraction of trials where a detecting input was found.
    """

    mean_queries: float
    median_queries: float
    min_queries: int
    max_queries: int
    success_rate: float


# ---------------------------------------------------------------------------
# Helper: is this input detecting for this fault site?
# ---------------------------------------------------------------------------

def _is_detecting(fault_site: FaultSite, a: int, b: int, cin: int) -> bool:
    """Check whether ``(a, b, cin)`` detects the given fault.

    Parameters
    ----------
    fault_site : FaultSite
        The fault to test.
    a, b, cin : int
        Single-bit inputs.

    Returns
    -------
    bool
        ``True`` if the faulty output differs from the fault-free output
        on the relevant output(s) for this fault class.
    """
    good_cout, good_sum = evaluate_full_adder(a, b, cin)
    bad_cout, bad_sum = evaluate_faulty(fault_site, a, b, cin)

    if fault_site.fault_class == "product_term":
        return bad_cout != good_cout
    elif fault_site.fault_class == "xor_chain":
        return bad_sum != good_sum
    else:  # control
        return False


# ---------------------------------------------------------------------------
# 1. Exhaustive search
# ---------------------------------------------------------------------------

def exhaustive_search(fault_site: FaultSite) -> ExhaustiveResult:
    """Walk all 8 inputs in canonical order; stop at first detecting input.

    Canonical order: ``itertools.product(range(2), repeat=3)`` as
    ``(a, b, cin)``, matching ``fault_family.py``'s own iteration order.

    Parameters
    ----------
    fault_site : FaultSite
        The fault to search for.

    Returns
    -------
    ExhaustiveResult
        ``found=True`` with the first hit and its 1-indexed position,
        or ``found=False`` with ``queries_used=8`` (every input tested,
        none detected — this is a certified negative, not just failure
        to find).
    """
    for position, (a, b, cin) in enumerate(
        itertools.product(range(2), repeat=3), start=1
    ):
        if _is_detecting(fault_site, a, b, cin):
            return ExhaustiveResult(
                found=True,
                first_detecting_input=(a, b, cin),
                queries_used=position,
            )

    return ExhaustiveResult(
        found=False,
        first_detecting_input=None,
        queries_used=8,
    )


# ---------------------------------------------------------------------------
# 2. Random sampling search (without replacement)
# ---------------------------------------------------------------------------

def random_sampling_search(
    fault_site: FaultSite,
    rng: random.Random,
) -> ExhaustiveResult:
    """Walk a random permutation of the 8 inputs; stop at first detecting input.

    Sampling is **without replacement** (``rng.sample(all_inputs, 8)``),
    so termination within 8 draws is guaranteed regardless of M.

    Parameters
    ----------
    fault_site : FaultSite
        The fault to search for.
    rng : random.Random
        Random number generator instance for reproducibility.

    Returns
    -------
    ExhaustiveResult
        Same semantics as ``exhaustive_search``.
    """
    all_inputs: List[Tuple[int, int, int]] = list(
        itertools.product(range(2), repeat=3)
    )
    permuted = rng.sample(all_inputs, len(all_inputs))

    for position, (a, b, cin) in enumerate(permuted, start=1):
        if _is_detecting(fault_site, a, b, cin):
            return ExhaustiveResult(
                found=True,
                first_detecting_input=(a, b, cin),
                queries_used=position,
            )

    return ExhaustiveResult(
        found=False,
        first_detecting_input=None,
        queries_used=8,
    )


# ---------------------------------------------------------------------------
# 3. Expected queries — closed-form formula
# ---------------------------------------------------------------------------

def expected_queries_formula(n_total: int, n_marked: int) -> Optional[float]:
    """Closed-form expected number of queries to find the first detecting input.

    Returns ``(N + 1) / (M + 1)`` — the expected 1-indexed position of
    the earliest marked item in a uniformly random permutation of N items
    containing M marked items.

    **Derivation:**

    Consider the N items in a uniformly random order.  Split the M marked
    items and N−M unmarked items.  The expected rank (1-indexed position)
    of the earliest marked item among N uniformly randomly ordered items,
    when there are M marked items, is (N+1)/(M+1).  This is a standard
    order-statistics result: by symmetry, the M marked items partition the
    N+1 "gaps" (before the first, between each pair, after the last
    unmarked-item boundary) evenly in expectation, giving expected rank
    (N+1)/(M+1).

    Returns ``None`` if ``n_marked == 0`` — the formula's extrapolation
    to M=0 is meaningless (there is no "expected position of a first
    success" when success never happens).

    Parameters
    ----------
    n_total : int
        Total number of items (N).
    n_marked : int
        Number of marked (detecting) items (M).

    Returns
    -------
    Optional[float]
        Expected number of queries, or ``None`` if ``n_marked == 0``.
    """
    if n_marked == 0:
        return None
    return (n_total + 1) / (n_marked + 1)


# ---------------------------------------------------------------------------
# 4. Expected queries — brute-force over all permutations
# ---------------------------------------------------------------------------

def expected_queries_bruteforce(fault_site: FaultSite) -> Optional[float]:
    """Exact expected queries via exhaustive permutation enumeration.

    Enumerates all 8! = 40320 permutations of the 8 inputs, finds the
    1-indexed position of the first detecting input in each, and
    averages.  This is an independent verification of
    ``expected_queries_formula``, not a wrapper around it.

    Returns ``None`` if ``fault_site.derived_m == 0`` (no detecting input
    exists in any permutation).

    Parameters
    ----------
    fault_site : FaultSite
        The fault to compute expected queries for.

    Returns
    -------
    Optional[float]
        Exact expected number of queries, or ``None`` for M=0.
    """
    if fault_site.derived_m == 0:
        return None

    all_inputs: List[Tuple[int, int, int]] = list(
        itertools.product(range(2), repeat=3)
    )
    detecting_set = set(get_detecting_inputs(fault_site))

    total_position = 0
    n_perms = 0

    for perm in itertools.permutations(all_inputs):
        n_perms += 1
        for position, inp in enumerate(perm, start=1):
            if inp in detecting_set:
                total_position += position
                break

    assert n_perms == 40320, f"Expected 40320 permutations, got {n_perms}"
    return total_position / n_perms


# ---------------------------------------------------------------------------
# 5. Random trial runner
# ---------------------------------------------------------------------------

def run_random_trials(
    fault_site: FaultSite,
    n_trials: int = 2000,
    seed: int = 42,
) -> TrialStats:
    """Run multiple random-sampling trials and collect statistics.

    Each trial uses an independent ``random.Random`` instance seeded with
    ``seed + trial_index`` to ensure trial-to-trial independence without
    cross-trial correlation.

    Parameters
    ----------
    fault_site : FaultSite
        The fault to search for.
    n_trials : int
        Number of independent trials.  Default: 2000.
    seed : int
        Base seed for reproducibility.  Default: 42.

    Returns
    -------
    TrialStats
        Aggregate statistics across all trials.
    """
    queries_list: List[int] = []
    successes = 0

    for i in range(n_trials):
        rng = random.Random(seed + i)
        result = random_sampling_search(fault_site, rng)
        queries_list.append(result.queries_used)
        if result.found:
            successes += 1

    queries_list.sort()
    n = len(queries_list)
    mean_q = sum(queries_list) / n

    # Median: average of two middle values for even n
    if n % 2 == 0:
        median_q = (queries_list[n // 2 - 1] + queries_list[n // 2]) / 2.0
    else:
        median_q = float(queries_list[n // 2])

    return TrialStats(
        mean_queries=mean_q,
        median_queries=median_q,
        min_queries=queries_list[0],
        max_queries=queries_list[-1],
        success_rate=successes / n_trials,
    )
