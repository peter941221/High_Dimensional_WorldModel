from __future__ import annotations

import torch


class DimensionTransfer:
    """Transfer compatible parameters between source and target models."""

    def __init__(
        self,
        source_dim: int,
        target_dim: int,
        transfer_strategy: str = "hidden_only",
    ):
        if transfer_strategy not in {"hidden_only", "truncate"}:
            raise ValueError("transfer_strategy must be one of: hidden_only, truncate")
        self.source_dim = int(source_dim)
        self.target_dim = int(target_dim)
        self.strategy = transfer_strategy

    def transfer(self, source_model, target_model):
        source_state = source_model.state_dict()
        target_state = target_model.state_dict()

        transferred = 0
        skipped = 0

        for key, target_tensor in target_state.items():
            if key not in source_state:
                skipped += 1
                continue

            source_tensor = source_state[key]
            if source_tensor.shape == target_tensor.shape:
                target_state[key] = source_tensor.clone()
                transferred += 1
                continue

            if self.strategy == "truncate":
                target_state[key] = self._truncate_or_pad(source_tensor, target_tensor.shape)
                transferred += 1
            else:
                skipped += 1

        target_model.load_state_dict(target_state)
        return target_model, {"transferred": transferred, "skipped": skipped}

    def _truncate_or_pad(self, tensor: torch.Tensor, target_shape: torch.Size) -> torch.Tensor:
        out = torch.zeros(target_shape, dtype=tensor.dtype, device=tensor.device)
        slices = tuple(slice(0, min(s, t)) for s, t in zip(tensor.shape, target_shape))
        out[slices] = tensor[slices]
        return out

