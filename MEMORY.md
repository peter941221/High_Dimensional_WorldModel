# Project Memory

## 2026-02-26
- Studied 技术文档.md and extracted architecture and roadmap.
- Bootstrapped project skeleton aligned with planned module layout.
- Added starter configs, placeholder modules, and basic test scaffolding.
- Initialized git repository, committed scaffold, and pushed initial `main` to GitHub.
- Implemented deterministic `Physics4D` engine with gravity, collisions, and boundaries.
- Implemented `PushBallNDEnv` with difficulty presets, reproducible reset/step, and reward logic.
- Implemented world models: `MLPWorldModel`, `GRUWorldModel`, `RSSMWorldModel`, plus `PolicyNetwork`.
- Implemented training stack: `ReplayBuffer`, `DimensionTransfer`, `DreamTrainer`.
- Replaced placeholder tests with behavior tests and reached `pytest` full pass (`17 passed`).
- Implemented experiment scripts (`run_baseline`, `run_transfer`, `run_robustness`, `run_ablation`) and visualization.
- Generated `results/*.json` and `figures/*.png` artifacts for baseline, transfer, robustness, and ablation.
