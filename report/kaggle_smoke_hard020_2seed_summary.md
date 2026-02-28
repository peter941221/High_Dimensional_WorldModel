# Kaggle smoke summary: hard_only scale=0.20 (2 seeds)

- run ids: `kg_smoke_hard020_s11_20260228`, `kg_smoke_hard020_s22_20260228`
- seeds: `11,22`
- budget: `baseline/transfer/ablation=1/1+1/1`, `robustness_episodes=20`, `eval_episodes=8`, `max_steps=60`
- robustness rand: `enabled`, `scale=0.20`, `profile=conservative`, `difficulties=hard_only`

| KPI | mean | std | min | max |
| --- | ---: | ---: | ---: | ---: |
| baseline_success_dim3 | 0.1250 | 0.0000 | 0.1250 | 0.1250 |
| baseline_success_dim4 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| transfer_success_mean | 0.1250 | 0.0000 | 0.1250 | 0.1250 |
| transfer_gain_mean | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| robust_easy | 0.8000 | 0.0000 | 0.8000 | 0.8000 |
| robust_medium | 0.1500 | 0.0000 | 0.1500 | 0.1500 |
| robust_hard | 0.1500 | 0.0000 | 0.1500 | 0.1500 |