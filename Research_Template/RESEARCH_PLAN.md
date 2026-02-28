# Research Plan

## Strategy
- Approach: Hypothesis-driven iterative loop with risk-based validation (paired seeds, significance checks, and reproducible artifacts).
- Why this approach: This project already has mature experiment tooling and prior evidence; the fastest path is to reuse validated pipelines, then close remaining evidence gaps with targeted runs.

## Workstreams
1. Workstream A
   - Objective: Establish reliable transfer/robustness evidence and decision boundaries across dimensions and domain-randomization settings.
   - Inputs: `experiments/run_p0_baseline_freeze.py`, Kaggle job manager flows, existing summary/significance artifacts in `results/` and `report/`.
   - Output: Updated paired summaries, significance reports, and explicit go/no-go decisions.
2. Workstream B
   - Objective: Explain and improve observed behavior via architecture/guidance choices and controlled ablations.
   - Inputs: `DreamTrainer` + guidance policy path, ablation scripts, historical run metadata from memory/runtime artifacts.
   - Output: Mechanism hypotheses, prioritized tuning actions, and validated next-step backlog.

## Milestones
- 25%: Baseline and memory recovery confirmed; required docs complete; loop runtime paths corrected to this workspace.
- 50%: Transfer and robustness evidence refreshed with reproducible command traces and paired-seed summary updates.
- 75%: High-value uncertainty reduced (major residual risks either mitigated or converted into explicit experiments).
- 100%: Director final signoff with quality score >= 0.95 and complete executive plus technical findings.

## Validation Plan
- Methods: Unit/regression tests, paired multi-seed comparisons, significance testing, and command-level config forwarding verification.
- Commands/checks:
  - `pytest -q`
  - `python experiments/run_p0_baseline_freeze.py --run-id-prefix <id> --seeds <...>`
  - `python kaggle_job_manager.py run --slug <slug> --run-id <id> --yes ...`
  - `powershell -ExecutionPolicy Bypass -File .\Research_Template\scripts\Research_native_loop.ps1 -TemplatePath .\Research_Template\RESEARCH_NATIVE_LOOP_TEMPLATE.json -RepoRoot . -PrdPath .\Research_Template\RESEARCH_GOALS.md -DevDocPath .\Research_Template\RESEARCH_PLAN.md -FindingsPath .\Research_Template\FINDINGS.md`
- Expected evidence: Updated runtime trace/final report, reproducible metrics summaries, and documented residual risk per loop iteration.

## Risks and Mitigations
- Risk:
  - Low statistical power or unstable conclusions from small seed counts.
  - Mitigation: Use paired seed expansion and exact sign-flip tests before final decisions.
- Risk:
  - Kaggle/API/network instability can interrupt long runs and artifact download.
  - Mitigation: Keep retry-enabled workflows, staged output pulls, and resumable run IDs.
- Risk:
  - Overfitting decisions to a narrow simulation regime (`hard_only` defaults).
  - Mitigation: Schedule targeted cross-setting checks and track any regressions in easy/medium or other dims.
