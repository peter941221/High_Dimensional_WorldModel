# Director Final Technical Synthesis

Date: 2026-03-01
Status: Final

## Scope

- Goal: determine whether >3D training improves 3D outcomes under matched compute and identify mechanism contributors.
- Source scope: simulation-only experiments and reproducible repository artifacts.
- Final gate record: `Research_Template/runtime/final_report.md` (`director_approved_final=true`, `quality_score=0.96`).

## Claim-to-Evidence Matrix

| Claim ID | Claim | Evidence (primary) | Statistical status | Confidence | Residual risk |
| --- | --- | --- | --- | --- | --- |
| C1 | Matched-compute ranking shows small positive transfer for 4D/5D over 6D/8D. | `report/director_evidence_closure_final.json`; `report/kaggle_hiconf_hard020_10seed_summary.json` | Pairwise sign-flip among dimensions not significant (min p=0.21875). | Medium | Weak-order, not decisive winner. |
| C2 | `phys_residual` is strongest among tested latent model families. | `report/director_evidence_closure_final.json` (`mechanism_attribution.latent_representation`) | Significant vs `gru` and `rssm`; trend vs `mlp`. | Medium-High | `phys_residual` vs `mlp` remains near-threshold. |
| C3 | Guidance-aware policies improve checkpoint-fixed behavior vs model-only control. | `report/director_evidence_closure_final.json` (`mechanism_attribution.guidance_policy`) | Significant on easy/medium/hard for `model_only` vs `guided_blend`. | High (checkpoint-fixed scope) | Not equal to training-time causal proof. |
| C4 | Robustness default `scale=0.20` is preferred to `0.25` in final paired test. | `report/kaggle_hifinal_hard020_vs_hard025_5seed_significance.json` | Flat paired outcomes, no gain from `0.25`; parsimony favors `0.20`. | High | Could shift in different tasks/budgets. |
| C5 | Domain randomization alters medium/hard tradeoff; `hard_only@0.20` supports hard target. | `report/release_significance_p0_vs_p2v2_9seed.json`; `report/kaggle_next_hard002_vs_hard020_9seed_significance.json` | Mixed but significant direction-specific effects. | Medium-High | Scope sensitivity remains. |
| C6 | Training-time guidance OFF vs ON causality is formally downgraded to inconclusive for this closure cycle. | `report/guidance_off_vs_on_5seed_significance_finallock.json`; `report/guidance_off_vs_on_causality_lock_final.json` | Key transfer KPIs at p=0.0625 (>0.05). | Medium | Requires >=9 paired seeds for decisive confirmation. |

## Causal Lock Decision

- Path selected: `B`
- Locked statement: training-time guidance causality is **inconclusive** at current sample power.
- Bound: maintain operational default but avoid causal-overclaim language.

## Runtime Packaging

- Run package: `Research_Template/runtime/runs/research_20260301_ultimate_closure/final_report.md`
- Root report: `Research_Template/runtime/final_report.md`
- Root state: `Research_Template/runtime/state.json`

## Residual Risks

1. Training-time guidance causality remains inconclusive under current 5-seed test.
2. Dimension ranking remains non-decisive despite matched compute.
3. External real-world transfer remains unvalidated (simulation-only evidence).
