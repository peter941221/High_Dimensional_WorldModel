# Equivalence-Oriented Report: guidance_train_matched_off_vs_on_9seed_equivalence_margin

- A (control): `p_guidance_matched_off_9seed`
- B (treatment): `p_guidance_matched_on_9seed`
- Seeds: `[11, 22, 33, 44, 55, 66, 77, 88, 99]`
- Method: `paired_bootstrap_mean_ci` (CI over mean delta)
- CI level: `0.9`
- Bootstrap: `10000` samples (seed `12345`)

## Meta Check

- Passed: `True`
- Allowed diff keys: `['training_guidance']`
- Unexpected diff keys: `[]`

## KPI Table

| KPI | n | mean Δ (B-A) | CI low | CI high | required | within? |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `baseline_success_dim3` | 9 | -0.005556 | -0.013889 | 0.002778 | 0.013889 | - |
| `baseline_success_dim4` | 9 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | - |
| `transfer_success_mean` | 9 | 0.000926 | -0.001389 | 0.003704 | 0.003704 | - |
| `transfer_gain_mean` | 9 | -0.001852 | -0.006481 | 0.002315 | 0.006481 | - |
| `robust_easy` | 9 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | - |
| `robust_medium` | 9 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | - |
| `robust_hard` | 9 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | - |

## Interpretation Guide

- `required` is the minimal absolute margin `m` such that the CI fits inside `[-m, +m]`.
- If you define a domain margin `m*` and `required <= m*`, then CI-based equivalence (at this CI level) holds.
