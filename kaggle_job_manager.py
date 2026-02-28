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
import zipfile


ROOT = Path(__file__).resolve().parent
DEFAULT_BUILD_DIR = ROOT / ".kaggle_kernel_build"
DEFAULT_DATASET_BUILD_DIR = ROOT / ".kaggle_code_dataset_build"

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
    if is_transient_network_error(text):
        raise RuntimeError("Kaggle 网络暂时不可用（SSL/连接波动）。请稍后重试。")
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
        "seed": args.seed,
        "resume": args.resume,
        "run_tests": args.run_tests,
        "skip_install_deps": args.skip_install_deps,
        "heartbeat_every": args.heartbeat_every,
        "baseline_epochs": args.baseline_epochs,
        "transfer_pretrain_epochs": args.transfer_pretrain_epochs,
        "transfer_finetune_epochs": args.transfer_finetune_epochs,
        "ablation_epochs": args.ablation_epochs,
        "robustness_episodes": args.robustness_episodes,
        "robustness_domain_rand": args.robustness_domain_rand,
        "robustness_domain_rand_scale": args.robustness_domain_rand_scale,
        "robustness_domain_rand_profile": args.robustness_domain_rand_profile,
        "robustness_domain_rand_warmup_episodes": args.robustness_domain_rand_warmup_episodes,
        "robustness_domain_rand_warmup_epochs": args.robustness_domain_rand_warmup_epochs,
        "robustness_domain_rand_difficulties": args.robustness_domain_rand_difficulties,
        "eval_episodes": args.eval_episodes,
        "max_steps": args.max_steps,
        "save_every": args.save_every,
        "keep_last": args.keep_last,
        "skip_visualize": args.skip_visualize,
        "use_code_dataset": args.use_code_dataset,
        "code_dataset_slug": slugify(args.code_dataset_slug),
        "code_bundle_filename": args.code_bundle_filename,
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

    dataset_sources = []
    if args.use_code_dataset:
        dataset_sources.append(f"{owner}/{slugify(args.code_dataset_slug)}")

    metadata = {
        "id": f"{owner}/{slug}",
        "title": title,
        "code_file": "kaggle/run_kaggle_job.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": args.is_private,
        "enable_gpu": args.enable_gpu,
        "enable_internet": args.enable_internet,
        "dataset_sources": dataset_sources,
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


def build_project_bundle_zip(zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE_DIRS:
            src = ROOT / rel
            if not src.exists():
                continue
            for file in src.rglob("*"):
                if file.is_dir():
                    continue
                if "__pycache__" in file.parts or file.suffix == ".pyc":
                    continue
                arcname = file.relative_to(ROOT).as_posix()
                zf.write(file, arcname=arcname)

        for rel in INCLUDE_FILES:
            src = ROOT / rel
            if src.exists() and src.is_file():
                zf.write(src, arcname=src.relative_to(ROOT).as_posix())


def inject_embedded_run_config(build_dir: Path, run_config: dict) -> None:
    runner_path = build_dir / "kaggle" / "run_kaggle_job.py"
    marker = 'EMBEDDED_RUN_CONFIG_JSON = "{}"'
    payload = json.dumps(run_config, ensure_ascii=False)
    replacement = f"EMBEDDED_RUN_CONFIG_JSON = {payload!r}"

    text = runner_path.read_text(encoding="utf-8")
    if marker not in text:
        raise RuntimeError(f"Embedded config marker not found in {runner_path}")
    runner_path.write_text(text.replace(marker, replacement, 1), encoding="utf-8")


def prepare_code_dataset_bundle(args: argparse.Namespace, run_config: dict) -> Path:
    dataset_dir = Path(args.code_dataset_build_dir).resolve()
    if dataset_dir.exists():
        shutil.rmtree(dataset_dir)
    dataset_dir.mkdir(parents=True, exist_ok=True)

    dataset_slug = slugify(args.code_dataset_slug)
    metadata = {
        "title": dataset_slug,
        "id": f"{args.owner}/{dataset_slug}",
        "licenses": [{"name": "CC0-1.0"}],
    }
    (dataset_dir / "dataset-metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    bundle_name = args.code_bundle_filename
    zip_path = dataset_dir / bundle_name
    build_project_bundle_zip(zip_path)
    # Ensure runtime config is available from dataset mount for de-colab direct runner.
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("kaggle/run_config.json", json.dumps(run_config, indent=2, ensure_ascii=False))
    log(f"Prepared code dataset bundle: {dataset_dir}")
    return dataset_dir


def push_code_dataset(args: argparse.Namespace, dataset_dir: Path) -> None:
    ensure_auth()
    kaggle = resolve_kaggle_cmd()

    message = f"auto-update {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    version_cmd = [*kaggle, "datasets", "version", "-p", str(dataset_dir), "-m", message, "-r", "skip"]
    version_proc = run_cmd(version_cmd, capture=True, check=False)
    if version_proc.returncode == 0:
        log("Code dataset version updated.")
        return

    create_cmd = [*kaggle, "datasets", "create", "-p", str(dataset_dir), "-r", "skip"]
    create_proc = run_cmd(create_cmd, capture=True, check=False)
    if create_proc.returncode == 0:
        log("Code dataset created.")
        return

    create_msg = ((create_proc.stdout or "") + "\n" + (create_proc.stderr or "")).lower()
    if "already exists" in create_msg:
        retry_proc = run_cmd(version_cmd, capture=True, check=False)
        if retry_proc.returncode == 0:
            log("Code dataset version updated (after create conflict fallback).")
            return

    raise RuntimeError("Code dataset push failed. See logs above.")


def prepare(args: argparse.Namespace) -> tuple[Path, dict, Path | None]:
    build_dir = Path(args.build_dir).resolve()
    copy_project(build_dir)
    run_config = to_run_config(args)
    inject_embedded_run_config(build_dir, run_config=run_config)
    (build_dir / "kaggle" / "run_config.json").write_text(json.dumps(run_config, indent=2, ensure_ascii=False), encoding="utf-8")
    metadata = write_metadata(args, build_dir)
    dataset_dir = None
    if args.use_code_dataset:
        dataset_dir = prepare_code_dataset_bundle(args, run_config=run_config)
    log(f"Prepared kernel bundle: {build_dir}")
    log(f"Kernel id: {metadata['id']}")
    return build_dir, metadata, dataset_dir


def parse_status_text(text: str) -> str:
    lower = text.lower()
    for token in ["running", "queued", "complete", "error", "failed", "cancelled", "canceled"]:
        if token in lower:
            return "cancelled" if token == "canceled" else token
    return "unknown"


def is_transient_network_error(text: str) -> bool:
    low = text.lower()
    patterns = [
        "max retries exceeded",
        "ssl",
        "unexpected eof",
        "eof occurred",
        "connection reset",
        "timed out",
        "temporary failure",
    ]
    return any(p in low for p in patterns)


def kernels_push(args: argparse.Namespace, build_dir: Path, dataset_dir: Path | None = None) -> None:
    kaggle = resolve_kaggle_cmd()
    if args.use_code_dataset:
        if dataset_dir is None:
            dataset_dir = Path(args.code_dataset_build_dir).resolve()
            if not (dataset_dir / "dataset-metadata.json").exists():
                dataset_dir = prepare_code_dataset_bundle(args, run_config=to_run_config(args))
        push_code_dataset(args, dataset_dir)
    ensure_auth()
    run_cmd([*kaggle, "kernels", "push", "-p", str(build_dir)], capture=True)


def kernels_status(kernel_id: str) -> str:
    kaggle = resolve_kaggle_cmd()
    last_text = ""
    for attempt in range(4):
        proc = run_cmd([*kaggle, "kernels", "status", kernel_id], capture=True, check=False)
        text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        last_text = text
        if proc.returncode == 0:
            return parse_status_text(text)
        if attempt < 3 and is_transient_network_error(text):
            log(f"Transient network error on status; retry {attempt + 1}/3")
            time.sleep(3)
            continue
        raise subprocess.CalledProcessError(proc.returncode, [*kaggle, "kernels", "status", kernel_id], output=proc.stdout, stderr=proc.stderr)
    return parse_status_text(last_text)


def kernels_watch(kernel_id: str, interval: int, timeout_minutes: int) -> str:
    ensure_auth()
    deadline = time.time() + timeout_minutes * 60
    while True:
        status = kernels_status(kernel_id)
        log(f"status={status}")
        if status in {"complete", "error", "failed", "cancelled"}:
            return status
        if time.time() > deadline:
            raise TimeoutError(f"watch timeout after {timeout_minutes} minutes")
        time.sleep(max(interval, 10))


def kernels_output(kernel_id: str, out_dir: Path, file_pattern: str | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    kaggle = resolve_kaggle_cmd()
    base_cmd = [*kaggle, "kernels", "output", kernel_id, "-p", str(out_dir), "--force"]
    if file_pattern:
        base_cmd.extend(["--file-pattern", file_pattern])
    last_error = None
    for attempt in range(4):
        proc = run_cmd(base_cmd, capture=True, check=False)
        if proc.returncode == 0:
            return
        text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        last_error = subprocess.CalledProcessError(
            proc.returncode,
            base_cmd,
            output=proc.stdout,
            stderr=proc.stderr,
        )
        if attempt < 3 and is_transient_network_error(text):
            log(f"Transient network error on output; retry {attempt + 1}/3")
            time.sleep(3)
            continue
        raise last_error
    if last_error is not None:
        raise last_error


def add_common_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--skip-install-deps", dest="skip_install_deps", action="store_true")
    parser.add_argument("--install-deps", dest="skip_install_deps", action="store_false")
    parser.set_defaults(skip_install_deps=True)
    parser.add_argument("--heartbeat-every", type=int, default=1)
    parser.add_argument("--skip-visualize", action="store_true")
    parser.add_argument("--baseline-epochs", type=int, default=12)
    parser.add_argument("--transfer-pretrain-epochs", type=int, default=8)
    parser.add_argument("--transfer-finetune-epochs", type=int, default=8)
    parser.add_argument("--ablation-epochs", type=int, default=8)
    parser.add_argument("--robustness-episodes", type=int, default=120)
    parser.add_argument(
        "--robustness-domain-rand",
        action="store_true",
        help="Enable domain randomization for robustness stage only.",
    )
    parser.add_argument(
        "--robustness-domain-rand-scale",
        type=float,
        default=0.20,
        help="Relative randomization scale for robustness stage.",
    )
    parser.add_argument(
        "--robustness-domain-rand-profile",
        type=str,
        choices=["full", "conservative"],
        default="conservative",
        help="Domain randomization profile for robustness stage.",
    )
    parser.add_argument(
        "--robustness-domain-rand-warmup-episodes",
        type=int,
        default=200,
        help="Warmup episodes for robustness-stage randomization scale.",
    )
    parser.add_argument(
        "--robustness-domain-rand-warmup-epochs",
        type=int,
        default=0,
        help="Warmup epochs for robustness-stage randomization scale.",
    )
    parser.add_argument(
        "--robustness-domain-rand-difficulties",
        type=str,
        choices=["all", "medium_hard", "hard_only"],
        default="hard_only",
        help="Difficulty scope for robustness-stage randomization.",
    )
    parser.add_argument("--eval-episodes", type=int, default=40)
    parser.add_argument("--max-steps", type=int, default=120)
    parser.add_argument("--save-every", type=int, default=4)
    parser.add_argument("--keep-last", type=int, default=6)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kaggle kernel automation for HyperDream.")
    parser.add_argument("--build-dir", type=str, default=str(DEFAULT_BUILD_DIR))
    parser.add_argument("--code-dataset-build-dir", type=str, default=str(DEFAULT_DATASET_BUILD_DIR))
    parser.add_argument("--owner", type=str, default="")
    parser.add_argument("--slug", type=str, default="high-dimensional-worldmodel-aggressive")
    parser.add_argument("--code-dataset-slug", type=str, default="high-dimensional-worldmodel-src")
    parser.add_argument("--code-bundle-filename", type=str, default="project_bundle.zip")
    parser.add_argument("--use-code-dataset", dest="use_code_dataset", action="store_true")
    parser.add_argument("--no-code-dataset", dest="use_code_dataset", action="store_false")
    parser.set_defaults(use_code_dataset=True)
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
    parser.add_argument(
        "--output-file-pattern",
        type=str,
        default=r"High_Dimensional_WorldModel/(results|figures|report)/.*|.*\.log|.*summary\.json",
        help="Regex passed to `kaggle kernels output --file-pattern` to limit downloads.",
    )

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
        dataset_dir = None
        if not (build_dir / "kernel-metadata.json").exists():
            build_dir, _, dataset_dir = prepare(args)
        kernels_push(args, build_dir, dataset_dir=dataset_dir)
        return

    if args.command == "status":
        if not kernel_id:
            raise ValueError("--owner is required for status")
        ensure_auth()
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
        ensure_auth()
        kernels_output(kernel_id, output_dir, file_pattern=args.output_file_pattern)
        return

    if args.command == "run":
        build_dir, metadata, dataset_dir = prepare(args)
        kernels_push(args, build_dir, dataset_dir=dataset_dir)
        status = kernels_watch(metadata["id"], interval=args.watch_interval, timeout_minutes=args.watch_timeout_minutes)
        if status != "complete":
            raise RuntimeError(f"Kaggle kernel ended with status={status}")
        kernels_output(metadata["id"], output_dir, file_pattern=args.output_file_pattern)
        return

    raise ValueError(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
