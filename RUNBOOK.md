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
