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
    parser.add_argument(
        "--out-dir",
        type=str,
        default="report",
        help="Output directory (relative to repo root unless absolute).",
    )
    parser.add_argument(
        "--meta-check",
        action="store_true",
        help="Compute a meta/config diff between A and B summaries (useful for confound detection).",
    )
    parser.add_argument(
        "--meta-allow-diff",
        type=str,
        nargs="*",
        default=[],
        help="Meta keys allowed to differ when --meta-check is enabled (keys are dotted paths).",
    )
    parser.add_argument(
        "--meta-strict",
        action="store_true",
        help="Fail if meta differs beyond --meta-allow-diff (requires --meta-check).",
    )
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


def _flatten_dict(obj: object, prefix: str = "") -> dict[str, object]:
    if not isinstance(obj, dict):
        return {prefix: obj} if prefix else {}
    out: dict[str, object] = {}
    for k, v in obj.items():
        key = str(k)
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(v, dict):
            out.update(_flatten_dict(v, prefix=path))
        else:
            out[path] = v
    return out


def _diff_meta(a_meta: dict, b_meta: dict) -> list[dict]:
    a_flat = _flatten_dict(a_meta)
    b_flat = _flatten_dict(b_meta)
    keys = sorted(set(a_flat.keys()) | set(b_flat.keys()))
    diffs: list[dict] = []
    for k in keys:
        a_val = a_flat.get(k, None)
        b_val = b_flat.get(k, None)
        if a_val != b_val:
            diffs.append({"key": k, "a": a_val, "b": b_val})
    return diffs


def run():
    args = parse_args()
    if args.meta_strict and not args.meta_check:
        raise ValueError("--meta-strict requires --meta-check")
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

    meta_check = None
    if args.meta_check:
        allowed = set(str(k) for k in (args.meta_allow_diff or []))
        diffs = _diff_meta(a.get("meta", {}) or {}, b.get("meta", {}) or {})
        unexpected = [d for d in diffs if str(d["key"]) not in allowed]
        meta_check = {
            "enabled": True,
            "allowed_diff_keys": sorted(allowed),
            "diffs": diffs,
            "unexpected_diff_keys": sorted({str(d["key"]) for d in unexpected}),
            "passed": len(unexpected) == 0,
        }
        if args.meta_strict and not meta_check["passed"]:
            unexpected_keys = ", ".join(meta_check["unexpected_diff_keys"][:20])
            raise ValueError(f"meta mismatch beyond allowed keys: {unexpected_keys}")

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
    if meta_check is not None:
        payload["meta_check"] = meta_check

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    save_json(out_dir / f"{args.report_name}.json", payload)

    md_lines = [
        f"# Significance Report: {args.report_name}",
        "",
        f"- A (control): `{args.a_prefix}`",
        f"- B (treatment): `{args.b_prefix}`",
        f"- Seeds: `{seeds}`",
        "- Method: `paired_exact_signflip`",
        "",
    ]

    if meta_check is not None:
        md_lines.extend(
            [
                "## Meta Check",
                "",
                f"- Passed: `{meta_check['passed']}`",
                f"- Allowed diff keys: `{meta_check['allowed_diff_keys']}`",
                f"- Unexpected diff keys: `{meta_check['unexpected_diff_keys']}`",
                "",
            ]
        )
        if meta_check["diffs"]:
            md_lines.extend(
                [
                    "| Meta key | A | B |",
                    "| --- | --- | --- |",
                ]
            )
            for d in meta_check["diffs"][:12]:
                md_lines.append(f"| `{d['key']}` | `{d['a']}` | `{d['b']}` |")
            if len(meta_check["diffs"]) > 12:
                md_lines.append(f"- (truncated) total meta diffs: `{len(meta_check['diffs'])}`")
            md_lines.append("")

    md_lines.extend(
        [
            "| KPI | A mean | B mean | Delta (B-A) | p-value | Significant(0.05) |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
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
