# Session Summary & Next Steps
### Grover's Algorithm for VLSI Design & Test — Phase 1 Complete, Phase 2 Starting

This document captures everything decided and completed since the last handoff (the original `Changes_Log.md` / `Project_Handoff_Summary_and_Phase1_Instructions.md` / `Antigravity_Handoff_Prompt.md` trio), so a new chat can pick up with full context.

---

## 1. Phase 1 — Shared Grover Framework: COMPLETE ✅

The Phase 1 prompt was reissued from scratch (the prior attempt was unconfirmed — no code had ever been pasted back for review). This time it was built, reviewed file-by-file, tested, and pushed.

### 1.1 Files built (all reviewed and confirmed correct)

| File | Status |
|---|---|
| `shared_framework/__init__.py` | ✅ Reviewed — correct re-exports |
| `shared_framework/oracle.py` | ✅ Reviewed — `bitstring_oracle` (MCZ-based) + `constraint_oracle` (compute→Z-kickback→uncompute) both correct |
| `shared_framework/diffusion.py` | ✅ Reviewed — standard H→X→MCZ→X→H, correct |
| `shared_framework/grover_utils.py` | ✅ Reviewed — `optimal_iterations` (approx + exact modes), `build_grover_circuit`, `run_circuit` (GPU→CPU fallback), all correct |
| `shared_framework/visualization.py` | ✅ Reviewed — `plot_counts`, `sweep_iterations`, both correct, uses `Agg` backend (file-only output, no display) |
| `shared_framework/tests/__init__.py` | ✅ Trivial package init |
| `shared_framework/tests/test_trivial_oracle.py` | ✅ Reviewed, one bug found and fixed (see below) |

### 1.2 Bug found and fixed: `optimal_iterations` test assertion

**The bug was in the original project documentation, not in any code written this session.** The original docs (`Project_Handoff_Summary_and_Phase1_Instructions.md`) claimed the 2-qubit/1-marked trivial case "should come out to 1 iteration" via the approximate formula. This is mathematically wrong:

- `round((π/4)·√(4/1)) = round(1.5708) = 2`, not 1.
- The agent initially tried to "fix" this by changing `round` to `floor` in `grover_utils.py` itself — **this was correctly rejected**, since `floor` is not the standard Grover convention and would have silently broken correctness for other qubit/marked-state combinations later.
- **Correct fix, applied**: left `grover_utils.py` untouched (`round`, not `floor`); fixed the test assertion instead to expect the formula's real, correct output (`k_approx == 2`), while keeping the `exact=True` mode assertion at `k_exact == 1` (the true analytical optimum). Test 3 now runs the actual Grover circuit at `iterations=1` explicitly (the true optimum), not at `k_approx`.

This confirms `optimal_iterations`'s `exact=True` mode — added this session as a new optional parameter, not a replacement for the default — genuinely works correctly, which matters because the same approximate-formula-overshoots-by-one pattern will very likely recur at Module 1's real scale (see §3 in the prior Changes Log: N=4096, M=840, approximate gives k=2 at ~50.5% success, exact gives k=1 at ~97.5%).

### 1.3 Test results (live run, confirmed)

```
[TEST 1] optimal_iterations(2, 1)             = 2      PASS ✓
[TEST 2] optimal_iterations(2, 1, exact=True) = 1      PASS ✓
[TEST 3] Grover 1-iter counts: {'11': 1000}            PASS ✓  (100% success)
[TEST 4] Sweep: 0→0.265, 1→1.000, 2→0.268, 3→0.230     PASS ✓
```

The sweep plot (`shared_framework/tests/sweep_trivial_oracle.png`) was visually inspected and confirmed: clean single peak at iteration 1, correctly labeled axes, no rendering issues.

### 1.4 Git status

Committed and pushed to `github.com:Akash-Kishore/Quantum_VLSI.git`, branch `main`.

### 1.5 Package/version compliance

Confirmed clean throughout — zero changes to `requirements.txt`, `environment.yml`, or any installed package version. All code uses Qiskit 1.x API only (`transpile()` + `sim.run()`), no Qiskit 2.x primitives.

---

## 2. Antigravity IDE / WSL Workflow — Resolved

Separately from the project work itself, the following environment/tooling issues were worked through and resolved:

- Antigravity IDE's WSL remote connection: use Ctrl+Shift+P → `Remote-WSL: Connect to WSL`, then Open Folder using the **Linux path** `/mnt/c/Quantum_VLSI` (not the Windows `C:\Quantum_VLSI` path or a `\\wsl.localhost\...` path).
- Two separate install folders exist on this machine: `Antigravity` (older, no usable CLI) and `Antigravity IDE` (current, has a working CLI). The correct executable for CLI/symlink purposes is:
  ```
  /mnt/c/Users/akash/AppData/Local/Programs/Antigravity IDE/bin/antigravity-ide
  ```
- An `agy` shortcut was set up via symlink to that path so `agy .` can launch Antigravity directly from a WSL terminal already in the project directory. Confirmed working.
- Confirmed working file structure (screenshot-verified): `docs/`, `module1_placement/` (empty), `module2_atpg/` (empty), `notebooks/`, `shared_framework/` (fully populated per §1.1), `.gitignore`, `environment.yml`, `README.md`, `requirements.txt` all present as expected.

---

## 3. Phase 2 — Module 2 (ATPG): Design Decided, Prompt Not Yet Written

This is the current in-progress item. Design decisions locked in this session:

### 3.1 Fault model chosen: AB-term Toffoli, stuck-at-0

The full adder's carry-out is `Cout = AB ⊕ BC ⊕ AC` (XOR-accumulated, since reversible circuits build multi-term Boolean functions via a chain of Toffolis feeding an accumulator qubit with CNOTs — not OR gates). **Chosen fault**: the Toffoli gate computing the `A·B` term is stuck-at-0 (its contribution never gets XORed into the Cout accumulator).

**⚠️ Correction made mid-session, worth flagging explicitly:** An initial pass reasoned about this fault using OR-logic intuition (`Cout = AB + BC + AC`) and concluded the fault would be masked at input `111` (only detected at `110`, i.e. M=1). This was wrong — a real reversible circuit XORs each term's contribution in, and XOR accumulation cannot mask a missing term the way OR can. The corrected analysis: **the fault is detected whenever the true AB product is 1**, i.e. whenever `A=1 AND B=1`, regardless of Cin. That's **two** inputs: `110` and `111`.

**Corrected fault-detection numbers: M=2 marked states out of N=8** (not M=1 as initially miscalculated).
- Approximate formula: `round((π/4)·√(8/2)) = round(1.5708) = 2` (same overshoot pattern as the Phase 1 trivial case — an intentional callback worth noting in the write-up).
- Exact formula: `k=1` gives **100% detection probability** (`sin²(90°) = 1.0`), vs. 25% random-guess baseline. Still a clean, strong demo (4× improvement), just not a literal single-solution case.

**This fault choice was picked over two alternatives** (fault directly on a primary output pin, or on the Sum XOR chain) specifically because both alternatives are detected by ~50% of inputs at random — barely distinguishable from a coin flip, and a much weaker demonstration of Grover's quadratic speedup than the AB-term internal-gate fault.

### 3.2 Qubit budget: 6 total qubits

| Qubits | Purpose |
|---|---|
| 3 | Shared inputs: A, B, Cin |
| 1 | Fault-free circuit's Cout, computed into an ancilla |
| 1 | Faulty circuit's Cout, computed into a separate ancilla |
| 1 | Comparison/flag ancilla — XOR of the two Cout ancillas, flags exactly when fault-free and faulty outputs disagree |

**Sum is deliberately not computed at all** — since the chosen fault (AB-term stuck-at-0) never affects Sum, comparing Sum would add 2+ more ancillas for zero fault-detection benefit. This keeps the module comfortably within the original scoping doc's "5-8 qubits including ancillas" range for Module 2.

### 3.3 Not yet done

- The actual Antigravity/Opus 4.6 prompt for Phase 2 has **not yet been written or issued**. This is the next concrete step.
- No code for Module 2 exists yet — `module2_atpg/` is still empty.

---

## 4. Still Open From the Prior Session (Unchanged, Not Yet Addressed)

Carried forward from the original `Changes_Log.md`, still unresolved:

- **Module 1 adjacency constraint**: the second of Module 1's two required constraints (cells with a required connection must be placed in adjacent sites) is still completely undecided — no site-adjacency topology (line/grid/ring) chosen, no specific cell pairs declared as requiring adjacency. Per the original log's own recommendation, this should be scoped as a follow-up *after* the no-collision + validity version of Module 1 is built and verified, not before.
- **Module 1's `optimal_iterations(exact=True)` usage**: the *decision* to add and use the exact mode was made and implemented in Phase 1 (§1.2 above) — but Module 1 itself hasn't been built yet, so this is really "ready to use, not yet applied."

---

## 5. Recommended Next Steps, In Order

1. **Write and issue the Phase 2 Antigravity prompt** for Module 2 (ATPG), covering: the full-adder-as-reversible-circuit construction (fault-free version), the faulty version with the AB-term Toffoli stuck-at-0, the comparison oracle built via `constraint_oracle` from the shared framework, the 6-qubit budget from §3.2, and validation that Grover converges on `{110, 111}` at `iterations=1`.
2. Review the generated code the same way Phase 1 was reviewed — file by file, checking oracle/circuit correctness and package-lock compliance first.
3. Run the Module 2 validation test, confirm it detects exactly `{110, 111}` with high probability at k=1, and visually check any generated plot.
4. Commit and push Module 2.
5. Only then move to Phase 3 (Module 1 — Placement), where the adjacency-constraint decision (§4) will need to be made before that module's oracle can be finalized.
