from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.common import save_json


KPI_KEYS = [
    "baseline_success_dim3",
    "baseline_success_dim4",
    "transfer_success_mean",
    "transfer_gain_mean",
    "robust_easy",
    "robust_medium",
    "robust_hard",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a results/p0_freeze/<out_prefix>/p0_summary.json from existing per-seed "
            "baseline/transfer/robustness JSON outputs."
        )
    )
    parser.add_argument(
        "--out-prefix",
        type=str,
        required=True,
        help="Output prefix under results/p0_freeze/<out_prefix>/p0_summary.json",
    )
    parser.add_argument(
        "--source-run-prefix",
        type=str,
        required=True,
        help="Prefix used to locate per-seed run outputs (run_id = <prefix>_s<seed>).",
    )
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument(
        "--meta-from-prefix",
        type=str,
        default=None,
        help="If set, copy the 'meta' dict from results/p0_freeze/<prefix>/p0_summary.json",
    )
    return parser.parse_args()


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
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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


def _transfer_means(transfer_payload: dict) -> tuple[float, float]:
    rows = transfer_payload.get("results", [])
    if not rows:
        return 0.0, 0.0
    transfer_success = [float(item.get("transfer_success", 0.0)) for item in rows]
    transfer_gain = [
        float(item.get("transfer_success", 0.0)) - float(item.get("baseline_success", 0.0))
        for item in rows
    ]
    return float(statistics.mean(transfer_success)), float(statistics.mean(transfer_gain))


def _meta_from_prefix(prefix: str) -> dict:
    summary_path = ROOT / "results" / "p0_freeze" / prefix / "p0_summary.json"
    payload = _load_json(summary_path)
    meta = payload.get("meta", {})
    if not isinstance(meta, dict):
        return {}
    return dict(meta)


def run() -> None:
    args = parse_args()
    seeds = [int(s) for s in args.seeds]

    meta = {}
    if args.meta_from_prefix is not None:
        meta = _meta_from_prefix(args.meta_from_prefix)
    meta["source_run_prefix"] = args.source_run_prefix
    meta["source_run_ids"] = [f"{args.source_run_prefix}_s{s}" for s in seeds]

    rows = []
    for seed in seeds:
        run_id = f"{args.source_run_prefix}_s{seed}"
        baseline_path = ROOT / "results" / "baseline" / run_id / "baseline.json"
        transfer_path = ROOT / "results" / "transfer" / run_id / "transfer.json"
        robustness_path = ROOT / "results" / "robustness" / run_id / "robustness.json"

        missing = [p for p in [baseline_path, transfer_path, robustness_path] if not p.exists()]
        if missing:
            raise FileNotFoundError(
                "Missing per-seed output(s) for run_id="
                f"{run_id}: {', '.join(str(p) for p in missing)}"
            )

        baseline = _load_json(baseline_path)
        transfer = _load_json(transfer_path)
        robustness = _load_json(robustness_path)

        transfer_success_mean, transfer_gain_mean = _transfer_means(transfer)
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

    summary = {key: _mean_std([r[key] for r in rows]) for key in KPI_KEYS}

    payload = {
        "experiment": "p0_baseline_freeze",
        "run_id_prefix": args.out_prefix,
        "seeds": seeds,
        "rows": rows,
        "summary": summary,
        "meta": meta,
    }

    out_path = ROOT / "results" / "p0_freeze" / args.out_prefix / "p0_summary.json"
    save_json(out_path, payload)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    run()

