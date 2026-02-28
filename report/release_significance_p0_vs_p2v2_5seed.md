# Significance Report: release_significance_p0_vs_p2v2_5seed

- A (control): `p0_freeze_5seed`
- B (treatment): `p2_v2_5seed`
- Seeds: `[11, 22, 33, 44, 55]`
- Method: `paired_exact_signflip`

| KPI | A mean | B mean | Delta (B-A) | p-value | Significant(0.05) |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_success_dim3 | 0.7250 | 0.7250 | 0.0000 | 1.0000 | False |
| baseline_success_dim4 | 0.6600 | 0.6600 | 0.0000 | 1.0000 | False |
| transfer_success_mean | 0.6342 | 0.6342 | 0.0000 | 1.0000 | False |
| transfer_gain_mean | 0.0342 | 0.0342 | 0.0000 | 1.0000 | False |
| robust_easy | 0.7333 | 0.7333 | 0.0000 | 1.0000 | False |
| robust_medium | 0.2417 | 0.2917 | 0.0500 | 0.0625 | False |
| robust_hard | 0.1667 | 0.1500 | -0.0167 | 0.0625 | False |