# Runbook

## Setup

```bash
pip install -r requirements.txt
```

## Test

```bash
pytest -q
```

## Baseline

```bash
python experiments/run_baseline.py
```

## P2 Domain Randomization (Starter)

```bash
python experiments/run_baseline.py \
  --run-id p2_baseline_seed11 \
  --seed 11 \
  --domain-rand \
  --domain-rand-scale 0.10 \
  --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 200 \
  --domain-rand-warmup-epochs 8 \
  --epochs 8 \
  --eval-episodes 40
```

```bash
python experiments/run_p0_baseline_freeze.py \
  --run-id-prefix p2_conservative_v2 \
  --seeds 11 22 33 \
  --domain-rand \
  --domain-rand-scope robustness_only \
  --robustness-domain-rand-difficulties medium_hard \
  --domain-rand-scale 0.10 \
  --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 200 \
  --domain-rand-warmup-epochs 8 \
  --domain-rand-finetune-multiplier 0.5 \
  --baseline-epochs 8 \
  --transfer-pretrain-epochs 6 \
  --transfer-finetune-epochs 6 \
  --robustness-episodes 120
```

## P4 Curriculum (easy -> medium -> hard)

```bash
python experiments/run_curriculum.py \
  --run-id p4_curriculum_v1 \
  --dim 3 \
  --target-easy 0.70 \
  --target-medium 0.35 \
  --target-hard 0.25 \
  --max-rounds-per-stage 20 \
  --epochs-per-round 2
```

## P5 Aggregate Report

```bash
python experiments/aggregate_report.py \
  --run-prefixes p0_freeze_v1 p2_rand_v1 p2_v2 \
  --report-name p5_phase_compare
```

## P6 Hi-Fi Migration

```bash
python experiments/run_hifi_migration.py \
  --run-id p6_hifi_v1 \
  --source-run-id p2_v2_s11 \
  --dim 3 \
  --difficulty medium \
  --fidelity-level mild \
  --finetune-epochs 6 \
  --eval-episodes 40
```

## P0 Baseline Freeze (Multi-Seed)

```bash
python experiments/run_p0_baseline_freeze.py \
  --run-id-prefix p0_freeze_v1 \
  --seeds 11 22 33 \
  --baseline-epochs 8 \
  --transfer-pretrain-epochs 6 \
  --transfer-finetune-epochs 6 \
  --robustness-episodes 120
```

输出：
- 每个 seed 的单项实验结果：`results/<experiment>/<run_id>/...`
- 多 seed 汇总：`results/p0_freeze/<run_id_prefix>/p0_summary.json`

## Resume Training

```bash
# Start a named run
python experiments/run_baseline.py --run-id demo_run --epochs 10

# Continue later from the same run
python experiments/run_baseline.py --run-id demo_run --resume --epochs 20

# Keep disk bounded: archive every 5 epochs, keep only last 3 archives
python experiments/run_baseline.py --run-id demo_run --resume --epochs 30 --save-every 5 --keep-last 3
```

## Train Until Target Success

```bash
python experiments/run_until_success.py \
  --dim 3 \
  --difficulty easy \
  --target-success 0.70 \
  --max-rounds 20 \
  --epochs-per-round 2 \
  --eval-episodes 40
```

## Runtime Policy

- 当前执行策略：仅使用 Local + Kaggle。
- Colab 入口已移除，不再维护。

## Kaggle Batch (No Keep-Tab-Alive)

`kaggle_job_manager.py` 提供 `prepare / push / watch / output / run` 全流程。

### 什么时候需要登录 Kaggle

- `prepare`: 不需要登录（只打包本地文件）
- `push / status / watch / output / run`: 需要已登录

登录方式（二选一）：

```bash
# 方式A：环境变量
set KAGGLE_USERNAME=your_name
set KAGGLE_KEY=your_api_key

# 方式B：~/.kaggle/kaggle.json
```

### 一键跑（推荐）

```bash
python kaggle_job_manager.py run \
  --owner your_kaggle_username \
  --slug high-dimensional-worldmodel-aggressive \
  --code-dataset-slug high-dimensional-worldmodel-src \
  --title "HyperDream Aggressive Runner" \
  --seed 11 \
  --baseline-epochs 12 \
  --transfer-pretrain-epochs 8 \
  --transfer-finetune-epochs 8 \
  --ablation-epochs 8 \
  --robustness-episodes 120 \
  --eval-episodes 40 \
  --max-steps 120
```

输出会自动下载到 `kaggle_outputs/`。

说明：
- 默认启用 `--use-code-dataset`，会先把项目源码上传为 Kaggle Dataset，再由 Kernel 从 `/kaggle/input/...` 读取，避免运行时依赖 GitHub 网络解析。
- 可通过 `--seed` 透传到 `baseline/transfer/ablation/robustness` 四个实验脚本，便于和本地配对复现。
