from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from models.base import BaseWorldModel


class GRUWorldModel(BaseWorldModel):
    """Recurrent world model with deterministic memory state."""

    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__(state_dim=state_dim, action_dim=action_dim)
        self.hidden_dim = int(hidden_dim)
        self.state_encoder = nn.Linear(state_dim, hidden_dim)
        self.gru = nn.GRUCell(hidden_dim + action_dim, hidden_dim)
        self.state_head = nn.Linear(hidden_dim, state_dim)
        self.reward_head = nn.Linear(hidden_dim, 1)

    def init_hidden(self, batch_size: int, device: str | torch.device = "cpu") -> torch.Tensor:
        return torch.zeros(batch_size, self.hidden_dim, device=device)

    def forward(
        self,
        state: torch.Tensor,
        action: torch.Tensor,
        hidden: torch.Tensor | None = None,
    ):
        if hidden is None:
            hidden = self.init_hidden(batch_size=state.shape[0], device=state.device)

        z = F.relu(self.state_encoder(state))
        x = torch.cat([z, action], dim=-1)
        hidden = self.gru(x, hidden)
        next_state = self.state_head(hidden)
        reward = self.reward_head(hidden)
        return next_state, reward, hidden
