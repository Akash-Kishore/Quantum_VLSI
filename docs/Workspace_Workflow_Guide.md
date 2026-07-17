# Workspace & Workflow Guide
### Grover's Algorithm for VLSI Design & Test — Project Environment

This document explains exactly where everything lives, how to access it, how to make changes, and how the Windows/WSL split works day-to-day.

---

## 1. The Big Picture

| Layer | What it is | Where it lives |
|---|---|---|
| **Your code & files** | Python scripts, notebooks, docs | `C:\Quantum_VLSI` (Windows drive) |
| **Python + Qiskit + CUDA runtime** | The actual execution environment | Inside WSL2 Ubuntu (`grover-vlsi` conda env) |
| **GPU driver** | NVIDIA driver enabling CUDA | Windows host only (never installed inside WSL) |
| **CUDA Toolkit 11.8** | Compiler + libraries qiskit-aer-gpu needs | Inside WSL2 Ubuntu |
| **Git repository** | Version control | `C:\Quantum_VLSI\.git`, pushed to GitHub (`Akash-Kishore/Quantum_VLSI`) |

**Key idea**: your files physically sit on the Windows C: drive so you can browse/edit them like normal Windows files, but they are *executed* using the Linux-side Python environment (WSL), because that's the only place the GPU-enabled Qiskit packages and CUDA toolkit are installed.

---

## 2. Exact File Structure

```
C:\Quantum_VLSI\
├── shared_framework\          # Grover core: oracle wrapper, diffusion operator,
│                               # iteration-count calculator, measurement helpers
│   └── tests\
│       └── gpu_test.py        # GPU verification script (already working)
├── module1_placement\         # Cell placement oracle + tests (Phase 3)
├── module2_atpg\               # Full-adder + fault-injection oracle + tests (Phase 2)
├── notebooks\                  # Jupyter notebooks for exploration/plots
├── docs\                       # Project documentation (docx/md files)
├── requirements.txt             # pip-freeze of the exact installed packages
├── environment.yml              # conda environment export (full reproducibility)
├── .gitignore
└── README.md
```

Everything above already exists except `module1_placement/` and `module2_atpg/` content, which will be filled in during Phases 2 and 3.

---

## 3. How to Access This Folder

### From Windows (File Explorer, VS Code, drag-and-drop, etc.)
Just navigate normally:
```
C:\Quantum_VLSI
```
It behaves exactly like any other Windows folder — because it is one.

### From WSL (to run code, use Git, activate the conda env)
Open your WSL Ubuntu terminal and go to:
```bash
cd /mnt/c/Quantum_VLSI
```
`/mnt/c/` is how WSL sees your Windows `C:\` drive. Everything under `C:\Quantum_VLSI` is reachable at `/mnt/c/Quantum_VLSI` from the Linux side.

### Quick Shortcut (already set up)
You added this alias to `~/.bashrc` earlier:
```bash
alias qvlsi='cd /mnt/c/Quantum_VLSI && conda activate grover-vlsi'
```
So opening a new WSL terminal and typing:
```bash
qvlsi
```
instantly puts you in the right folder **and** activates the right conda environment in one step.

---

## 4. How to Make Changes to the Code

You have two comfortable options — pick whichever fits the moment.

### Option A: Edit directly in Windows, run from WSL
1. Open/edit files normally in Windows — Notepad, VS Code (as a plain Windows app), or any editor.
2. Save the file as usual (Ctrl+S).
3. Switch to your WSL terminal (already `cd`'d into `/mnt/c/Quantum_VLSI` via `qvlsi`).
4. Run it:
   ```bash
   python module2_atpg/atpg_oracle.py
   ```
Changes save instantly to the Windows-side file, and WSL sees them immediately since it's reading the same physical file through the `/mnt/c/` mount — no syncing or copying needed.

### Option B: Edit and run entirely from inside WSL, using VS Code's Remote-WSL connection (recommended if you install VS Code)
1. Install the **"WSL"** extension in VS Code (on the Windows side).
2. In your WSL terminal:
   ```bash
   cd /mnt/c/Quantum_VLSI
   code .
   ```
3. This opens VS Code connected directly to WSL — you get integrated terminal, IntelliSense, and debugging all pointed at the `grover-vlsi` conda environment automatically, while still editing the same files under `C:\Quantum_VLSI`.

Either option edits the **same files** — there's no duplication or separate copies to keep in sync. The Windows path and the WSL path are two doors into the same room.

---

## 5. Running Jupyter Notebooks

From WSL:
```bash
qvlsi                      # cd + activate environment
jupyter notebook
```
This starts the Jupyter server inside WSL, but it automatically opens in your normal Windows web browser (via `localhost` port-forwarding, which WSL2 handles automatically). Notebooks you create/save will appear in:
```
C:\Quantum_VLSI\notebooks\
```
and are immediately visible/double-clickable from Windows too.

---

## 6. Running Python Scripts

Always run scripts through WSL (never through a Windows-side Python, since the GPU-enabled Qiskit packages only exist in the WSL conda environment):

```bash
qvlsi
python shared_framework/tests/gpu_test.py
```

---

## 7. Saving Your Work

There is nothing special to do — saving a file in Windows (Ctrl+S in any editor) **is** saving it for WSL too, since they're the same file on disk. There's no "sync," "upload," or "transfer" step. The only thing that has its own separate save/commit step is **Git** (see below) and the **conda environment** itself (which lives inside WSL's own Linux filesystem, not under `C:\Quantum_VLSI`, and doesn't need "saving" — it's just installed).

---

## 8. Git & GitHub Workflow

Git operations should be run from **WSL**, from inside `/mnt/c/Quantum_VLSI`:

```bash
qvlsi
git status                 # see what's changed
git add .                  # stage changes
git commit -m "Description of what changed"
git push                   # push to GitHub (Akash-Kishore/Quantum_VLSI)
```

To get the latest version (e.g., if you ever work from a second machine):
```bash
git pull
```

**Performance note**: Git operations on `/mnt/c/...` are slightly slower than they would be on a pure Linux filesystem, due to the WSL/Windows filesystem boundary. For a project this size (small Python files, notebooks), this is not noticeable in practice.

---

## 9. Reproducing This Environment on Another Machine (or After a Reset)

If you ever need to recreate the exact environment (new machine, reinstalled WSL, etc.):

```bash
conda env create -f environment.yml
conda activate grover-vlsi
```

Or, if you only want the pip packages on top of an existing Python 3.10:
```bash
pip install -r requirements.txt
```

Both files (`environment.yml`, `requirements.txt`) already live in `C:\Quantum_VLSI` and are committed to GitHub, so this is fully reproducible from the repo alone.

---

## 10. Quick Reference Card

| I want to... | Do this |
|---|---|
| Open the project folder in Windows | Navigate to `C:\Quantum_VLSI` |
| Open the project folder in WSL | `qvlsi` (or `cd /mnt/c/Quantum_VLSI`) |
| Edit a file | Edit it normally in Windows, or via VS Code Remote-WSL |
| Run a script | `qvlsi` then `python path/to/script.py` |
| Run Jupyter | `qvlsi` then `jupyter notebook` |
| Save my work | Just Ctrl+S — no extra step needed |
| Commit to Git | `qvlsi` then `git add . && git commit -m "..."` |
| Push to GitHub | `git push` |
| Pull latest from GitHub | `git pull` |
| Recreate the environment elsewhere | `conda env create -f environment.yml` |
| Check GPU is working | `python shared_framework/tests/gpu_test.py` |

---

## 11. Things to Never Do

- ❌ Don't install an NVIDIA driver *inside* WSL — the driver lives on Windows only.
- ❌ Don't try to run the project's Python scripts using a Windows-native Python install — `qiskit-aer-gpu-cu11` is Linux-only; it will not work outside WSL.
- ❌ Don't edit `environment.yml` or `requirements.txt` by hand unless you know exactly what you're changing — regenerate them with `conda env export` / `pip freeze` instead.
- ❌ Don't create a second copy of the project folder inside WSL's own filesystem (e.g., `~/Quantum_VLSI`) — this would create two diverging copies. Keep the single source of truth at `C:\Quantum_VLSI`.
