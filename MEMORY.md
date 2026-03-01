# Project Memory (Compressed Canonical)

## Purpose
- Preserve only durable decisions, canonical evidence baselines, and trigger-based next actions.
- Avoid high-churn runtime logs that do not improve future decision quality.

## Stable Project Decisions
- Research scope remains simulation-first and repository-contained (`envs`, `physics`, `models`, `training`, `experiments`).
- Claims stay bounded to simulation evidence unless external validation is explicitly added.
- Reproducibility and paired-seed significance checks are required before major claim upgrades.

## Canonical Baseline (Path B Closure)
- Canonical closure run: `research_20260301_ultimate_closure`.
- Canonical authority file: `Research_Template/runtime/state.json`.
- Locked closure status: `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`.
- Current lock decision: Path B remains canonical; guidance OFF vs ON causality is still inconclusive at current power.

## Locked Findings (Do Not Drift Without New Evidence)
- Robustness operating default: `scale=0.20`, `profile=conservative`, `difficulties=hard_only`.
- Dimension-effect statement remains weak-order: `4D ~= 5D > 6D ~= 8D` under matched-compute evidence.
- Guidance OFF vs ON training-time causality remains unproven due to confounds (domain-randomization settings differ between OFF vs ON pipelines), despite stronger paired evidence with more seeds (e.g., `n=7` yields `p=0.015625` on key transfer KPIs in `report/guidance_off_vs_on_7seed_significance.json`).

## Canonical Artifacts
- `report/director_final_executive.md`
- `report/director_final_technical.md`
- `report/director_evidence_closure_final.json`
- `report/guidance_off_vs_on_causality_lock_final.json`
- `Research_Template/runtime/final_report.md`
- `Research_Template/runtime/state.json`

## Open Risks
- Guidance OFF vs ON causal isolation risk remains unresolved (current paired evidence is significant at `n=7` but is a pipeline comparison, not a matched guidance-only ablation).
- Ranking confidence risk for source-dimension ordering remains weak-order only.
- External-validity risk remains because evidence is simulation-only.

## Trigger-Based Next Actions
- Trigger A: If guidance causality decisiveness is required, complete Optional Path A (add missing paired seeds up to `n>=9` and/or run a matched-setting guidance-only ON vs OFF ablation).
- Trigger B: If contradictory primary evidence appears, reopen synthesis and re-run claim-evidence matrix.
- Trigger C: If scope expands beyond simulation, add explicit external-validation protocol first.
- Trigger D: If runtime integrity anomalies appear, run lock/pointer/state hygiene checks.

## Loop Template Decisions (2026-03-01)
- Default loop mode is `researcher_only`.
- Iteration protocol:
  - Round 1: recover memory/context, select next step, execute.
  - Round 2+: review previous round artifact, select next step, execute.
- Per iteration outputs include both machine JSON and human-readable markdown.
- Iteration auto-commit is enabled with scoped path policy and runtime-path exclusion:
  - Commit only iteration-local deltas (prefer `files_touched`, fallback to git delta).
  - Exclude `Research_Template/runtime/` from auto-commit.
  - Auto-push remains disabled by default.

## Compression Log
- 2026-03-01: Compressed historical high-churn memory into canonical durable memory.

## Iteration Progress (2026-03-01, researcher-only, iteration 1/1)
- Recovered context from `MEMORY.md`, `RESEARCH_GOALS.md`, `RESEARCH_PLAN.md`, and `FINDINGS.md`.
- Decision held: keep Path B closure frozen as canonical for this iteration; Optional Path A remains trigger-based (only if stronger causal decisiveness is required).
- Revalidated canonical authority and package integrity:
  - `Research_Template/runtime/state.json` still reports `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`.
  - Canonical SHA256 fingerprints remain unchanged for runtime final package and director final artifacts.
  - No post-closure `report/` evidence drift detected past closure boundary.
- Active loop hygiene snapshot: `active.lock` currently points to live run `research_20260301_163804`; this is compatible with keeping root canonical closure unchanged.
- Open risks unchanged: guidance OFF vs ON training-time causality remains inconclusive at 5 paired seeds (`p=0.0625`); source-dimension ranking remains weak-order; external validity remains simulation-bounded.
- Repo-wide smart scan (2026-03-01):
  - Validation PASS: `pytest -q` (50 passed; 1 warning from Torch/CUDA NVML deprecation).
  - Validation PASS: JSON parse/load for canonical artifacts (`Research_Template/runtime/state.json`, `report/director_evidence_closure_final.json`, `report/guidance_off_vs_on_causality_lock_final.json`, `report/guidance_off_vs_on_5seed_significance_finallock.json`).
  - Observed runtime: `Research_Template/runtime/active.lock` indicates live loop run `research_20260301_171951` with `pid=1872` (PowerShell process present at scan time); canonical baseline remains unchanged in `Research_Template/runtime/state.json`.

## Iteration Progress (2026-03-01, researcher-only, iteration 1/2)
- Added explicit seed-power math for `paired_exact_signflip` planning: all-aligned `p = 1/2^(n-1)`; `n=6 => 0.03125`, `n=9 => 0.00390625`. Conservative 1-discordant bound: `n=9`, 8/9 sign agreement => two-sided sign-test `p = 0.0390625`.
- Documented Optional Path A stop rule + decision flow in `Research_Template/RESEARCH_PLAN.md` and `Research_Template/FINDINGS.md` without changing canonical closure artifacts.
- Clarified that `p_guidance_off_*` vs `p2_v2_*` is pipeline-confounded (domain-rand scope/scale/difficulty differ), so upgrading *training-time guidance causality* requires a matched-setting guidance-only ON vs OFF ablation (hold `--eval-policy-mode model_only`, toggle `--training-guidance` only).
- Validation PASS (maintenance-only): JSON load of canonical artifacts + `pytest -q` (50 passed; 1 warning).

## Iteration Progress (2026-03-01, researcher-only, iteration 2/2)
- Found that `p_guidance_off` seed runs already existed for seeds `66` and `77` under `results/{baseline,transfer,robustness}/p_guidance_off_5seed_s{seed}`; regenerated missing robustness output for seed `77`.
- Added `experiments/build_p0_summary_from_runs.py` to build `results/p0_freeze/<prefix>/p0_summary.json` from existing per-seed outputs (no retraining).
- Built `results/p0_freeze/p_guidance_off_7seed/p0_summary.json` and generated `report/guidance_off_vs_on_7seed_significance.json` vs `p2_v2_9seed`.
  - Result: `n=7` paired exact sign-flip yields `p=0.015625` on key transfer KPIs (statistically significant).
  - Remaining caveat: comparison is still confounded by differing domain-randomization settings; canonical Path B closure remains unchanged.

## Iteration Progress (2026-03-01, researcher-only, iteration 2/2 - Optional Path A Tooling)
- Added `--dry-run` to `experiments/run_p0_baseline_freeze.py` to print planned commands/outputs without executing training (supports low-risk smoke validation before compute).
- Added `--out-dir` + `--meta-check/--meta-allow-diff/--meta-strict` to `experiments/significance_report.py` to explicitly detect/guard confounds when comparing prefixes.
- Updated Optional Path A documentation to include a 2-seed smoke recipe and a strict meta guardrail for matched-setting guidance-only OFF vs ON.
- Validation PASS: `pytest -q` (50 passed, 1 warning).

## Iteration Progress (2026-03-01, researcher-only, iteration 1/3)
- Maintenance-only revalidation: canonical closure artifacts load successfully; `pytest -q` PASS (50 passed, 1 warning).
- No new experiments executed; residual risks unchanged (guidance causality still confounded; ranking weak-order; external validity simulation-only).
- Next direction unchanged: keep repo closed unless training-time guidance causality is required; if required, run Optional Path A matched-setting guidance-only OFF vs ON (start with a 2-seed smoke using `--dry-run` + `--meta-check`, then scale to `n>=9` paired seeds).

Last Compressed: 2026-03-01
