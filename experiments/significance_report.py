from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import sys

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


def parse_args():
    parser = argparse.ArgumentParser(description="Paired significance report between two run prefixes.")
    parser.add_argument("--a-prefix", type=str, required=True, help="Control run prefix under results/p0_freeze/")
    parser.add_argument("--b-prefix", type=str, required=True, help="Treatment run prefix under results/p0_freeze/")
    parser.add_argument("--report-name", type=str, default="significance_report")
    return parser.parse_args()


def _load_summary(prefix: str) -> dict:
    path = ROOT / "results" / "p0_freeze" / prefix / "p0_summary.json"
    if not path.exists():
        raise FileNotFoundError(f"summary not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    payload["_path"] = str(path)
    return payload


def _rows_by_seed(payload: dict) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for row in payload.get("rows", []):
        out[int(row["seed"])] = row
    return out


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


def _mean(vals: list[float]) -> float:
    return sum(vals) / max(len(vals), 1)


def run():
    args = parse_args()
    a = _load_summary(args.a_prefix)
    b = _load_summary(args.b_prefix)

    a_by_seed = _rows_by_seed(a)
    b_by_seed = _rows_by_seed(b)
    seeds = sorted(set(a_by_seed.keys()) & set(b_by_seed.keys()))
    if not seeds:
        raise ValueError("no overlapping seeds between A and B summaries")

    rows = []
    for key in KPI_KEYS:
        a_vals = [float(a_by_seed[s][key]) for s in seeds]
        b_vals = [float(b_by_seed[s][key]) for s in seeds]
        diffs = [bv - av for av, bv in zip(a_vals, b_vals)]
        p = _exact_signflip_pvalue(diffs)
        rows.append(
            {
                "kpi": key,
                "n": len(seeds),
                "a_mean": _mean(a_vals),
                "b_mean": _mean(b_vals),
                "delta_mean": _mean(diffs),
                "p_value": p,
                "significant_0_05": bool(p < 0.05),
            }
        )

    payload = {
        "report_name": args.report_name,
        "a_prefix": args.a_prefix,
        "b_prefix": args.b_prefix,
        "a_path": a["_path"],
        "b_path": b["_path"],
        "seeds": seeds,
        "method": "paired_exact_signflip",
        "alpha": 0.05,
        "rows": rows,
    }

    out_dir = ROOT / "report"
    save_json(out_dir / f"{args.report_name}.json", payload)

    md_lines = [
        f"# Significance Report: {args.report_name}",
        "",
        f"- A (control): `{args.a_prefix}`",
        f"- B (treatment): `{args.b_prefix}`",
        f"- Seeds: `{seeds}`",
        "- Method: `paired_exact_signflip`",
        "",
        "| KPI | A mean | B mean | Delta (B-A) | p-value | Significant(0.05) |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in rows:
        md_lines.append(
            f"| {r['kpi']} | {r['a_mean']:.4f} | {r['b_mean']:.4f} | {r['delta_mean']:.4f} | "
            f"{r['p_value']:.4f} | {r['significant_0_05']} |"
        )
    (out_dir / f"{args.report_name}.md").write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Saved {out_dir / f'{args.report_name}.json'}")
    print(f"Saved {out_dir / f'{args.report_name}.md'}")


if __name__ == "__main__":
    run()

