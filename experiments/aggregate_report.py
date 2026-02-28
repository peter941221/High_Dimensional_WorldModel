from __future__ import annotations

import argparse
from datetime import datetime
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
    parser = argparse.ArgumentParser(description="Aggregate phase summaries into one report.")
    parser.add_argument(
        "--run-prefixes",
        nargs="+",
        required=True,
        help="Summary run_id_prefix list under results/p0_freeze/<prefix>/p0_summary.json",
    )
    parser.add_argument("--report-name", type=str, default=None)
    return parser.parse_args()


def _load_summary(prefix: str) -> dict:
    path = ROOT / "results" / "p0_freeze" / prefix / "p0_summary.json"
    if not path.exists():
        raise FileNotFoundError(f"summary not found: {path}")
    import json

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    payload["_path"] = str(path)
    return payload


def _extract_row(prefix: str, payload: dict) -> dict:
    summary = payload.get("summary", {})
    row = {"run_prefix": prefix}
    for key in KPI_KEYS:
        row[key] = float(summary.get(key, {}).get("mean", 0.0))
        row[f"{key}_std"] = float(summary.get(key, {}).get("std", 0.0))
    return row


def _markdown_table(rows: list[dict]) -> str:
    headers = ["run_prefix"] + KPI_KEYS
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        vals = [row["run_prefix"]] + [f"{row[k]:.4f}" for k in KPI_KEYS]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def run():
    args = parse_args()
    report_name = args.report_name or f"aggregate_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    summaries = []
    rows = []
    for prefix in args.run_prefixes:
        payload = _load_summary(prefix)
        summaries.append({"run_prefix": prefix, "path": payload["_path"]})
        rows.append(_extract_row(prefix, payload))

    report = {
        "report_name": report_name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": summaries,
        "rows": rows,
        "kpis": KPI_KEYS,
    }

    out_dir = ROOT / "results" / "reports" / report_name
    save_json(out_dir / "aggregate.json", report)

    md = [
        f"# Aggregate Report: {report_name}",
        "",
        "## Inputs",
        "",
    ]
    for item in summaries:
        md.append(f"- `{item['run_prefix']}` -> `{item['path']}`")
    md.extend(
        [
            "",
            "## KPI Mean Table",
            "",
            _markdown_table(rows),
            "",
        ]
    )
    (out_dir / "aggregate.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Saved {out_dir / 'aggregate.json'}")
    print(f"Saved {out_dir / 'aggregate.md'}")


if __name__ == "__main__":
    run()

