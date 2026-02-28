from __future__ import annotations

import torch
import torch.nn as nn

from models.base import BaseWorldModel


class PhysicsResidualWorldModel(BaseWorldModel):
    """
    Physics-prior + residual world model.

    The prior uses a lightweight analytic update on the structured state:
      [agent_pos, agent_vel, ball_pos, ball_vel, target_pos]
    and the residual network learns correction terms.
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_dim: int = 256,
        dt: float = 0.02,
        agent_force_gain: float = 8.0,
        push_gain: float = 0.2,
        damping: float = 0.995,
        action_penalty: float = 0.01,
    ):
        super().__init__(state_dim=state_dim, action_dim=action_dim)
        if state_dim != 5 * action_dim:
            raise ValueError("PhysicsResidualWorldModel expects state_dim == 5 * action_dim")

        self.dim = int(action_dim)
        self.dt = float(dt)
        self.agent_force_gain = float(agent_force_gain)
        self.push_gain = float(push_gain)
        self.damping = float(damping)
        self.action_penalty = float(action_penalty)

        self.residual_net = nn.Sequential(
            nn.Linear(state_dim + action_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.state_residual_head = nn.Linear(hidden_dim, state_dim)
        self.reward_residual_head = nn.Linear(hidden_dim, 1)

    def _split(self, state: torch.Tensor) -> tuple[torch.Tensor, ...]:
        d = self.dim
        agent_pos = state[..., 0:d]
        agent_vel = state[..., d : 2 * d]
        ball_pos = state[..., 2 * d : 3 * d]
        ball_vel = state[..., 3 * d : 4 * d]
        target_pos = state[..., 4 * d : 5 * d]
        return agent_pos, agent_vel, ball_pos, ball_vel, target_pos

    def _physics_prior(self, state: torch.Tensor, action: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        agent_pos, agent_vel, ball_pos, ball_vel, target_pos = self._split(state)

        dt = self.dt
        agent_acc = self.agent_force_gain * action - (1.0 - self.damping) * agent_vel / max(dt, 1e-6)
        next_agent_vel = agent_vel + agent_acc * dt
        next_agent_vel = next_agent_vel * self.damping
        next_agent_pos = agent_pos + next_agent_vel * dt

        ball_acc = self.push_gain * action - (1.0 - self.damping) * ball_vel / max(dt, 1e-6)
        next_ball_vel = ball_vel + ball_acc * dt
        next_ball_vel = next_ball_vel * self.damping
        next_ball_pos = ball_pos + next_ball_vel * dt

        next_state_prior = torch.cat(
            [next_agent_pos, next_agent_vel, next_ball_pos, next_ball_vel, target_pos],
            dim=-1,
        )
        dist = torch.linalg.norm(next_ball_pos - target_pos, dim=-1, keepdim=True)
        reward_prior = -dist - self.action_penalty * action.pow(2).sum(dim=-1, keepdim=True)
        return next_state_prior, reward_prior

    def forward(self, state: torch.Tensor, action: torch.Tensor):
        next_state_prior, reward_prior = self._physics_prior(state, action)
        h = self.residual_net(torch.cat([state, action], dim=-1))
        next_state = next_state_prior + self.state_residual_head(h)
        reward = reward_prior + self.reward_residual_head(h)
        return next_state, reward

