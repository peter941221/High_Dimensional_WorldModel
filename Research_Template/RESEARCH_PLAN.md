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
  --report-name guidance_train_matched_off_vs_on_9seed_significance
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
