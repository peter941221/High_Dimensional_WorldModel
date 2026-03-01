# Director Final Executive Memo

Date: 2026-03-01
Audience: Executive / non-technical stakeholders
Status: Final

## Final Decision

Adopt and retain the following robustness operating default:
- domain randomization scale `0.20`
- profile `conservative`
- difficulty scope `hard_only`

## Causality Handling (Locked)

- Decision path: `B` (formal downgrade)
- Training-time guidance ON (`guided_blend`) vs OFF (`model_only`) claim under matched settings: `bounded non-significant` at alpha `0.05`
- Evidence: `results/analysis_guidance/guidance_train_matched_off_vs_on_9seed_significance.json`
- Why: paired exact sign-flip at `n=9` with meta-strict guard (`meta_check.passed=true`, only allowed diff key `training_guidance`) shows no significant KPI deltas.

## Confidence Summary

- Operational default confidence: High
- Exact best source dimension confidence (`4D/5D/6D/8D`): Moderate (weak-order tie)
- Guidance training-time causal confidence: Medium for "no detected KPI effect under matched 9-seed test"; no equivalence claim.

## Primary Evidence Backbone

- `report/director_evidence_closure_final.json`
- `report/director_evidence_closure_final.md`
- `results/p0_freeze/p_guidance_matched_on_9seed/p0_summary.json`
- `results/analysis_guidance/guidance_train_matched_off_vs_on_9seed_significance.json`
- `report/kaggle_hiconf_hard020_10seed_summary.json`
- `report/release_significance_p0_vs_p2v2_9seed.json`
- `report/kaggle_next_hard002_vs_hard020_9seed_significance.json`
- `report/kaggle_hifinal_hard020_vs_hard025_5seed_significance.json`

## Residual Risks

1. Dimension ranking remains weak-order (`4D ~= 5D > 6D ~= 8D`) without pairwise significance at alpha 0.05.
2. Non-significance is not proof of equivalence; small effects may remain undetected at current sample size.
3. Randomization effects remain scope-sensitive (`medium_hard` vs `hard_only`).
