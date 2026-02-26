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
