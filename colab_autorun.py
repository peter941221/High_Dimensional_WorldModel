from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


DEFAULT_REPO_URL = "https://github.com/peter941221/High_Dimensional_WorldModel.git"


def log(message: str) -> None:
    print(f"[colab-autorun] {message}", flush=True)


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    where = f" (cwd={cwd})" if cwd else ""
    log(f"RUN {' '.join(cmd)}{where}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def maybe_mount_drive(enable: bool) -> None:
    if not enable:
        return
    try:
        from google.colab import drive  # type: ignore

        log("Mounting Google Drive at /content/drive ...")
        drive.mount("/content/drive", force_remount=False)
    except Exception as exc:  # pragma: no cover - only on Colab runtime
        log(f"Drive mount skipped: {exc}")


def ensure_repo(project_dir: Path, repo_url: str, branch: str) -> None:
    if (project_dir / ".git").exists():
        log("Repository already exists, pulling latest changes.")
        run_cmd(["git", "fetch", "origin"], cwd=project_dir)
        run_cmd(["git", "checkout", branch], cwd=project_dir)
        run_cmd(["git", "pull", "--ff-only", "origin", branch], cwd=project_dir)
    else:
        project_dir.parent.mkdir(parents=True, exist_ok=True)
        run_cmd(["git", "clone", "--branch", branch, repo_url, str(project_dir)])


def install_dependencies(project_dir: Path) -> None:
    run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], cwd=project_dir)
    run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=project_dir)


def sync_artifacts(project_dir: Path, sync_root: Path, run_id: str) -> None:
    sync_root.mkdir(parents=True, exist_ok=True)
    run_root = sync_root / run_id
    run_root.mkdir(parents=True, exist_ok=True)

    targets = ["results", "checkpoints", "figures", "report"]
    for name in targets:
        src = project_dir / name
        dst = run_root / name
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)
    log(f"Artifacts synced to: {run_root}")


def save_run_manifest(project_dir: Path, run_id: str, manifest: dict) -> Path:
    manifest_dir = project_dir / "results" / "automation_runs"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{run_id}.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="One-click Colab automation for HyperDream experiments.")
    parser.add_argument("--repo-url", type=str, default=DEFAULT_REPO_URL)
    parser.add_argument("--branch", type=str, default="main")
    parser.add_argument("--project-dir", type=str, default="/content/High_Dimensional_WorldModel")
    parser.add_argument("--mount-drive", action="store_true", help="Mount Google Drive at /content/drive")
    parser.add_argument(
        "--drive-sync-dir",
        type=str,
        default="/content/drive/MyDrive/High_Dimensional_WorldModel_runs",
        help="Destination root for syncing artifacts",
    )

    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--run-tests", action="store_true")

    parser.add_argument("--skip-baseline", action="store_true")
    parser.add_argument("--skip-transfer", action="store_true")
    parser.add_argument("--skip-ablation", action="store_true")
    parser.add_argument("--skip-robustness", action="store_true")
    parser.add_argument("--skip-visualize", action="store_true")

    parser.add_argument("--baseline-epochs", type=int, default=5)
    parser.add_argument("--transfer-pretrain-epochs", type=int, default=3)
    parser.add_argument("--transfer-finetune-epochs", type=int, default=3)
    parser.add_argument("--ablation-epochs", type=int, default=4)
    parser.add_argument("--robustness-episodes", type=int, default=50)
    parser.add_argument("--eval-episodes", type=int, default=20)
    parser.add_argument("--max-steps", type=int, default=80)

    parser.add_argument("--save-every", type=int, default=5)
    parser.add_argument("--keep-last", type=int, default=5)
    parser.add_argument("--sync-to-drive", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or now_tag()
    project_dir = Path(args.project_dir).resolve()
    drive_sync_dir = Path(args.drive_sync_dir).resolve()

    manifest: dict = {
        "run_id": run_id,
        "started_at": datetime.now().isoformat(),
        "project_dir": str(project_dir),
        "commands": [],
        "status": "running",
    }

    maybe_mount_drive(args.mount_drive)
    ensure_repo(project_dir=project_dir, repo_url=args.repo_url, branch=args.branch)
    install_dependencies(project_dir=project_dir)

    if args.run_tests:
        cmd = [sys.executable, "-m", "pytest", "-q"]
        run_cmd(cmd, cwd=project_dir)
        manifest["commands"].append(" ".join(cmd))

    common = [
        "--run-id",
        run_id,
        "--max-steps",
        str(args.max_steps),
        "--eval-episodes",
        str(args.eval_episodes),
        "--save-every",
        str(args.save_every),
        "--keep-last",
        str(args.keep_last),
    ]
    if args.resume:
        common.append("--resume")

    if not args.skip_baseline:
        cmd = [sys.executable, "experiments/run_baseline.py", *common, "--epochs", str(args.baseline_epochs)]
        run_cmd(cmd, cwd=project_dir)
        manifest["commands"].append(" ".join(cmd))

    if not args.skip_transfer:
        cmd = [
            sys.executable,
            "experiments/run_transfer.py",
            *common,
            "--pretrain-epochs",
            str(args.transfer_pretrain_epochs),
            "--finetune-epochs",
            str(args.transfer_finetune_epochs),
        ]
        run_cmd(cmd, cwd=project_dir)
        manifest["commands"].append(" ".join(cmd))

    if not args.skip_ablation:
        cmd = [sys.executable, "experiments/run_ablation.py", *common, "--epochs", str(args.ablation_epochs)]
        run_cmd(cmd, cwd=project_dir)
        manifest["commands"].append(" ".join(cmd))

    if not args.skip_robustness:
        robust_cmd = [
            sys.executable,
            "experiments/run_robustness.py",
            "--run-id",
            run_id,
            "--episodes",
            str(args.robustness_episodes),
        ]
        if args.resume:
            robust_cmd.append("--resume")
        run_cmd(robust_cmd, cwd=project_dir)
        manifest["commands"].append(" ".join(robust_cmd))

    if not args.skip_visualize:
        cmd = [sys.executable, "experiments/visualize.py"]
        run_cmd(cmd, cwd=project_dir)
        manifest["commands"].append(" ".join(cmd))

    if args.sync_to_drive:
        sync_artifacts(project_dir=project_dir, sync_root=drive_sync_dir, run_id=run_id)

    manifest["status"] = "completed"
    manifest["finished_at"] = datetime.now().isoformat()
    path = save_run_manifest(project_dir=project_dir, run_id=run_id, manifest=manifest)
    log(f"Run manifest saved: {path}")
    log("Automation pipeline completed.")


if __name__ == "__main__":
    main()
