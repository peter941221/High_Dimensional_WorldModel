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

## Resume Experiments

Each training script now supports checkpoint-based resume with `--run-id` and `--resume`.

```bash
python experiments/run_baseline.py --run-id my_run --epochs 5
python experiments/run_baseline.py --run-id my_run --resume --epochs 10
```
