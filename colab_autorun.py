from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys


DEFAULT_REPO_URL = "https://github.com/peter941221/High_Dimensional_WorldModel.git"


def log(message: str) -> None:
    print(f"[colab-autorun] {message}", flush=True)


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    where = f" (cwd={cwd})" if cwd else ""
    log(f"RUN {' '.join(cmd)}{where}")
    try:
        subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)
    except subprocess.CalledProcessError as exc:
        log(f"FAILED (code={exc.returncode}): {' '.join(cmd)}")
        raise


def run_cmd_capture(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    where = f" (cwd={cwd})" if cwd else ""
    log(f"RUN {' '.join(cmd)}{where}")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if proc.returncode != 0:
        log(f"FAILED (code={proc.returncode}): {' '.join(cmd)}")
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr)
    return proc


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_repo(project_dir: Path, repo_url: str, branch: str) -> None:
    if (project_dir / ".git").exists():
        log("Repository already exists, pulling latest changes.")
        run_cmd(["git", "fetch", "origin"], cwd=project_dir)
        try:
            run_cmd(["git", "checkout", branch], cwd=project_dir)
        except subprocess.CalledProcessError:
            # Recover from detached head or missing local branch in Colab runtime.
            run_cmd(["git", "checkout", "-B", branch, f"origin/{branch}"], cwd=project_dir)

        pull_proc = subprocess.run(
            ["git", "pull", "--ff-only", "origin", branch],
            cwd=str(project_dir),
            check=False,
            text=True,
            capture_output=True,
        )
        if pull_proc.returncode != 0:
            if pull_proc.stdout:
                print(pull_proc.stdout, end="")
            if pull_proc.stderr:
                print(pull_proc.stderr, end="", file=sys.stderr)
            log("Fast-forward pull failed; force-reset local branch to remote for Colab reproducibility.")
            run_cmd(["git", "reset", "--hard", f"origin/{branch}"], cwd=project_dir)
    else:
        project_dir.parent.mkdir(parents=True, exist_ok=True)
        run_cmd(["git", "clone", "--branch", branch, repo_url, str(project_dir)])


def install_dependencies(project_dir: Path) -> None:
    run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], cwd=project_dir)
    run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=project_dir)


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
    parser.add_argument("--push-results-to-github", action="store_true", help="Auto commit/push this run's results to GitHub.")
    parser.add_argument("--push-branch", type=str, default="colab-results")
    parser.add_argument("--base-branch", type=str, default="main")
    parser.add_argument("--github-user", type=str, default="peter941221")
    parser.add_argument("--repo-name", type=str, default="High_Dimensional_WorldModel")
    parser.add_argument("--token-env", type=str, default="GITHUB_TOKEN")
    parser.add_argument(
        "--token-secret-name",
        type=str,
        default="GITHUB_TOKEN",
        help="Colab Secrets key name for token fallback.",
    )
    parser.add_argument("--include-checkpoints-in-push", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run_id or now_tag()
    project_dir = Path(args.project_dir).resolve()

    manifest: dict = {
        "run_id": run_id,
        "started_at": datetime.now().isoformat(),
        "project_dir": str(project_dir),
        "commands": [],
        "status": "running",
    }

    ensure_repo(project_dir=project_dir, repo_url=args.repo_url, branch=args.branch)
    install_dependencies(project_dir=project_dir)

    if args.push_results_to_github:
        preflight_cmd = [
            sys.executable,
            "colab_push_results.py",
            "--repo-dir",
            str(project_dir),
            "--run-id",
            run_id,
            "--branch",
            args.push_branch,
            "--base-branch",
            args.base_branch,
            "--github-user",
            args.github_user,
            "--repo-name",
            args.repo_name,
            "--token-env",
            args.token_env,
            "--token-secret-name",
            args.token_secret_name,
            "--check-push-access-only",
        ]
        run_cmd_capture(preflight_cmd, cwd=project_dir)
        manifest["commands"].append(" ".join(preflight_cmd))

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

    if args.push_results_to_github:
        push_cmd = [
            sys.executable,
            "colab_push_results.py",
            "--repo-dir",
            str(project_dir),
            "--run-id",
            run_id,
            "--branch",
            args.push_branch,
            "--base-branch",
            args.base_branch,
            "--github-user",
            args.github_user,
            "--repo-name",
            args.repo_name,
            "--token-env",
            args.token_env,
            "--token-secret-name",
            args.token_secret_name,
        ]
        if args.include_checkpoints_in_push:
            push_cmd.append("--include-checkpoints")
        run_cmd_capture(push_cmd, cwd=project_dir)
        manifest["commands"].append(" ".join(push_cmd))

    manifest["status"] = "completed"
    manifest["finished_at"] = datetime.now().isoformat()
    path = save_run_manifest(project_dir=project_dir, run_id=run_id, manifest=manifest)
    log(f"Run manifest saved: {path}")
    log("Automation pipeline completed.")


if __name__ == "__main__":
    main()
