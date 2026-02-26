from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


def _load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_baseline(data, out_dir: Path):
    dims = [r["dim"] for r in data["results"]]
    success = [r["success_rate"] for r in data["results"]]
    plt.figure(figsize=(7, 4))
    plt.plot(dims, success, marker="o", linewidth=2)
    plt.title("Baseline Success Across Dimensions")
    plt.xlabel("Dimension")
    plt.ylabel("Success Rate")
    plt.ylim(0, 1)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "baseline_dim_scan.png", dpi=160)
    plt.close()


def plot_transfer(data, out_dir: Path):
    src = [r["source_dim"] for r in data["results"]]
    transfer = [r["transfer_success"] for r in data["results"]]
    baseline = [r["baseline_success"] for r in data["results"]]
    plt.figure(figsize=(7, 4))
    plt.plot(src, transfer, marker="o", label="Transfer")
    plt.plot(src, baseline, linestyle="--", label="Scratch Baseline")
    plt.title("Transfer to 3D from Different Pretraining Dimensions")
    plt.xlabel("Source Dimension")
    plt.ylabel("3D Success Rate")
    plt.ylim(0, 1)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "transfer_to_3d.png", dpi=160)
    plt.close()


def plot_robustness(data, out_dir: Path):
    labels = [r["difficulty"] for r in data["results"]]
    values = [r["success_rate"] for r in data["results"]]
    plt.figure(figsize=(7, 4))
    plt.bar(labels, values)
    plt.title("Robustness Across Difficulty Levels")
    plt.xlabel("Condition")
    plt.ylabel("Success Rate")
    plt.ylim(0, 1)
    plt.tight_layout()
    plt.savefig(out_dir / "robustness.png", dpi=160)
    plt.close()


def plot_ablation(data, out_dir: Path):
    labels = [r["model"] for r in data["results"]]
    values = [r["success_rate"] for r in data["results"]]
    plt.figure(figsize=(7, 4))
    plt.bar(labels, values)
    plt.title("Model Ablation")
    plt.xlabel("World Model")
    plt.ylabel("Success Rate")
    plt.ylim(0, 1)
    plt.tight_layout()
    plt.savefig(out_dir / "ablation_models.png", dpi=160)
    plt.close()


def run():
    result_dir = Path("results")
    out_dir = Path("figures")
    out_dir.mkdir(exist_ok=True)

    baseline = _load_json(result_dir / "baseline.json")
    transfer = _load_json(result_dir / "transfer.json")
    robustness = _load_json(result_dir / "robustness.json")
    ablation = _load_json(result_dir / "ablation.json")

    if baseline:
        plot_baseline(baseline, out_dir)
    if transfer:
        plot_transfer(transfer, out_dir)
    if robustness:
        plot_robustness(robustness, out_dir)
    if ablation:
        plot_ablation(ablation, out_dir)

    print("Figure generation complete.")


if __name__ == "__main__":
    run()
