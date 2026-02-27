from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent
DEFAULT_BUILD_DIR = ROOT / ".kaggle_kernel_build"

INCLUDE_DIRS = [
    "configs",
    "envs",
    "experiments",
    "models",
    "physics",
    "training",
    "kaggle",
]

INCLUDE_FILES = [
    "colab_autorun.py",
    "colab_push_results.py",
    "requirements.txt",
    "README.md",
    "RUNBOOK.md",
]


def log(message: str) -> None:
    print(f"[kaggle-manager] {message}", flush=True)


def run_cmd(cmd: list[str], cwd: Path | None = None, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    log(f"RUN {' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        capture_output=capture,
    )
    if capture:
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr)
    return proc


def resolve_kaggle_cmd() -> list[str]:
    kaggle_exe = shutil.which("kaggle")
    if kaggle_exe:
        return [kaggle_exe]

    scripts_dir = Path(sys.executable).resolve().parent / "Scripts"
    candidate = scripts_dir / "kaggle.exe"
    if candidate.exists():
        return [str(candidate)]

    raise FileNotFoundError(
        "未找到 kaggle CLI。请先安装：python -m pip install -U kaggle"
    )


def ensure_auth() -> None:
    kaggle = resolve_kaggle_cmd()
    run_cmd([*kaggle, "config", "view"], capture=True, check=False)

    probe = run_cmd([*kaggle, "kernels", "list", "--mine", "--page-size", "1"], capture=True, check=False)
    if probe.returncode == 0:
        return

    text = ((probe.stdout or "") + "\n" + (probe.stderr or "")).lower()
    if "401" in text or "unauthorized" in text:
        raise RuntimeError(
            "Kaggle 认证失败（401 Unauthorized）。\n"
            "请在 Kaggle 网站重新生成 API key，更新 ~/.kaggle/kaggle.json 后重试。"
        )
    raise RuntimeError(
        "Kaggle 未登录或认证不可用。请先完成任一方式：\n"
        "1) 放置 ~/.kaggle/kaggle.json\n"
        "2) 设置环境变量 KAGGLE_USERNAME / KAGGLE_KEY\n"
        "然后再执行 push/status/watch/output。"
    )


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return slug or "hyperdream-aggressive"


def to_run_config(args: argparse.Namespace) -> dict:
    run_id = args.run_id or f"kaggle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return {
        "run_id": run_id,
        "resume": args.resume,
        "run_tests": args.run_tests,
        "skip_install_deps": args.skip_install_deps,
        "heartbeat_every": args.heartbeat_every,
        "push_after_each_stage": args.push_after_each_stage,
        "baseline_epochs": args.baseline_epochs,
        "transfer_pretrain_epochs": args.transfer_pretrain_epochs,
        "transfer_finetune_epochs": args.transfer_finetune_epochs,
        "ablation_epochs": args.ablation_epochs,
        "robustness_episodes": args.robustness_episodes,
        "eval_episodes": args.eval_episodes,
        "max_steps": args.max_steps,
        "save_every": args.save_every,
        "keep_last": args.keep_last,
        "push_results_to_github": args.push_results_to_github,
        "push_branch": args.push_branch,
        "base_branch": args.base_branch,
        "github_user": args.github_user,
        "repo_name": args.repo_name,
        "token_env": args.token_env,
        "token_secret_name": args.token_secret_name,
        "include_checkpoints_in_push": args.include_checkpoints_in_push,
    }


def write_metadata(args: argparse.Namespace, build_dir: Path) -> dict:
    slug = slugify(args.slug)
    owner = args.owner
    if not owner:
        raise ValueError("缺少 --owner（你的 Kaggle 用户名）")

    requested_title = (args.title or "").strip()
    title = requested_title or slug
    if slugify(title) != slug:
        log(f"title 与 slug 不一致，已自动对齐 title='{slug}' 以避免 Kaggle slug 偏移")
        title = slug

    metadata = {
        "id": f"{owner}/{slug}",
        "title": title,
        "code_file": "kaggle/run_kaggle_job.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": args.is_private,
        "enable_gpu": args.enable_gpu,
        "enable_internet": args.enable_internet,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
    }
    (build_dir / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return metadata


def copy_project(build_dir: Path) -> None:
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    for rel in INCLUDE_DIRS:
        src = ROOT / rel
        dst = build_dir / rel
        if src.exists():
            shutil.copytree(
                src,
                dst,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".ipynb_checkpoints"),
            )

    for rel in INCLUDE_FILES:
        src = ROOT / rel
        dst = build_dir / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # Keep runtime directories expected by training scripts.
    for rel in ["checkpoints", "results", "figures"]:
        d = build_dir / rel
        d.mkdir(parents=True, exist_ok=True)
        keep = d / ".gitkeep"
        keep.write_text("", encoding="utf-8")


def prepare(args: argparse.Namespace) -> tuple[Path, dict]:
    build_dir = Path(args.build_dir).resolve()
    copy_project(build_dir)
    run_config = to_run_config(args)
    (build_dir / "kaggle" / "run_config.json").write_text(json.dumps(run_config, indent=2, ensure_ascii=False), encoding="utf-8")
    metadata = write_metadata(args, build_dir)
    log(f"Prepared kernel bundle: {build_dir}")
    log(f"Kernel id: {metadata['id']}")
    return build_dir, metadata


def parse_status_text(text: str) -> str:
    lower = text.lower()
    for token in ["running", "queued", "complete", "error", "failed", "cancelled", "canceled"]:
        if token in lower:
            return "cancelled" if token == "canceled" else token
    return "unknown"


def kernels_push(build_dir: Path) -> None:
    ensure_auth()
    kaggle = resolve_kaggle_cmd()
    run_cmd([*kaggle, "kernels", "push", "-p", str(build_dir)], capture=True)


def kernels_status(kernel_id: str) -> str:
    ensure_auth()
    kaggle = resolve_kaggle_cmd()
    proc = run_cmd([*kaggle, "kernels", "status", kernel_id], capture=True)
    return parse_status_text((proc.stdout or "") + "\n" + (proc.stderr or ""))


def kernels_watch(kernel_id: str, interval: int, timeout_minutes: int) -> str:
    deadline = time.time() + timeout_minutes * 60
    while True:
        status = kernels_status(kernel_id)
        log(f"status={status}")
        if status in {"complete", "error", "failed", "cancelled"}:
            return status
        if time.time() > deadline:
            raise TimeoutError(f"watch timeout after {timeout_minutes} minutes")
        time.sleep(max(interval, 10))


def kernels_output(kernel_id: str, out_dir: Path) -> None:
    ensure_auth()
    out_dir.mkdir(parents=True, exist_ok=True)
    kaggle = resolve_kaggle_cmd()
    run_cmd([*kaggle, "kernels", "output", kernel_id, "-p", str(out_dir), "--force"], capture=True)


def add_common_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--skip-install-deps", dest="skip_install_deps", action="store_true")
    parser.add_argument("--install-deps", dest="skip_install_deps", action="store_false")
    parser.set_defaults(skip_install_deps=True)
    parser.add_argument("--heartbeat-every", type=int, default=1)
    parser.add_argument("--push-after-each-stage", dest="push_after_each_stage", action="store_true")
    parser.add_argument("--no-push-after-each-stage", dest="push_after_each_stage", action="store_false")
    parser.set_defaults(push_after_each_stage=True)
    parser.add_argument("--baseline-epochs", type=int, default=12)
    parser.add_argument("--transfer-pretrain-epochs", type=int, default=8)
    parser.add_argument("--transfer-finetune-epochs", type=int, default=8)
    parser.add_argument("--ablation-epochs", type=int, default=8)
    parser.add_argument("--robustness-episodes", type=int, default=120)
    parser.add_argument("--eval-episodes", type=int, default=40)
    parser.add_argument("--max-steps", type=int, default=120)
    parser.add_argument("--save-every", type=int, default=4)
    parser.add_argument("--keep-last", type=int, default=6)
    parser.add_argument("--push-results-to-github", action="store_true")
    parser.add_argument("--push-branch", type=str, default="colab-results")
    parser.add_argument("--base-branch", type=str, default="main")
    parser.add_argument("--github-user", type=str, default="peter941221")
    parser.add_argument("--repo-name", type=str, default="High_Dimensional_WorldModel")
    parser.add_argument("--token-env", type=str, default="GITHUB_TOKEN")
    parser.add_argument("--token-secret-name", type=str, default="GITHUB_TOKEN")
    parser.add_argument("--include-checkpoints-in-push", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kaggle kernel automation for HyperDream.")
    parser.add_argument("--build-dir", type=str, default=str(DEFAULT_BUILD_DIR))
    parser.add_argument("--owner", type=str, default="")
    parser.add_argument("--slug", type=str, default="high-dimensional-worldmodel-aggressive")
    parser.add_argument("--title", type=str, default="")
    parser.add_argument("--private", dest="is_private", action="store_true")
    parser.add_argument("--public", dest="is_private", action="store_false")
    parser.set_defaults(is_private=True)
    parser.add_argument("--enable-gpu", dest="enable_gpu", action="store_true")
    parser.add_argument("--disable-gpu", dest="enable_gpu", action="store_false")
    parser.set_defaults(enable_gpu=True)
    parser.add_argument("--enable-internet", dest="enable_internet", action="store_true")
    parser.add_argument("--disable-internet", dest="enable_internet", action="store_false")
    parser.set_defaults(enable_internet=True)
    parser.add_argument("--output-dir", type=str, default=str(ROOT / "kaggle_outputs"))

    add_common_runtime_args(parser)
    parser.add_argument("--watch-interval", type=int, default=60)
    parser.add_argument("--watch-timeout-minutes", type=int, default=720)

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare", help="Build Kaggle bundle only.")
    sub.add_parser("push", help="Push prepared bundle to Kaggle.")
    sub.add_parser("status", help="Query Kaggle kernel status.")
    sub.add_parser("watch", help="Poll status until complete/error.")
    sub.add_parser("output", help="Download kernel output files.")
    sub.add_parser("run", help="Prepare + push + watch + download outputs.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    kernel_id = f"{args.owner}/{slugify(args.slug)}" if args.owner else ""
    build_dir = Path(args.build_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if args.command == "prepare":
        prepare(args)
        return

    if args.command == "push":
        if not (build_dir / "kernel-metadata.json").exists():
            prepare(args)
        kernels_push(build_dir)
        return

    if args.command == "status":
        if not kernel_id:
            raise ValueError("--owner is required for status")
        status = kernels_status(kernel_id)
        log(f"status={status}")
        return

    if args.command == "watch":
        if not kernel_id:
            raise ValueError("--owner is required for watch")
        status = kernels_watch(kernel_id, interval=args.watch_interval, timeout_minutes=args.watch_timeout_minutes)
        log(f"final_status={status}")
        return

    if args.command == "output":
        if not kernel_id:
            raise ValueError("--owner is required for output")
        kernels_output(kernel_id, output_dir)
        return

    if args.command == "run":
        build_dir, metadata = prepare(args)
        kernels_push(build_dir)
        status = kernels_watch(metadata["id"], interval=args.watch_interval, timeout_minutes=args.watch_timeout_minutes)
        if status != "complete":
            raise RuntimeError(f"Kaggle kernel ended with status={status}")
        kernels_output(metadata["id"], output_dir)
        return

    raise ValueError(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
