from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.common import save_json


DEFAULT_KPI_KEYS = [
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
            "Paired equivalence-oriented report between two run prefixes. "
            "Computes a bootstrap CI for the mean delta and the minimal absolute margin "
            "needed for CI-based equivalence at the chosen CI level."
        )
    )
    parser.add_argument("--a-prefix", type=str, required=True, help="Control run prefix under results/p0_freeze/")
    parser.add_argument("--b-prefix", type=str, required=True, help="Treatment run prefix under results/p0_freeze/")
    parser.add_argument("--report-name", type=str, default="equivalence_report")
    parser.add_argument(
        "--out-dir",
        type=str,
        default="report",
        help="Output directory (relative to repo root unless absolute).",
    )
    parser.add_argument(
        "--kpi-keys",
        type=str,
        nargs="*",
        default=list(DEFAULT_KPI_KEYS),
        help="KPI keys to compare (defaults match significance_report.py).",
    )
    parser.add_argument(
        "--ci-level",
        type=float,
        default=0.90,
        help="CI level for mean delta (e.g., 0.90 corresponds to alpha=0.05 equivalence CI framing).",
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=10000,
        help="Bootstrap resamples for CI estimation.",
    )
    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=12345,
        help="RNG seed for deterministic bootstrap.",
    )
    parser.add_argument(
        "--margin-abs",
        type=float,
        default=None,
        help="Optional absolute equivalence margin. If provided, reports whether CI is within [-margin, +margin].",
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


def _load_summary(prefix: str) -> dict[str, Any]:
    path = ROOT / "results" / "p0_freeze" / prefix / "p0_summary.json"
    if not path.exists():
        raise FileNotFoundError(f"summary not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    payload["_path"] = str(path)
    return payload


def _rows_by_seed(payload: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in payload.get("rows", []):
        out[int(row["seed"])] = row
    return out


def bootstrap_mean_ci(
    vals: list[float],
    *,
    ci_level: float = 0.90,
    n_samples: int = 10000,
    seed: int = 12345,
) -> tuple[float, float]:
    if not (0.0 < ci_level < 1.0):
        raise ValueError(f"ci_level must be in (0,1); got {ci_level}")
    if n_samples <= 0:
        raise ValueError(f"n_samples must be >0; got {n_samples}")
    if len(vals) == 0:
        return (0.0, 0.0)
    if len(vals) == 1:
        x = float(vals[0])
        return (x, x)

    arr = np.asarray(vals, dtype=np.float64)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(arr), size=(n_samples, len(arr)))
    means = arr[idx].mean(axis=1)
    alpha = (1.0 - ci_level) / 2.0
    lo = float(np.quantile(means, alpha))
    hi = float(np.quantile(means, 1.0 - alpha))
    return (lo, hi)


def _mean(vals: list[float]) -> float:
    return float(sum(vals) / max(len(vals), 1))


def _std(vals: list[float]) -> float:
    if len(vals) <= 1:
        return 0.0
    mu = _mean(vals)
    var = sum((x - mu) ** 2 for x in vals) / (len(vals) - 1)
    return float(math.sqrt(max(var, 0.0)))


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


def _diff_meta(a_meta: dict[str, Any], b_meta: dict[str, Any]) -> list[dict[str, Any]]:
    a_flat = _flatten_dict(a_meta)
    b_flat = _flatten_dict(b_meta)
    keys = sorted(set(a_flat.keys()) | set(b_flat.keys()))
    diffs: list[dict[str, Any]] = []
    for k in keys:
        a_val = a_flat.get(k, None)
        b_val = b_flat.get(k, None)
        if a_val != b_val:
            diffs.append({"key": k, "a": a_val, "b": b_val})
    return diffs


def run() -> None:
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

    rows: list[dict[str, Any]] = []
    for key in list(args.kpi_keys or []):
        a_vals = [float(a_by_seed[s][key]) for s in seeds]
        b_vals = [float(b_by_seed[s][key]) for s in seeds]
        diffs = [bv - av for av, bv in zip(a_vals, b_vals)]

        ci_lo, ci_hi = bootstrap_mean_ci(
            diffs,
            ci_level=float(args.ci_level),
            n_samples=int(args.bootstrap_samples),
            seed=int(args.bootstrap_seed),
        )
        required_margin_abs = float(max(abs(ci_lo), abs(ci_hi)))

        std_d = _std(diffs)
        dz = float(_mean(diffs) / std_d) if std_d > 0 else 0.0

        row: dict[str, Any] = {
            "kpi": key,
            "n": len(seeds),
            "a_mean": _mean(a_vals),
            "b_mean": _mean(b_vals),
            "delta_mean": _mean(diffs),
            "delta_std": std_d,
            "cohens_dz": dz,
            "ci_level": float(args.ci_level),
            "ci_low": float(ci_lo),
            "ci_high": float(ci_hi),
            "required_margin_abs": required_margin_abs,
            "per_seed_deltas": diffs,
        }
        if args.margin_abs is not None:
            margin = float(args.margin_abs)
            row["margin_abs"] = margin
            row["equivalent_ci_within_margin"] = bool(ci_lo >= -margin and ci_hi <= margin)
        rows.append(row)

    meta_check = None
    if args.meta_check:
        allowed = set(str(k) for k in (args.meta_allow_diff or []))
        diffs = _diff_meta((a.get("meta", {}) or {}), (b.get("meta", {}) or {}))
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

    payload: dict[str, Any] = {
        "report_name": args.report_name,
        "a_prefix": args.a_prefix,
        "b_prefix": args.b_prefix,
        "a_path": a["_path"],
        "b_path": b["_path"],
        "seeds": seeds,
        "method": "paired_bootstrap_mean_ci",
        "ci_level": float(args.ci_level),
        "bootstrap_samples": int(args.bootstrap_samples),
        "bootstrap_seed": int(args.bootstrap_seed),
        "margin_abs": float(args.margin_abs) if args.margin_abs is not None else None,
        "rows": rows,
        "notes": [
            "This report does not claim equivalence unless a domain-meaningful margin is defined and CI falls within it.",
            "CI is estimated via bootstrap of the paired per-seed deltas (deterministic seed).",
        ],
    }
    if meta_check is not None:
        payload["meta_check"] = meta_check

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    save_json(out_dir / f"{args.report_name}.json", payload)

    md_lines = [
        f"# Equivalence-Oriented Report: {args.report_name}",
        "",
        f"- A (control): `{args.a_prefix}`",
        f"- B (treatment): `{args.b_prefix}`",
        f"- Seeds: `{seeds}`",
        f"- Method: `paired_bootstrap_mean_ci` (CI over mean delta)",
        f"- CI level: `{float(args.ci_level)}`",
        f"- Bootstrap: `{int(args.bootstrap_samples)}` samples (seed `{int(args.bootstrap_seed)}`)",
    ]
    if args.margin_abs is not None:
        md_lines.append(f"- Margin abs: `{float(args.margin_abs)}`")
    md_lines.append("")

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

    md_lines.extend(
        [
            "## KPI Table",
            "",
            "| KPI | n | mean Δ (B-A) | CI low | CI high | required | within? |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for r in rows:
        within = "-"
        if args.margin_abs is not None:
            within = "`true`" if r.get("equivalent_ci_within_margin") else "`false`"
        md_lines.append(
            "| `{kpi}` | {n} | {dm:.6f} | {lo:.6f} | {hi:.6f} | {req:.6f} | {within} |".format(
                kpi=r["kpi"],
                n=r["n"],
                dm=float(r["delta_mean"]),
                lo=float(r["ci_low"]),
                hi=float(r["ci_high"]),
                req=float(r["required_margin_abs"]),
                within=within,
            )
        )

    md_lines.extend(
        [
            "",
            "## Interpretation Guide",
            "",
            "- `required` is the minimal absolute margin `m` such that the CI fits inside `[-m, +m]`.",
            "- If you define a domain margin `m*` and `required <= m*`, then CI-based equivalence (at this CI level) holds.",
        ]
    )

    (out_dir / f"{args.report_name}.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()

