from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path


def default_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def find_latest_run(experiment_name: str) -> str | None:
    root = Path("results") / experiment_name
    if not root.exists():
        return None
    candidates = [p for p in root.iterdir() if p.is_dir()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.name


def prepare_run_dirs(experiment_name: str, run_id: str) -> tuple[Path, Path]:
    result_dir = Path("results") / experiment_name / run_id
    checkpoint_dir = Path("checkpoints") / experiment_name / run_id
    result_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return result_dir, checkpoint_dir


def load_json(path: Path, default: dict):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
