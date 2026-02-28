# Kaggle Experiment Summary (2026-02-28)

## Runs
- ctrl_s11: run_id=kg_exp_ctrl_s11_20260228, seed=11, budget={'baseline_epochs': 12, 'transfer_pretrain_epochs': 8, 'transfer_finetune_epochs': 8, 'ablation_epochs': 8, 'robustness_episodes': 120, 'eval_episodes': 40, 'max_steps': 120}
- hi_s11: run_id=kg_exp_hi_s11_20260228, seed=11, budget={'baseline_epochs': 24, 'transfer_pretrain_epochs': 16, 'transfer_finetune_epochs': 16, 'ablation_epochs': 16, 'robustness_episodes': 200, 'eval_episodes': 60, 'max_steps': 150}
- hi_s22: run_id=kg_exp_hi_s22_20260228, seed=22, budget={'baseline_epochs': 24, 'transfer_pretrain_epochs': 16, 'transfer_finetune_epochs': 16, 'ablation_epochs': 16, 'robustness_episodes': 200, 'eval_episodes': 60, 'max_steps': 150}

## KPI
- ctrl_s11: {'baseline_dim3': 0.65, 'baseline_dim4': 0.65, 'baseline_dim6': 0.55, 'baseline_dim8': 0.325, 'transfer_success_mean': 0.6375, 'transfer_gain_mean': 0.03750000000000003, 'robust_easy': 0.7333333333333333, 'robust_medium': 0.24166666666666667, 'robust_hard': 0.16666666666666666, 'ablation_best_model': 'gru', 'ablation_best_score': 0.725}
- hi_s11: {'baseline_dim3': 0.8833333333333333, 'baseline_dim4': 0.8, 'baseline_dim6': 0.55, 'baseline_dim8': 0.36666666666666664, 'transfer_success_mean': 0.8444444444444444, 'transfer_gain_mean': -0.005555555555555518, 'robust_easy': 0.74, 'robust_medium': 0.215, 'robust_hard': 0.17, 'ablation_best_model': 'phys_residual', 'ablation_best_score': 0.9}
  - delta_vs_ctrl_s11: {'baseline_dim3': 0.233333, 'baseline_dim4': 0.15, 'baseline_dim6': 0.0, 'baseline_dim8': 0.041667, 'transfer_success_mean': 0.206944, 'transfer_gain_mean': -0.043056, 'robust_easy': 0.006667, 'robust_medium': -0.026667, 'robust_hard': 0.003333}
- hi_s22: {'baseline_dim3': 0.8333333333333334, 'baseline_dim4': 0.7666666666666667, 'baseline_dim6': 0.65, 'baseline_dim8': 0.38333333333333336, 'transfer_success_mean': 0.8444444444444444, 'transfer_gain_mean': 0.061111111111111116, 'robust_easy': 0.74, 'robust_medium': 0.215, 'robust_hard': 0.17, 'ablation_best_model': 'phys_residual', 'ablation_best_score': 0.9}
  - delta_vs_ctrl_s11: {'baseline_dim3': 0.183333, 'baseline_dim4': 0.116667, 'baseline_dim6': 0.1, 'baseline_dim8': 0.058333, 'transfer_success_mean': 0.206944, 'transfer_gain_mean': 0.023611, 'robust_easy': 0.006667, 'robust_medium': -0.026667, 'robust_hard': 0.003333}

## High Budget Mean
- mean_kpi: {'baseline_dim3': 0.8583333333333334, 'baseline_dim4': 0.7833333333333334, 'baseline_dim6': 0.6000000000000001, 'baseline_dim8': 0.375, 'transfer_success_mean': 0.8444444444444444, 'transfer_gain_mean': 0.0277777777777778, 'robust_easy': 0.74, 'robust_medium': 0.215, 'robust_hard': 0.17}
- mean_delta_vs_ctrl_s11: {'baseline_dim3': 0.208333, 'baseline_dim4': 0.133333, 'baseline_dim6': 0.05, 'baseline_dim8': 0.05, 'transfer_success_mean': 0.206944, 'transfer_gain_mean': -0.009722, 'robust_easy': 0.006667, 'robust_medium': -0.026667, 'robust_hard': 0.003333}