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
- Guidance OFF vs ON at training time remains inconclusive at 5 paired seeds (`p=0.0625` on key transfer KPIs).

## Canonical Artifacts
- `report/director_final_executive.md`
- `report/director_final_technical.md`
- `report/director_evidence_closure_final.json`
- `report/guidance_off_vs_on_causality_lock_final.json`
- `Research_Template/runtime/final_report.md`
- `Research_Template/runtime/state.json`

## Open Risks
- Statistical causality risk for guidance OFF vs ON remains unresolved.
- Ranking confidence risk for source-dimension ordering remains weak-order only.
- External-validity risk remains because evidence is simulation-only.

## Trigger-Based Next Actions
- Trigger A: If causal decisiveness is required, run Optional Path A with >=9 paired OFF vs ON seeds.
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

Last Compressed: 2026-03-01
