# HyperDream
### 🌌 Higher-Dimensional World Models for Cross-Dimensional Transfer

Train world models in N-dimensional physics, then transfer policies back to 3D tasks with reproducible, staged validation.

```text
Core Idea
├─ Learn in flexible N-D simulation
├─ Transfer structure across dimensions
└─ Validate robustness with reproducible seed-based reports
```

## ✨ Why This Repo

- 🎯 Build a research-grade playground for **world model + transfer** experiments.
- 🧪 Keep everything measurable via **multi-seed summaries** and **significance reports**.
- 🚚 Run locally or on Kaggle with one operational path (**no Colab dependency**).

## 🧱 System Map

```text
[Physics Engine (N-D)]
        |
        v
[PushBallNDEnv]
        |
        v
[World Model]
  |---- MLP
  |---- GRU
  |---- RSSM
  |---- Physics+Residual
        |
        v
[DreamTrainer + ReplayBuffer]
        |
        v
[Experiments]
  |---- baseline
  |---- transfer
  |---- ablation
  |---- robustness
  |---- curriculum
  |---- hifi_migration
```

## 🚦 Current Status

```text
Roadmap
├─ P0 Baseline Freeze: ✅
├─ P1 Semantic Interface Lock: ✅
├─ P2 Domain Randomization: ✅
├─ P3 Physics+Residual Model: ✅
├─ P4 Curriculum Runner: ✅
├─ P5 Aggregate Reporting: ✅
├─ P6 Hi-Fi Proxy Migration: ✅
└─ De-Colab + Kaggle Consistency: ✅
```

## 📊 Snapshot

### Release comparison (5 seeds, paired exact sign-flip)

| KPI | Delta (P2_v2 - P0) | p-value | Significant @0.05 |
| --- | ---: | ---: | --- |
| baseline_success_dim3 | 0.0000 | 1.0000 | No |
| baseline_success_dim4 | 0.0000 | 1.0000 | No |
| transfer_success_mean | 0.0000 | 1.0000 | No |
| transfer_gain_mean | 0.0000 | 1.0000 | No |
| robust_easy | 0.0000 | 1.0000 | No |
| robust_medium | +0.0500 | 0.0625 | No (trend up) |
| robust_hard | -0.0167 | 0.0625 | No |

Source: `report/release_significance_p0_vs_p2v2_5seed.md`

### Latest P0 freeze (9 seeds) summary mean

| KPI | Mean |
| --- | ---: |
| baseline_success_dim3 | 0.7306 |
| baseline_success_dim4 | 0.6556 |
| transfer_success_mean | 0.6301 |
| transfer_gain_mean | 0.0162 |
| robust_medium | 0.2417 |
| robust_hard | 0.1667 |

Source: `results/p0_freeze/p0_freeze_9seed/p0_summary.json`

## 🚀 Quick Start

```bash
pip install -r requirements.txt
pytest -q
python experiments/run_baseline.py
```

## 🔁 Repro Workflows

### 1) Baseline freeze (multi-seed)

```bash
python experiments/run_p0_baseline_freeze.py \
  --run-id-prefix p0_freeze_5seed \
  --seeds 11 22 33 44 55 \
  --baseline-epochs 8 \
  --transfer-pretrain-epochs 6 \
  --transfer-finetune-epochs 6 \
  --robustness-episodes 120
```

### 2) P2 v2 recommendation (robustness-focused randomization)

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

### 3) Significance report

```bash
python experiments/significance_report.py \
  --a-prefix p0_freeze_5seed \
  --b-prefix p2_v2_5seed \
  --report-name release_significance_p0_vs_p2v2_5seed
```

## ☁️ Kaggle (No Colab)

```text
Runtime Policy
├─ Local + Kaggle only
└─ Colab path removed from active pipeline
```

```bash
python kaggle_job_manager.py run \
  --owner <your_kaggle_username> \
  --slug high-dimensional-worldmodel-aggressive \
  --seed 11
```

- Direct stage execution inside kernel: baseline/transfer/ablation/robustness.
- `run_id` and `seed` are verified to propagate end-to-end.

## 🗂️ Project Layout

```text
.
├─ envs/
├─ physics/
├─ models/
├─ training/
├─ experiments/
├─ kaggle/
├─ report/
├─ results/
└─ RUNBOOK.md
```

## 🧩 GitHub About (Copy/Paste)

### Description

`Higher-dimensional world models for cross-dimensional transfer: reproducible N-D physics training, robustness evaluation, and Kaggle-ready experiment orchestration.`

### Website

`(optional) link to your latest report or project page`

### Topics

`reinforcement-learning, world-model, model-based-rl, transfer-learning, simulation, physics, pytorch, kaggle, reproducibility, research`

## 📘 More Docs

- `RUNBOOK.md` for execution commands.
- `report/` for technical and significance reports.
- `改造计划.MD` for phased roadmap (P0 -> P6).
