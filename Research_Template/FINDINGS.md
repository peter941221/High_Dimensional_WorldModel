# Findings

## Executive Summary
- The robustness operating default is locked to `scale=0.20`, `profile=conservative`, `difficulties=hard_only`.
- Higher-dimensional pretraining remains directionally beneficial for 3D transfer, but source-dimension ranking is weak-order rather than decisive.
- Training-time guidance OFF vs ON causality is explicitly downgraded to **inconclusive** for this closure cycle (Path B).

## Iteration Update (2026-03-01 Final Closure)
- Regenerated director closure artifact:
  - `report/director_evidence_closure_final.json`
  - `report/director_evidence_closure_final.md`
- Re-ran and locked training-time guidance OFF vs ON significance:
  - `report/guidance_off_vs_on_5seed_significance_finallock.json`
  - `report/guidance_off_vs_on_5seed_significance_finallock.md`
- Published explicit causality lock:
  - `report/guidance_off_vs_on_causality_lock_final.json`
  - `report/guidance_off_vs_on_causality_lock_final.md`
- Final synthesis artifacts updated to non-draft final state:
  - `report/director_final_executive.md`
  - `report/director_final_technical.md`
- Runtime packaging record published:
  - `Research_Template/runtime/final_report.md`
  - `Research_Template/runtime/state.json`
  - `Research_Template/runtime/runs/research_20260301_ultimate_closure/final_report.md`

## Iteration Update (2026-03-01 Optional Path A Addendum)
- Found that additional `p_guidance_off` seed runs already existed for seeds `66` and `77` (baseline + transfer); regenerated missing robustness output for seed `77`.
- Built `results/p0_freeze/p_guidance_off_7seed/p0_summary.json` from the existing per-seed outputs.
- Re-ran paired significance vs `p2_v2_9seed`:
  - `report/guidance_off_vs_on_7seed_significance.json` (`n=7`, key transfer KPIs `p=0.015625`).
- Interpretation caveat: the compared pipelines differ in domain randomization settings; treat this as a pipeline comparison, not an isolated guidance-only training ablation.

## Key Findings
1. `scale=0.20` remains preferred over `0.25` under final paired evidence (no measurable gain from `0.25`).
2. Matched-compute ranking remains `4D ~= 5D > 6D ~= 8D`, with no pairwise significance at alpha 0.05.
3. Latent mechanism evidence still favors `phys_residual` over `gru/rssm` in paired tests.
4. Guidance checkpoint-fixed evaluations show strong benefit vs model-only, but this does not prove training-time causality.
5. Guidance OFF vs ON paired evidence reaches statistical significance at `n=7` (`p=0.015625` on key transfer KPIs), but causal attribution to guidance alone remains unproven because the compared pipelines are not matched on domain randomization settings.

## Evidence Log
- Claim:
  - Operational robustness default remains `0.20 + hard_only + conservative`.
  - Evidence source: `report/kaggle_hifinal_hard020_vs_hard025_5seed_significance.json`, `report/kaggle_hiconf_hard020_10seed_summary.json`.
  - Confidence: High
- Claim:
  - Training-time guidance causality remains *confounded* (not isolated to guidance-only) in the current OFF vs ON comparison, despite stronger paired evidence with more seeds.
  - Evidence source: `report/guidance_off_vs_on_5seed_significance_finallock.json`, `report/guidance_off_vs_on_7seed_significance.json`, `report/guidance_off_vs_on_causality_lock_final.json`.
  - Confidence: Medium
- Claim:
  - Closure synthesis is reproducibly regenerated and packaged.
  - Evidence source: `report/director_evidence_closure_final.json`, `Research_Template/runtime/final_report.md`.
  - Confidence: High

## Limitations
- Simulation-only evidence; no real-world deployment validation.
- Guidance training-time causality is not isolated (domain-randomization settings differ between OFF vs ON pipelines).
- Dimension ranking remains weak-order.

## Open Questions
- Which representation features in >3D pretraining causally drive transfer gains?
- Would a matched-setting guidance-only ablation (ideally `n>=9` paired seeds) confirm training-time causality without confounds?
- How stable is the `hard_only` recommendation across expanded task families?

## Guidance OFF vs ON: Paired-seed power note

- Under `paired_exact_signflip` (exact sign-flip permutation test on the mean delta), the two-sided p-value is `p = 2 / 2^n = 1 / 2^(n-1)` when all per-seed deltas share the same sign (non-zero).
  - Historic lock: `n=5` paired seeds (`[11, 22, 33, 44, 55]`) yielded `p=0.0625` on key transfer KPIs (`report/guidance_off_vs_on_5seed_significance_finallock.json`).
  - Addendum: `n=7` paired seeds (`[11, 22, 33, 44, 55, 66, 77]`) yields `p=0.015625` on key transfer KPIs (`report/guidance_off_vs_on_7seed_significance.json`).
- Minimal significance threshold: if the next paired seed preserves sign (i.e., 6/6 aligned, non-zero), then `p = 1/2^(6-1) = 0.03125` (< 0.05).
- "Decisive" planning: `n=9` yields `p = 1/2^(9-1) = 0.00390625` if all 9 align; and even 8/9 sign agreement has a conservative, magnitude-agnostic two-sided sign-test bound `p = 0.0390625` (< 0.05), motivating the `>=9` recommendation.

```text
Optional Path A decision flow (guidance OFF vs ON)

(7 paired seeds) p=0.015625 on transfer KPIs (significant)
             |
             v
Need more decisiveness / less confounding?
   |-------------------|
   | No                | Yes
   v                   v
Keep Path B        Run to 9 seeds (or matched-setting ablation)
(still confounded)      |
                        v
               Re-run significance_report.py
                        |
                        v
                {p<0.05 on transfer KPIs?}
                    |             |
                   Yes            No
                    v             v
             Upgrade evidence  Keep bounded language
```

## Recommended Next Actions
1. Optional Path A (decisiveness): add the missing seeds (`88`, `99`) to reach `n=9`, then re-run `significance_report.py`.
2. Optional Path A (causal isolation): run a matched-setting guidance-only ON vs OFF ablation (same domain-rand settings) if the goal is *training-time guidance causality* rather than a pipeline comparison.
3. Keep causal language bounded until matched-setting evidence is produced; treat current OFF vs ON paired significance as pipeline-level evidence.

## Maintenance Checkpoint (2026-03-01)
- Mode: maintenance (claims locked; no new causal upgrade run executed).
- Risk Tier: L (documentation/state verification only; no model/training changes).
- Validation actions:
  - `Get-Content Research_Template/runtime/final_report.md -TotalCount 20` -> PASS (`director_approved_final: true`, `quality_score: 0.96`, `progress_pct: 100`).
  - `Get-Content Research_Template/runtime/state.json -TotalCount 20` -> PASS (`"director_approved_final": true`, `"quality_score": 0.96`).
  - `Test-Path report/director_final_executive.md; Test-Path report/director_final_technical.md` -> PASS (`True`, `True`).
  - `Get-Content -Raw Research_Template/runtime/active.lock` -> PASS (lock points to live loop run `research_20260301_111322`, `pid=16040`).
  - `Get-CimInstance Win32_Process -Filter "ProcessId = 16040"` -> PASS (process command line confirms active `Research_native_loop.ps1` invocation).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` + `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (pointer/state divergence confirmed and interpreted safely: `latest_run` tracks active loop; authoritative approval baseline remains root `state.json`).
- Coverage:
  - Runtime signoff gate fields remain satisfied.
  - Final executive + technical synthesis artifacts remain present.
  - Path B causal downgrade remains explicitly locked at 5 paired seeds.
  - Runtime pointer integrity interpretation is now explicitly documented for maintenance cycles.
- Residual risk:
  - Training-time guidance causality remains inconclusive (`p=0.0625`) until optional Path A (>=9 paired seeds) is executed.

## Maintenance Checkpoint (2026-03-01 Iteration 1 Runtime Hygiene Re-check)
- Mode: maintenance (Path B baseline preserved; no new causal claim expansion).
- Risk Tier: L (runtime hygiene verification and evidence logging only).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` -> PASS (`run_id=research_20260301_115446`, `pid=4200`).
  - `Get-CimInstance Win32_Process -Filter "ProcessId=4200"` -> PASS (`process_alive=true`; command line includes `Research_native_loop.ps1`).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (points to active run path `.../research_20260301_115446`).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (`run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-Content -Raw Research_Template/runtime/final_report.md` -> PASS (approved closure report still present with same gate values).
- Coverage:
  - Active lock-process binding is live and valid.
  - Runtime pointer reflects active maintenance loop ownership.
  - Authoritative approval baseline remains intact in root runtime state/report.
- Residual risk:
  - Pointer/state divergence is expected during active loop ownership and should be re-checked again after active lock release.
  - Optional Path A (>=9 paired OFF vs ON seeds) is still required for stronger causal decisiveness.

## Maintenance Checkpoint (2026-03-01 Iteration 1 Runtime Hygiene Addendum B)
- Mode: maintenance (approved baseline preserved; no core-claim reopen).
- Risk Tier: L (runtime-state verification only; no training/codepath claim changes).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` -> PASS (`run_id=research_20260301_121956`, `pid=9240`).
  - `Get-Process -Id 9240 -ErrorAction SilentlyContinue` -> PASS (live `powershell` process; lock ownership remains active).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (points to active run path `.../runs/research_20260301_121956`).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_121956/state.json` -> PASS (`status=running`, `current_iteration=1`).
  - `Test-Path Research_Template/runtime/runs/research_20260301_121956/iter_0_bootstrap_merge.txt` -> PASS (`True`; bootstrap merge artifact exists for this active run).
  - `Get-Content -Raw Research_Template/runtime/state.json` + `Get-Content -Raw Research_Template/runtime/final_report.md` -> PASS (authoritative root baseline still `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
- Coverage:
  - Confirms active lock is live and mapped to the current active maintenance run.
  - Confirms `latest_run` pointer tracks active ownership while root approval baseline remains unchanged.
  - Resolves one stale risk detail in rolling context: for run `research_20260301_121956`, bootstrap merge artifact is present (not missing).
- Residual risk:
  - Active run is still executing; runtime metadata can continue changing until lock release.
  - Optional Path A (>=9 paired OFF vs ON seeds) remains required for stronger causal decisiveness.

## Maintenance Checkpoint (2026-03-01 Iteration 2 Canonical Integrity Addendum)
- Mode: maintenance (canonical package preserved; no conclusion reopen).
- Risk Tier: L (runtime hygiene and artifact-integrity verification only).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 9240 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_121956`, lock owner process alive).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_121956/state.json` -> PASS (`status=running`, `current_iteration=2`, `process_approval_satisfied=false`).
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTime -gt [datetime]'2026-03-01T10:28:40' }` -> PASS (no materially new post-closure primary-source evidence detected).
  - `Get-FileHash -Algorithm SHA256` on canonical files -> PASS (integrity fingerprints captured):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
- Coverage:
  - Confirms active maintenance loop liveness without mutating lock ownership.
  - Confirms canonical closure package content integrity via explicit hashes.
  - Confirms no materially new primary-source evidence was introduced; full loop escalation is not triggered.
- Residual risk:
  - Active run remains live, so runtime metadata can continue to evolve until lock release.
  - Guidance OFF vs ON causal decisiveness remains pending Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 3 Pointer/State Hygiene Addendum)
- Mode: maintenance (canonical package preserved; no conclusion reopen).
- Risk Tier: L (runtime lock/pointer/state normalization check only; no experimental reruns).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 9240 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_121956`, process alive).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (stores absolute run path); normalized basename maps to `research_20260301_121956` and matches lock ownership.
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_121956/state.json` -> PASS (`status=running`, but gate fields still `quality_score=0`, `progress_pct=0` while loop is active).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_121956/context_snapshot.json` -> PASS (active snapshot goals state remains `quality_score=0.97`, `progress_pct=100` for this maintenance thread).
  - `Test-Path Research_Template/runtime/runs/research_20260301_121956/iter_0_bootstrap_merge.txt` -> PASS (`True`).
  - `Get-Content -Raw Research_Template/runtime/state.json` + `Get-Content -Raw Research_Template/runtime/final_report.md` -> PASS (authoritative baseline unchanged: `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-FileHash -Algorithm SHA256` on canonical package files -> PASS (all hashes unchanged vs prior checkpoint).
- Coverage:
  - Confirms lock ownership remains live and pointer path format is interpretable via normalized run ID.
  - Confirms canonical final package integrity remains stable with unchanged fingerprints.
  - Confirms no materially new primary-source evidence was introduced; no full-loop escalation triggered.
- Residual risk:
  - Active-run `state.json` gate fields (`0/0`) can diverge from context snapshot while loop is in-flight and may confuse naive automation.
  - `latest_run.txt` path-vs-run-id representation mismatch across files requires normalization in external checks.
  - Guidance OFF vs ON causal decisiveness remains pending Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 4 Active-Run Alignment Addendum)
- Mode: maintenance (Path B closure baseline locked; no causal axis reopen).
- Risk Tier: L (runtime integrity verification only; no training/experiment changes).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_125457`, process alive).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (pointer path basename `research_20260301_125457` matches lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (active run state exists; `status=running`, `current_iteration=1`).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (canonical baseline unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-Content -Raw Research_Template/runtime/final_report.md` -> PASS (`director_approved_final: true`, `quality_score: 0.96` present).
  - `Test-Path report/director_final_executive.md; Test-Path report/director_final_technical.md` -> PASS (`True`, `True`).
- Coverage:
  - Confirms lock/pointer alignment for the current active run.
  - Confirms approved canonical closure state/report remains unchanged.
  - Confirms executive and technical final artifacts remain present.
- Residual risk:
  - Active run metadata may continue changing until lock release.
  - Training-time guidance OFF vs ON causality remains inconclusive at current power and still requires Optional Path A (>=9 paired seeds) for stronger decisiveness.

## Maintenance Checkpoint (2026-03-01 Iteration 3 Canonical Drift Monitor)
- Mode: maintenance (Path B locked; integrity-only monitoring).
- Risk Tier: L (runtime/state/artifact verification only; no experimental reruns).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_125457`, process alive, start `2026-03-01 12:54:56`).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (absolute path basename `research_20260301_125457`, aligned with active lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (`status=running`, `current_iteration=3`, `process_approval_satisfied=false` while in-flight).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/context_snapshot.json` -> PASS (latest stored snapshot remains iteration 2 with goals state `quality_score=0.98`, `progress_pct=100`).
  - `Get-Content -Raw Research_Template/runtime/state.json` + `Get-Content -Raw Research_Template/runtime/final_report.md` -> PASS (canonical baseline unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Test-Path report/director_final_executive.md; Test-Path report/director_final_technical.md; Test-Path report/director_evidence_closure_final.json; Test-Path report/guidance_off_vs_on_causality_lock_final.json` -> PASS (`True`, `True`, `True`, `True`).
  - `Get-FileHash -Algorithm SHA256` on canonical closure artifacts -> PASS (all unchanged vs prior integrity checkpoint):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTime -gt [datetime]'2026-03-01T10:28:40' }` -> PASS (no materially new post-closure primary experimental evidence detected).
- Coverage:
  - Confirms active lock/pointer/state coherence for the current maintenance run.
  - Confirms canonical approval source-of-truth (`runtime/state.json`) and final package files remain unchanged and present.
  - Confirms no new primary evidence was introduced; closure claims remain locked.
- Residual risk:
  - Active-run metadata is still mutable while lock ownership is live.
  - Snapshot cadence can lag active state iteration counters during in-flight loops.
  - Guidance OFF vs ON causal decisiveness remains unresolved without Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 4 Canonical Authority Monitor)
- Mode: maintenance (Path B closure locked; integrity-only monitoring).
- Risk Tier: L (runtime/state integrity checks only; no experiment reruns).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_125457`, process alive, start `2026-03-01 12:54:56`).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (absolute path basename is `research_20260301_125457`, aligned with active lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (`status=approved_continuing`, `current_iteration=4`, `process_approval_satisfied=true`).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/context_snapshot.json` -> PASS (latest snapshot remains iteration 3 with `quality_score=0.98`, `progress_pct=100`; expected snapshot lag while loop remains active).
  - `Get-Content -Raw Research_Template/runtime/state.json` + `Get-Content -Raw Research_Template/runtime/final_report.md` -> PASS (canonical baseline unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-FileHash -Algorithm SHA256` on canonical closure package -> PASS (all fingerprints unchanged):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTime -gt $closureBoundary }` with `$closureBoundary=max(last write of director_evidence_closure_final.{json,md})=2026-03-01T10:28:40.214` -> PASS (no files newer than closure boundary).
- Coverage:
  - Confirms live active-loop ownership is coherent across lock + pointer + active state.
  - Confirms authoritative canonical approval source remains root `runtime/state.json`.
  - Confirms closure package integrity via unchanged SHA256 hashes.
  - Confirms no post-closure primary evidence drift in `report/`.
- Residual risk:
  - Active-run metadata remains mutable until lock release.
  - Guidance OFF vs ON training-time causality remains inconclusive at current power (`p=0.0625`, 5 paired seeds); stronger decisiveness still requires Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 5 Canonical Integrity Monitor)
- Mode: maintenance (Path B closure locked; integrity-only monitoring).
- Risk Tier: L (runtime/state/artifact integrity verification only; no new experiments).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_125457`, process alive).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (basename `research_20260301_125457` matches lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (`status=approved_continuing`, `current_iteration=5`, `process_approval_satisfied=true`).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (canonical authority unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-FileHash -Algorithm SHA256` on canonical closure package -> PASS (all fingerprints unchanged vs prior checkpoint):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTime -gt [datetime]'2026-03-01T10:28:40.2143259' }` -> PASS (no newer files found in `report/` after closure boundary).
- Coverage:
  - Confirms lock/pointer/process alignment for active maintenance run.
  - Confirms root canonical authority remains unchanged and approved.
  - Confirms canonical closure artifact package integrity via unchanged SHA256 fingerprints.
  - Confirms no post-closure primary experimental evidence drift in `report/`.
- Residual risk:
  - Active-run metadata can continue changing until lock release.
  - Training-time guidance OFF vs ON causality remains inconclusive at current power (`p=0.0625`, 5 paired seeds); stronger decisiveness still requires Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 6 Canonical Integrity Monitor)
- Mode: maintenance (Path B closure locked; integrity-only monitoring).
- Risk Tier: L (runtime/state/artifact integrity verification only; no new experiments).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_125457`, process alive).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (absolute path basename `research_20260301_125457` matches lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (`status=approved_continuing`, `current_iteration=6`, `process_approval_satisfied=true`).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (canonical authority unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-FileHash -Algorithm SHA256` on canonical closure package -> PASS (all fingerprints unchanged vs prior checkpoint):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTimeUtc -gt [datetime]'2026-03-01T02:28:40.2143259Z' }` -> PASS (no newer files found in `report/` after closure boundary).
- Coverage:
  - Confirms lock/pointer/process coherence for active maintenance run.
  - Confirms root canonical authority remains unchanged and approved.
  - Confirms canonical closure artifact package integrity via unchanged SHA256 fingerprints.
  - Confirms no post-closure primary experimental evidence drift in `report/`.
- Residual risk:
  - Active-run metadata can continue changing until lock release.
  - Training-time guidance OFF vs ON causality remains inconclusive at current power (`p=0.0625`, 5 paired seeds); stronger decisiveness still requires Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 7 Canonical Integrity Monitor)
- Mode: maintenance (Path B closure locked; integrity-only monitoring).
- Risk Tier: L (runtime/state/artifact integrity verification only; no new experiments).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_125457`, process alive).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (absolute path basename `research_20260301_125457` matches lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (`status=approved_continuing`, `current_iteration=7`, `process_approval_satisfied=true`).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (canonical authority unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-FileHash -Algorithm SHA256` on canonical closure package -> PASS (all fingerprints unchanged vs prior checkpoint):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTimeUtc -gt [datetime]'2026-03-01T02:28:40.2143259Z' }` -> PASS (no newer files found in `report/` after closure boundary).
- Coverage:
  - Confirms lock/pointer/process coherence for active maintenance run.
  - Confirms root canonical authority remains unchanged and approved.
  - Confirms canonical closure artifact package integrity via unchanged SHA256 fingerprints.
  - Confirms no post-closure primary experimental evidence drift in `report/`.
- Residual risk:
  - Active-run metadata can continue changing until lock release.
  - Training-time guidance OFF vs ON causality remains inconclusive at current power (`p=0.0625`, 5 paired seeds); stronger decisiveness still requires Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 8 Canonical Integrity Monitor)
- Mode: maintenance (Path B closure locked; integrity-only monitoring).
- Risk Tier: L (runtime/state/artifact integrity verification only; no new experiments).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction Stop` -> PASS (`run_id=research_20260301_125457`, process alive).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (absolute path basename `research_20260301_125457` matches lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (`status=approved_continuing`, `current_iteration=8`, `process_approval_satisfied=true`).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (canonical authority unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-FileHash -Algorithm SHA256` on canonical closure package -> PASS (all fingerprints unchanged vs prior checkpoint):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTimeUtc -gt [datetime]'2026-03-01T02:28:40.2143259Z' }` -> PASS (no newer files found in `report/` after closure boundary).
- Coverage:
  - Confirms lock/pointer/process coherence for active maintenance run.
  - Confirms root canonical authority remains unchanged and approved.
  - Confirms canonical closure artifact package integrity via unchanged SHA256 fingerprints.
  - Confirms no post-closure primary experimental evidence drift in `report/`.
- Residual risk:
  - Active-run metadata can continue changing until lock release.
  - Training-time guidance OFF vs ON causality remains inconclusive at current power (`p=0.0625`, 5 paired seeds); stronger decisiveness still requires Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 9 Canonical Integrity Monitor)
- Mode: maintenance (Path B closure locked; integrity-only monitoring).
- Risk Tier: L (runtime/state/artifact integrity verification only; no new experiments).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction Stop` -> PASS (`run_id=research_20260301_125457`, process alive).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (absolute path basename `research_20260301_125457` matches lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (`status=approved_continuing`, `current_iteration=9`, `process_approval_satisfied=true`).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (canonical authority unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-FileHash -Algorithm SHA256` on canonical closure package -> PASS (all fingerprints unchanged vs prior checkpoint):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTimeUtc -gt [datetime]'2026-03-01T02:28:40.2143259Z' }` -> PASS (no newer files found in `report/` after closure boundary).
- Coverage:
  - Confirms lock/pointer/process coherence for active maintenance run.
  - Confirms root canonical authority remains unchanged and approved.
  - Confirms canonical closure artifact package integrity via unchanged SHA256 fingerprints.
  - Confirms no post-closure primary experimental evidence drift in `report/`.
- Residual risk:
  - Active-run metadata can continue changing until lock release.
  - Training-time guidance OFF vs ON causality remains inconclusive at current power (`p=0.0625`, 5 paired seeds); stronger decisiveness still requires Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 10 Canonical Integrity Monitor)
- Mode: maintenance (Path B closure locked; integrity-only monitoring).
- Risk Tier: L (runtime/state/artifact integrity verification only; no new experiments).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_125457`, process alive).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (absolute path basename `research_20260301_125457` matches lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (`status=approved_continuing`, `current_iteration=10`, `process_approval_satisfied=true`).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (canonical authority unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-FileHash -Algorithm SHA256` on canonical closure package -> PASS (all fingerprints unchanged vs prior checkpoint):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTimeUtc -gt [datetime]'2026-03-01T02:28:40.2143259Z' }` -> PASS (no newer files found in `report/` after closure boundary).
- Coverage:
  - Confirms lock/pointer/process coherence for active maintenance run.
  - Confirms root canonical authority remains unchanged and approved.
  - Confirms canonical closure artifact package integrity via unchanged SHA256 fingerprints.
  - Confirms no post-closure primary experimental evidence drift in `report/`.
- Residual risk:
  - Active-run metadata can continue changing until lock release.
  - Training-time guidance OFF vs ON causality remains inconclusive at current power (`p=0.0625`, 5 paired seeds); stronger decisiveness still requires Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 11 Canonical Integrity Monitor)
- Mode: maintenance (Path B closure locked; integrity-only monitoring).
- Risk Tier: L (runtime/state/artifact integrity verification only; no new experiments).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_125457`, process alive).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (absolute path basename `research_20260301_125457` matches lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (`status=approved_continuing`, `current_iteration=11`, `process_approval_satisfied=true`).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (canonical authority unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-FileHash -Algorithm SHA256` on canonical closure package -> PASS (all fingerprints unchanged vs prior checkpoint):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTimeUtc -gt [datetime]'2026-03-01T02:28:40.2143259Z' }` -> PASS (no newer files found in `report/` after closure boundary).
- Coverage:
  - Confirms lock/pointer/process coherence for active maintenance run.
  - Confirms root canonical authority remains unchanged and approved.
  - Confirms canonical closure artifact package integrity via unchanged SHA256 fingerprints.
  - Confirms no post-closure primary experimental evidence drift in `report/`.
- Residual risk:
  - Active-run metadata can continue changing until lock release.
  - Training-time guidance OFF vs ON causality remains inconclusive at current power (`p=0.0625`, 5 paired seeds); stronger decisiveness still requires Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 12 Canonical Integrity Monitor)
- Mode: maintenance (Path B closure locked; integrity-only monitoring).
- Risk Tier: L (runtime/state/artifact integrity verification only; no new experiments).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_125457`, process alive).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (absolute path basename `research_20260301_125457` matches lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (`status=approved_continuing`, `current_iteration=12`, `process_approval_satisfied=true`).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (canonical authority unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-FileHash -Algorithm SHA256` on canonical closure package -> PASS (all fingerprints unchanged vs prior checkpoint):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTimeUtc -gt [datetime]'2026-03-01T02:28:40.2143259Z' }` -> PASS (no newer files found in `report/` after closure boundary).
- Coverage:
  - Confirms lock/pointer/process coherence for active maintenance run.
  - Confirms root canonical authority remains unchanged and approved.
  - Confirms canonical closure artifact package integrity via unchanged SHA256 fingerprints.
  - Confirms no post-closure primary experimental evidence drift in `report/`.
- Residual risk:
  - Active-run metadata can continue changing until lock release.
  - Training-time guidance OFF vs ON causality remains inconclusive at current power (`p=0.0625`, 5 paired seeds); stronger decisiveness still requires Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 13 Canonical Integrity Monitor)
- Mode: maintenance (Path B closure locked; integrity-only monitoring).
- Risk Tier: L (runtime/state/artifact integrity verification only; no new experiments).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Process -Id 4632 -ErrorAction SilentlyContinue` -> PASS (`run_id=research_20260301_125457`, process alive).
  - `Get-Content -Raw Research_Template/runtime/latest_run.txt` -> PASS (basename `research_20260301_125457` matches lock run ID).
  - `Get-Content -Raw Research_Template/runtime/runs/research_20260301_125457/state.json` -> PASS (`status=approved_continuing`, `current_iteration=13`, `process_approval_satisfied=true`).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (canonical authority unchanged: `run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-FileHash -Algorithm SHA256` on canonical closure package -> PASS (all fingerprints unchanged vs prior checkpoint):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTimeUtc -gt [datetime]'2026-03-01T02:28:40.2143259Z' }` -> PASS (no newer files found in `report/` after closure boundary).
- Coverage:
  - Confirms lock/pointer/process coherence for active maintenance run.
  - Confirms root canonical authority remains unchanged and approved.
  - Confirms canonical closure artifact package integrity via unchanged SHA256 fingerprints.
  - Confirms no post-closure primary experimental evidence drift in `report/`.
- Residual risk:
  - Active-run metadata can continue changing until lock release.
  - Training-time guidance OFF vs ON causality remains inconclusive at current power (`p=0.0625`, 5 paired seeds); stronger decisiveness still requires Optional Path A (>=9 paired seeds).

## Maintenance Checkpoint (2026-03-01 Iteration 1 Canonical Freeze Revalidation)
- Mode: maintenance (Path B closure remains canonical; no causal-axis reopen).
- Risk Tier: L (documentation/runtime integrity verification only; no training changes).
- Validation actions:
  - `Get-Content -Raw Research_Template/runtime/active.lock` + `Get-Content -Raw Research_Template/runtime/latest_run.txt` + `Get-Process -Id 13588 -ErrorAction SilentlyContinue` -> PASS (active run `research_20260301_163804` is live and pointer-aligned).
  - `Get-Content -Raw Research_Template/runtime/state.json` -> PASS (`run_id=research_20260301_ultimate_closure`, `director_approved_final=true`, `quality_score=0.96`, `progress_pct=100`).
  - `Get-Content -Raw Research_Template/runtime/final_report.md` -> PASS (final package still reports approved closure and same gate values).
  - `Test-Path` on final artifacts (`report/director_final_executive.md`, `report/director_final_technical.md`, `report/director_evidence_closure_final.json`, `report/guidance_off_vs_on_causality_lock_final.json`) -> PASS (all `True`).
  - `Get-FileHash -Algorithm SHA256` on canonical package -> PASS (all fingerprints unchanged):
    - `Research_Template/runtime/state.json` -> `A857760C1910D1738C60BDD1FEF7BEE0FBE39070DDC3E1F47477A537D9A63B55`
    - `Research_Template/runtime/final_report.md` -> `89659F53A6152BF1474AF820ACEA120C824748B8223804A5B21C20B10E6BED0A`
    - `report/director_final_executive.md` -> `CB930CF40F2855DD66F73115EB2573F1811F50438FA8396E32EADFD7427A165D`
    - `report/director_final_technical.md` -> `A02EB92E9FF681F79F3A2904B24872440C7825368FFA968DF4CB84E8A8425390`
    - `report/director_evidence_closure_final.json` -> `5E263DECB1420AABA47226AF7A86AEF47A1FDE9529C3C8FA0CD61C29AEE8C094`
    - `report/guidance_off_vs_on_causality_lock_final.json` -> `4E873C83CF211E5DD5C14159D0A2116388F9E25155421E97CFBB17D4F451408A`
  - `Get-ChildItem report -File | Where-Object { $_.LastWriteTimeUtc -gt [datetime]'2026-03-01T02:28:40.2143259Z' }` -> PASS (no post-closure report drift).
- Coverage:
  - Confirms canonical authority fields still meet final gate requirements.
  - Confirms executive + technical + closure-lock artifacts are present and unchanged.
  - Confirms no newer primary report evidence has appeared to force synthesis reopening.
- Residual risk:
  - Active-run metadata may continue changing while lock ownership remains active.
  - Guidance OFF vs ON training-time causality is still inconclusive at 5 paired seeds (`p=0.0625`) and requires Optional Path A (>=9 paired seeds) only if stronger decisiveness is required.
