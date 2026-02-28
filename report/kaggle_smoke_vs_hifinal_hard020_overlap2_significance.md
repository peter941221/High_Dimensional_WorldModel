# Significance Report: kaggle_smoke_vs_hifinal_hard020_overlap2_significance

- A (control): `hifinal_hard020_5seed`
- B (treatment): `kaggle_smoke_hard020_2seed`
- Seeds: `[11, 22]`
- Method: `paired_exact_signflip`

| KPI | A mean | B mean | Delta (B-A) | p-value | Significant(0.05) |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_success_dim3 | 0.8583 | 0.1250 | -0.7333 | 0.5000 | False |
| baseline_success_dim4 | 0.7833 | 0.0000 | -0.7833 | 0.5000 | False |
| transfer_success_mean | 0.8444 | 0.1250 | -0.7194 | 0.5000 | False |
| transfer_gain_mean | 0.0278 | 0.0000 | -0.0278 | 1.0000 | False |
| robust_easy | 0.7292 | 0.8000 | 0.0708 | 0.5000 | False |
| robust_medium | 0.2167 | 0.1500 | -0.0667 | 0.5000 | False |
| robust_hard | 0.1417 | 0.1500 | 0.0083 | 0.5000 | False |