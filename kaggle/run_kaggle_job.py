from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "kaggle" / "run_config.json"
OUTPUT_SUMMARY = Path("/kaggle/working") / "hyperdream_kaggle_summary.json"


def log(message: str) -> None:
    print(f"[kaggle-runner] {message}", flush=True)


def to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> dict:
    defaults = {
        "run_id": f"kaggle_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "resume": False,
        "run_tests": False,
        "skip_install_deps": True,
        "heartbeat_every": 1,
        "push_after_each_stage": True,
        "baseline_epochs": 12,
        "transfer_pretrain_epochs": 8,
        "transfer_finetune_epochs": 8,
        "ablation_epochs": 8,
        "robustness_episodes": 120,
        "eval_episodes": 40,
        "max_steps": 120,
        "save_every": 4,
        "keep_last": 6,
        "push_results_to_github": False,
        "push_branch": "colab-results",
        "base_branch": "main",
        "github_user": "peter941221",
        "repo_name": "High_Dimensional_WorldModel",
        "token_env": "GITHUB_TOKEN",
        "token_secret_name": "GITHUB_TOKEN",
        "include_checkpoints_in_push": False,
    }

    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        defaults.update(data)
    return defaults


def build_cmd(cfg: dict) -> list[str]:
    cmd = [
        sys.executable,
        "colab_autorun.py",
        "--project-dir",
        str(ROOT),
        "--run-id",
        str(cfg["run_id"]),
        "--skip-repo-sync",
        "--baseline-epochs",
        str(cfg["baseline_epochs"]),
        "--transfer-pretrain-epochs",
        str(cfg["transfer_pretrain_epochs"]),
        "--transfer-finetune-epochs",
        str(cfg["transfer_finetune_epochs"]),
        "--ablation-epochs",
        str(cfg["ablation_epochs"]),
        "--robustness-episodes",
        str(cfg["robustness_episodes"]),
        "--eval-episodes",
        str(cfg["eval_episodes"]),
        "--max-steps",
        str(cfg["max_steps"]),
        "--save-every",
        str(cfg["save_every"]),
        "--keep-last",
        str(cfg["keep_last"]),
        "--heartbeat-every",
        str(cfg["heartbeat_every"]),
    ]

    if to_bool(cfg.get("skip_install_deps", True)):
        cmd.append("--skip-install-deps")
    if to_bool(cfg.get("resume", False)):
        cmd.append("--resume")
    if to_bool(cfg.get("run_tests", False)):
        cmd.append("--run-tests")
    if to_bool(cfg.get("push_after_each_stage", True)):
        cmd.append("--push-after-each-stage")
    else:
        cmd.append("--no-push-after-each-stage")

    if to_bool(cfg.get("push_results_to_github", False)):
        cmd.extend(
            [
                "--push-results-to-github",
                "--push-branch",
                str(cfg.get("push_branch", "colab-results")),
                "--base-branch",
                str(cfg.get("base_branch", "main")),
                "--github-user",
                str(cfg.get("github_user", "")),
                "--repo-name",
                str(cfg.get("repo_name", "")),
                "--token-env",
                str(cfg.get("token_env", "GITHUB_TOKEN")),
                "--token-secret-name",
                str(cfg.get("token_secret_name", "GITHUB_TOKEN")),
            ]
        )
        if to_bool(cfg.get("include_checkpoints_in_push", False)):
            cmd.append("--include-checkpoints-in-push")
    return cmd


def main() -> None:
    cfg = load_config()
    cmd = build_cmd(cfg)
    log("Running command:")
    log(" ".join(cmd))
    subprocess.run(cmd, cwd=str(ROOT), check=True)

    summary = {
        "run_id": cfg["run_id"],
        "finished_at": datetime.now().isoformat(),
        "results_dir": str(ROOT / "results"),
        "figures_dir": str(ROOT / "figures"),
        "checkpoints_dir": str(ROOT / "checkpoints"),
    }
    OUTPUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Saved run summary: {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
