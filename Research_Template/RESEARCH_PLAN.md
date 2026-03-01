# Research Plan

## Strategy
- Approach: hypothesis-driven iterative loop with risk-based validation and reproducible artifacts.
- Why: mature existing tooling allows focused closure rather than broad retraining.

## Workstreams
1. Workstream A
   - Objective: transfer/robustness evidence and decision boundaries across dimensions and randomization settings.
2. Workstream B
   - Objective: mechanism attribution (representation, guidance, randomization) and bounded causal claims.

## Milestones
- 25%: Baseline/doc/runtime recovery complete.
- 50%: Multi-seed transfer and robustness evidence refreshed.
- 75%: Major uncertainty reduced through targeted closure artifacts.
- 100%: Director signoff package finalized with explicit residual-risk bounds.

## Final-Mile Director Gate
1. Executive artifact completion: Completed
2. Causal closure decision (Path A/B): Completed (Path B selected)
3. Technical synthesis completion: Completed
4. Runtime final packaging with score gate fields: Completed

## Director Closure Sprint Protocol (Final Status)
1. Non-dry closure regeneration
   - Status: Completed
   - Evidence: `report/director_evidence_closure_final.json`
2. Training-time guidance OFF vs ON lock
   - Status: Completed via Path B downgrade
   - Evidence: `report/guidance_off_vs_on_5seed_significance_finallock.json`, `report/guidance_off_vs_on_causality_lock_final.json`
3. Final synthesis docs
   - Status: Completed
   - Evidence: `report/director_final_executive.md`, `report/director_final_technical.md`
4. Runtime packaging
   - Status: Completed
   - Evidence: `Research_Template/runtime/final_report.md`, `Research_Template/runtime/state.json`

## Validation Plan (Executed)
- `python experiments/significance_report.py --a-prefix p_guidance_off_5seed --b-prefix p2_v2_5seed --report-name guidance_off_vs_on_5seed_significance_finallock`
- `python experiments/evidence_closure_report.py --report-name director_evidence_closure_final`
- JSON parse/integrity checks on final closure and causality-lock artifacts
- Runtime final report/state packaging checks
- Maintenance-only revalidation (2026-03-01 iteration 1/3):
  - JSON load checks for canonical artifacts
  - Regression: `pytest -q` (`50 passed, 1 warning`)

## Risks and Mitigations
- Risk: guidance training-time causality remains inconclusive.
  - Mitigation: bounded claim language and optional Path A >=9-seed rerun.
- Risk: dimension ranking remains weak-order.
  - Mitigation: avoid over-selecting a single dimension winner without stronger evidence.
- Risk: simulation-only scope.
  - Mitigation: mark external validity as out-of-scope in this closure.

## Optional Path A (Training-time guidance causality): matched-setting guidance-only ON vs OFF

Primary evidence context:
- The 5-seed lock uses `paired_exact_signflip` (exact sign-flip permutation test on the mean delta) and lands at `p=0.0625` on key transfer KPIs in `report/guidance_off_vs_on_5seed_significance_finallock.json`.
- Under this test, if all per-seed deltas share the same sign (non-zero), the two-sided p-value is `p = 2 / 2^n = 1 / 2^(n-1)`. This is why `n=5` yields `0.0625`.

Important confound note (why matched settings are required for causality):
- The existing OFF vs ON comparisons in this closure cycle (`p_guidance_off_*` vs `p2_v2_*`) are **pipeline comparisons**, not isolated guidance-only ablations.
- Evidence: `results/p0_freeze/*/p0_summary.json` `meta` shows substantial non-guidance differences, e.g.:
  - `p_guidance_off_5seed`: `domain_rand_scope=all`, `domain_rand_scale=0.20`, `robustness_domain_rand_difficulties=hard_only`, warmup `0`.
  - `p2_v2_9seed`: `domain_rand_scope=robustness_only`, `domain_rand_scale=0.10`, `robustness_domain_rand_difficulties=medium_hard`, warmup `200 eps / 8 epochs`.
- Therefore:
  - It is valid as "end-to-end pipeline evidence" (useful operationally), but
  - It is **not sufficient** to upgrade *training-time guidance causality* beyond "inconclusive".

Seed planning (two-sided p):
- Minimal threshold (direction must hold): `n=6` => `p = 1/2^(6-1) = 0.03125`.
- "Decisive" planning: `n=9` => `p = 1/2^(9-1) = 0.00390625` if all 9 align.
- Conservative (magnitude-agnostic) robustness to 1 discordant seed: `n=9`, 8/9 sign agreement => two-sided sign-test bound `p = 0.0390625`.

Matched-setting design (guidance-only ablation):
- Hold fixed: all non-guidance settings (epochs, steps, eval episodes, domain-rand flags/scope/scale/profile/warmup, robustness difficulty scope, etc).
- Hold fixed: inference-time action mode by forcing `--eval-policy-mode model_only` for **both** conditions (so evaluation does not re-introduce guidance blending).
- Toggle only: `--training-guidance {model_only vs guided_blend}` (optionally add `guide_only` as a separate third condition, not mixed into ON/OFF).

Matched-setting smoke (optional, 2 seeds; for wiring validation only):

```bash
# Dry-run (prints planned commands without executing)
python experiments/run_p0_baseline_freeze.py \
  --run-id-prefix p_guidance_matched_off_smoke2 \
  --seeds 11 22 \
  --baseline-epochs 1 --transfer-pretrain-epochs 1 --transfer-finetune-epochs 1 \
  --robustness-episodes 30 \
  --training-guidance model_only --eval-policy-mode model_only \
  --domain-rand --domain-rand-scope all --domain-rand-scale 0.20 --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 0 --domain-rand-warmup-epochs 0 \
  --robustness-domain-rand-difficulties hard_only \
  --dry-run

# OFF (smoke): matched settings; reduced compute
python experiments/run_p0_baseline_freeze.py \
  --run-id-prefix p_guidance_matched_off_smoke2 \
  --seeds 11 22 \
  --baseline-epochs 1 --transfer-pretrain-epochs 1 --transfer-finetune-epochs 1 \
  --robustness-episodes 30 \
  --training-guidance model_only --eval-policy-mode model_only \
  --domain-rand --domain-rand-scope all --domain-rand-scale 0.20 --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 0 --domain-rand-warmup-epochs 0 \
  --robustness-domain-rand-difficulties hard_only

# ON (smoke): ONLY toggle training-guidance
python experiments/run_p0_baseline_freeze.py \
  --run-id-prefix p_guidance_matched_on_smoke2 \
  --seeds 11 22 \
  --baseline-epochs 1 --transfer-pretrain-epochs 1 --transfer-finetune-epochs 1 \
  --robustness-episodes 30 \
  --training-guidance guided_blend --eval-policy-mode model_only \
  --domain-rand --domain-rand-scope all --domain-rand-scale 0.20 --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 0 --domain-rand-warmup-epochs 0 \
  --robustness-domain-rand-difficulties hard_only

# Optional: paired significance report for smoke (write to ignored results/ to avoid report drift)
python experiments/significance_report.py \
  --a-prefix p_guidance_matched_off_smoke2 \
  --b-prefix p_guidance_matched_on_smoke2 \
  --report-name guidance_train_matched_off_vs_on_smoke2_significance \
  --out-dir results/analysis_smoke \
  --meta-check --meta-allow-diff training_guidance --meta-strict
```

Preflight status (2026-03-01, iteration 1/3):
- Dry-run command planning executed for both `p_guidance_matched_off_smoke2` and `p_guidance_matched_on_smoke2` (seeds `11 22`).
- Normalized planned-command diff (allowing only `--run-id` value and `--training-guidance` value to vary) indicates exact match across baseline/transfer/robustness commands.
  - Evidence (local, git-ignored): `results/analysis_smoke/p_guidance_matched_smoke2_dryrun_cmd_diff.json` + `results/analysis_smoke/p_guidance_matched_*_dryrun.txt`.
- Meta-check guard verified on known-confounded pipeline comparison (`p_guidance_off_7seed` vs `p2_v2_9seed`): `meta_check.passed=false` with unexpected diffs in domain-rand and eval settings.
  - Evidence (local, git-ignored): `results/analysis_smoke/meta_check_confounded_p_guidance_off_7seed_vs_p2_v2_9seed.json`.

Smoke2 execution status (2026-03-01, iteration 2/3):
- Non-dry matched-setting smoke2 executed for both prefixes (seeds `11 22`):
  - OFF: `results/p0_freeze/p_guidance_matched_off_smoke2/p0_summary.json`
  - ON: `results/p0_freeze/p_guidance_matched_on_smoke2/p0_summary.json`
- Meta-strict paired report executed and passed:
  - Evidence (local, git-ignored): `results/analysis_smoke/guidance_train_matched_off_vs_on_smoke2_significance.json`
  - `meta_check.passed=true` with only allowed diff key `training_guidance`.
  - KPI deltas are not significant at `n=2` (all `p=1.0` under `paired_exact_signflip`), as expected for a wiring smoke test.

Overlap3 interim status (2026-03-01, iteration 1/3):
- Objective: use existing partial `p_guidance_matched_on_9seed` artifacts to compute a meta-checked paired report on overlap seeds only (no new training).
- Built ON overlap summary (no-train rebuild; `--skip-existing`) for seeds `11 22 33`:
  - `results/p0_freeze/p_guidance_matched_on_9seed/p0_summary.json`
- Interim paired significance report (overlap seeds only via `significance_report.py` intersection logic):
  - `results/analysis_guidance/guidance_train_matched_off_vs_on_overlap3_significance.json`
  - `meta_check.passed=true` with allowed diff key `training_guidance`.
  - Result: no KPI significant at `n=3` (power-limited).
- Note: seed `44` remains incomplete (baseline has `progress.json` + checkpoints but no `baseline.json`; no transfer/robustness), so it is excluded from the overlap set.

Seed44 triage + decision status (2026-03-01, iteration 2/3, analysis-only):
- Why `baseline.json` is missing:
  - `progress.json` has only `dim=2` committed.
  - Baseline checkpoints include `dim3_latest.pt` with extra epoch metadata (`epoch=2`), indicating the run advanced into `dim=3`.
  - `experiments/run_baseline.py` writes `progress.json` per-dim, but writes `baseline.json` only after the full dims loop completes.
  - Conclusion: seed `44` baseline was interrupted/preempted mid-run (not a summary script bug).
- Cost/power gate:
  - Test method is `paired_exact_signflip`; for overlap `n=4`, minimum two-sided p-value is `0.125`, so significance at alpha `0.05` is impossible even in best-case sign alignment.
  - Resume is feasible, but not cheap enough to be decisive in this loop (baseline resume still leaves most baseline epochs plus full transfer/robustness for seed `44`).
- Decision for this 3-iteration loop:
  - Keep analysis-only posture and defer long training.
  - Defer seed `44` execution to a scheduled minimal resume plan (for bookkeeping/interim `n=4`, not for decisive causality).

Minimal resume plan for seed `44` (scheduled; not executed here):

```bash
# 1) Resume baseline from existing checkpoints
python experiments/run_baseline.py \
  --run-id p_guidance_matched_on_9seed_s44 \
  --resume \
  --epochs 8 --max-steps 120 --eval-episodes 40 --heartbeat-every 1 \
  --seed 44 \
  --training-guidance guided_blend --guidance-blend-ratio 0.7 --policy-noise-std 0.1 \
  --eval-policy-mode model_only --eval-guidance-blend-ratio 0.7 \
  --domain-rand --domain-rand-scale 0.20 --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 0 --domain-rand-warmup-epochs 0

# 2) Run missing transfer for seed 44
python experiments/run_transfer.py \
  --run-id p_guidance_matched_on_9seed_s44 \
  --pretrain-epochs 6 --finetune-epochs 6 --max-steps 120 --eval-episodes 40 --heartbeat-every 1 \
  --seed 44 \
  --training-guidance guided_blend --guidance-blend-ratio 0.7 --policy-noise-std 0.1 \
  --eval-policy-mode model_only --eval-guidance-blend-ratio 0.7 \
  --domain-rand --domain-rand-scale 0.20 --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 0 --domain-rand-warmup-epochs 0 \
  --domain-rand-scratch-multiplier 1.0 --domain-rand-source-multiplier 1.0 --domain-rand-finetune-multiplier 0.5

# 3) Run missing robustness for seed 44
python experiments/run_robustness.py \
  --run-id p_guidance_matched_on_9seed_s44 \
  --episodes 120 --dim 3 --heartbeat-every 10 \
  --seed 44 \
  --domain-rand --domain-rand-scale 0.20 --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 0 --domain-rand-warmup-epochs 0 \
  --domain-rand-difficulties hard_only

# 4) Rebuild ON overlap summary (11,22,33,44) without extra training
python experiments/run_p0_baseline_freeze.py \
  --run-id-prefix p_guidance_matched_on_9seed \
  --seeds 11 22 33 44 \
  --skip-existing \
  --baseline-epochs 8 --transfer-pretrain-epochs 6 --transfer-finetune-epochs 6 \
  --robustness-episodes 120 \
  --training-guidance guided_blend --eval-policy-mode model_only \
  --domain-rand --domain-rand-scope all --domain-rand-scale 0.20 --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 0 --domain-rand-warmup-epochs 0 \
  --robustness-domain-rand-difficulties hard_only

# 5) Interim paired report at overlap n=4 (still not decisive by p-floor)
python experiments/significance_report.py \
  --a-prefix p_guidance_matched_off_9seed \
  --b-prefix p_guidance_matched_on_9seed \
  --report-name guidance_train_matched_off_vs_on_overlap4_significance \
  --out-dir results/analysis_guidance \
  --meta-check --meta-allow-diff training_guidance --meta-strict
```

Matched-setting execution commands (recommended, `n=9` paired seeds):

```bash
# OFF (matched): training guidance disabled; eval policy fixed to model_only
python experiments/run_p0_baseline_freeze.py \
  --run-id-prefix p_guidance_matched_off_9seed \
  --seeds 11 22 33 44 55 66 77 88 99 \
  --baseline-epochs 8 --transfer-pretrain-epochs 6 --transfer-finetune-epochs 6 \
  --robustness-episodes 120 \
  --training-guidance model_only --eval-policy-mode model_only \
  --domain-rand --domain-rand-scope all --domain-rand-scale 0.20 --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 0 --domain-rand-warmup-epochs 0 \
  --robustness-domain-rand-difficulties hard_only

# ON (matched): ONLY toggle training-guidance; keep eval-policy-mode model_only
python experiments/run_p0_baseline_freeze.py \
  --run-id-prefix p_guidance_matched_on_9seed \
  --seeds 11 22 33 44 55 66 77 88 99 \
  --baseline-epochs 8 --transfer-pretrain-epochs 6 --transfer-finetune-epochs 6 \
  --robustness-episodes 120 \
  --training-guidance guided_blend --eval-policy-mode model_only \
  --domain-rand --domain-rand-scope all --domain-rand-scale 0.20 --domain-rand-profile conservative \
  --domain-rand-warmup-episodes 0 --domain-rand-warmup-epochs 0 \
  --robustness-domain-rand-difficulties hard_only

# Paired significance report (training-time guidance causality candidate evidence)
python experiments/significance_report.py \
  --a-prefix p_guidance_matched_off_9seed \
  --b-prefix p_guidance_matched_on_9seed \
  --report-name guidance_train_matched_off_vs_on_9seed_significance \
  --out-dir results/analysis_guidance \
  --meta-check --meta-allow-diff training_guidance --meta-strict
```

```text
Optional Path A (matched-setting) flow

[Choose fixed base config]  (domain-rand, scope/scale, epochs, eval-policy-mode=model_only)
            |
            v
   +-------------------+     +-------------------+
   |  Train OFF (n=9)  |     |  Train ON (n=9)   |
   | guidance=model    |     | guidance=blend    |
   +---------+---------+     +---------+---------+
             \\                   //
              \\                 //
               v               v
        [build p0_summary.json for both prefixes]
                      |
                      v
         [experiments/significance_report.py]
                      |
                      v
     {p<0.05 on transfer KPIs under matched settings?}
            |                             |
           Yes                            No
            v                             v
   Upgrade causal language         Keep "inconclusive" lock
 (bounded + residual risks)        (still allow pipeline evidence)
```

Pipeline-only note (optional, not causal):
- Extending `p_guidance_off_*` to 9 seeds and comparing against existing `p2_v2_9seed` can strengthen the *pipeline* claim, but **does not remove confounds** and should not upgrade training-time causality language.

Stop rule (for upgrading beyond Path B):
1. Run Optional Path A with **matched settings** to reach `n>=9` paired seeds.
2. Re-run `experiments/significance_report.py` between `p_guidance_matched_off_9seed` and `p_guidance_matched_on_9seed`.
3. Upgrade training-time guidance causality only if key transfer KPIs achieve `p < 0.05` without introducing a large regression on `robust_hard`; otherwise keep the "inconclusive" lock.

## Iteration 3/3 Closure Addendum (2026-03-01, analysis-only)

Status:
- Risk Tier: `L`
- Loop progress: `3/3` complete
- Long training launched in this iteration: `No`

Final Optional Path A status for this loop:
1. Matched-setting interim evidence is bounded to overlap seeds `[11, 22, 33]`.
2. Meta-checked paired report is valid (`meta_check.passed=true`; allowed diff key only `training_guidance`) but non-significant at `n=3`.
3. Seed `44` remains incomplete and is locked behind a cost/power gate; therefore no causality upgrade action is taken in this loop.

Decision boundaries (locked):
1. Keep deferral when all are true:
   - Decisive causality is required at alpha `0.05`.
   - Available overlap remains `n<=4` (sign-flip floor at `n=4`: `p_min=0.125`).
   - No contradictory matched-setting primary evidence appears.
2. Execute seed44 minimal resume (scheduled path) only when at least one is true:
   - Reporting requires overlap4 bookkeeping completeness, or
   - Resume-path operability must be validated operationally.
   - Plus acceptance that resulting evidence remains non-decisive.
3. Escalate to full execution only when decision demand is causal decisiveness now:
   - Run matched OFF/ON to `n>=9`.
   - Re-run `significance_report.py` with `--meta-check --meta-allow-diff training_guidance --meta-strict`.
   - Reassess both transfer significance and robustness regression constraints.

Next direction (post-loop precise handoff):
- Preserve analysis-only deferral by default.
- If triggered, execute either:
  - minimal seed44 resume path for bookkeeping/recovery validation only, or
  - full matched `n>=9` causal upgrade path for decisiveness.

```text
Decision boundary map (locked)

[Current evidence: overlap3 only, n=3, non-significant]
                      |
                      v
          {Need causal decisiveness now?}
               |                 |
              No                Yes
               |                 |
               v                 v
 [Keep deferral + bounded language]   {Can run matched n>=9 now?}
                                            |            |
                                           No           Yes
                                            |            |
                                            v            v
                       [Optional seed44 minimal resume]  [Run full matched path]
                       [bookkeeping/recovery only]       [causal upgrade candidate]
```

## Iteration Update (2026-03-01 Researcher Loop: Overlap Refresh)
- Mode: analysis-only refresh (no new training).
- Risk Tier: L
- Concrete step executed:
  - Re-ran matched-setting paired significance with meta-strict guard:
    - `python experiments/significance_report.py --a-prefix p_guidance_matched_off_9seed --b-prefix p_guidance_matched_on_9seed --report-name guidance_train_matched_off_vs_on_overlap_refresh_significance --out-dir results/analysis_guidance --meta-check --meta-allow-diff training_guidance --meta-strict`
  - Output artifacts:
    - `results/analysis_guidance/guidance_train_matched_off_vs_on_overlap_refresh_significance.json`
    - `results/analysis_guidance/guidance_train_matched_off_vs_on_overlap_refresh_significance.md`
- Results:
  - Overlap seeds remain `[11, 22, 33]` (`n=3`).
  - `meta_check.passed=true`; only allowed diff key is `training_guidance`.
  - No KPI significant at alpha `0.05` (power-limited).
- Why local (not Kaggle) in this step:
  - This step is pure report recomputation on already-local artifacts and completes in seconds.
  - Trigger to move to Kaggle: launching full matched OFF/ON training to `n>=9` seeds for causal decisiveness.
- Next direction:
  - Keep closure artifacts as canonical baseline.
  - Execute Optional Path A only if decisiveness is required now: either
    1) seed44 minimal resume for overlap bookkeeping, or
    2) full matched OFF/ON `n>=9` with meta-strict recheck for causal upgrade.

## Iteration Update (2026-03-01 Researcher Loop Iteration 2: Seed44 Resume + Overlap4 Refresh)
- Mode: targeted execution for Optional Path A1 bookkeeping expansion.
- Risk Tier: M
- Concrete steps executed:
  - Resumed and completed baseline for `p_guidance_matched_on_9seed_s44`:
    - `python experiments/run_baseline.py --run-id p_guidance_matched_on_9seed_s44 --resume ...`
  - Executed missing transfer for seed 44:
    - `python experiments/run_transfer.py --run-id p_guidance_matched_on_9seed_s44 ...`
  - Executed missing robustness for seed 44:
    - `python experiments/run_robustness.py --run-id p_guidance_matched_on_9seed_s44 ...`
  - Rebuilt ON summary overlap with skip-existing:
    - `python experiments/run_p0_baseline_freeze.py --run-id-prefix p_guidance_matched_on_9seed --seeds 11 22 33 44 --skip-existing ...`
  - Recomputed paired significance with meta-strict guard:
    - `python experiments/significance_report.py --a-prefix p_guidance_matched_off_9seed --b-prefix p_guidance_matched_on_9seed --report-name guidance_train_matched_off_vs_on_overlap4_significance --out-dir results/analysis_guidance --meta-check --meta-allow-diff training_guidance --meta-strict`
- Evidence artifacts:
  - `results/baseline/p_guidance_matched_on_9seed_s44/baseline.json`
  - `results/transfer/p_guidance_matched_on_9seed_s44/transfer.json`
  - `results/robustness/p_guidance_matched_on_9seed_s44/robustness.json`
  - `results/p0_freeze/p_guidance_matched_on_9seed/p0_summary.json` (now includes seed 44)
  - `results/analysis_guidance/guidance_train_matched_off_vs_on_overlap4_significance.json`
  - `results/analysis_guidance/guidance_train_matched_off_vs_on_overlap4_significance.md`
- Results:
  - Overlap seeds expanded to `[11, 22, 33, 44]` (`n=4`).
  - `meta_check.passed=true` with only allowed diff key `training_guidance`.
  - No KPI significant at alpha `0.05`; strongest transfer KPI p-value is `0.25`.
- Why local (not Kaggle) in this step:
  - Resume used existing local checkpoints for seed 44 and completed quickly with low orchestration overhead.
  - Trigger to move this path to Kaggle: launching full matched OFF/ON scale-up to `n>=9` paired seeds for decisive causal isolation.
- Precise next direction:
  - Keep closure artifacts as canonical baseline.
  - If causal decisiveness is required now, execute Optional Path A2: run full matched OFF/ON at `n>=9` paired seeds using `--meta-check --meta-allow-diff training_guidance --meta-strict`, then regenerate significance and closure synthesis.

## Iteration Update (2026-03-01 Researcher Loop Iteration 3: A2 Kaggle Enablement + Seed55 Dispatch)
- Mode: execution-enablement + dispatch (A2 path advancement).
- Risk Tier: M
- Concrete step executed:
  - Upgraded Kaggle orchestration to support matched-setting guidance causality controls (so Kaggle can run guidance-only matched ON/OFF design):
    - Added pass-through flags to `kaggle_job_manager.py` and `kaggle/run_kaggle_job.py`:
      - `--training-guidance`, `--guidance-blend-ratio`, `--policy-noise-std`
      - `--eval-policy-mode`, `--eval-guidance-blend-ratio`
      - `--domain-rand`, `--domain-rand-scale`, `--domain-rand-profile`
      - `--domain-rand-warmup-episodes`, `--domain-rand-warmup-epochs`
      - `--domain-rand-scratch-multiplier`, `--domain-rand-source-multiplier`, `--domain-rand-finetune-multiplier`
      - `--skip-ablation` (compute reduction for matched baseline/transfer/robustness path)
  - Validation run:
    - `python kaggle_job_manager.py --help` confirms new flags are available.
    - `python kaggle_job_manager.py ... prepare` produced:
      - `.kaggle_kernel_build/kaggle/run_config.json` with matched ON seed55 config
      - embedded run config in `.kaggle_kernel_build/kaggle/run_kaggle_job.py`
  - A2 dispatch launched:
    - `python kaggle_job_manager.py --owner peter941221 --slug high-dimensional-worldmodel-guidance-on-s55 push`
    - Kernel push succeeded: `peter941221/high-dimensional-worldmodel-guidance-on-s55`
- Execution gate / blocker:
  - `kaggle kernels status peter941221/high-dimensional-worldmodel-guidance-on-s55` returned `403 Forbidden` in this environment, so CLI status polling is currently blocked.
  - Independent existence validation passed via `kaggle kernels list --mine --page-size 50` (new kernel appears with current timestamp).
- Coverage:
  - Unblocked Kaggle-first execution path for strict matched-setting A2.
  - Completed first ON missing-seed dispatch (`seed=55`) to remote execution channel.
- Residual risk:
  - Status/output collection via Kaggle CLI remains partially blocked by `403` and may require web UI confirmation or permission refresh.
  - A2 decisiveness still requires completing remaining ON seeds (`66,77,88,99`) and regenerating meta-strict significance.
- Precise next direction:
  - Dispatch ON seeds `66/77/88/99` with the same matched config via Kaggle slugs `high-dimensional-worldmodel-guidance-on-s{seed}`.
  - After outputs land locally, rebuild `results/p0_freeze/p_guidance_matched_on_9seed/p0_summary.json` and run:
    - `python experiments/significance_report.py --a-prefix p_guidance_matched_off_9seed --b-prefix p_guidance_matched_on_9seed --report-name guidance_train_matched_off_vs_on_9seed_significance --out-dir results/analysis_guidance --meta-check --meta-allow-diff training_guidance --meta-strict`

## Iteration Update (2026-03-01 Researcher Loop Iteration 4: A2 Kaggle Dispatch Seeds 66/77/88/99)
- Mode: remote execution dispatch (A2 matched-setting scale-up progression).
- Risk Tier: M
- Concrete step executed:
  - Dispatched all remaining matched ON seeds to Kaggle with the same strict settings used for seed55:
    - `seed=66` -> `peter941221/high-dimensional-worldmodel-guidance-on-s66`
    - `seed=77` -> `peter941221/high-dimensional-worldmodel-guidance-on-s77`
    - `seed=88` -> `peter941221/high-dimensional-worldmodel-guidance-on-s88`
    - `seed=99` -> `peter941221/high-dimensional-worldmodel-guidance-on-s99`
  - Configuration lock preserved across all pushes:
    - `training_guidance=guided_blend`
    - `eval_policy_mode=model_only`
    - matched domain-rand controls (`scale=0.20`, `profile=conservative`, warmup=0)
    - transfer multipliers (`scratch=1.0`, `source=1.0`, `finetune=0.5`)
    - `skip_ablation=true`
- Validation actions executed:
  - For each seed in `{66,77,88,99}`:
    - `python kaggle_job_manager.py ... prepare` -> PASS
    - `python kaggle_job_manager.py ... push` -> PASS
  - Listing validation:
    - `kaggle kernels list --mine --page-size 100` -> PASS (shows `...-s55/-s66/-s77/-s88/-s99`)
  - Status probe:
    - `python kaggle_job_manager.py --owner peter941221 --slug high-dimensional-worldmodel-guidance-on-s99 status` -> PASS (`status=running`)
- Coverage:
  - Completed all planned A2 ON-seed Kaggle dispatch actions (`55/66/77/88/99`).
  - Confirms remote execution has started for at least one newly dispatched seed (`s99` running).
- Residual risk:
  - No new local output artifacts ingested this iteration; paired significance remains unchanged locally.
  - Completion timing and output retrieval still depend on Kaggle runtime queue/execution lifecycle.
- Precise next direction:
  - Poll and download outputs for ON seeds `55/66/77/88/99` as they complete.
  - Once outputs are synchronized locally, rebuild ON summary and run:
    - `python experiments/run_p0_baseline_freeze.py --run-id-prefix p_guidance_matched_on_9seed --seeds 11 22 33 44 55 66 77 88 99 --skip-existing --baseline-epochs 8 --transfer-pretrain-epochs 6 --transfer-finetune-epochs 6 --robustness-episodes 120 --training-guidance guided_blend --eval-policy-mode model_only --domain-rand --domain-rand-scope all --domain-rand-scale 0.20 --domain-rand-profile conservative --domain-rand-warmup-episodes 0 --domain-rand-warmup-epochs 0 --robustness-domain-rand-difficulties hard_only`
    - `python experiments/significance_report.py --a-prefix p_guidance_matched_off_9seed --b-prefix p_guidance_matched_on_9seed --report-name guidance_train_matched_off_vs_on_9seed_significance --out-dir results/analysis_guidance --meta-check --meta-allow-diff training_guidance --meta-strict`

## Iteration Update (2026-03-01 Researcher Loop Iteration 5: Poll/Sync Attempt + Kaggle Recovery)
- Mode: Kaggle-first execution recovery (one-step unblock for A2 output synchronization).
- Risk Tier: M
- Concrete step executed:
  - Polled status for ON seeds `55/66/77/88/99`:
    - initial probe showed all five in `ERROR`.
  - Downloaded kernel logs for each failed slug and identified shared root cause:
    - `Dataset mount not found: /kaggle/input/high-dimensional-worldmodel-src`
    - fallback `git clone` failed due DNS/network: `Could not resolve host: github.com`.
  - Added a network-independent fallback in Kaggle runner:
    - updated `kaggle/run_kaggle_job.py` to attempt `prepare_from_kernel_bundle()` before `ensure_repo()`.
    - validated syntax: `python -m py_compile kaggle/run_kaggle_job.py` (PASS).
  - Re-dispatched all ON slugs with matched config, then performed targeted retries:
    - first retry via manager `prepare+push` (all slugs pushed to v2).
    - observed mixed state (`s55/s66/s77` still error, `s88/s99` running then error/rerun cycle).
    - second retry for failed slugs using `prepare + kaggle kernels push` (no extra dataset version bump).
    - latest state at end of iteration: `s88=error`, `s99=error`, `s55/s66/s77=error`.
- Validation actions/results:
  - `python kaggle_job_manager.py --owner peter941221 --slug ... status` for each seed -> PASS (status retrieval works).
  - `python kaggle_job_manager.py --owner peter941221 --slug ... output` for failed seeds -> PASS (logs retrieved).
  - `kaggle kernels pull ...` confirms patched runner is present in pushed code (contains `prepare_from_kernel_bundle`).
  - Sync objective not yet met: no new completed ON result artifacts were downloaded locally.
- Coverage and residual risk:
  - Covered full poll/download/diagnose loop and executed a concrete recovery attempt in the same iteration.
  - Residual risk remains high for persistent dataset mount instability across all five ON slugs (`s55/s66/s77/s88/s99`).
  - 9-seed meta-strict significance refresh remains blocked until ON outputs are synchronized locally.
- Precise next direction:
  - Launch replacement Kaggle slugs for all failed ON seeds (`55/66/77/88/99`) using identical `run_id` + seed settings, and avoid immediate repeated dataset re-version churn between launches.
  - Poll replacement slugs and download outputs immediately on completion, then sync locally.
  - Once at least seeds `55/66/77/88/99` are locally ingested, rebuild ON summary and run:
    - `python experiments/significance_report.py --a-prefix p_guidance_matched_off_9seed --b-prefix p_guidance_matched_on_9seed --report-name guidance_train_matched_off_vs_on_9seed_significance --out-dir results/analysis_guidance --meta-check --meta-allow-diff training_guidance --meta-strict`

## Iteration Update (2026-03-01 Researcher Loop Iteration 6: Replacement Slugs Launched + Failure Signature Refresh)
- Mode: Kaggle-first replacement launch and poll/download verification.
- Risk Tier: M
- Concrete step executed:
  - Launched replacement ON slugs with identical `run_id` + seed for `55/66/77/88/99`:
    - `high-dimensional-worldmodel-guidance-on-s55-r1` -> `run_id=p_guidance_matched_on_9seed_s55`
    - `high-dimensional-worldmodel-guidance-on-s66-r1` -> `run_id=p_guidance_matched_on_9seed_s66`
    - `high-dimensional-worldmodel-guidance-on-s77-r1` -> `run_id=p_guidance_matched_on_9seed_s77`
    - `high-dimensional-worldmodel-guidance-on-s88-r1` -> `run_id=p_guidance_matched_on_9seed_s88`
    - `high-dimensional-worldmodel-guidance-on-s99-r1` -> `run_id=p_guidance_matched_on_9seed_s99`
  - To avoid immediate dataset re-version churn, launches used `--no-code-dataset` (no code-dataset publish in this batch).
- Validation actions/results:
  - For each seed, `prepare` + `push` completed successfully.
  - Immediate post-push status probe showed all five replacement slugs in `running`.
  - Follow-up status probes showed all five replacement slugs moved to `error`.
  - Output logs were downloaded for representative failed replacement slugs (`s55-r1`, `s66-r1`, `s99-r1`).
- New evidence from replacement logs:
  - Shared failure remains `git clone` DNS failure:
    - `fatal: unable to access 'https://github.com/peter941221/High_Dimensional_WorldModel.git/': Could not resolve host: github.com`
  - Replacement logs no longer show the prior dataset-mount-missing message.
  - Runtime trace also shows:
    - `[kaggle-runner] run_config.json not found, using built-in defaults.`
    - then falls through to `ensure_repo()` clone path.
- Coverage and residual risk:
  - Covered replacement launch path end-to-end (dispatch -> initial run -> fail -> log retrieval).
  - No completed ON outputs were synchronized locally this iteration.
  - 9-seed ON summary rebuild and meta-strict significance refresh remain blocked.
- Precise next direction:
  - Add a diagnostic patch in `kaggle/run_kaggle_job.py` to log startup path inventory (`__file__` parent, cwd, `/kaggle/src`) and explicit reasons `prepare_from_kernel_bundle()` returns `None`.
  - Launch one diagnostic replacement slug (`s55-r2`) with identical run config and collect logs to confirm whether script kernels expose bundled repo files.
  - Based on that evidence, implement one deterministic source bootstrap path that does not require external git DNS, then relaunch remaining ON seeds and resume poll/download sync.

## Iteration Update (2026-03-01 Researcher Loop Iteration 7: Startup Diagnostics + s55-r2 Confirmation)
- Mode: Kaggle-first diagnosis closure for bootstrap-path causality.
- Risk Tier: M
- Concrete step executed:
  - Patched `kaggle/run_kaggle_job.py` with explicit startup diagnostics:
    - runtime path inventory (`__file__`, cwd, `/kaggle/src`, `/kaggle/input`)
    - bundle root checks (`has_experiments`, `has_configs`, `has_kaggle`)
    - explicit fallback-reason logs for dataset disabled/empty slug and kernel-bundle rejection.
  - Launched diagnostic replacement slug with identical seed/run mapping:
    - `high-dimensional-worldmodel-guidance-on-s55-r2` -> `run_id=p_guidance_matched_on_9seed_s55`, `seed=55`.
    - kept `--no-code-dataset` to isolate non-dataset startup behavior.
- Validation actions/results:
  - Local syntax gate: `python -m py_compile kaggle/run_kaggle_job.py` -> PASS.
  - Kaggle dispatch:
    - `python kaggle_job_manager.py ... --slug high-dimensional-worldmodel-guidance-on-s55-r2 ... prepare` -> PASS
    - `python kaggle_job_manager.py ... --slug high-dimensional-worldmodel-guidance-on-s55-r2 ... push` -> PASS
  - Status probes:
    - initial `running`, then transitions to `error`.
  - Log retrieval:
    - `python kaggle_job_manager.py --owner peter941221 --slug high-dimensional-worldmodel-guidance-on-s55-r2 --output-dir tmp_kaggle_pull_guidance_on_s55_r2 output` -> PASS.
- Decisive evidence captured from `tmp_kaggle_pull_guidance_on_s55_r2/high-dimensional-worldmodel-guidance-on-s55-r2.log`:
  - `use_code_dataset=False` was active (by design for this diagnostic launch).
  - Bundle-root diagnostics show no source tree in script runtime:
    - `/kaggle/src`: `has_experiments=False`, `has_configs=False`, `has_kaggle=False`
    - `/kaggle/working`: `has_experiments=False`, `has_configs=False`, `has_kaggle=False`
  - Runner logs explicit fallback path:
    - `Dataset bootstrap disabled by config: use_code_dataset=false`
    - `Kernel bundle fallback unavailable across all candidate roots.`
    - then `git clone` fails with DNS (`Could not resolve host: github.com`).
- Locked interpretation:
  - `prepare_from_kernel_bundle()` is not a no-op bug; it is correctly bypassed because Kaggle script runtime lacks repository directories.
  - Current non-dataset startup path is deterministically blocked by external git DNS dependency.
- Precise next direction:
  - Implement deterministic non-git bootstrap in `kaggle/run_kaggle_job.py` + `kaggle_job_manager.py` by embedding an offline project bundle payload at prepare time and extracting it at runtime before `ensure_repo()`.
  - Validate with one probe slug (`s66-r2`), then relaunch `s77-r2/s88-r2/s99-r2` under the same run_id+seed mapping.
  - After any successful ON completions are synced locally, rebuild ON summary and rerun 9-seed meta-strict significance refresh.

## Iteration Update (2026-03-01 Researcher Loop Iteration 8: Embedded Bootstrap Implemented + s66-r2 Validation)
- Mode: Kaggle-first implementation + runtime validation.
- Risk Tier: M
- Concrete step executed:
  - Implemented deterministic non-git bootstrap path:
    - `kaggle_job_manager.py` now embeds a base64 offline project bundle payload (`project_bundle.zip` + `kaggle/run_config.json`) into prepared kernel script.
    - `kaggle/run_kaggle_job.py` now decodes/extracts that embedded payload before `ensure_repo()` and uses it as a network-free source fallback.
  - Launched validation probe slug:
    - `high-dimensional-worldmodel-guidance-on-s66-r2` -> `run_id=p_guidance_matched_on_9seed_s66`, `seed=66`, `--no-code-dataset`.
- Validation actions/results:
  - Local code gate:
    - `python -m py_compile kaggle/run_kaggle_job.py kaggle_job_manager.py` -> PASS.
  - Kaggle dispatch + execution:
    - `... s66-r2 ... prepare` -> PASS
    - `... s66-r2 ... push` -> PASS
    - `status` transitioned to `complete` (no startup DNS failure).
  - Output retrieval + sync:
    - `python kaggle_job_manager.py --owner peter941221 --slug high-dimensional-worldmodel-guidance-on-s66-r2 --output-dir tmp_kaggle_pull_guidance_on_s66_r2 output` -> PASS
    - Synced local artifacts:
      - `results/baseline/p_guidance_matched_on_9seed_s66/baseline.json`
      - `results/transfer/p_guidance_matched_on_9seed_s66/transfer.json`
      - `results/robustness/p_guidance_matched_on_9seed_s66/robustness.json`
- Decisive evidence from `tmp_kaggle_pull_guidance_on_s66_r2/high-dimensional-worldmodel-guidance-on-s66-r2.log`:
  - `Embedded project bundle present: True`
  - `Using embedded offline project bundle fallback.`
  - Run completed and saved summary (`Saved run summary: /kaggle/working/hyperdream_kaggle_summary.json`).
- Locked interpretation:
  - Deterministic offline bootstrap is now validated on Kaggle runtime under `--no-code-dataset`.
  - Prior startup blocker (`git clone` DNS dependency) is no longer on the critical path for this validated seed.
- Precise next direction:
  - Relaunch remaining ON replacement slugs with identical run mapping and embedded bootstrap path:
    - `s77-r2` (`run_id=p_guidance_matched_on_9seed_s77`)
    - `s88-r2` (`run_id=p_guidance_matched_on_9seed_s88`)
    - `s99-r2` (`run_id=p_guidance_matched_on_9seed_s99`)
  - On completion, sync artifacts locally, rebuild `results/p0_freeze/p_guidance_matched_on_9seed/p0_summary.json`, then rerun:
    - `python experiments/significance_report.py --a-prefix p_guidance_matched_off_9seed --b-prefix p_guidance_matched_on_9seed --report-name guidance_train_matched_off_vs_on_9seed_significance --out-dir results/analysis_guidance --meta-check --meta-allow-diff training_guidance --meta-strict`

