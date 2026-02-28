# Significance Report: kaggle_next_hard002_vs_hard020_9seed_significance

- A (control): `next_hard002_9seed`
- B (treatment): `next_hard020_9seed`
- Seeds: `[11, 22, 33, 44, 55, 66, 77, 88, 99]`
- Method: `paired_exact_signflip`

| KPI | A mean | B mean | Delta (B-A) | p-value | Significant(0.05) |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_success_dim3 | 0.1250 | 0.1250 | 0.0000 | 1.0000 | False |
| baseline_success_dim4 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | False |
| transfer_success_mean | 0.1250 | 0.1250 | 0.0000 | 1.0000 | False |
| transfer_gain_mean | 0.0000 | 0.0000 | 0.0000 | 1.0000 | False |
| robust_easy | 0.7292 | 0.7292 | 0.0000 | 1.0000 | False |
| robust_medium | 0.2167 | 0.2167 | 0.0000 | 1.0000 | False |
| robust_hard | 0.1375 | 0.1417 | 0.0042 | 0.0039 | True |