# Research Template Bundle

This folder is a portable bundle for running the Codex native research loop in any target workspace.

## Included Files
- RESEARCH_NATIVE_LOOP_TEMPLATE.json
- loop.md
- scripts/Research_native_loop.ps1
- RESEARCH_GOALS.md
- RESEARCH_PLAN.md
- FINDINGS.md

## Quick Use
1. Place this entire `Research_Template` folder under your workspace root.
2. Fill in `RESEARCH_GOALS.md`, `RESEARCH_PLAN.md`, and `FINDINGS.md`.
3. In Codex chat, use one short phrase:

```text
run research template
```

or

```text
run research loop
```

4. Terminal command:

```powershell
powershell -ExecutionPolicy Bypass -File .\Research_Template\scripts\Research_native_loop.ps1
```

## Portability Notes
- The script now auto-detects the correct workspace root from the template path when current shell directory is different.
- The script validates that required docs exist before execution:
  - `Research_Template/RESEARCH_GOALS.md`
  - `Research_Template/RESEARCH_PLAN.md`
  - `Research_Template/FINDINGS.md`
- For real completion target (`quality_score >= 0.95`), do not use `-DryRun`.
- `-MaxIterations 1` is useful for smoke checks only; use higher value (or default unlimited) for completion runs.

If `Research_Template` is not present in a workspace, AI should prompt you to place/copy this folder first before loop execution.

## Runtime Visibility and Tracing
- Live execution output is streamed by default in CLI.
- Step-level trace file:
  - `.\Research_Template\runtime\runs\<run_id>\execution_trace.jsonl`
- Heartbeat log:
  - `.\Research_Template\runtime\runs\<run_id>\heartbeat.log`
- Auto-merge bootstrap artifacts:
  - `bootstrap_snapshot.json`
  - `merge_baseline.json`
  - `reused_items_verified.md`
- Context control artifacts (adaptive):
  - `context_pressure.json`
  - `context_snapshot.json`
  - `context_snapshot.md`
  - `iter_<n>_context_checkpoint.json`
  - `iter_<n>_context_checkpoint.md`

## Defaults
- Default mode is unlimited iterations until completion (`max_iterations = 0`).
- Final completion gate:
  - Director final signoff required
  - Evaluator quality score must be `>= 0.95`
- Major milestone event:
  - quality score `>= 0.90` triggers immediate Director deep intervention.
- Context policy:
  - rolling-thread continuity by default
  - Evaluator can enforce adaptive compression checkpoints when context pressure rises.

## Concurrency Protection
- Active run lock:
  - `.\Research_Template\runtime\active.lock`
- Latest run pointer:
  - `.\Research_Template\runtime\latest_run.txt`
