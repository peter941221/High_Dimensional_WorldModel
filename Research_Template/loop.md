# Research Loop Guide (CLI-only)

## 0) One-line Contract

```text
Input  : Ultimate research goals + plan + current findings + repository context
Output : Director-signed research completion with validated evidence and residual risk
```

---

## 1) Role Architecture

```text
                +-----------------------------+
                | Director (Professor)        |
                | Preflight + post-iteration  |
                +-------------+---------------+
                              |
                              v
                +-------------+---------------+
                | Researcher (PhD Executor)   |
                | Implements next research    |
                +-------------+---------------+
                              |
                              v
                +-------------+---------------+
                | Evaluator (Hidden Scorer)   |
                | quality/progress/risk gate  |
                +-------------+---------------+
                              |
                              v
                  {Director final + score>=0.95?}
                     | Yes                | No
                     v                    v
                [Finalize]       [Next Direction Loop]
```

---

## 2) Mandatory Flow

```text
(Start)
  |
  v
[Bootstrap Merge]
  - smart scan repo/docs/code/tests
  - estimate baseline progress
  - reuse prior work with confidence check
  |
  v
[Director Preflight]
  - set first research direction
  |
  v
[Researcher Iteration]
  |
  v
[Evaluator JSON Gate]
  - approved / quality_score / progress_pct / risk
  - adaptive compression authority when context pressure is high
  |
  v
[Director Post Note]
  - compact actionable guidance
  - evaluator tie-break if directions conflict
  |
  v
{25/50/75/100 or quality>=0.90 or stall/risk spike?}
  | Yes
  v
[Director Full Intervention]
  |
  +-----------------------> back to Researcher (commit and push during steps)
```

```text
Context Handling
├─ Default: rolling thread continuity
├─ Evaluator monitors context pressure each iteration
├─ Composite triggers: size/stall/drift
└─ If triggered: enforce checkpoint compression (JSON + Markdown)
```

---

## 3) Completion and Quality Gates

1. Final completion requires:
   - `director_approved_final = true`
   - `quality_score >= 0.95`
2. Major milestone:
   - `quality_score >= 0.90` triggers immediate Director deep intervention.
3. Default mode:
   - `max_iterations = 0` (unlimited until completion).

---

## 4) Runtime Safety

```text
Safety
├─ no_silent_stop = true
├─ live console output = true
├─ active lock = Research_Template/runtime/active.lock
├─ heartbeat every 45s
├─ step trace = execution_trace.jsonl
├─ max_idle_minutes = 8
├─ retry 3x with backoff (5/15/30)
├─ blocker short-circuit on blocked patterns
├─ rolling-thread context packets
├─ evaluator-driven adaptive compression
└─ blocked => blocker_report.md + reproducible resume command
```

---

## 5) Commands

### 5.1 Default Run

```powershell
powershell -ExecutionPolicy Bypass -File .\Research_Template\scripts\Research_native_loop.ps1
```

### 5.2 Dry Run

```powershell
powershell -ExecutionPolicy Bypass -File .\Research_Template\scripts\Research_native_loop.ps1 -DryRun
```

### 5.3 Quiet Mode

```powershell
powershell -ExecutionPolicy Bypass -File .\Research_Template\scripts\Research_native_loop.ps1 -NoLiveOutput
```

---

## 6) Artifact Layout

```text
Research_Template/runtime/
├─ active.lock
├─ latest_run.txt
└─ runs/
   └─ <run_id>/
      ├─ state.json
      ├─ heartbeat.log
      ├─ execution_trace.jsonl
      ├─ final_report.md
      ├─ blocker_report.md
      ├─ bootstrap_snapshot.json
      ├─ merge_baseline.json
      ├─ reused_items_verified.md
      ├─ context_pressure.json
      ├─ context_snapshot.json
      ├─ context_snapshot.md
      ├─ iter_<n>_context_checkpoint.json
      ├─ iter_<n>_context_checkpoint.md
      └─ iter_*_*.txt
```

---

## 7) Trigger Hint

```text
run research template
```

or

```text
run research loop
```
