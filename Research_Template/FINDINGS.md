# Findings

## Executive Summary
- Current evidence supports a practical default for robustness randomization (`scale=0.20`, `profile=conservative`, `difficulties=hard_only`) with reproducible behavior across recent multi-seed studies.
- Transfer from higher-dimensional training to 3D appears feasible and repeatable, but the causal mechanism and "4D-like" representation benefit are not yet fully isolated.
- The research loop should now focus on mechanism validation and final-quality synthesis rather than rebuilding baseline infrastructure.

## Key Findings
1. High-budget final decider showed no measurable gain from `scale=0.25` over `scale=0.20` (all tracked deltas 0, including `robust_hard=0.1417`).
2. A 10-seed confidence summary for `scale=0.20 + hard_only` reported stable robustness KPIs (`easy=0.7292`, `medium=0.2167`, `hard=0.1417`).
3. Tooling and docs were aligned to the validated default, and local/Kaggle smoke validations confirmed parameter forwarding and end-to-end reproducibility.

## Evidence Log
- Claim:
  - `0.20` is the preferred robustness scale over `0.25` under high-budget paired evaluation.
  - Evidence source: `report/kaggle_hifinal_hard020_vs_hard025_5seed_significance.md` and corresponding JSON report.
  - Confidence: High
  - Notes: 5 paired seeds; flat performance, so lower scale retained by parsimony.
- Claim:
  - `0.20 + hard_only + conservative` is stable across expanded seeds.
  - Evidence source: `report/kaggle_hiconf_hard020_10seed_summary.md` and JSON summary.
  - Confidence: Medium-High
  - Notes: Robustness metrics were identical across listed seeds in that setup.
- Claim:
  - End-to-end execution path is reproducible and command-forwarding is correct.
  - Evidence source: `MEMORY.md` session logs, smoke run artifacts, and runtime command traces.
  - Confidence: High
  - Notes: Verified command-line flags appear in output metadata and kernel logs.

## Limitations
- Most findings are simulation-bound and may not transfer directly to real physical systems.
- Some comparisons still rely on small seed counts in specific sub-studies.
- The "real 4D world" objective remains operational/approximate rather than physically verified.

## Open Questions
- Which representation properties in >3D pretraining causally drive transfer gains to 3D?
- Does the recommended robustness default remain optimal when training budgets or task dynamics change?
- Can we design stronger falsification tests for the 4D-inspired hypothesis beyond current environment settings?

## Recommended Next Actions
1. Run a targeted mechanism loop: controlled ablations isolating dimension, guidance, and randomization interactions with fixed seeds.
2. Prepare final synthesis package tying goals, evidence, limitations, and decision rationale to the template final-quality gate.
