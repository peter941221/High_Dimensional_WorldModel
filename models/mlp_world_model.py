from __future__ import annotations

import torch
import torch.nn as nn

from models.base import BaseWorldModel


class MLPWorldModel(BaseWorldModel):
    """Feed-forward world model for one-step dynamics."""

    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__(state_dim=state_dim, action_dim=action_dim)
        self.net = nn.Sequential(
            nn.Linear(state_dim + action_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.state_head = nn.Linear(hidden_dim, state_dim)
        self.reward_head = nn.Linear(hidden_dim, 1)

    def forward(self, state: torch.Tensor, action: torch.Tensor):
        x = torch.cat([state, action], dim=-1)
        h = self.net(x)
        next_state = self.state_head(h)
        reward = self.reward_head(h)
        return next_state, reward
