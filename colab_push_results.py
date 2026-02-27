from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys


def log(message: str) -> None:
    print(f"[colab-push] {message}", flush=True)


def run_cmd(cmd: list[str], cwd: Path, quiet: bool = False) -> subprocess.CompletedProcess:
    if not quiet:
        log(f"RUN {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd), check=True, text=True, capture_output=quiet)


def run_cmd_output(cmd: list[str], cwd: Path) -> str:
    out = subprocess.run(cmd, cwd=str(cwd), check=True, text=True, capture_output=True)
    return out.stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Push experiment results from Colab to GitHub.")
    parser.add_argument("--repo-dir", type=str, default="/content/High_Dimensional_WorldModel")
    parser.add_argument("--run-id", type=str, required=True, help="Run identifier to push (results/<exp>/<run_id>).")
    parser.add_argument("--branch", type=str, default="colab-results", help="Target branch for result commits.")
    parser.add_argument("--base-branch", type=str, default="main", help="Base branch used when creating target branch.")
    parser.add_argument("--github-user", type=str, default="peter941221")
    parser.add_argument("--repo-name", type=str, default="High_Dimensional_WorldModel")
    parser.add_argument("--token-env", type=str, default="GITHUB_TOKEN", help="Environment variable holding PAT.")
    parser.add_argument("--git-user-name", type=str, default="colab-bot")
    parser.add_argument("--git-user-email", type=str, default="colab-bot@users.noreply.github.com")
    parser.add_argument("--include-checkpoints", action="store_true", help="Also push checkpoints for this run.")
    parser.add_argument("--allow-empty", action="store_true", help="Create commit even if no file changes.")
    return parser.parse_args()


def ensure_repo(repo_dir: Path) -> None:
    if not (repo_dir / ".git").exists():
        raise FileNotFoundError(f"Not a git repo: {repo_dir}")


def ensure_branch(repo_dir: Path, branch: str, base_branch: str) -> None:
    run_cmd(["git", "fetch", "origin"], cwd=repo_dir)
    remote_heads = run_cmd_output(["git", "ls-remote", "--heads", "origin", branch], cwd=repo_dir)
    if remote_heads:
        run_cmd(["git", "checkout", branch], cwd=repo_dir)
        run_cmd(["git", "pull", "--ff-only", "origin", branch], cwd=repo_dir)
    else:
        run_cmd(["git", "checkout", base_branch], cwd=repo_dir)
        run_cmd(["git", "pull", "--ff-only", "origin", base_branch], cwd=repo_dir)
        run_cmd(["git", "checkout", "-b", branch], cwd=repo_dir)


def stage_run_files(repo_dir: Path, run_id: str, include_checkpoints: bool) -> list[str]:
    candidates = []
    for exp in ["baseline", "transfer", "ablation", "robustness"]:
        path = repo_dir / "results" / exp / run_id
        if path.exists():
            candidates.append(path.relative_to(repo_dir).as_posix())

    for top_file in [
        repo_dir / "results" / "baseline.json",
        repo_dir / "results" / "transfer.json",
        repo_dir / "results" / "ablation.json",
        repo_dir / "results" / "robustness.json",
    ]:
        if top_file.exists():
            candidates.append(top_file.relative_to(repo_dir).as_posix())

    figures = repo_dir / "figures"
    if figures.exists():
        for png in figures.glob("*.png"):
            candidates.append(png.relative_to(repo_dir).as_posix())

    if include_checkpoints:
        for exp in ["baseline", "transfer", "ablation", "robustness"]:
            ck = repo_dir / "checkpoints" / exp / run_id
            if ck.exists():
                candidates.append(ck.relative_to(repo_dir).as_posix())

    # remove duplicates while keeping order
    unique = []
    seen = set()
    for item in candidates:
        if item not in seen:
            unique.append(item)
            seen.add(item)

    if not unique:
        raise FileNotFoundError(f"No result artifacts found for run_id={run_id}")

    run_cmd(["git", "add", *unique], cwd=repo_dir)
    return unique


def has_staged_changes(repo_dir: Path) -> bool:
    out = run_cmd_output(["git", "diff", "--cached", "--name-only"], cwd=repo_dir)
    return bool(out.strip())


def set_authenticated_remote(repo_dir: Path, github_user: str, repo_name: str, token: str) -> None:
    auth_url = f"https://{github_user}:{token}@github.com/{github_user}/{repo_name}.git"
    # quiet to avoid leaking token in logs
    subprocess.run(["git", "remote", "set-url", "origin", auth_url], cwd=str(repo_dir), check=True, text=True, capture_output=True)


def restore_public_remote(repo_dir: Path, github_user: str, repo_name: str) -> None:
    public_url = f"https://github.com/{github_user}/{repo_name}.git"
    subprocess.run(["git", "remote", "set-url", "origin", public_url], cwd=str(repo_dir), check=True, text=True, capture_output=True)


def main() -> None:
    args = parse_args()
    repo_dir = Path(args.repo_dir).resolve()
    ensure_repo(repo_dir)

    token = os.environ.get(args.token_env, "").strip()
    if not token:
        raise EnvironmentError(f"Missing GitHub token in env var: {args.token_env}")

    run_cmd(["git", "config", "user.name", args.git_user_name], cwd=repo_dir)
    run_cmd(["git", "config", "user.email", args.git_user_email], cwd=repo_dir)
    ensure_branch(repo_dir, args.branch, args.base_branch)

    staged = stage_run_files(repo_dir, run_id=args.run_id, include_checkpoints=args.include_checkpoints)
    changed = has_staged_changes(repo_dir)

    commit_message = f"results: colab run {args.run_id} @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if changed:
        run_cmd(["git", "commit", "-m", commit_message], cwd=repo_dir)
    elif args.allow_empty:
        run_cmd(["git", "commit", "--allow-empty", "-m", commit_message], cwd=repo_dir)
    else:
        log("No staged changes detected; skip commit/push.")
        return

    set_authenticated_remote(repo_dir, args.github_user, args.repo_name, token)
    try:
        run_cmd(["git", "push", "-u", "origin", args.branch], cwd=repo_dir)
    finally:
        restore_public_remote(repo_dir, args.github_user, args.repo_name)

    log("Pushed result artifacts to GitHub successfully.")
    log(f"Branch: {args.branch}")
    log(f"Included paths: {', '.join(staged)}")


if __name__ == "__main__":
    main()
