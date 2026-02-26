from __future__ import annotations

import torch.nn as nn


class BaseWorldModel(nn.Module):
    """Base interface for world models."""

    def __init__(self, state_dim: int, action_dim: int):
        super().__init__()
        self.state_dim = int(state_dim)
        self.action_dim = int(action_dim)

    def forward(self, *args, **kwargs):
        raise NotImplementedError
