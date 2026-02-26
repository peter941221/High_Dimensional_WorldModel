from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from models.base import BaseWorldModel


class RSSMWorldModel(BaseWorldModel):
    """Minimal recurrent state-space model used for imagination experiments."""

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        det_dim: int = 200,
        stoch_dim: int = 30,
        hidden_dim: int = 200,
    ):
        super().__init__(state_dim=state_dim, action_dim=action_dim)
        self.det_dim = int(det_dim)
        self.stoch_dim = int(stoch_dim)

        self.gru = nn.GRUCell(stoch_dim + action_dim, det_dim)
        self.prior_net = nn.Sequential(
            nn.Linear(det_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, stoch_dim * 2),
        )
        self.posterior_net = nn.Sequential(
            nn.Linear(det_dim + state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, stoch_dim * 2),
        )
        self.decoder = nn.Sequential(
            nn.Linear(det_dim + stoch_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, state_dim),
        )
        self.reward_head = nn.Sequential(
            nn.Linear(det_dim + stoch_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def init_hidden(self, batch_size: int, device: str | torch.device = "cpu"):
        h = torch.zeros(batch_size, self.det_dim, device=device)
        z = torch.zeros(batch_size, self.stoch_dim, device=device)
        return h, z

    def _stats_to_dist(self, params: torch.Tensor):
        mean, log_std = params.chunk(2, dim=-1)
        std = F.softplus(log_std) + 1e-3
        return mean, std

    def _sample(self, mean: torch.Tensor, std: torch.Tensor):
        return mean + std * torch.randn_like(std)

    def _kl_normal(
        self,
        post_mean: torch.Tensor,
        post_std: torch.Tensor,
        prior_mean: torch.Tensor,
        prior_std: torch.Tensor,
    ) -> torch.Tensor:
        post_var = post_std.pow(2)
        prior_var = prior_std.pow(2)
        kl = torch.log(prior_std / post_std) + (post_var + (post_mean - prior_mean).pow(2)) / (2.0 * prior_var) - 0.5
        return kl.sum(dim=-1, keepdim=True)

    def forward(
        self,
        state: torch.Tensor,
        action: torch.Tensor,
        hidden: tuple[torch.Tensor, torch.Tensor] | None = None,
    ):
        batch = state.shape[0]
        if hidden is None:
            hidden = self.init_hidden(batch_size=batch, device=state.device)
        h, prev_z = hidden

        h = self.gru(torch.cat([prev_z, action], dim=-1), h)

        prior_mean, prior_std = self._stats_to_dist(self.prior_net(h))
        post_mean, post_std = self._stats_to_dist(self.posterior_net(torch.cat([h, state], dim=-1)))
        z = self._sample(post_mean, post_std)

        features = torch.cat([h, z], dim=-1)
        next_state = self.decoder(features)
        reward = self.reward_head(features)
        kl = self._kl_normal(post_mean, post_std, prior_mean, prior_std)
        return next_state, reward, (h, z), kl
