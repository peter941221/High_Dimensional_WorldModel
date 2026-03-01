# director_evidence_closure_iter1

## Matched-compute dimension ranking (4D/5D/6D/8D -> 3D)

- cohort: `C:\AI Projects\Fun Stuff\High_Dimensional_WorldModel\report\kaggle_hiconf_hard020_10seed_summary.json`; seeds=[11, 22, 33, 44, 55, 66, 77, 88, 99, 111]; matched_compute=True

| Rank | Source Dim | Mean Gain | Std Gain | Mean Transfer Success | p(gain>0, signflip) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 4 | 0.0133 | 0.0514 | 0.8483 | 0.4844 |
| 2 | 5 | 0.0133 | 0.0350 | 0.8483 | 0.3203 |
| 3 | 6 | 0.0017 | 0.0434 | 0.8367 | 1.0000 |
| 4 | 8 | 0.0017 | 0.0412 | 0.8367 | 1.0000 |

## Mechanism attribution

### Latent representation (ablation)

| Rank | Model | Mean Success | Std |
| ---: | --- | ---: | ---: |
| 1 | phys_residual | 0.8800 | 0.0219 |
| 2 | mlp | 0.8533 | 0.0219 |
| 3 | gru | 0.8300 | 0.0367 |
| 4 | rssm | 0.8250 | 0.0387 |

### Guidance policy (checkpoint-fixed evaluation)

- run_prefix=`p2_v2_9seed`; seeds_used=[11, 22, 33, 44, 55, 66, 77, 88, 99]; episodes=20

| Difficulty | Model Only | Guided Blend | Guide Only |
| --- | ---: | ---: | ---: |
| easy | 0.0000 | 0.7389 | 0.9000 |
| medium | 0.0556 | 0.2000 | 0.2500 |
| hard | 0.0556 | 0.1500 | 0.2000 |

### Domain randomization (paired significance)

- `release_significance_p0_vs_p2v2_9seed`: robust_medium delta=0.0500 (p=0.0039), robust_hard delta=-0.0167 (p=0.0039)
- `kaggle_next_hard002_vs_hard020_9seed_significance`: robust_medium delta=0.0000 (p=1.0000), robust_hard delta=0.0042 (p=0.0039)

## Claims -> artifacts

- C1: Matched-compute 4D/5D/6D/8D-to-3D ranking is computed from the hard020 10-seed cohort with paired significance.
  - artifact: `C:\AI Projects\Fun Stuff\High_Dimensional_WorldModel\report\kaggle_hiconf_hard020_10seed_summary.json`
  - artifact: `C:\AI Projects\Fun Stuff\High_Dimensional_WorldModel\report\director_evidence_closure_iter1.json`
  - artifact: `C:\AI Projects\Fun Stuff\High_Dimensional_WorldModel\report\director_evidence_closure_iter1.md`
  - rerun: `python experiments/evidence_closure_report.py --report-name director_evidence_closure_iter1`
- C2: Latent representation contribution is isolated via fixed-budget model ablations (gru/mlp/phys_residual/rssm) on the same 10-seed cohort.
  - artifact: `C:\AI Projects\Fun Stuff\High_Dimensional_WorldModel\report\kaggle_hiconf_hard020_10seed_summary.json`
  - artifact: `C:\AI Projects\Fun Stuff\High_Dimensional_WorldModel\report\director_evidence_closure_iter1.json`
  - rerun: `python experiments/evidence_closure_report.py --report-name director_evidence_closure_iter1`
- C3: Guidance policy contribution is isolated by checkpoint-fixed evaluation (model_only vs guided_blend vs guide_only) over 9 seeds.
  - artifact: `C:\AI Projects\Fun Stuff\High_Dimensional_WorldModel\checkpoints\baseline`
  - artifact: `C:\AI Projects\Fun Stuff\High_Dimensional_WorldModel\report\director_evidence_closure_iter1.json`
  - rerun: `python experiments/evidence_closure_report.py --guidance-prefix p2_v2_9seed --guidance-seeds 11 22 33 44 55 66 77 88 99`
- C4: Domain-randomization contribution is anchored to paired-significance reports (9-seed robustness tradeoff studies).
  - artifact: `C:\AI Projects\Fun Stuff\High_Dimensional_WorldModel\report\release_significance_p0_vs_p2v2_9seed.json`
  - artifact: `C:\AI Projects\Fun Stuff\High_Dimensional_WorldModel\report\kaggle_next_hard002_vs_hard020_9seed_significance.json`
  - rerun: `python experiments/significance_report.py --a-prefix p0_freeze_9seed --b-prefix p2_v2_9seed --report-name release_significance_p0_vs_p2v2_9seed`
  - rerun: `python experiments/significance_report.py --a-prefix next_hard002_9seed --b-prefix next_hard020_9seed --report-name kaggle_next_hard002_vs_hard020_9seed_significance`

## Residual risks

- Dimension ranking is currently a weak-order tie (4D~5D > 6D~8D) rather than a decisive winner.
- Guidance causal claim does not yet isolate training-time guidance from inference-time blending.
- Randomization effects depend on chosen scope (medium_hard vs hard_only) and may shift with budget.