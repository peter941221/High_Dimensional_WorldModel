# Technical Report

## Snapshot (2026-02-26)

This report summarizes the current MVP implementation status against `技术文档.md`.

## 1. Completed Scope

- N-dimensional physics engine implemented (`physics/engine.py`)
- Push-ball RL environment implemented (`envs/push_ball.py`)
- World models implemented: MLP / GRU / RSSM (`models/`)
- Training stack implemented: replay buffer, transfer utility, dream trainer (`training/`)
- Policy optimization upgraded to imagination-based actor-critic (actor + value + target value)
- Checkpoint/resume implemented for cross-session continuous training (model + optimizer + replay buffer + RNG + progress)
- Experiment runners implemented (`experiments/run_*.py`)
- Visualization pipeline implemented (`experiments/visualize.py`)

## 2. Validation Results

- Full test suite: `21 passed`
- Command: `pytest -q`

Key validated areas:
- Physics conservation/free-fall/determinism checks
- Environment shape/reward/reproducibility and easy solvability checks
- Model forward/gradient/prediction tests
- Buffer and transfer tests
- Trainer epoch smoke test
- Actor/critic parameter update regression test
- Checkpoint round-trip and replay-buffer round-trip tests
- Checkpoint rotation tests (`latest/best/archive retention`)

## 3. Experiment Outputs (Current MVP)

Generated files:
- `results/baseline.json`
- `results/transfer.json`
- `results/robustness.json`
- `results/ablation.json`
- `figures/*.png`

Observed metrics (quick-run settings):
- Baseline success: non-zero on low dimensions, sparse on higher dimensions
- Transfer success: low but measurable (`~0.05` in current quick settings)
- Robustness: easy has non-zero success; medium/hard currently near zero
- Ablation: all three models still near zero under short training budget

## 4. Gap Analysis vs Target Document

Partially complete:
- Acceptance criteria are represented in code/tests but not all thresholds match target strictness.
- Experiment protocol is runnable, but current training budget is intentionally short (smoke-scale), not publication-scale.

Not yet complete:
- Full-scale training schedule (multi-seed long-horizon runs)
- Statistical significance reporting with error bars over 5 seeds
- Robust high-performance policy training for medium/hard and high dimensions

## 5. Recommended Next Iteration

1. Increase training budget and seed count in experiment scripts.
2. Upgrade policy optimization to full actor-critic (or Dreamer-style value learning).
3. Add integration tests for checkpoint resume and long rollout stability.
4. Automate experiment orchestration + aggregated summary report.

## 6. Resume Workflow

Example:

```bash
python experiments/run_baseline.py --run-id my_run --epochs 5
python experiments/run_baseline.py --run-id my_run --resume --epochs 10
```

Result persistence:
- Per-run outputs: `results/<experiment>/<run_id>/*.json`
- Per-run checkpoints: `checkpoints/<experiment>/<run_id>/*.pt`
- Compatibility summary: `results/<experiment>.json`

Checkpoint retention controls:
- `--save-every N`: periodic archive cadence
- `--keep-last K`: max archived checkpoints retained per worker
