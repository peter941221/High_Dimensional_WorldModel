from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import shutil


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


def rotate_checkpoint(
    latest_path: Path,
    epoch: int,
    metric: float,
    higher_is_better: bool = False,
    save_every: int = 0,
    keep_last: int = 5,
) -> dict:
    """
    Maintain latest/best/periodic archive checkpoints.

    latest_path example:
      checkpoints/baseline/run_x/dim3_latest.pt
    """
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = latest_path.stem.replace("_latest", "")
    best_path = latest_path.parent / f"{prefix}_best.pt"

    # Update best checkpoint according to metric.
    should_update_best = False
    if not best_path.exists():
        should_update_best = True
    else:
        try:
            import torch

            best_extra = torch.load(best_path, map_location="cpu").get("extra", {})
            best_metric = float(best_extra.get("wm_loss", float("inf")))
            if higher_is_better:
                should_update_best = metric > best_metric
            else:
                should_update_best = metric < best_metric
        except Exception:
            should_update_best = True

    if should_update_best:
        shutil.copy2(latest_path, best_path)

    # Periodic archive for rollback points.
    archived = None
    if save_every > 0 and epoch % save_every == 0:
        archived = latest_path.parent / f"{prefix}_epoch{epoch:04d}.pt"
        shutil.copy2(latest_path, archived)

        if keep_last > 0:
            archives = sorted(latest_path.parent.glob(f"{prefix}_epoch*.pt"))
            if len(archives) > keep_last:
                to_delete = archives[: len(archives) - keep_last]
                for old in to_delete:
                    old.unlink(missing_ok=True)

    return {
        "latest": str(latest_path),
        "best": str(best_path),
        "archived": str(archived) if archived is not None else None,
    }
