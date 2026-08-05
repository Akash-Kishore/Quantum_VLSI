"""
Module 1 — QAOA Placement Arm
===============================

One-hot QUBO formulation for placing 4 logic cells onto 7 physical sites,
targeting a QAOA solver (circuit implementation deferred to Stage 2).

Encoding: Path A one-hot — each cell gets 7 binary variables (one per
site 0–6), 28 total.  x[cell][site] = 1 means "cell is placed at site."
"""
