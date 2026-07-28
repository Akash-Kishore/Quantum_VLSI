# Module 1 — Placement: Implementation Walkthrough

## Files Created

| File | Purpose |
|---|---|
| [\_\_init\_\_.py](file:///mnt/c/Quantum_VLSI/module1_placement/__init__.py) | Package init |
| [classical_baseline.py](file:///mnt/c/Quantum_VLSI/module1_placement/classical_baseline.py) | Brute-force enumeration via `itertools.permutations(range(7), 4)` → 840 placements |
| [encoding.py](file:///mnt/c/Quantum_VLSI/module1_placement/encoding.py) | Bitstring decode (little-endian, LSB=q3k) and validity/collision checking |
| [placement_oracle.py](file:///mnt/c/Quantum_VLSI/module1_placement/placement_oracle.py) | 25-qubit phase-flip oracle (collision + validity constraints) |
| [tests/\_\_init\_\_.py](file:///mnt/c/Quantum_VLSI/module1_placement/tests/__init__.py) | Test package init |
| [tests/test_encoding.py](file:///mnt/c/Quantum_VLSI/module1_placement/tests/test_encoding.py) | Stage 1: Pure Python decode/validate tests |
| [tests/test_oracle_sanity.py](file:///mnt/c/Quantum_VLSI/module1_placement/tests/test_oracle_sanity.py) | Stage 2: Exact statevector oracle verification (3 cases) |
| [tests/test_placement.py](file:///mnt/c/Quantum_VLSI/module1_placement/tests/test_placement.py) | Stage 3: Full Grover circuit, 1000 shots |

## Test Results — All 3 Stages PASS

### Stage 1: PASS
```
decode('000000000000') = (0, 0, 0, 0)  ✓
decode('011110000101') = (5, 0, 6, 3)  ✓
decode('111000000000') = (0, 0, 0, 7)  ✓
is_valid_collision_free((0, 1, 2, 3)) = True  ✓
is_valid_collision_free((0, 0, 1, 2)) = False  ✓
is_valid_collision_free((0, 1, 2, 7)) = False  ✓
```

### Stage 2: PASS
- Oracle decomposed gate count: **261**
- Used `AerSimulator(method="statevector")` with `save_statevector()` for compiled simulation

| Case | Meaning | sv.data[index] | Result |
|---|---|---|---|
| A | (0,1,2,3) valid | -1+0j | Marked ✓ |
| B | (0,0,1,2) collision | +1+0j | Unmarked ✓ |
| C | (0,1,2,7) invalid | +1+0j | Unmarked ✓ |

- Zero residual probability in all cases → ancilla uncomputation correct

### Stage 3: PASS
```
count_valid_placements() = 840  ✓
optimal_iterations(12, 840)             = 2
optimal_iterations(12, 840, exact=True) = 1
Oracle circuit: 25 qubits, 259 gates
```

| Iterations | Valid Probability | Distinct Valid Placements |
|---|---|---|
| 1 (exact optimum) | **97.4%** (>90% threshold) ✓ | 580 |
| 2 (approx formula) | **50.2%** (comparison only) | 392 |

> [!NOTE]
> The overshoot at `iterations=2` (50.2% vs 97.4% at `iterations=1`) confirms the same pattern as Phases 1 and 2 — expected behavior, not a bug.

## Architecture Confirmation

- `build_placement_oracle().num_qubits = 25` — no ancilla drift from `mcx`
- Grover loop: **manual** (Module 2 precedent) — 12-qubit diffusion composed onto qubits [0..11] of the 25-qubit circuit
- `shared_framework/` was **NOT modified**
- **No packages changed, upgraded, or installed**
- **No pytest or any other new dependency introduced**
- All tests are plain scripts with `assert` + `main()`, run via `python path/to/test.py`
