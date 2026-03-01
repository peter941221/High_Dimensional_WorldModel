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

## Optional Path A (Guidance OFF vs ON): seed count + stop rule

Primary evidence context:
- The 5-seed lock uses `paired_exact_signflip` (exact sign-flip permutation test on the mean delta) and lands at `p=0.0625` on key transfer KPIs in `report/guidance_off_vs_on_5seed_significance_finallock.json`.
- Under this test, if all per-seed deltas share the same sign (non-zero), the two-sided p-value is `p = 2 / 2^n = 1 / 2^(n-1)`. This is why `n=5` yields `0.0625`.

Seed planning (two-sided p):
- Minimal threshold (direction must hold): `n=6` => `p = 1/2^(6-1) = 0.03125`.
- "Decisive" planning: `n=9` => `p = 1/2^(9-1) = 0.00390625` if all 9 align.
- Conservative (magnitude-agnostic) robustness to 1 discordant seed: `n=9`, 8/9 sign agreement => two-sided sign-test bound `p = 0.0390625`.

Execution commands:
- See `report/guidance_off_vs_on_causality_lock_final.json` `next_commands` for the canonical `p_guidance_off_9seed` rerun + `significance_report.py` invocation against `p2_v2_9seed`.
- Note: `p2_v2_9seed` already exists under `results/p0_freeze/`; Optional Path A primarily requires producing the matching `p_guidance_off_9seed` summary (the runner can reuse any already-computed seed outputs).

Update (2026-03-01): 7 paired seeds already available
- Additional `p_guidance_off` seed runs were already present for `66` and `77` under:
  - `results/baseline/p_guidance_off_5seed_s{seed}/baseline.json`
  - `results/transfer/p_guidance_off_5seed_s{seed}/transfer.json`
  - `results/robustness/p_guidance_off_5seed_s{seed}/robustness.json`
- A 7-seed `p0_summary.json` was built *without retraining* via:
  - `python experiments/build_p0_summary_from_runs.py --out-prefix p_guidance_off_7seed --source-run-prefix p_guidance_off_5seed --seeds 11 22 33 44 55 66 77 --meta-from-prefix p_guidance_off_5seed`
- New paired significance vs existing `p2_v2_9seed`:
  - `python experiments/significance_report.py --a-prefix p_guidance_off_7seed --b-prefix p2_v2_9seed --report-name guidance_off_vs_on_7seed_significance`
  - Result: key transfer KPIs reach `p=0.015625` at `n=7` under `paired_exact_signflip` (see `report/guidance_off_vs_on_7seed_significance.json`).
- Note: `robust_*` KPIs come from `experiments/run_robustness.py`'s heuristic policy and primarily reflect evaluation-domain-randomization settings, not trained-policy robustness.

Stop rule (for upgrading beyond Path B):
1. Run Optional Path A to reach `n=9` paired seeds under matched settings.
2. Re-run `experiments/significance_report.py` between `p_guidance_off_9seed` and `p2_v2_9seed`.
3. Upgrade training-time guidance causality only if key transfer KPIs achieve `p < 0.05` without introducing a large regression on `robust_hard`; otherwise keep the "inconclusive" lock.

Practical next step (if `n=9` is still desired for decisiveness):
- Run the missing `p_guidance_off` seeds `88` and `99` with the same settings used in `p_guidance_off_5seed` seed runs (training-guidance=`model_only`, `--domain-rand --domain-rand-scope all --domain-rand-scale 0.20 --domain-rand-profile conservative --robustness-domain-rand-difficulties hard_only`), then rebuild a 9-seed summary and re-run significance.
