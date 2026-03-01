from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import time


REPO_URL = "https://github.com/peter941221/High_Dimensional_WorldModel.git"
PROJECT_DIR = Path("/kaggle/working/High_Dimensional_WorldModel")
OUTPUT_SUMMARY = Path("/kaggle/working") / "hyperdream_kaggle_summary.json"
# Patched at kernel build time by kaggle_job_manager.py when available.
EMBEDDED_RUN_CONFIG_JSON = "{}"


def log(message: str) -> None:
    print(f"[kaggle-runner] {message}", flush=True)


def to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_config(extra_candidates: list[Path] | None = None) -> dict:
    defaults = {
        "run_id": f"kaggle_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "seed": None,
        "resume": False,
        "run_tests": False,
        "skip_install_deps": False,
        "heartbeat_every": 1,
        "baseline_epochs": 12,
        "transfer_pretrain_epochs": 8,
        "transfer_finetune_epochs": 8,
        "ablation_epochs": 8,
        "skip_ablation": False,
        "robustness_episodes": 120,
        "domain_rand": False,
        "domain_rand_scale": 0.20,
        "domain_rand_profile": "conservative",
        "domain_rand_warmup_episodes": 0,
        "domain_rand_warmup_epochs": 0,
        "domain_rand_scratch_multiplier": 1.0,
        "domain_rand_source_multiplier": 1.0,
        "domain_rand_finetune_multiplier": 1.0,
        "training_guidance": "model_only",
        "guidance_blend_ratio": 0.7,
        "policy_noise_std": 0.1,
        "eval_policy_mode": "model_only",
        "eval_guidance_blend_ratio": 0.7,
        "robustness_domain_rand": False,
        "robustness_domain_rand_scale": 0.20,
        "robustness_domain_rand_profile": "conservative",
        "robustness_domain_rand_warmup_episodes": 200,
        "robustness_domain_rand_warmup_epochs": 0,
        "robustness_domain_rand_difficulties": "hard_only",
        "eval_episodes": 40,
        "max_steps": 120,
        "save_every": 4,
        "keep_last": 6,
        "skip_visualize": False,
        "use_code_dataset": True,
        "code_dataset_slug": "high-dimensional-worldmodel-src",
        "code_bundle_filename": "project_bundle.zip",
    }
    try:
        embedded_cfg = json.loads(EMBEDDED_RUN_CONFIG_JSON)
    except json.JSONDecodeError:
        embedded_cfg = {}
        log("Embedded run config JSON decode failed; ignored.")
    if isinstance(embedded_cfg, dict) and embedded_cfg:
        defaults.update(embedded_cfg)
        log("Loaded embedded run config from kernel script.")

    config_candidates = [
        # Preferred: config generated adjacent to this runtime script in Kaggle kernel bundle.
        Path(__file__).resolve().parent / "run_config.json",
        # Legacy fallback path used by earlier kernel layouts.
        Path("/kaggle/src/kaggle/run_config.json"),
        # Runtime extracted project path fallback.
        PROJECT_DIR / "kaggle" / "run_config.json",
        # CWD fallbacks for varying Kaggle script layouts.
        Path.cwd() / "kaggle" / "run_config.json",
        Path.cwd() / "run_config.json",
    ]
    if extra_candidates:
        config_candidates.extend(extra_candidates)
    for cfg_path in config_candidates:
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            defaults.update(data)
            log(f"Loaded run config from: {cfg_path}")
            break
    else:
        log("run_config.json not found, using built-in defaults.")
    return defaults


def dataset_mount_path(dataset_slug: str) -> Path:
    return Path("/kaggle/input") / dataset_slug


def log_startup_diagnostics(cfg: dict) -> None:
    log("Startup path diagnostics begin.")
    log(f"Python executable: {sys.executable}")
    log(f"CWD: {Path.cwd()}")
    log(f"__file__: {Path(__file__).resolve()}")
    log(f"PROJECT_DIR target: {PROJECT_DIR}")
    log(f"/kaggle/src exists: {Path('/kaggle/src').exists()}")
    log(f"/kaggle/input exists: {Path('/kaggle/input').exists()}")
    log(
        "Config toggles: "
        f"use_code_dataset={cfg.get('use_code_dataset')} "
        f"code_dataset_slug={cfg.get('code_dataset_slug')} "
        f"code_bundle_filename={cfg.get('code_bundle_filename')}"
    )
    bundle_roots = [
        Path(__file__).resolve().parent,
        Path.cwd(),
        Path("/kaggle/src"),
    ]
    for root in bundle_roots:
        log(
            "Bundle root candidate: "
            f"{root} "
            f"exists={root.exists()} "
            f"has_experiments={(root / 'experiments').exists()} "
            f"has_configs={(root / 'configs').exists()} "
            f"has_kaggle={(root / 'kaggle').exists()}"
        )
    log("Startup path diagnostics end.")


def prepare_from_dataset(cfg: dict) -> Path | None:
    if not to_bool(cfg.get("use_code_dataset", True)):
        log("Dataset bootstrap disabled by config: use_code_dataset=false")
        return None

    slug = str(cfg.get("code_dataset_slug", "")).strip()
    if not slug:
        log("Dataset bootstrap skipped: empty code_dataset_slug")
        return None

    mount_dir = dataset_mount_path(slug)
    bundle_name = str(cfg.get("code_bundle_filename", "project_bundle.zip"))
    bundle_path = mount_dir / bundle_name
    if not mount_dir.exists():
        # Fallback: search all mounted datasets for the expected bundle/source layout.
        input_root = Path("/kaggle/input")
        if input_root.exists():
            for candidate_dir in input_root.iterdir():
                if not candidate_dir.is_dir():
                    continue
                if (candidate_dir / bundle_name).exists() or (candidate_dir / "experiments").exists():
                    mount_dir = candidate_dir
                    bundle_path = mount_dir / bundle_name
                    log(f"Dataset slug fallback matched mount: {mount_dir}")
                    break
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

    if (mount_dir / "experiments").exists():
        log(f"Copying source tree from dataset mount: {mount_dir}")
        shutil.copytree(mount_dir, PROJECT_DIR, dirs_exist_ok=True)
        return PROJECT_DIR

    log("Dataset mount exists but no code bundle/source file found.")
    return None


def prepare_from_kernel_bundle() -> Path | None:
    # Kaggle script kernels already ship repository files in /kaggle/src.
    # Use that bundle as a network-free fallback when dataset mount is unavailable.
    bundle_roots = [
        Path(__file__).resolve().parent,
        Path.cwd(),
        Path("/kaggle/src"),
    ]
    for root in bundle_roots:
        has_experiments = (root / "experiments").exists()
        has_configs = (root / "configs").exists()
        has_kaggle = (root / "kaggle").exists()
        if has_experiments and has_configs:
            if PROJECT_DIR.exists():
                shutil.rmtree(PROJECT_DIR)
            PROJECT_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copytree(root, PROJECT_DIR, dirs_exist_ok=True)
            log(f"Using kernel bundled source fallback: {root}")
            return PROJECT_DIR
        log(
            "Kernel bundle root rejected: "
            f"{root} "
            f"has_experiments={has_experiments} "
            f"has_configs={has_configs} "
            f"has_kaggle={has_kaggle}"
        )
    log("Kernel bundle fallback unavailable across all candidate roots.")
    return None


def ensure_repo() -> Path:
    if (PROJECT_DIR / ".git").exists():
        subprocess.run(["git", "-C", str(PROJECT_DIR), "fetch", "origin"], check=True)
        subprocess.run(["git", "-C", str(PROJECT_DIR), "checkout", "main"], check=True)
        subprocess.run(["git", "-C", str(PROJECT_DIR), "reset", "--hard", "origin/main"], check=True)
    else:
        subprocess.run(["git", "clone", "--branch", "main", REPO_URL, str(PROJECT_DIR)], check=True)
    return PROJECT_DIR


def run_cmd(cmd: list[str], cwd: Path, stage: str) -> None:
    log(f"[stage={stage}] RUN {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def run_stage(name: str, cmd: list[str], cwd: Path) -> dict:
    started = time.time()
    log(f"[heartbeat] stage={name} status=start")
    run_cmd(cmd, cwd=cwd, stage=name)
    elapsed = time.time() - started
    log(f"[heartbeat] stage={name} status=done elapsed_sec={elapsed:.1f}")
    return {
        "name": name,
        "elapsed_sec": round(elapsed, 3),
    }


def install_dependencies(root: Path) -> None:
    run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], cwd=root, stage="install")
    run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=root, stage="install")


def build_common_args(cfg: dict) -> list[str]:
    common = [
        "--run-id",
        str(cfg["run_id"]),
        "--max-steps",
        str(cfg["max_steps"]),
        "--eval-episodes",
        str(cfg["eval_episodes"]),
        "--save-every",
        str(cfg["save_every"]),
        "--keep-last",
        str(cfg["keep_last"]),
    ]
    if cfg.get("seed") is not None:
        common.extend(["--seed", str(cfg["seed"])])
    if to_bool(cfg.get("resume", False)):
        common.append("--resume")
    return common


def build_train_rand_guidance_args(cfg: dict) -> list[str]:
    args: list[str] = []
    if to_bool(cfg.get("domain_rand", False)):
        args.extend(
            [
                "--domain-rand",
                "--domain-rand-scale",
                str(cfg.get("domain_rand_scale", 0.20)),
                "--domain-rand-profile",
                str(cfg.get("domain_rand_profile", "conservative")),
                "--domain-rand-warmup-episodes",
                str(cfg.get("domain_rand_warmup_episodes", 0)),
                "--domain-rand-warmup-epochs",
                str(cfg.get("domain_rand_warmup_epochs", 0)),
            ]
        )
    args.extend(
        [
            "--training-guidance",
            str(cfg.get("training_guidance", "model_only")),
            "--guidance-blend-ratio",
            str(cfg.get("guidance_blend_ratio", 0.7)),
            "--policy-noise-std",
            str(cfg.get("policy_noise_std", 0.1)),
            "--eval-policy-mode",
            str(cfg.get("eval_policy_mode", "model_only")),
            "--eval-guidance-blend-ratio",
            str(cfg.get("eval_guidance_blend_ratio", 0.7)),
        ]
    )
    return args


def build_stage_cmds(cfg: dict) -> list[tuple[str, list[str]]]:
    common = build_common_args(cfg)
    heartbeat = max(int(cfg.get("heartbeat_every", 1)), 1)
    train_rand_guidance_args = build_train_rand_guidance_args(cfg)

    robustness_cmd = [
        sys.executable,
        "experiments/run_robustness.py",
        "--run-id",
        str(cfg["run_id"]),
        "--episodes",
        str(cfg["robustness_episodes"]),
        "--heartbeat-every",
        str(heartbeat * 5),
    ]
    if cfg.get("seed") is not None:
        robustness_cmd.extend(["--seed", str(cfg["seed"])])
    if to_bool(cfg.get("resume", False)):
        robustness_cmd.append("--resume")
    if to_bool(cfg.get("robustness_domain_rand", False)):
        robustness_cmd.extend(
            [
                "--domain-rand",
                "--domain-rand-scale",
                str(cfg.get("robustness_domain_rand_scale", 0.20)),
                "--domain-rand-profile",
                str(cfg.get("robustness_domain_rand_profile", "conservative")),
                "--domain-rand-warmup-episodes",
                str(cfg.get("robustness_domain_rand_warmup_episodes", 200)),
                "--domain-rand-warmup-epochs",
                str(cfg.get("robustness_domain_rand_warmup_epochs", 0)),
                "--domain-rand-difficulties",
                str(cfg.get("robustness_domain_rand_difficulties", "hard_only")),
            ]
        )

    cmds: list[tuple[str, list[str]]] = [
        (
            "baseline",
            [
                sys.executable,
                "experiments/run_baseline.py",
                *common,
                "--epochs",
                str(cfg["baseline_epochs"]),
                "--heartbeat-every",
                str(heartbeat),
                *train_rand_guidance_args,
            ],
        ),
        (
            "transfer",
            [
                sys.executable,
                "experiments/run_transfer.py",
                *common,
                "--pretrain-epochs",
                str(cfg["transfer_pretrain_epochs"]),
                "--finetune-epochs",
                str(cfg["transfer_finetune_epochs"]),
                "--heartbeat-every",
                str(heartbeat),
                *train_rand_guidance_args,
                "--domain-rand-scratch-multiplier",
                str(cfg.get("domain_rand_scratch_multiplier", 1.0)),
                "--domain-rand-source-multiplier",
                str(cfg.get("domain_rand_source_multiplier", 1.0)),
                "--domain-rand-finetune-multiplier",
                str(cfg.get("domain_rand_finetune_multiplier", 1.0)),
            ],
        ),
        (
            "robustness",
            robustness_cmd,
        ),
    ]
    if not to_bool(cfg.get("skip_ablation", False)):
        cmds.insert(
            2,
            (
                "ablation",
                [
                    sys.executable,
                    "experiments/run_ablation.py",
                    *common,
                    "--epochs",
                    str(cfg["ablation_epochs"]),
                    "--heartbeat-every",
                    str(heartbeat),
                ],
            ),
        )

    if not to_bool(cfg.get("skip_visualize", False)):
        cmds.append(("visualize", [sys.executable, "experiments/visualize.py"]))
    return cmds


def main() -> None:
    cfg = load_config()
    log_startup_diagnostics(cfg)
    root = prepare_from_dataset(cfg) or prepare_from_kernel_bundle() or ensure_repo()
    # Reload after dataset extraction/repo ready so runtime-mounted config can override defaults.
    cfg = load_config(extra_candidates=[root / "kaggle" / "run_config.json"])

    stage_results: list[dict] = []

    if not to_bool(cfg.get("skip_install_deps", False)):
        install_dependencies(root)
    else:
        log("Skip dependency install enabled.")

    if to_bool(cfg.get("run_tests", False)):
        stage_results.append(
            run_stage(
                name="tests",
                cmd=[sys.executable, "-m", "pytest", "-q"],
                cwd=root,
            )
        )

    for stage_name, stage_cmd in build_stage_cmds(cfg):
        stage_results.append(run_stage(name=stage_name, cmd=stage_cmd, cwd=root))

    summary = {
        "run_id": cfg["run_id"],
        "seed": cfg.get("seed"),
        "finished_at": datetime.now().isoformat(),
        "results_dir": str(root / "results"),
        "figures_dir": str(root / "figures"),
        "checkpoints_dir": str(root / "checkpoints"),
        "stages": stage_results,
    }
    OUTPUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Saved run summary: {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
