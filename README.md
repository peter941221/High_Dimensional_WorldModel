# HyperDream: Higher-Dimensional World Models for Cross-Dimensional Transfer

Research codebase for training world models in N-dimensional physics environments and studying transfer to 3D tasks.

## Quick Start

```bash
pip install -r requirements.txt
pytest -q
python experiments/run_baseline.py
```

## Scope

- N-dimensional physics simulator
- RL environments and replay buffer
- World models (MLP -> GRU -> RSSM)
- Cross-dimensional transfer and robustness experiments

## Phase Roadmap (P0 -> P6)

- P0: `experiments/run_p0_baseline_freeze.py` for multi-seed release baseline/freeze.
- P1: state semantics lock + checkpoint compatibility guard.
- P2: conservative domain randomization with warmup/scope/stage multipliers.
- P3: `PhysicsResidualWorldModel` (physics prior + learnable residual).
- P4: `experiments/run_curriculum.py` for threshold-driven easy->medium->hard curriculum.
- P5: `experiments/aggregate_report.py` for cross-run KPI aggregation.
- P6: `envs/high_fidelity_proxy.py` + `experiments/run_hifi_migration.py` for proxy hi-fi migration.

## Resume Experiments

Each training script now supports checkpoint-based resume with `--run-id` and `--resume`.

```bash
python experiments/run_baseline.py --run-id my_run --epochs 5
python experiments/run_baseline.py --run-id my_run --resume --epochs 10
```

Checkpoint files include:
- `*_latest.pt`: last epoch snapshot
- `*_best.pt`: best world-model-loss snapshot
- `*_epochXXXX.pt`: periodic archives (controlled by `--save-every` and `--keep-last`)

## Train Until Success Threshold

Use iterative rounds and stop automatically once success-rate reaches target:

```bash
python experiments/run_until_success.py --dim 3 --difficulty easy --target-success 0.70
```

## Colab Auto Push

- `colab_autorun.py` now supports pushing result artifacts to GitHub branch automatically.
- Use `--push-results-to-github` and provide token via environment variable (default: `GITHUB_TOKEN`).
- For Colab Secrets workflow, set `--token-secret-name <your_secret_key>` (for example: `GITHUB_T`).
- GitHub-only pipeline is supported (no Drive dependency required).

## Kaggle Batch Runner

Use `kaggle_job_manager.py` for asynchronous Kaggle workflow:

```bash
python kaggle_job_manager.py run --owner <your_kaggle_username>
```

It supports:
- kernel bundle preparation
- code dataset packaging/versioning (for network-independent source loading)
- push to Kaggle
- status polling
- output download

## P0 Baseline Freeze

Use `experiments/run_p0_baseline_freeze.py` to run baseline/transfer/robustness across multiple seeds and generate a single summary report (`mean/std`) for migration-safe baselines.

```bash
python experiments/run_p0_baseline_freeze.py \
  --run-id-prefix p0_freeze_5seed \
  --seeds 11 22 33 44 55 \
  --baseline-epochs 8 \
  --transfer-pretrain-epochs 6 \
  --transfer-finetune-epochs 6 \
  --robustness-episodes 120
```

## P2 Domain Randomization

`PushBallNDEnv` now supports per-episode physics randomization (`domain_randomization`, `domain_rand_scale`) to reduce sim-gap and improve robustness. Experiment runners expose this via `--domain-rand --domain-rand-scale`.
Use `--domain-rand-profile conservative` and `--domain-rand-warmup-episodes <N>` for safer staged randomization.
Use `--domain-rand-warmup-epochs <N>` for epoch-linked warmup and transfer multipliers (`--domain-rand-source-multiplier`, `--domain-rand-finetune-multiplier`) to make finetune-stage randomization weaker.

Current migration-safe recommendation:

```bash
python experiments/run_p0_baseline_freeze.py \
  --run-id-prefix p2_v2_5seed \
  --seeds 11 22 33 44 55 \
  --domain-rand \
  --domain-rand-scope robustness_only \
  --robustness-domain-rand-difficulties medium_hard \
  --domain-rand-scale 0.10 \
  --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 200 \
  --domain-rand-warmup-epochs 8 \
  --domain-rand-source-multiplier 1.0 \
  --domain-rand-finetune-multiplier 0.5 \
  --baseline-epochs 8 \
  --transfer-pretrain-epochs 6 \
  --transfer-finetune-epochs 6 \
  --robustness-episodes 120
```

## P3/P4/P5/P6 Additions

- P3: `PhysicsResidualWorldModel` (physics prior + learnable residual).
- P4: `experiments/run_curriculum.py` for threshold-driven easy->medium->hard curriculum.
- P5: `experiments/aggregate_report.py` for multi-run KPI summary reports.
- P6: `envs/high_fidelity_proxy.py` + `experiments/run_hifi_migration.py` for proxy high-fidelity migration evaluation.

## Release Freeze + Significance (5 Seeds)

Release freeze should use:

```bash
pytest -q .
```

5-seed paired significance report:

```bash
python experiments/significance_report.py \
  --a-prefix p0_freeze_5seed \
  --b-prefix p2_v2_5seed \
  --report-name release_significance_p0_vs_p2v2_5seed
```

Outputs:
- `report/release_significance_p0_vs_p2v2_5seed.json`
- `report/release_significance_p0_vs_p2v2_5seed.md`

Latest 5-seed result snapshot (paired exact sign-flip, alpha=0.05):
- No KPI crossed `p < 0.05` with `n=5`.
- `robust_medium`: `+0.0500`, `p=0.0625` (trend up, not significant yet).
- `robust_hard`: `-0.0167`, `p=0.0625` (small drop, not significant yet).
- Baseline and transfer KPIs were unchanged between the two prefixes.

Interpretation rule:
- If `p < 0.05`: treat as statistically significant difference for this paired setup.
- If `p >= 0.05`: treat as "insufficient evidence" (do not claim real improvement/regression yet).
