# Guidance OFF vs ON Causality Lock (Final)

- Decision path: `B`
- Final status: `inconclusive`
- Decision: Downgrade training-time guidance causality claim to inconclusive
- Justification: Exact paired sign-flip remains p=0.0625 on key transfer KPIs at 5 seeds; robustness deltas are mixed by difficulty, so training-time causality is not claimed.

## Key 5-seed evidence (final lock rerun)

| KPI | Delta (ON-OFF) | p-value | Significant(0.05) |
| --- | ---: | ---: | --- |
| baseline_success_dim3 | 0.7150 | 0.0625 | False |
| baseline_success_dim4 | 0.6600 | 0.0625 | False |
| transfer_success_mean | 0.6325 | 0.0625 | False |
| transfer_gain_mean | 0.0375 | 0.0625 | False |
| robust_easy | 0.0000 | 1.0000 | False |
| robust_medium | 0.0500 | 0.0625 | False |
| robust_hard | -0.0167 | 0.0625 | False |

## Interpretation Lock

- Training-time OFF vs ON causality remains **inconclusive** in current closure cycle.
- Checkpoint-fixed guidance gains are retained as mechanism evidence only.

## Repro Commands
- `python experiments/run_p0_baseline_freeze.py --run-id-prefix p_guidance_off_9seed --seeds 11 22 33 44 55 66 77 88 99 --baseline-epochs 8 --transfer-pretrain-epochs 6 --transfer-finetune-epochs 6 --robustness-episodes 120 --training-guidance model_only --eval-policy-mode model_only --domain-rand --domain-rand-scope all --domain-rand-scale 0.20 --domain-rand-profile conservative --robustness-domain-rand-difficulties hard_only`
- `python experiments/significance_report.py --a-prefix p_guidance_off_9seed --b-prefix p2_v2_9seed --report-name guidance_off_vs_on_9seed_significance`
