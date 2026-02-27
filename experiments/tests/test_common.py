from pathlib import Path

import torch

from experiments.common import rotate_checkpoint


def _save_ckpt(path: Path, wm_loss: float):
    payload = {"extra": {"wm_loss": wm_loss}}
    torch.save(payload, path)


def test_rotate_checkpoint_creates_best_and_archives(tmp_path):
    latest = tmp_path / "dim3_latest.pt"

    _save_ckpt(latest, wm_loss=5.0)
    out1 = rotate_checkpoint(latest_path=latest, epoch=1, metric=5.0, save_every=1, keep_last=2)
    assert Path(out1["best"]).exists()
    assert Path(out1["archived"]).exists()

    _save_ckpt(latest, wm_loss=4.0)
    out2 = rotate_checkpoint(latest_path=latest, epoch=2, metric=4.0, save_every=1, keep_last=2)
    assert Path(out2["best"]).exists()

    _save_ckpt(latest, wm_loss=6.0)
    rotate_checkpoint(latest_path=latest, epoch=3, metric=6.0, save_every=1, keep_last=2)

    archives = sorted(tmp_path.glob("dim3_epoch*.pt"))
    assert len(archives) == 2
