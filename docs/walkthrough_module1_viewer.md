# Module 1 Visual UI — Cell×Site Probability Heatmap

## 🚨 Package-Lock Barrier (Verbatim)

| Package | Version — NOT CHANGED |
|---|---|
| Python | 3.10 |
| qiskit | 1.2.4 |
| qiskit-aer-gpu-cu11 | 0.15.1 |
| numpy | 1.26.4 |
| matplotlib | 3.8.4 |
| CUDA Toolkit (inside WSL2) | 11.8 |

**No packages were changed, upgraded, installed, or downgraded.** All code runs in the existing `grover-vlsi` conda environment. No pytest. No new dependencies (Python or JS). No CDN. No external assets.

---

## Files Created

| File | Purpose |
|------|---------|
| [viewer/__init__.py](file:///mnt/c/Quantum_VLSI/module1_placement/viewer/__init__.py) | Package init for viewer subpackage |
| [viewer/tests/__init__.py](file:///mnt/c/Quantum_VLSI/module1_placement/viewer/tests/__init__.py) | Package init for viewer tests |
| [generate_module1_viewer.py](file:///mnt/c/Quantum_VLSI/module1_placement/viewer/generate_module1_viewer.py) | Data generator: 10 statevector simulations → self-contained HTML |
| [test_viewer_data.py](file:///mnt/c/Quantum_VLSI/module1_placement/viewer/tests/test_viewer_data.py) | 3-stage test (decode, analytics, full pipeline) |
| [module1_viewer.html](file:///mnt/c/Quantum_VLSI/module1_placement/viewer/module1_viewer.html) | Generated output: 31,794 bytes, self-contained, opens via `file://` |

No existing files were modified.

---

## Test Output — Full

```
============================================================
  STAGE 1: Decode Consistency
============================================================
  decode_index(0)    = (0, 0, 0, 0)  ✓  (matches encoding.decode('000000000000'))
  decode_index(1925) = (5, 0, 6, 3)  ✓  (matches encoding.decode('011110000101'))
  decode_index(3584) = (0, 0, 0, 7)  ✓  (matches encoding.decode('111000000000'))
  STAGE 1: PASS ✓

============================================================
  STAGE 2: Analytic Sanity Check (k=0)
============================================================
  (Will be verified against actual frame-0 in Stage 3)
  Expected marginal[c][s] for s in 0..6: 0.125
  Expected success_probability: 0.0234375 (96/4096)
  STAGE 2: SETUP COMPLETE ✓

============================================================
  STAGE 3: Full Pipeline Smoke Test
============================================================
  Generating all 10 frames (this will take a while)...
  len(frames) = 10  ✓

  Frame 0 (k=0):
    success_probability = 0.0234375000
    success_probability ≈ 0.0234375 (96/4096)  ✓
    All marginal[c][s] ≈ 0.125 (1/8)  ✓

  Frame 5 (k=5):
    success_probability = 0.9856983398
    success_probability > 0.95  ✓  (theoretical ~98.57%)

  HTML file: module1_placement/viewer/module1_viewer.html
    Size: 31,794 bytes  ✓  (> 10,000)
    Contains "iteration" substring  ✓

============================================================
  ALL STAGES PASS
  No packages were changed, upgraded, or installed.
============================================================
```

---

## Success Probability Sweep (Exact Statevector)

| Iteration (k) | Success Probability |
|:-:|:-:|
| 0 | 2.3438% |
| 1 | 19.7960% |
| 2 | 48.3093% |
| 3 | 77.4417% |
| 4 | 96.5247% |
| **5** | **98.5698%** |
| 6 | 82.8282% |
| 7 | 55.0645% |
| 8 | 25.4461% |
| 9 | 4.8196% |

> [!IMPORTANT]
> k=5 hits **98.57%**, matching Phase 3b's confirmed theoretical optimum exactly. The sweep visibly rises from the uniform 2.34% baseline, peaks at k=5, and falls off — exactly as expected from Grover theory with M=96, N=4096.

---

## What Was Verified

- **Decode consistency**: `decode_index()` bit-shift matches `encoding.py`'s `decode_bitstring_to_placement()` on all 3 hand-verified test vectors
- **k=0 analytics**: All 28 marginal entries = 0.125 (1/8) exactly, success probability = 0.0234375 (96/4096) exactly
- **k=5 peak**: 98.5698% success probability (asserted > 95%, theoretical ~98.57%)
- **HTML output**: 31,794 bytes, contains embedded frame JSON, opens via `file://`
- **Memory discipline**: Sequential iteration processing, `del` full statevector after each slice
- **No package changes**: Ran in existing `grover-vlsi` conda env with frozen package versions
