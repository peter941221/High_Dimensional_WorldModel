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

## Resume Training

```bash
# Start a named run
python experiments/run_baseline.py --run-id demo_run --epochs 10

# Continue later from the same run
python experiments/run_baseline.py --run-id demo_run --resume --epochs 20

# Keep disk bounded: archive every 5 epochs, keep only last 3 archives
python experiments/run_baseline.py --run-id demo_run --resume --epochs 30 --save-every 5 --keep-last 3
```

## Colab One-Click

```bash
python colab_autorun.py \
  --run-tests \
  --run-id colab_first_run \
  --baseline-epochs 5 \
  --transfer-pretrain-epochs 3 \
  --transfer-finetune-epochs 3 \
  --ablation-epochs 4
```

## Colab Auto Push To GitHub

```bash
# 推荐：在 Colab Secrets 新建 key（例如 GITHUB_T），然后脚本自动读取
# 也可手动 export GITHUB_TOKEN=your_pat

python colab_autorun.py \
  --run-id colab_push_demo \
  --run-tests \
  --push-results-to-github \
  --push-branch colab-results \
  --github-user peter941221 \
  --repo-name High_Dimensional_WorldModel \
  --token-env GITHUB_TOKEN \
  --token-secret-name GITHUB_T
```
