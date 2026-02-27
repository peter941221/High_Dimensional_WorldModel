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
- Added assessment report at `report/technical_report.md` with coverage, metrics snapshot, and gap analysis.
- Upgraded `DreamTrainer` from imitation-only policy updates to imagination-based actor-critic with `ValueNetwork` and target value soft update.
- Added actor-critic parameter-update regression test and restored full suite pass (`18 passed`).
- Added checkpoint/resume support to `DreamTrainer` (model/optimizer/buffer/RNG/progress serialization).
- Added replay buffer state serialization (`state_dict`/`load_state_dict`) for true cross-session continuation.
- Upgraded experiment scripts with persistent `run_id` directories and resume flags:
  - `run_baseline.py --run-id ... --resume`
  - `run_transfer.py --run-id ... --resume`
  - `run_ablation.py --run-id ... --resume`
  - `run_robustness.py` now writes run-scoped outputs too
- Added checkpoint round-trip tests and buffer round-trip tests; full test suite now `20 passed`.
- Smoke-validated resume flow on baseline/transfer/ablation with epoch continuation logs.
