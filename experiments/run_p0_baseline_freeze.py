from __future__ import annotations

import argparse
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.common import save_json


def _mean_std(values: Iterable[float]) -> dict:
    vals = [float(v) for v in values]
    if not vals:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    if len(vals) == 1:
        v = vals[0]
        return {"mean": v, "std": 0.0, "min": v, "max": v}
    return {
        "mean": float(statistics.mean(vals)),
        "std": float(statistics.stdev(vals)),
        "min": float(min(vals)),
        "max": float(max(vals)),
    }


def _load_json(path: Path) -> dict:
    import json

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _run(cmd: list[str]) -> None:
    print(f"[p0-freeze] run: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True, cwd=str(ROOT))


def _maybe_run(cmd: list[str], out_file: Path, skip_existing: bool) -> dict:
    if skip_existing and out_file.exists():
        print(f"[p0-freeze] skip existing: {out_file}", flush=True)
        return _load_json(out_file)
    _run(cmd)
    return _load_json(out_file)


def _pick_dim_success(baseline_payload: dict, dim: int) -> float:
    for row in baseline_payload.get("results", []):
        if int(row.get("dim", -1)) == int(dim):
            return float(row.get("success_rate", 0.0))
    return 0.0


def _pick_difficulty_success(robust_payload: dict, difficulty: str) -> float:
    for row in robust_payload.get("results", []):
        if str(row.get("difficulty", "")) == difficulty:
            return float(row.get("success_rate", 0.0))
    return 0.0


def parse_args():
    parser = argparse.ArgumentParser(description="P0 baseline-freeze multi-seed orchestrator.")
    parser.add_argument("--run-id-prefix", type=str, default="p0_freeze")
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 22, 33])
    parser.add_argument("--skip-existing", action="store_true")

    parser.add_argument("--baseline-epochs", type=int, default=8)
    parser.add_argument("--baseline-max-steps", type=int, default=120)
    parser.add_argument("--baseline-eval-episodes", type=int, default=40)
    parser.add_argument("--baseline-heartbeat-every", type=int, default=1)

    parser.add_argument("--transfer-pretrain-epochs", type=int, default=6)
    parser.add_argument("--transfer-finetune-epochs", type=int, default=6)
    parser.add_argument("--transfer-max-steps", type=int, default=120)
    parser.add_argument("--transfer-eval-episodes", type=int, default=40)
    parser.add_argument("--transfer-heartbeat-every", type=int, default=1)

    parser.add_argument("--robustness-episodes", type=int, default=120)
    parser.add_argument("--robustness-dim", type=int, default=3)
    parser.add_argument("--robustness-heartbeat-every", type=int, default=10)
    parser.add_argument("--domain-rand", action="store_true", help="Enable domain randomization for all runs.")
    parser.add_argument(
        "--domain-rand-scope",
        type=str,
        default="all",
        choices=["all", "robustness_only", "train_only"],
        help="Where to apply domain randomization in orchestrated runs.",
    )
    parser.add_argument("--domain-rand-scale", type=float, default=0.15, help="Relative randomization scale.")
    parser.add_argument(
        "--domain-rand-profile",
        type=str,
        default="full",
        choices=["full", "conservative"],
        help="Domain randomization parameter profile.",
    )
    parser.add_argument(
        "--domain-rand-warmup-episodes",
        type=int,
        default=0,
        help="Linear warmup episodes for effective randomization scale.",
    )
    parser.add_argument(
        "--domain-rand-warmup-epochs",
        type=int,
        default=0,
        help="Linear warmup epochs for effective randomization scale.",
    )
    parser.add_argument(
        "--robustness-domain-rand-difficulties",
        type=str,
        default="all",
        choices=["all", "medium_hard", "hard_only"],
        help="Difficulty scope for robustness randomization.",
    )
    parser.add_argument("--domain-rand-scratch-multiplier", type=float, default=1.0)
    parser.add_argument("--domain-rand-source-multiplier", type=float, default=1.0)
    parser.add_argument("--domain-rand-finetune-multiplier", type=float, default=0.5)
    return parser.parse_args()


def run():
    args = parse_args()
    python = sys.executable
    enable_train_rand = args.domain_rand and args.domain_rand_scope in {"all", "train_only"}
    enable_robust_rand = args.domain_rand and args.domain_rand_scope in {"all", "robustness_only"}

    rows = []
    for seed in args.seeds:
        run_id = f"{args.run_id_prefix}_s{seed}"

        baseline_out = ROOT / "results" / "baseline" / run_id / "baseline.json"
        transfer_out = ROOT / "results" / "transfer" / run_id / "transfer.json"
        robust_out = ROOT / "results" / "robustness" / run_id / "robustness.json"

        baseline = _maybe_run(
            [
                python,
                "experiments/run_baseline.py",
                "--run-id",
                run_id,
                "--epochs",
                str(args.baseline_epochs),
                "--max-steps",
                str(args.baseline_max_steps),
                "--eval-episodes",
                str(args.baseline_eval_episodes),
                "--heartbeat-every",
                str(args.baseline_heartbeat_every),
                "--seed",
                str(seed),
            ]
            + (
                [
                    "--domain-rand",
                    "--domain-rand-scale",
                    str(args.domain_rand_scale),
                    "--domain-rand-profile",
                    args.domain_rand_profile,
                    "--domain-rand-warmup-episodes",
                    str(args.domain_rand_warmup_episodes),
                    "--domain-rand-warmup-epochs",
                    str(args.domain_rand_warmup_epochs),
                ]
                if enable_train_rand
                else []
            ),
            baseline_out,
            skip_existing=args.skip_existing,
        )

        transfer = _maybe_run(
            [
                python,
                "experiments/run_transfer.py",
                "--run-id",
                run_id,
                "--pretrain-epochs",
                str(args.transfer_pretrain_epochs),
                "--finetune-epochs",
                str(args.transfer_finetune_epochs),
                "--max-steps",
                str(args.transfer_max_steps),
                "--eval-episodes",
                str(args.transfer_eval_episodes),
                "--heartbeat-every",
                str(args.transfer_heartbeat_every),
                "--seed",
                str(seed),
            ]
            + (
                [
                    "--domain-rand",
                    "--domain-rand-scale",
                    str(args.domain_rand_scale),
                    "--domain-rand-profile",
                    args.domain_rand_profile,
                    "--domain-rand-warmup-episodes",
                    str(args.domain_rand_warmup_episodes),
                    "--domain-rand-warmup-epochs",
                    str(args.domain_rand_warmup_epochs),
                    "--domain-rand-scratch-multiplier",
                    str(args.domain_rand_scratch_multiplier),
                    "--domain-rand-source-multiplier",
                    str(args.domain_rand_source_multiplier),
                    "--domain-rand-finetune-multiplier",
                    str(args.domain_rand_finetune_multiplier),
                ]
                if enable_train_rand
                else []
            ),
            transfer_out,
            skip_existing=args.skip_existing,
        )

        robustness = _maybe_run(
            [
                python,
                "experiments/run_robustness.py",
                "--run-id",
                run_id,
                "--episodes",
                str(args.robustness_episodes),
                "--dim",
                str(args.robustness_dim),
                "--heartbeat-every",
                str(args.robustness_heartbeat_every),
                "--seed",
                str(seed),
            ]
            + (
                [
                    "--domain-rand",
                    "--domain-rand-scale",
                    str(args.domain_rand_scale),
                    "--domain-rand-profile",
                    args.domain_rand_profile,
                    "--domain-rand-warmup-episodes",
                    str(args.domain_rand_warmup_episodes),
                    "--domain-rand-warmup-epochs",
                    str(args.domain_rand_warmup_epochs),
                    "--domain-rand-difficulties",
                    args.robustness_domain_rand_difficulties,
                ]
                if enable_robust_rand
                else []
            ),
            robust_out,
            skip_existing=args.skip_existing,
        )

        transfer_rows = transfer.get("results", [])
        transfer_success_mean = statistics.mean(
            [float(item.get("transfer_success", 0.0)) for item in transfer_rows]
        )
        transfer_gain_mean = statistics.mean(
            [
                float(item.get("transfer_success", 0.0)) - float(item.get("baseline_success", 0.0))
                for item in transfer_rows
            ]
        )

        row = {
            "seed": int(seed),
            "run_id": run_id,
            "baseline_success_dim3": _pick_dim_success(baseline, dim=3),
            "baseline_success_dim4": _pick_dim_success(baseline, dim=4),
            "transfer_success_mean": float(transfer_success_mean),
            "transfer_gain_mean": float(transfer_gain_mean),
            "robust_easy": _pick_difficulty_success(robustness, "easy"),
            "robust_medium": _pick_difficulty_success(robustness, "medium"),
            "robust_hard": _pick_difficulty_success(robustness, "hard"),
        }
        rows.append(row)
        print(f"[p0-freeze] seed={seed} row={row}", flush=True)

    summary = {
        "baseline_success_dim3": _mean_std([r["baseline_success_dim3"] for r in rows]),
        "baseline_success_dim4": _mean_std([r["baseline_success_dim4"] for r in rows]),
        "transfer_success_mean": _mean_std([r["transfer_success_mean"] for r in rows]),
        "transfer_gain_mean": _mean_std([r["transfer_gain_mean"] for r in rows]),
        "robust_easy": _mean_std([r["robust_easy"] for r in rows]),
        "robust_medium": _mean_std([r["robust_medium"] for r in rows]),
        "robust_hard": _mean_std([r["robust_hard"] for r in rows]),
    }

    payload = {
        "experiment": "p0_baseline_freeze",
        "run_id_prefix": args.run_id_prefix,
        "seeds": [int(s) for s in args.seeds],
        "rows": rows,
        "summary": summary,
        "meta": {
            "baseline": {
                "epochs": args.baseline_epochs,
                "max_steps": args.baseline_max_steps,
                "eval_episodes": args.baseline_eval_episodes,
            },
            "transfer": {
                "pretrain_epochs": args.transfer_pretrain_epochs,
                "finetune_epochs": args.transfer_finetune_epochs,
                "max_steps": args.transfer_max_steps,
                "eval_episodes": args.transfer_eval_episodes,
            },
            "robustness": {
                "episodes": args.robustness_episodes,
                "dim": args.robustness_dim,
            },
            "domain_rand": args.domain_rand,
            "domain_rand_scope": args.domain_rand_scope,
            "domain_rand_scale": args.domain_rand_scale,
            "domain_rand_profile": args.domain_rand_profile,
            "domain_rand_warmup_episodes": args.domain_rand_warmup_episodes,
            "domain_rand_warmup_epochs": args.domain_rand_warmup_epochs,
            "robustness_domain_rand_difficulties": args.robustness_domain_rand_difficulties,
            "domain_rand_scratch_multiplier": args.domain_rand_scratch_multiplier,
            "domain_rand_source_multiplier": args.domain_rand_source_multiplier,
            "domain_rand_finetune_multiplier": args.domain_rand_finetune_multiplier,
        },
    }

    result_dir = ROOT / "results" / "p0_freeze" / args.run_id_prefix
    save_json(result_dir / "p0_summary.json", payload)
    save_json(ROOT / "results" / "p0_freeze_summary.json", payload)
    print(f"Saved {result_dir / 'p0_summary.json'}")
    print("Saved results/p0_freeze_summary.json")


if __name__ == "__main__":
    run()
