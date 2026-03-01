# Project Memory (Compressed Canonical)

## Purpose
- Preserve durable decisions, canonical baselines, and trigger-based next actions.
- Avoid high-churn runtime/log details (pids, lock snapshots, etc).

## Stable Decisions
- Research scope remains simulation-first and repository-contained (`envs`, `physics`, `models`, `training`, `experiments`).
- Claims stay bounded to simulation evidence unless external validation is explicitly added.
- Reproducibility and paired-seed significance checks (with meta-check confound guards) are required before major claim upgrades.

## Canonical Baseline (Path B Closure)
- Canonical closure run: `research_20260301_ultimate_closure`.
- Canonical authority file: `Research_Template/runtime/state.json`.
- Locked closure status: `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`.
- Canonical decision: keep Path B closure frozen unless Trigger A/B fires.

## Locked Findings (Do Not Drift Without New Evidence)
- Robustness operating default: `domain-rand-scale=0.20`, `profile=conservative`, `difficulties=hard_only`.
- Dimension-effect statement remains weak-order: `4D ~= 5D > 6D ~= 8D` under matched-compute evidence (no decisive pairwise winner at alpha=0.05).
- Training-time guidance OFF vs ON causality remains inconclusive because existing OFF vs ON comparisons are pipeline-confounded (non-guidance settings differ).

## Canonical Artifacts
- `report/director_final_executive.md`
- `report/director_final_technical.md`
- `report/director_evidence_closure_final.json`
- `report/guidance_off_vs_on_causality_lock_final.json`
- `Research_Template/runtime/final_report.md`
- `Research_Template/runtime/state.json`

## Open Risks
- Guidance OFF vs ON causal isolation risk remains unresolved (confounds).
- Ranking confidence risk for source-dimension ordering remains weak-order only (power-limited).
- External-validity risk remains because evidence is simulation-only.

## Trigger-Based Next Actions
- Trigger A (decisive training-time guidance causality needed):
  - Run Optional Path A matched-setting ablation (toggle ONLY `--training-guidance`; keep `--eval-policy-mode model_only`).
  - Enforce meta-strict: `--meta-check --meta-allow-diff training_guidance --meta-strict`.
  - Power planning for `paired_exact_signflip` (all-aligned): p = 1/2^(n-1). `n=6 -> 0.03125`; `n=9 -> 0.00390625`.
- Trigger B: If contradictory primary evidence appears, reopen synthesis and re-run claim-evidence matrix.
- Trigger C: If scope expands beyond simulation, add explicit external-validation protocol first.
- Trigger D: If runtime/tooling anomalies appear, run lock/state hygiene checks + minimal regressions.

## Recent Work (2026-03-01)
- Optional Path A preflight:
  - Matched OFF/ON dry-run command plans normalized and verified to differ only in run-id and training_guidance.
  - Meta-check guard validated on a known-confounded pipeline comparison (expected fail).
- Optional Path A smoke2 executed (seeds 11,22):
  - OFF: `results/p0_freeze/p_guidance_matched_off_smoke2/p0_summary.json`
  - ON: `results/p0_freeze/p_guidance_matched_on_smoke2/p0_summary.json`
  - Meta-strict paired report written under `results/analysis_smoke/` (git-ignored); meta_check.passed=true.
- Optional Path A overlap3 interim (analysis-only; no training):
  - Built ON overlap p0 summary (seeds `11 22 33`): `results/p0_freeze/p_guidance_matched_on_9seed/p0_summary.json`
  - Meta-strict paired report vs OFF 9seed: `results/analysis_guidance/guidance_train_matched_off_vs_on_overlap3_significance.json`
    - meta_check.passed=true (allowed diff key: `training_guidance` only)
    - `n=3`; no KPI significant (power-limited)
- Optional Path A seed44 triage (analysis-only; no training):
  - Confirmed incompleteness: `results/baseline|transfer|robustness/p_guidance_matched_on_9seed_s44/*.json` missing (`baseline.json`, `transfer.json`, `robustness.json` all absent).
  - Failure mode classified as interrupted baseline run (not summary bug): `progress.json` has only dim2 committed while checkpoints include `dim3_latest.pt` (`epoch=2`).
  - Power gate: under `paired_exact_signflip`, overlap `n=4` has best-case two-sided `p_min=0.125`; cannot be decisive at alpha `0.05`.
  - Loop decision: defer long ON `n=9` completion and defer seed44 execution in this 3-iteration loop; keep analysis-only.
- Scale-up attempt status:
  - OFF n=9 complete: `results/p0_freeze/p_guidance_matched_off_9seed/p0_summary.json`
  - ON partial (not n=9):
    - baseline: seeds `11 22 33` complete; seed `44` incomplete (`results/baseline/p_guidance_matched_on_9seed_s44/progress.json` only; checkpoints under `checkpoints/baseline/p_guidance_matched_on_9seed_s44/`)
    - transfer+robustness: seeds `11 22 33` complete; seed `44` missing
  - Scheduled minimal resume plan (not executed):
    - `python experiments/run_baseline.py --run-id p_guidance_matched_on_9seed_s44 --resume ...`
    - `python experiments/run_transfer.py --run-id p_guidance_matched_on_9seed_s44 ...`
    - `python experiments/run_robustness.py --run-id p_guidance_matched_on_9seed_s44 ...`
    - Then rebuild overlap summary/report (`overlap4`) for bookkeeping only; still not decisive by p-floor.

## Research Loop Notes (Template)
- Default role mode: researcher_only (iteration 1 memory recovery; iteration 2+ review previous artifact).
- Per-iteration artifacts:
  - machine output: `Research_Template/runtime/runs/<run_id>/iter_<n>_researcher.txt`
  - human summary: `Research_Template/runtime/runs/<run_id>/iter_<n>_researcher.md`
- Auto-commit each iteration is enabled; auto-push is enabled by default as of template v1.3.8.

## Iteration 3/3 Durable Addendum (2026-03-01, Optional Path A Analysis-Only Closure)
- Executive lock:
  - Optional Path A remains evidence-bounded and non-decisive in this loop.
  - Valid matched-setting overlap evidence uses seeds `[11, 22, 33]` only.
  - Causality language remains `inconclusive` pending larger matched paired sample.
- Technical lock:
  - `results/analysis_guidance/guidance_train_matched_off_vs_on_overlap3_significance.json` is the canonical interim matched-setting evidence for this loop:
    - `meta_check.passed=true`
    - allowed diff key only `training_guidance`
    - no KPI significant at `n=3`
  - Seed44 remains triaged as interrupted mid-baseline:
    - missing `baseline.json`, `transfer.json`, `robustness.json`
    - has `progress.json` (dim2 only) and `checkpoints/.../dim3_latest.pt`
- Decision-boundary lock (defer vs resume):
  - Default: keep deferral (analysis-only) while overlap size is `n<=4` and decisiveness is required.
  - Minimal seed44 resume is allowed only for bookkeeping/recovery validation with explicit acknowledgment that `n=4` remains non-decisive (`p_min=0.125`).
  - Decisive upgrade path requires matched OFF/ON scale-up to `n>=9` with meta-strict significance recheck.
- Handoff next-direction lock:
  - No long training by default after this loop.
  - Triggered execution choices only:
    - Choice A: seed44 minimal resume for completeness/recovery proof.
    - Choice B: full matched `n>=9` run for causality decisiveness.

Last Compressed: 2026-03-01

## Recent Work (2026-03-01, Researcher Loop Iteration 1)
- Memory/context recovery completed against canonical docs:
  - `Research_Template/RESEARCH_GOALS.md`
  - `Research_Template/RESEARCH_PLAN.md`
  - `Research_Template/FINDINGS.md`
- Concrete step executed (analysis-only refresh; no training):
  - Recomputed matched-setting OFF vs ON significance with meta-strict guard:
    - `python experiments/significance_report.py --a-prefix p_guidance_matched_off_9seed --b-prefix p_guidance_matched_on_9seed --report-name guidance_train_matched_off_vs_on_overlap_refresh_significance --out-dir results/analysis_guidance --meta-check --meta-allow-diff training_guidance --meta-strict`
- New evidence artifacts:
  - `results/analysis_guidance/guidance_train_matched_off_vs_on_overlap_refresh_significance.json`
  - `results/analysis_guidance/guidance_train_matched_off_vs_on_overlap_refresh_significance.md`
- Locked outcomes from this step:
  - Overlap seeds remain `[11,22,33]` (`n=3`); no expansion detected.
  - `meta_check.passed=true` and only allowed diff key is `training_guidance`.
  - No KPI significant at alpha `0.05`; training-time guidance causality remains inconclusive.
- Execution venue note:
  - Local chosen (not Kaggle) because this is a quick report recomputation over existing local artifacts.
  - Move to Kaggle when launching full matched OFF/ON training at `n>=9` seeds for causal decisiveness.
- Next-direction lock (precise):
  - Keep closure artifacts as canonical baseline.
  - Optional Path A only if decisiveness is required now:
    - Path A1: seed44 minimal resume for bookkeeping overlap expansion.
    - Path A2: full matched OFF/ON at `n>=9` with meta-strict significance regeneration for causal upgrade.

## Recent Work (2026-03-01, Researcher Loop Iteration 2)
- Concrete Optional Path A1 execution completed (local checkpoint resume path):
  - Completed seed44 ON baseline via resume:
    - `results/baseline/p_guidance_matched_on_9seed_s44/baseline.json`
  - Completed seed44 ON transfer:
    - `results/transfer/p_guidance_matched_on_9seed_s44/transfer.json`
  - Completed seed44 ON robustness:
    - `results/robustness/p_guidance_matched_on_9seed_s44/robustness.json`
- Overlap bookkeeping expanded and validated:
  - Rebuilt ON summary for seeds `11 22 33 44`:
    - `results/p0_freeze/p_guidance_matched_on_9seed/p0_summary.json`
  - Re-ran paired meta-strict report:
    - `results/analysis_guidance/guidance_train_matched_off_vs_on_overlap4_significance.json`
    - `results/analysis_guidance/guidance_train_matched_off_vs_on_overlap4_significance.md`
- Locked results from this iteration:
  - Overlap seeds are now `[11,22,33,44]` (`n=4`).
  - `meta_check.passed=true`; unexpected diff keys remain empty; only allowed key is `training_guidance`.
  - No KPI significant at alpha `0.05`; strongest transfer KPI remains non-significant (`p=0.25`).
- Execution venue note:
  - Local chosen (not Kaggle) because this step depended on existing local seed44 checkpoints and completed quickly.
  - Move to Kaggle when executing full matched OFF/ON `n>=9` causal-scale training.
- Next-direction lock (precise):
  - Keep canonical closure package unchanged.
  - If stronger causal decisiveness is required, execute Optional Path A2 full matched OFF/ON at `n>=9` paired seeds with meta-strict checks, then regenerate significance and closure synthesis.

## Recent Work (2026-03-01, Researcher Loop Iteration 3)
- Concrete A2 advancement executed (Kaggle-first):
  - Added matched-setting pass-through controls to Kaggle tooling:
    - `kaggle_job_manager.py`
    - `kaggle/run_kaggle_job.py`
    - `kaggle/run_config.example.json`
  - New supported controls include:
    - `training_guidance`, `eval_policy_mode`, blend/noise knobs
    - baseline/transfer domain-rand controls + transfer stage multipliers
    - `skip_ablation` for lean matched A2 runs
- Validation and dispatch:
  - `python kaggle_job_manager.py --help` confirms new flags.
  - Prepared ON seed55 matched bundle:
    - `.kaggle_kernel_build/kaggle/run_config.json` contains `run_id=p_guidance_matched_on_9seed_s55`, `training_guidance=guided_blend`, `eval_policy_mode=model_only`, `skip_ablation=true`, and matched domain-rand fields.
  - Pushed kernel successfully:
    - `peter941221/high-dimensional-worldmodel-guidance-on-s55`
  - Status polling via manager currently blocked by `403 Forbidden`, but kernel presence is confirmed in `kaggle kernels list --mine`.
- Locked interpretation:
  - This iteration upgrades execution infrastructure and launches the first missing ON seed on Kaggle.
  - No causal-claim upgrade yet (awaiting output ingestion and paired significance refresh).
- Next-direction lock (precise):
  - Dispatch ON seeds `66/77/88/99` with the same matched config on Kaggle.
  - After outputs sync locally, rebuild ON summary and run meta-strict paired significance for `guidance_train_matched_off_vs_on_9seed_significance`.

## Recent Work (2026-03-01, Researcher Loop Iteration 4)
- Concrete A2 dispatch completion executed (Kaggle-first):
  - Dispatched all remaining matched ON seeds with strict matched settings:
    - `peter941221/high-dimensional-worldmodel-guidance-on-s66`
    - `peter941221/high-dimensional-worldmodel-guidance-on-s77`
    - `peter941221/high-dimensional-worldmodel-guidance-on-s88`
    - `peter941221/high-dimensional-worldmodel-guidance-on-s99`
  - Matched config lock kept identical to seed55:
    - `training_guidance=guided_blend`
    - `eval_policy_mode=model_only`
    - domain-rand matched controls (`scale=0.20`, `profile=conservative`, warmup=`0`)
    - transfer rand multipliers (`scratch=1.0`, `source=1.0`, `finetune=0.5`)
    - `skip_ablation=true`
- Validation evidence:
  - For each seed `66/77/88/99`, both `prepare` and `push` passed via `kaggle_job_manager.py`.
  - `kaggle kernels list --mine --page-size 100` confirms presence of ON kernels `s55/s66/s77/s88/s99`.
  - `python kaggle_job_manager.py --owner peter941221 --slug high-dimensional-worldmodel-guidance-on-s99 status` now returns `status=running` (previous 403 state is not universal).
- Locked interpretation:
  - A2 remote dispatch set for missing ON seeds is complete.
  - No new local significance evidence yet; claim language remains unchanged until output sync + meta-strict rerun.
- Next-direction lock (precise):
  - Poll/download outputs for `s55/s66/s77/s88/s99`.
  - After synchronization, rebuild `p_guidance_matched_on_9seed` summary and run:
    - `python experiments/significance_report.py --a-prefix p_guidance_matched_off_9seed --b-prefix p_guidance_matched_on_9seed --report-name guidance_train_matched_off_vs_on_9seed_significance --out-dir results/analysis_guidance --meta-check --meta-allow-diff training_guidance --meta-strict`

## Recent Work (2026-03-01, Researcher Loop Iteration 5)
- Concrete next-best step executed (poll/download + unblock attempt):
  - Polled ON kernels `s55/s66/s77/s88/s99`; initial state was all `ERROR`.
  - Pulled per-seed logs and confirmed shared failure path:
    - dataset mount absent (`/kaggle/input/high-dimensional-worldmodel-src`)
    - fallback clone failed (`Could not resolve host: github.com`).
- Recovery actions completed this iteration:
  - Patched `kaggle/run_kaggle_job.py` to add `prepare_from_kernel_bundle()` fallback before repo clone.
  - Syntax validation PASS: `python -m py_compile kaggle/run_kaggle_job.py`.
  - Re-dispatched ON seeds with matched settings; performed additional targeted retries using raw `kaggle kernels push` to avoid repeated dataset-version churn.
- End-of-iteration remote state snapshot:
  - `s55=error`, `s66=error`, `s77=error`, `s88=error`, `s99=error`.
- Evidence notes:
  - Pulled kernel source confirms patched fallback is present in pushed scripts.
  - No new local ON artifacts were ingested yet, so paired significance remains unchanged this iteration.
- Next-direction lock (precise):
  - Relaunch all five seeds on replacement slugs with identical run config (keep `run_id` and seed fixed) and avoid repeated immediate dataset re-versioning between launches.
  - After local sync of ON `55/66/77/88/99`, rebuild ON summary and regenerate meta-strict `guidance_train_matched_off_vs_on_9seed_significance`.

## Recent Work (2026-03-01, Researcher Loop Iteration 6)
- Concrete next-best step executed (replacement-slug launch path):
  - Launched replacement ON slugs for seeds `55/66/77/88/99` with identical `run_id` + seed mapping:
    - `high-dimensional-worldmodel-guidance-on-s55-r1` -> `p_guidance_matched_on_9seed_s55`
    - `high-dimensional-worldmodel-guidance-on-s66-r1` -> `p_guidance_matched_on_9seed_s66`
    - `high-dimensional-worldmodel-guidance-on-s77-r1` -> `p_guidance_matched_on_9seed_s77`
    - `high-dimensional-worldmodel-guidance-on-s88-r1` -> `p_guidance_matched_on_9seed_s88`
    - `high-dimensional-worldmodel-guidance-on-s99-r1` -> `p_guidance_matched_on_9seed_s99`
  - Launches intentionally used `--no-code-dataset` to avoid immediate repeated code-dataset re-version churn.
- Validation/evidence:
  - Prepare + push succeeded for all five replacement slugs.
  - Immediate status probes showed all five `running`; follow-up probes showed all five `error`.
  - Downloaded replacement logs (`s55-r1/s66-r1/s99-r1`) confirm persistent fallback failure:
    - `fatal: unable to access 'https://github.com/peter941221/High_Dimensional_WorldModel.git/': Could not resolve host: github.com`
  - New replacement logs no longer contain the previous dataset-mount-missing error signature.
  - Replacement logs include:
    - `[kaggle-runner] run_config.json not found, using built-in defaults.`
    - execution then reaches clone fallback (`ensure_repo()`).
- Locked interpretation:
  - Replacing slugs and removing dataset-version churn did not unblock execution completion.
  - Current blocker has narrowed to deterministic source bootstrap under Kaggle runtime constraints (bundle/dataset fallback not taking effect before git clone path).
- Next-direction lock (precise):
  - Add diagnostic instrumentation in `kaggle/run_kaggle_job.py` to log candidate startup paths and explicit fallback failure reasons.
  - Launch one diagnostic replacement slug (`s55-r2`) with same run config, collect logs, then implement a deterministic non-git bootstrap path and relaunch remaining seeds.

