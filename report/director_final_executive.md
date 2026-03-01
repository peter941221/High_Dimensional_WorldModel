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
- Training-time guidance OFF vs ON causal claim: `inconclusive`
- Evidence: `report/guidance_off_vs_on_5seed_significance_finallock.json`, `report/guidance_off_vs_on_causality_lock_final.json`
- Why: exact paired sign-flip on key transfer KPIs remains `p=0.0625` at 5 seeds; robustness deltas are mixed by difficulty.

## Confidence Summary

- Operational default confidence: High
- Exact best source dimension confidence (`4D/5D/6D/8D`): Moderate (weak-order tie)
- Guidance training-time causal confidence: Inconclusive (explicitly bounded)

## Primary Evidence Backbone

- `report/director_evidence_closure_final.json`
- `report/director_evidence_closure_final.md`
- `report/guidance_off_vs_on_5seed_significance_finallock.json`
- `report/guidance_off_vs_on_causality_lock_final.json`
- `report/kaggle_hiconf_hard020_10seed_summary.json`
- `report/release_significance_p0_vs_p2v2_9seed.json`
- `report/kaggle_next_hard002_vs_hard020_9seed_significance.json`
- `report/kaggle_hifinal_hard020_vs_hard025_5seed_significance.json`

## Residual Risks

1. Dimension ranking remains weak-order (`4D ~= 5D > 6D ~= 8D`) without pairwise significance at alpha 0.05.
2. Training-time guidance causality remains inconclusive under current paired power.
3. Randomization effects remain scope-sensitive (`medium_hard` vs `hard_only`).
