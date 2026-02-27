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
    parser.add_argument(
        "--token-secret-name",
        type=str,
        default=None,
        help="Colab Secrets key name. If token-env is empty, try google.colab.userdata.get(secret-name).",
    )
    parser.add_argument("--git-user-name", type=str, default="colab-bot")
    parser.add_argument("--git-user-email", type=str, default="colab-bot@users.noreply.github.com")
    parser.add_argument("--include-checkpoints", action="store_true", help="Also push checkpoints for this run.")
    parser.add_argument("--allow-empty", action="store_true", help="Create commit even if no file changes.")
    parser.add_argument(
        "--check-token-only",
        action="store_true",
        help="Only validate token resolution and exit without git add/commit/push.",
    )
    parser.add_argument(
        "--check-push-access-only",
        action="store_true",
        help="Validate token + remote write permission (git push --dry-run) and exit.",
    )
    return parser.parse_args()


def resolve_token(token_env: str, token_secret_name: str | None) -> str:
    token = os.environ.get(token_env, "").strip()
    if token:
        return token

    # Try Colab Secrets fallbacks to minimize notebook-side manual edits.
    secret_candidates = []
    if token_secret_name and token_secret_name.strip():
        secret_candidates.append(token_secret_name.strip())
    secret_candidates.extend(
        [
            token_env,
            "GITHUB_TOKEN",
            "GITHUB_1",
            "GITHUB_T",
            "GH_TOKEN",
        ]
    )

    # de-dup while preserving order
    seen = set()
    secret_candidates = [s for s in secret_candidates if not (s in seen or seen.add(s))]

    if secret_candidates:
        try:
            from google.colab import userdata  # type: ignore

            for candidate in secret_candidates:
                try:
                    secret = userdata.get(candidate)
                except Exception:
                    continue
                if secret:
                    token = str(secret).strip()
                    if token:
                        os.environ[token_env] = token
                        log(f"Token resolved from Colab Secret: {candidate}")
                        return token
        except Exception as exc:
            log(f"Secret lookup skipped: {exc}")

    raise EnvironmentError(
        "Missing token. Provide env "
        f"`{token_env}` or set one of Colab Secrets: {', '.join(secret_candidates)}."
    )


def ensure_repo(repo_dir: Path) -> None:
    if not (repo_dir / ".git").exists():
        raise FileNotFoundError(f"Not a git repo: {repo_dir}")


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

    # Result artifacts are intentionally ignored in project .gitignore.
    # Force-add only the selected run outputs for result branch publishing.
    run_cmd(["git", "add", "-f", *unique], cwd=repo_dir)
    return unique


def has_staged_changes(repo_dir: Path) -> bool:
    out = run_cmd_output(["git", "diff", "--cached", "--name-only"], cwd=repo_dir)
    return bool(out.strip())


def set_authenticated_remote(repo_dir: Path, github_user: str, repo_name: str, token: str) -> None:
    auth_url = f"https://x-access-token:{token}@github.com/{github_user}/{repo_name}.git"
    # quiet to avoid leaking token in logs
    subprocess.run(["git", "remote", "set-url", "origin", auth_url], cwd=str(repo_dir), check=True, text=True, capture_output=True)


def restore_public_remote(repo_dir: Path, github_user: str, repo_name: str) -> None:
    public_url = f"https://github.com/{github_user}/{repo_name}.git"
    subprocess.run(["git", "remote", "set-url", "origin", public_url], cwd=str(repo_dir), check=True, text=True, capture_output=True)


def ensure_push_access(repo_dir: Path, branch: str) -> None:
    probe = subprocess.run(
        ["git", "push", "--dry-run", "origin", f"HEAD:refs/heads/{branch}"],
        cwd=str(repo_dir),
        check=False,
        text=True,
        capture_output=True,
    )
    if probe.stdout:
        print(probe.stdout, end="")
    if probe.stderr:
        print(probe.stderr, end="", file=sys.stderr)
    if probe.returncode != 0:
        msg = (probe.stderr or probe.stdout or "").lower()
        if (
            "403" in msg
            or "permission" in msg
            or "denied" in msg
            or "authentication failed" in msg
            or "invalid username or token" in msg
        ):
            raise PermissionError(
                "GitHub push denied (403). Check token scope/access:\n"
                "- Fine-grained PAT: Repository access includes target repo + Contents=Read and write.\n"
                "- Classic PAT: include `repo` scope.\n"
                "- Confirm Colab Secret value is the token itself (not username).\n"
            )
        raise RuntimeError("Git push dry-run failed. See logs above for details.")


def main() -> None:
    args = parse_args()
    repo_dir = Path(args.repo_dir).resolve()

    token = resolve_token(token_env=args.token_env, token_secret_name=args.token_secret_name)
    if args.check_token_only:
        log("Token preflight passed.")
        return

    ensure_repo(repo_dir)

    run_cmd(["git", "config", "user.name", args.git_user_name], cwd=repo_dir)
    run_cmd(["git", "config", "user.email", args.git_user_email], cwd=repo_dir)
    run_cmd(["git", "fetch", "origin"], cwd=repo_dir)

    set_authenticated_remote(repo_dir, args.github_user, args.repo_name, token)
    try:
        ensure_push_access(repo_dir, branch=args.branch)
    finally:
        restore_public_remote(repo_dir, args.github_user, args.repo_name)

    if args.check_push_access_only:
        log("Push-access preflight passed.")
        return

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
        # Push current HEAD commit to target result branch directly; avoids branch checkout conflicts.
        push = subprocess.run(
            ["git", "push", "-u", "origin", f"HEAD:refs/heads/{args.branch}", "--force-with-lease"],
            cwd=str(repo_dir),
            check=False,
            text=True,
            capture_output=True,
        )
        if push.stdout:
            print(push.stdout, end="")
        if push.stderr:
            print(push.stderr, end="", file=sys.stderr)
        if push.returncode != 0:
            msg = (push.stderr or push.stdout or "").lower()
            if (
                "403" in msg
                or "permission" in msg
                or "denied" in msg
                or "authentication failed" in msg
                or "invalid username or token" in msg
            ):
                raise PermissionError(
                    "GitHub push denied (403). Verify PAT permissions and repository access in Colab Secret."
                )
            raise subprocess.CalledProcessError(
                push.returncode,
                ["git", "push", "-u", "origin", f"HEAD:refs/heads/{args.branch}", "--force-with-lease"],
                output=push.stdout,
                stderr=push.stderr,
            )
    finally:
        restore_public_remote(repo_dir, args.github_user, args.repo_name)

    log("Pushed result artifacts to GitHub successfully.")
    log(f"Branch: {args.branch}")
    log(f"Included paths: {', '.join(staged)}")


if __name__ == "__main__":
    main()
