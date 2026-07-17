# Changes Log
### Everything decided since the original Phase 1 handoff documents

This document exists so nothing discussed in the (very long) follow-up conversation gets lost or silently re-derived incorrectly in a fresh chat. It is organized chronologically, in the order decisions were actually made, with the reasoning behind each one. Nothing here should be treated as "obvious" or skippable — several of these points correct a real bug that would otherwise have shipped silently.

---

## 1. Phase 1 prompt was generated (no change in status since)

The Phase 1 Antigravity/Opus 4.6 prompt (shared Grover framework: `oracle.py`, `diffusion.py`, `grover_utils.py`, `visualization.py`, `test_trivial_oracle.py`) was written in full and handed over for pasting into Antigravity IDE.

**Status as of this log: unconfirmed.** No generated code was ever pasted back into this chat for review. The new chat should open by explicitly checking: has Phase 1 actually been run in Antigravity, did `test_trivial_oracle.py` pass, and was it committed to GitHub per the original "Definition of Phase 1 Done" checklist? Do not assume Phase 1 is complete just because the prompt was issued.

---

## 2. Qubit counts across phases were clarified (no scope change)

Confirmed, per the original requirements doc: Phase 1's validation is 2 qubits (trivial `|11⟩` case); Module 1 was originally scoped at "4-6 qubits"; Module 2 was originally scoped at "5-8 qubits including ancillas." This was just a restatement of the existing docs, not a change.

---

## 3. Module 1 encoding scheme was worked out

Established the general encoding rule used for the rest of the conversation: **each logic cell gets `⌈log₂(number of sites)⌉` qubits**, representing that cell's assigned site as a binary-encoded index — not one-hot encoding, which would cost far more qubits.

Total qubit cost for Module 1 = `(number of cells) × ⌈log₂(number of sites)⌉`.

---

## 4. The pairwise no-collision check was identified as O(cells²), not O(cells)

No-collision has to be checked **pair by pair** ("is cell A on the same site as cell B?" for every pair), not per-cell. Number of pairs = `cells × (cells−1) / 2`. This grows quadratically even though the qubit count only grows linearly with cell count — meaning circuit complexity (comparator sub-circuits, ancillas) scales faster than the qubit budget suggests. This was true at every cell count discussed and remains true at the final 4-cell design.

---

## 5. GPU capacity check — 4×4 case (superseded, kept for reference)

Before the site count was finalized, checked whether the RTX 3050 could handle a hypothetical 4 cells × 4 sites instance: 8 data qubits, ~14-15 qubits total with ancillas, statevector memory in the hundreds-of-KB range — trivially within the GPU's 6GB VRAM (by a factor of roughly 10 million). Also noted: at this qubit scale, GPU may show **no speed advantage over CPU** (kernel-launch/data-copy overhead can outweigh the tiny simulation cost) — this is expected and not a sign of anything broken. This exact instance (4×4) was never built; it was superseded by the 4×7 decision below, but the capacity conclusion (trivially runnable, GPU parity-or-worse-than-CPU is normal at this scale) still applies to the final design.

---

## 6. Scope decision #1 (superseded): 4 cells / 5 sites

First concrete scope change from the original "3-4 cells, small number of sites": **decided to move to 4 logic cells and 5 placement sites.**

This surfaced the first version of a critical correctness issue (see §7) and prompted a request for more headroom, which led to re-evaluating the site count (§9-10).

---

## 7. ⚠️ Critical correctness issue identified: non-power-of-2 site counts need an explicit validity check

**This is the single most important technical catch in this whole log — do not lose it.**

When the number of sites isn't a power of 2, the qubit register per cell (sized to `⌈log₂(sites)⌉` bits) can represent more values than there are real sites. Example: 5 sites needs 3 qubits, but 3 qubits represent 8 values (0–7) — codes 5, 6, 7 don't correspond to any physical site.

**The bug this creates:** if the oracle only checks for collisions (no two cells share the same code) and never checks that each code is actually a *valid* site, then a placement where some cell holds an invalid code (e.g. code 6) will pass the no-collision check anyway — because an invalid code never happens to equal another cell's valid code. The oracle would wrongly mark that placement as a success.

**The fix:** every oracle for a non-power-of-2 site count needs an explicit **per-cell validity sub-check** (each cell's code is a legal site index), ANDed together with the no-collision checks, before the final phase kick. This applies regardless of which site count is chosen (5, 6, or 7) — it only disappears entirely at 8 sites (a clean power of 2).

---

## 8. UI need identified as new project scope

Realized that visualizing "which cell went to which site" is not covered anywhere in the original project documents — it's a genuinely new deliverable, not something already implied by the existing Phase 1-5 plan.

---

## 9. UI approach decided: standalone HTML/JS viewer (not ipywidgets, not Jupyter-only matplotlib)

Compared three options for building the UI:

- **Static matplotlib images** — fits the pinned stack perfectly, but not "live."
- **Interactive Jupyter widgets (ipywidgets)** — live and Python-native, but:
  - Requires adding a **new dependency** (`ipywidgets`, plus its JS-side counterpart `jupyterlab-widgets`), which directly triggers the project's version-lock barrier clause.
  - Prone to a well-documented, still-current class of bugs where the Python package and the JS widget-manager fall out of sync, producing a blank "Error displaying widget" with no useful traceback.
  - The community's standard fix for that bug is "just upgrade ipywidgets" — which is exactly the move the project's barrier clause is designed to prevent.
  - Confirmed via live web search that this version-sync fragility is still a live issue as of recent (2025–2026) troubleshooting writeups, not an outdated concern.
  - **Finickiness rating given: ~4-5/10 in general use, ~6-7/10 specifically in this project's WSL2 + tightly-version-locked-conda-env context.**
- **Standalone HTML/JS viewer** — doesn't touch the Python stack at all, fully portable (opens in any browser, no conda/WSL/Jupyter needed to view it), and a much more natural fit for drawing a "chip layout" grid than for slider/form-style widgets.

**Decision: standalone HTML/JS viewer.** Zero interaction with the barrier clause, and better suited to the actual visual being requested (a grid of sites with cells placed in them) than either alternative.

**A middle-ground alternative was also raised and is worth remembering:** matplotlib's own `FuncAnimation`, embedded directly in the notebook, gets a "live/moving" feel using only already-pinned packages (no ipywidgets) — the tradeoff is losing manual scrub-to-any-iteration control in favor of an auto-playing animation. This wasn't chosen, but it's a legitimate fallback if the HTML/JS approach ever hits a wall.

---

## 10. Scope decision #2 (final): 4 cells / 7 sites

Wanting more headroom than 5 sites to properly demonstrate "efficient mapping in available space," a comparison was run across 5, 6, 7, and 8 sites (holding qubits/cell at 3 throughout):

| Sites | Invalid codes/cell | Validity check complexity | Valid placements (M) | Search space (N) | M/N ratio | Optimal iterations (approx. formula) |
|---|---|---|---|---|---|---|
| 5 | 3 (codes 5,6,7) | OR of two 2-bit ANDs | 120 | 4096 | 2.9% | ~5 |
| 6 | 2 (codes 6,7) | OR of two 2-bit ANDs | 360 | 4096 | 8.8% | ~3 |
| **7** | **1 (code 7 only)** | **single 3-input AND** | **840** | **4096** | **20.5%** | **~2** |
| 8 | 0 (perfect fit) | none needed | 1680 | 4096 | 41% | ~1 |

**7 sites was chosen** as the best balance: the validity check is the cheapest non-trivial one on the table (7 = `111` in binary, so "invalid" is just a single 3-input AND of all three bits — no OR-of-ANDs needed like at 5 or 6 sites), it gives real visual headroom (3 empty sites out of 7, vs. 4 cells), and it keeps the search meaningfully "hard" (only 1-in-5 placements valid by chance) — unlike 8 sites, where 41% of random guesses are already valid and Grover's advantage becomes much less visually dramatic.

**Final locked-in Module 1 dimensions: 4 logic cells, 7 placement sites, 3 qubits per cell, 12 total data qubits.**

---

## 11. Clarified what "kind" of logic cells Module 1 actually represents

The 3 qubits per cell encode **only which site the cell is on** — a location — never the cell's function. Module 1 does not simulate any gate-level logic (truth tables, inputs/outputs) for any cell; that's exclusively Module 2's job (the full adder). This means any real standard-cell type can be used purely as a cosmetic/narrative label with zero effect on the actual circuit — e.g. INV, NAND2, AND2, OR2, XOR2, BUF, DFF. A cell's "type" only becomes functionally relevant later if/when adjacency constraints are added (since a real reason two cells need to be adjacent would typically come from one cell's output feeding another's input in an actual netlist) — but that reasoning lives in how you choose which cell *pairs* require adjacency, not in the qubit encoding itself.

---

## 12. Viewer richness decided: full cell×site probability heatmap ("rich" version)

Two viewer designs were compared:

- **Simple** — animate just the single most-likely decoded placement plus an overall success-probability number.
- **Rich** — export, for every Grover iteration, a full 4×7 matrix of marginal probabilities: for each cell, its probability of being on each of the 7 sites, marginalized over what the other 3 cells are doing. Rendered as a heatmap that visibly starts near-uniform (superposition, no information) and sharpens into four clear rows (one lit-up site per cell) as iterations proceed.

**Decision: the rich version.** It actually shows Grover's amplitude convergence happening, rather than just revealing an answer — considered core to the point of the demo, not a nice-to-have.

---

## 13. Viewer technical design, worked out in detail

- **Export format:** one JSON "frame" per iteration count (0 through some max, e.g. 2-3× the computed optimum), each containing: iteration number, overall success probability, the top ~8-10 measured bitstrings decoded into per-cell site assignments (with a valid/invalid flag each), and the 4×7 marginal probability matrix described above.
- **⚠️ Correctness gotcha, easy to get wrong:** Qiskit returns measured bitstrings in **little-endian order — qubit 0 is the rightmost character of the string**, not the leftmost. Slicing a cell's 3-bit segment out of the raw bitstring naively (left-to-right, assuming qubit 0 is first) will scramble or reverse every cell's decoded site assignment. **Recommend a standalone, isolated unit test for the bitstring→per-cell-site decode function** (known bitstring in, known site-list out) before wiring it into anything else, so this bug is caught in isolation rather than being confused with an oracle bug later.
- **Delivery format:** a single self-contained `.html` file with the JSON frame data **embedded directly inline** in a `<script>` block at export time — not fetched separately at runtime. This sidesteps browser `file://` CORS restrictions entirely and keeps the file double-click-openable with zero server setup, on any machine, with nothing installed.
- **Playback mechanics:** plain JavaScript only — a shared `currentFrame` index, a Play/Pause button driving a `setInterval` timer that advances the index, and a range-slider ("scrubber") input bound to the same index so any iteration can be jumped to directly (dragging the slider pauses auto-play).
- **Animation feel:** CSS `transition` set on the heatmap cells' `background-color`/`opacity` so frame-to-frame changes animate smoothly instead of snapping — no canvas library, no JS animation framework, no new dependency of any kind (Python or JS).

---

## 14. ⚠️ New technical consideration surfaced while preparing this handoff (not discussed live in chat — flagging now)

The project's `optimal_iterations` formula (as specified in the Phase 1 prompt) is: `k = round((π/4) × √(N/M))`. This is a **small-angle approximation** of the true optimal iteration count, valid when `M/N` is small. It was exact-by-coincidence for the Phase 1 trivial case (`M/N = 25%` happened to land on a clean integer).

At Module 1's final dimensions (`M=840, N=4096, M/N ≈ 20.5%`), this ratio is **not small enough for the approximation to stay tight.** Working the exact math (using the true relation `success probability after k iterations = sin²((2k+1)θ)`, where `θ = arcsin(√(M/N))` exactly, rather than approximating `θ ≈ √(M/N)`):

- The approximate formula gives **k = 2** (rounds `1.734` up).
- The exact formula's true optimum is actually **k = 1** — which gives a success probability of roughly **97.5%**, versus roughly **50.5%** at k = 2.

**This is a real discrepancy, not a rounding nitpick** — using the approximate formula as-is for Module 1 will still work (50.5% is far better than the 20.5% baseline of guessing), but it leaves a large amount of achievable success probability on the table compared to using the exact formula. **This needs an explicit decision in the new chat**, not a silent fix:

- **Option A:** leave `optimal_iterations` exactly as specified in Phase 1 (don't touch previously-agreed shared-framework code), accept ~50.5% success at k=2 for Module 1, and note this in the write-up as an interesting real-world limitation of the standard approximation.
- **Option B:** add an exact-formula mode (using `arcsin`, not `sqrt`) either as a new function or an optional parameter on `optimal_iterations`, and use it for Module 1 to get the true ~97.5% success rate at k=1.

Neither option touches any pinned package or version — this is pure algorithm logic, not a dependency change — but it does change previously-agreed shared-framework behavior, which is exactly the kind of thing that should be decided explicitly rather than assumed.

---

## 15. Adjacency constraint status: still open, not decided

The original project documents specify **two** Module 1 constraints: no-collision *and* adjacency ("cells with a required connection must be placed in adjacent sites"). Everything worked out in this conversation covers no-collision + validity only. Adjacency was never revisited for the final 4-cell/7-site design — specifically, **no site-adjacency topology has been chosen** (line of 7 sites? 2D grid? ring?) and **no specific pairs of the 4 cells have been declared as requiring adjacency.** This needs to be decided before an adjacency-aware oracle can be built. Recommend treating it the same way the project already treats Phase 5 (the pipeline stretch goal) — build and verify the no-collision + validity version first as the guaranteed deliverable, then add adjacency as a scoped follow-up once that's solid.

---

## 16. Why a fresh chat now

This conversation has grown long enough that continuing to build on top of it risks model drift/hallucination on the accumulated details above. Two companion documents were generated alongside this log — an updated `Project_Handoff_Summary_and_Module1_Instructions.md` and an updated `Antigravity_Handoff_Prompt_Module1.md` — so a new chat can pick up with the full, correct context and immediately proceed to drafting the Module 1 Antigravity build prompt, without re-deriving any of the above from scratch.
