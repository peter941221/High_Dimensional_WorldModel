from __future__ import annotations

import argparse
import glob
import itertools
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from envs.push_ball import PushBallNDEnv
from experiments.common import save_json
from experiments.policy_guidance import guided_push_action
from models.policy import PolicyNetwork


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate director-ready evidence closure report (ranking + mechanism attribution)."
    )
    parser.add_argument(
        "--cohort-summary",
        type=Path,
        default=ROOT / "report" / "kaggle_hiconf_hard020_10seed_summary.json",
        help="Cohort summary JSON containing seed/run_id rows (default: hard020 10-seed summary).",
    )
    parser.add_argument(
        "--guidance-prefix",
        type=str,
        default="p2_v2_9seed",
        help="Checkpoint run prefix under checkpoints/baseline/<prefix>_s<seed>/dim3_latest.pt",
    )
    parser.add_argument(
        "--guidance-seeds",
        type=int,
        nargs="+",
        default=[11, 22, 33, 44, 55, 66, 77, 88, 99],
    )
    parser.add_argument("--guidance-episodes", type=int, default=20)
    parser.add_argument("--guidance-max-steps", type=int, default=120)
    parser.add_argument(
        "--randomization-reports",
        type=Path,
        nargs="+",
        default=[
            ROOT / "report" / "release_significance_p0_vs_p2v2_9seed.json",
            ROOT / "report" / "kaggle_next_hard002_vs_hard020_9seed_significance.json",
        ],
    )
    parser.add_argument("--report-name", type=str, default="director_evidence_closure_iter1")
    return parser.parse_args()


def _mean(vals: list[float]) -> float:
    return float(sum(vals) / max(len(vals), 1))


def _std(vals: list[float]) -> float:
    if len(vals) <= 1:
        return 0.0
    return float(statistics.stdev(vals))


def _exact_signflip_pvalue(diffs: list[float]) -> float:
    n = len(diffs)
    if n == 0:
        return 1.0
    observed = abs(sum(diffs) / n)
    total = 0
    extreme = 0
    for signs in itertools.product([-1.0, 1.0], repeat=n):
        total += 1
        stat = abs(sum(s * d for s, d in zip(signs, diffs)) / n)
        if stat >= observed - 1e-12:
            extreme += 1
    return extreme / total


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _find_unique(pattern: str) -> Path:
    hits = glob.glob(pattern, recursive=True)
    if not hits:
        raise FileNotFoundError(f"artifact not found for pattern: {pattern}")
    if len(hits) > 1:
        raise RuntimeError(f"ambiguous artifact for pattern: {pattern}\n{hits}")
    return Path(hits[0])


def _load_cohort_items(cohort_summary_path: Path) -> list[dict[str, Any]]:
    payload = _load_json(cohort_summary_path)
    items: list[dict[str, Any]] = []
    for row in payload.get("rows", []):
        seed = int(row["seed"])
        run_id = str(row["run_id"])
        transfer_path = _find_unique(
            str(ROOT / "kaggle_outputs" / "**" / "results" / "transfer" / run_id / "transfer.json")
        )
        ablation_path = _find_unique(
            str(ROOT / "kaggle_outputs" / "**" / "results" / "ablation" / run_id / "ablation.json")
        )
        items.append(
            {
                "seed": seed,
                "run_id": run_id,
                "transfer_path": str(transfer_path),
                "ablation_path": str(ablation_path),
            }
        )
    return items


def _build_transfer_ranking(items: list[dict[str, Any]]) -> dict[str, Any]:
    dims = [4, 5, 6, 8]
    gains_by_dim: dict[int, list[float]] = {d: [] for d in dims}
    success_by_dim: dict[int, list[float]] = {d: [] for d in dims}
    compute_by_dim: dict[int, dict[str, set[Any]]] = {
        d: {"trained_epochs": set(), "gradient_steps": set()} for d in dims
    }
    meta_sets: dict[str, set[Any]] = {
        "pretrain_epochs": set(),
        "finetune_epochs": set(),
        "max_steps": set(),
        "eval_episodes": set(),
    }

    for item in items:
        transfer_payload = _load_json(Path(item["transfer_path"]))
        by_dim = {int(r["source_dim"]): r for r in transfer_payload.get("results", [])}
        for dim in dims:
            row = by_dim[dim]
            baseline_success = float(row["baseline_success"])
            transfer_success = float(row["transfer_success"])
            gain = transfer_success - baseline_success
            gains_by_dim[dim].append(gain)
            success_by_dim[dim].append(transfer_success)
            compute_by_dim[dim]["trained_epochs"].add(int(row.get("trained_epochs", 0)))
            compute_by_dim[dim]["gradient_steps"].add(int(row.get("gradient_steps", 0)))

        meta = transfer_payload.get("meta", {})
        for key in list(meta_sets.keys()):
            meta_sets[key].add(meta.get(key))

    dim_stats = []
    for dim in dims:
        gains = gains_by_dim[dim]
        succ = success_by_dim[dim]
        dim_stats.append(
            {
                "source_dim": dim,
                "n": len(gains),
                "mean_transfer_gain": _mean(gains),
                "std_transfer_gain": _std(gains),
                "mean_transfer_success": _mean(succ),
                "std_transfer_success": _std(succ),
                "p_gain_vs_zero_signflip": _exact_signflip_pvalue(gains),
                "compute": {
                    "trained_epochs": sorted(compute_by_dim[dim]["trained_epochs"]),
                    "gradient_steps": sorted(compute_by_dim[dim]["gradient_steps"]),
                },
            }
        )

    ranking = sorted(
        dim_stats,
        key=lambda x: (-x["mean_transfer_gain"], -x["mean_transfer_success"], x["source_dim"]),
    )
    for i, row in enumerate(ranking, start=1):
        row["rank_by_mean_gain"] = i

    pairwise = []
    for a, b in itertools.combinations(dims, 2):
        diffs = [vb - va for va, vb in zip(gains_by_dim[a], gains_by_dim[b])]
        pairwise.append(
            {
                "a_dim": a,
                "b_dim": b,
                "delta_mean_gain_b_minus_a": _mean(diffs),
                "p_value_signflip": _exact_signflip_pvalue(diffs),
            }
        )

    matched_compute = {
        "global_meta_unique_values": {k: sorted(v, key=lambda x: str(x)) for k, v in meta_sets.items()},
        "per_dim_compute_unique_values": {
            str(k): {
                "trained_epochs": sorted(v["trained_epochs"]),
                "gradient_steps": sorted(v["gradient_steps"]),
            }
            for k, v in compute_by_dim.items()
        },
        "is_matched_compute": all(len(v) == 1 for v in meta_sets.values())
        and all(len(v["trained_epochs"]) == 1 and len(v["gradient_steps"]) == 1 for v in compute_by_dim.values()),
    }

    return {
        "seed_count": len(items),
        "seeds": sorted([int(x["seed"]) for x in items]),
        "run_ids": [x["run_id"] for x in sorted(items, key=lambda y: int(y["seed"]))],
        "dim_stats": dim_stats,
        "ranking": ranking,
        "pairwise_significance": pairwise,
        "matched_compute": matched_compute,
    }


def _build_latent_representation_attribution(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_model: dict[str, list[float]] = {}
    meta_sets: dict[str, set[Any]] = {"epochs": set(), "eval_episodes": set(), "dim": set()}
    for item in items:
        payload = _load_json(Path(item["ablation_path"]))
        for row in payload.get("results", []):
            model = str(row["model"])
            by_model.setdefault(model, []).append(float(row["success_rate"]))
        meta = payload.get("meta", {})
        for key in list(meta_sets.keys()):
            meta_sets[key].add(meta.get(key))

    model_stats = []
    for model, vals in sorted(by_model.items()):
        model_stats.append(
            {
                "model": model,
                "n": len(vals),
                "mean_success_rate": _mean(vals),
                "std_success_rate": _std(vals),
            }
        )
    ranking = sorted(model_stats, key=lambda x: (-x["mean_success_rate"], x["model"]))
    for i, row in enumerate(ranking, start=1):
        row["rank_by_mean_success"] = i

    pairwise = []
    models = sorted(by_model.keys())
    for a, b in itertools.combinations(models, 2):
        diffs = [vb - va for va, vb in zip(by_model[a], by_model[b])]
        pairwise.append(
            {
                "a_model": a,
                "b_model": b,
                "delta_mean_success_b_minus_a": _mean(diffs),
                "p_value_signflip": _exact_signflip_pvalue(diffs),
            }
        )

    return {
        "seed_count": len(items),
        "seeds": sorted([int(x["seed"]) for x in items]),
        "model_stats": model_stats,
        "ranking": ranking,
        "pairwise_significance": pairwise,
        "control_meta_unique_values": {k: sorted(v, key=lambda x: str(x)) for k, v in meta_sets.items()},
    }


def _evaluate_policy_mode(
    policy: PolicyNetwork,
    difficulty: str,
    mode: str,
    episodes: int,
    max_steps: int,
) -> float:
    env = PushBallNDEnv(dim=3, difficulty=difficulty, max_steps=max_steps)
    success = 0
    for ep in range(episodes):
        state = env.reset(seed=7000 + ep)
        done = False
        info = {"success": False}
        while not done:
            with torch.no_grad():
                s = torch.as_tensor(state, dtype=torch.float32)
                model_action = policy(s.unsqueeze(0)).squeeze(0)
            guide_action = guided_push_action(s, env.dim)
            if mode == "model_only":
                action = model_action
            elif mode == "guided_blend":
                action = 0.3 * model_action + 0.7 * guide_action
            elif mode == "guide_only":
                action = guide_action
            else:
                raise ValueError(f"unknown mode: {mode}")
            state, _, done, info = env.step(action.clamp(-1.0, 1.0))
        success += int(info.get("success", False))
    return success / max(episodes, 1)


def _build_guidance_attribution(
    run_prefix: str,
    seeds: list[int],
    episodes: int,
    max_steps: int,
) -> dict[str, Any]:
    difficulties = ["easy", "medium", "hard"]
    modes = ["model_only", "guided_blend", "guide_only"]

    rows: list[dict[str, Any]] = []
    missing_checkpoints: list[str] = []

    for seed in seeds:
        ckpt_path = ROOT / "checkpoints" / "baseline" / f"{run_prefix}_s{seed}" / "dim3_latest.pt"
        if not ckpt_path.exists():
            missing_checkpoints.append(str(ckpt_path))
            continue
        payload = torch.load(ckpt_path, map_location="cpu")
        env_for_shape = PushBallNDEnv(dim=3, difficulty="easy", max_steps=max_steps)
        policy = PolicyNetwork(
            state_dim=env_for_shape.state_dim,
            action_dim=env_for_shape.action_dim,
            hidden_dim=128,
        )
        policy.load_state_dict(payload["policy"])
        policy.eval()

        seed_row: dict[str, Any] = {"seed": seed, "checkpoint_path": str(ckpt_path), "metrics": {}}
        for difficulty in difficulties:
            metric_row = {}
            for mode in modes:
                metric_row[mode] = _evaluate_policy_mode(
                    policy=policy,
                    difficulty=difficulty,
                    mode=mode,
                    episodes=episodes,
                    max_steps=max_steps,
                )
            seed_row["metrics"][difficulty] = metric_row
        rows.append(seed_row)

    summary = {}
    pairwise = []
    for difficulty in difficulties:
        summary[difficulty] = {}
        for mode in modes:
            vals = [float(r["metrics"][difficulty][mode]) for r in rows]
            summary[difficulty][mode] = {
                "mean_success_rate": _mean(vals),
                "std_success_rate": _std(vals),
            }
        comparisons = [
            ("model_only", "guided_blend"),
            ("model_only", "guide_only"),
            ("guided_blend", "guide_only"),
        ]
        for a_mode, b_mode in comparisons:
            diffs = [
                float(r["metrics"][difficulty][b_mode]) - float(r["metrics"][difficulty][a_mode]) for r in rows
            ]
            pairwise.append(
                {
                    "difficulty": difficulty,
                    "a_mode": a_mode,
                    "b_mode": b_mode,
                    "delta_mean_success_b_minus_a": _mean(diffs),
                    "p_value_signflip": _exact_signflip_pvalue(diffs),
                }
            )

    return {
        "run_prefix": run_prefix,
        "episodes": episodes,
        "max_steps": max_steps,
        "seeds_requested": seeds,
        "seeds_used": [int(r["seed"]) for r in rows],
        "missing_checkpoints": missing_checkpoints,
        "rows": rows,
        "summary": summary,
        "pairwise_significance": pairwise,
    }


def _build_randomization_attribution(report_paths: list[Path]) -> dict[str, Any]:
    reports = []
    for path in report_paths:
        payload = _load_json(path)
        by_kpi = {str(r["kpi"]): r for r in payload.get("rows", [])}
        reports.append(
            {
                "path": str(path),
                "report_name": payload.get("report_name"),
                "a_prefix": payload.get("a_prefix"),
                "b_prefix": payload.get("b_prefix"),
                "seeds": payload.get("seeds", []),
                "robust_medium": by_kpi.get("robust_medium"),
                "robust_hard": by_kpi.get("robust_hard"),
                "transfer_gain_mean": by_kpi.get("transfer_gain_mean"),
                "transfer_success_mean": by_kpi.get("transfer_success_mean"),
            }
        )
    return {"reports": reports}


def _build_claim_map(args: argparse.Namespace) -> list[dict[str, Any]]:
    return [
        {
            "claim_id": "C1",
            "claim": "Matched-compute 4D/5D/6D/8D-to-3D ranking is computed from the hard020 10-seed cohort with paired significance.",
            "artifacts": [
                str(args.cohort_summary),
                str(ROOT / "report" / f"{args.report_name}.json"),
                str(ROOT / "report" / f"{args.report_name}.md"),
            ],
            "rerun_commands": [
                "python experiments/evidence_closure_report.py --report-name director_evidence_closure_iter1",
            ],
        },
        {
            "claim_id": "C2",
            "claim": "Latent representation contribution is isolated via fixed-budget model ablations (gru/mlp/phys_residual/rssm) on the same 10-seed cohort.",
            "artifacts": [
                str(ROOT / "report" / "kaggle_hiconf_hard020_10seed_summary.json"),
                str(ROOT / "report" / f"{args.report_name}.json"),
            ],
            "rerun_commands": [
                "python experiments/evidence_closure_report.py --report-name director_evidence_closure_iter1",
            ],
        },
        {
            "claim_id": "C3",
            "claim": "Guidance policy contribution is isolated by checkpoint-fixed evaluation (model_only vs guided_blend vs guide_only) over 9 seeds.",
            "artifacts": [
                str(ROOT / "checkpoints" / "baseline"),
                str(ROOT / "report" / f"{args.report_name}.json"),
            ],
            "rerun_commands": [
                "python experiments/evidence_closure_report.py --guidance-prefix p2_v2_9seed --guidance-seeds 11 22 33 44 55 66 77 88 99",
            ],
        },
        {
            "claim_id": "C4",
            "claim": "Domain-randomization contribution is anchored to paired-significance reports (9-seed robustness tradeoff studies).",
            "artifacts": [str(p) for p in args.randomization_reports],
            "rerun_commands": [
                "python experiments/significance_report.py --a-prefix p0_freeze_9seed --b-prefix p2_v2_9seed --report-name release_significance_p0_vs_p2v2_9seed",
                "python experiments/significance_report.py --a-prefix next_hard002_9seed --b-prefix next_hard020_9seed --report-name kaggle_next_hard002_vs_hard020_9seed_significance",
            ],
        },
    ]


def _to_md(payload: dict[str, Any]) -> str:
    transfer = payload["matched_compute_ranking"]
    latent = payload["mechanism_attribution"]["latent_representation"]
    guidance = payload["mechanism_attribution"]["guidance_policy"]
    randomization = payload["mechanism_attribution"]["domain_randomization"]

    lines: list[str] = []
    lines.append(f"# {payload['report_name']}")
    lines.append("")
    lines.append("## Matched-compute dimension ranking (4D/5D/6D/8D -> 3D)")
    lines.append("")
    lines.append(
        f"- cohort: `{payload['inputs']['cohort_summary']}`; seeds={transfer['seeds']}; matched_compute={transfer['matched_compute']['is_matched_compute']}"
    )
    lines.append("")
    lines.append("| Rank | Source Dim | Mean Gain | Std Gain | Mean Transfer Success | p(gain>0, signflip) |")
    lines.append("| ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in transfer["ranking"]:
        lines.append(
            f"| {row['rank_by_mean_gain']} | {row['source_dim']} | {row['mean_transfer_gain']:.4f} | "
            f"{row['std_transfer_gain']:.4f} | {row['mean_transfer_success']:.4f} | {row['p_gain_vs_zero_signflip']:.4f} |"
        )

    lines.append("")
    lines.append("## Mechanism attribution")
    lines.append("")
    lines.append("### Latent representation (ablation)")
    lines.append("")
    lines.append("| Rank | Model | Mean Success | Std |")
    lines.append("| ---: | --- | ---: | ---: |")
    for row in latent["ranking"]:
        lines.append(
            f"| {row['rank_by_mean_success']} | {row['model']} | {row['mean_success_rate']:.4f} | {row['std_success_rate']:.4f} |"
        )

    lines.append("")
    lines.append("### Guidance policy (checkpoint-fixed evaluation)")
    lines.append("")
    lines.append(
        f"- run_prefix=`{guidance['run_prefix']}`; seeds_used={guidance['seeds_used']}; episodes={guidance['episodes']}"
    )
    lines.append("")
    lines.append("| Difficulty | Model Only | Guided Blend | Guide Only |")
    lines.append("| --- | ---: | ---: | ---: |")
    for difficulty in ["easy", "medium", "hard"]:
        row = guidance["summary"][difficulty]
        lines.append(
            f"| {difficulty} | {row['model_only']['mean_success_rate']:.4f} | "
            f"{row['guided_blend']['mean_success_rate']:.4f} | {row['guide_only']['mean_success_rate']:.4f} |"
        )

    lines.append("")
    lines.append("### Domain randomization (paired significance)")
    lines.append("")
    for r in randomization["reports"]:
        hard = r["robust_hard"]
        medium = r["robust_medium"]
        lines.append(
            f"- `{r['report_name']}`: robust_medium delta={medium['delta_mean']:.4f} (p={medium['p_value']:.4f}), "
            f"robust_hard delta={hard['delta_mean']:.4f} (p={hard['p_value']:.4f})"
        )

    lines.append("")
    lines.append("## Claims -> artifacts")
    lines.append("")
    for claim in payload["claim_to_artifacts"]:
        lines.append(f"- {claim['claim_id']}: {claim['claim']}")
        for artifact in claim["artifacts"]:
            lines.append(f"  - artifact: `{artifact}`")
        for cmd in claim["rerun_commands"]:
            lines.append(f"  - rerun: `{cmd}`")

    lines.append("")
    lines.append("## Residual risks")
    lines.append("")
    for risk in payload["residual_risks"]:
        lines.append(f"- {risk}")

    return "\n".join(lines)


def run() -> None:
    args = parse_args()
    cohort_items = _load_cohort_items(args.cohort_summary)
    transfer_ranking = _build_transfer_ranking(cohort_items)
    latent = _build_latent_representation_attribution(cohort_items)
    guidance = _build_guidance_attribution(
        run_prefix=args.guidance_prefix,
        seeds=args.guidance_seeds,
        episodes=args.guidance_episodes,
        max_steps=args.guidance_max_steps,
    )
    randomization = _build_randomization_attribution(args.randomization_reports)

    payload = {
        "report_name": args.report_name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "cohort_summary": str(args.cohort_summary),
            "randomization_reports": [str(p) for p in args.randomization_reports],
            "guidance_checkpoint_prefix": args.guidance_prefix,
        },
        "matched_compute_ranking": transfer_ranking,
        "mechanism_attribution": {
            "latent_representation": latent,
            "guidance_policy": guidance,
            "domain_randomization": randomization,
        },
        "claim_to_artifacts": _build_claim_map(args),
        "limitations": [
            "4D/5D/6D/8D ranking deltas are small in the hard020 cohort and not pairwise-significant at alpha=0.05.",
            "Guidance attribution is checkpoint-fixed evaluation (inference/control effect), not full retraining ablation.",
            "Evidence remains simulation-bound (PushBallNDEnv), so external physical transfer is unvalidated.",
        ],
        "residual_risks": [
            "Dimension ranking is currently a weak-order tie (4D~5D > 6D~8D) rather than a decisive winner.",
            "Guidance causal claim does not yet isolate training-time guidance from inference-time blending.",
            "Randomization effects depend on chosen scope (medium_hard vs hard_only) and may shift with budget.",
        ],
        "next_commands": [
            "python experiments/evidence_closure_report.py --report-name director_evidence_closure_iter1",
            "python experiments/run_p0_baseline_freeze.py --run-id-prefix p_guidance_off_5seed --seeds 11 22 33 44 55 --baseline-epochs 8 --transfer-pretrain-epochs 6 --transfer-finetune-epochs 6 --robustness-episodes 120",
            "python experiments/significance_report.py --a-prefix p_guidance_off_5seed --b-prefix p2_v2_5seed --report-name guidance_off_vs_on_5seed_significance",
        ],
    }

    out_dir = ROOT / "report"
    save_json(out_dir / f"{args.report_name}.json", payload)
    (out_dir / f"{args.report_name}.md").write_text(_to_md(payload), encoding="utf-8")
    print(f"Saved {out_dir / f'{args.report_name}.json'}")
    print(f"Saved {out_dir / f'{args.report_name}.md'}")


if __name__ == "__main__":
    run()
