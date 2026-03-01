# Significance Report: guidance_off_vs_on_7seed_significance

- A (control): `p_guidance_off_7seed`
- B (treatment): `p2_v2_9seed`
- Seeds: `[11, 22, 33, 44, 55, 66, 77]`
- Method: `paired_exact_signflip`

| KPI | A mean | B mean | Delta (B-A) | p-value | Significant(0.05) |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_success_dim3 | 0.0107 | 0.7286 | 0.7179 | 0.0156 | True |
| baseline_success_dim4 | 0.0000 | 0.6536 | 0.6536 | 0.0156 | True |
| transfer_success_mean | 0.0012 | 0.6327 | 0.6315 | 0.0156 | True |
| transfer_gain_mean | -0.0060 | 0.0256 | 0.0315 | 0.0156 | True |
| robust_easy | 0.7333 | 0.7333 | 0.0000 | 1.0000 | False |
| robust_medium | 0.2417 | 0.2917 | 0.0500 | 0.0156 | True |
| robust_hard | 0.1667 | 0.1500 | -0.0167 | 0.0156 | True |