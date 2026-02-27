from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


REPO_URL = "https://github.com/peter941221/High_Dimensional_WorldModel.git"
PROJECT_DIR = Path("/kaggle/working/High_Dimensional_WorldModel")
CONFIG_PATH = Path("/kaggle/src/kaggle/run_config.json")
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
        "skip_install_deps": False,
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
        "use_code_dataset": True,
        "code_dataset_slug": "high-dimensional-worldmodel-src",
        "code_bundle_filename": "project_bundle.zip",
    }

    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        defaults.update(data)
    return defaults


def dataset_mount_path(dataset_slug: str) -> Path:
    return Path("/kaggle/input") / dataset_slug


def prepare_from_dataset(cfg: dict) -> Path | None:
    if not to_bool(cfg.get("use_code_dataset", True)):
        return None

    slug = str(cfg.get("code_dataset_slug", "")).strip()
    if not slug:
        return None

    mount_dir = dataset_mount_path(slug)
    bundle_name = str(cfg.get("code_bundle_filename", "project_bundle.zip"))
    bundle_path = mount_dir / bundle_name
    if not mount_dir.exists():
        log(f"Dataset mount not found: {mount_dir}")
        return None

    if PROJECT_DIR.exists():
        shutil.rmtree(PROJECT_DIR)
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)

    if bundle_path.exists():
        log(f"Extracting code bundle from dataset: {bundle_path}")
        with zipfile.ZipFile(bundle_path, "r") as zf:
            zf.extractall(PROJECT_DIR)
        return PROJECT_DIR

    if (mount_dir / "colab_autorun.py").exists():
        log(f"Copying source tree from dataset mount: {mount_dir}")
        shutil.copytree(mount_dir, PROJECT_DIR, dirs_exist_ok=True)
        return PROJECT_DIR

    log("Dataset mount exists but no code bundle/source file found.")
    return None


def ensure_repo() -> Path:
    if (PROJECT_DIR / ".git").exists():
        subprocess.run(["git", "-C", str(PROJECT_DIR), "fetch", "origin"], check=True)
        subprocess.run(["git", "-C", str(PROJECT_DIR), "checkout", "main"], check=True)
        subprocess.run(["git", "-C", str(PROJECT_DIR), "reset", "--hard", "origin/main"], check=True)
    else:
        subprocess.run(["git", "clone", "--branch", "main", REPO_URL, str(PROJECT_DIR)], check=True)
    return PROJECT_DIR


def build_cmd(cfg: dict, root: Path) -> list[str]:
    cmd = [
        sys.executable,
        "colab_autorun.py",
        "--project-dir",
        str(root),
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
    root = prepare_from_dataset(cfg) or ensure_repo()
    cmd = build_cmd(cfg, root=root)
    log("Running command:")
    log(" ".join(cmd))
    subprocess.run(cmd, cwd=str(root), check=True)

    summary = {
        "run_id": cfg["run_id"],
        "finished_at": datetime.now().isoformat(),
        "results_dir": str(root / "results"),
        "figures_dir": str(root / "figures"),
        "checkpoints_dir": str(root / "checkpoints"),
    }
    OUTPUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Saved run summary: {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
