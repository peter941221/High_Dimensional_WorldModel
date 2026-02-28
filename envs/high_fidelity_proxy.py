from __future__ import annotations

import math

import torch

from envs.push_ball import PushBallNDEnv


class HiFiPushBallProxyEnv:
    """
    Proxy high-fidelity environment.

    It wraps PushBallNDEnv and introduces deterministic action coupling
    and observation warp to emulate simulator mismatch.
    """

    def __init__(
        self,
        dim: int = 3,
        difficulty: str = "medium",
        max_steps: int = 120,
        dt: float = 0.02,
        fidelity_level: str = "mild",
        domain_randomization: bool = False,
        domain_rand_scale: float = 0.10,
        domain_rand_profile: str = "conservative",
        domain_rand_warmup_episodes: int = 0,
        domain_rand_warmup_epochs: int = 0,
    ):
        if fidelity_level not in {"mild", "strong"}:
            raise ValueError("fidelity_level must be one of: mild, strong")
        self.fidelity_level = fidelity_level
        self.base = PushBallNDEnv(
            dim=dim,
            difficulty=difficulty,
            max_steps=max_steps,
            dt=dt,
            domain_randomization=domain_randomization,
            domain_rand_scale=domain_rand_scale,
            domain_rand_profile=domain_rand_profile,
            domain_rand_warmup_episodes=domain_rand_warmup_episodes,
            domain_rand_warmup_epochs=domain_rand_warmup_epochs,
        )
        self._last_raw_state: torch.Tensor | None = None
        self._step_index = 0

    @property
    def dim(self):
        return self.base.dim

    @property
    def state_dim(self):
        return self.base.state_dim

    @property
    def action_dim(self):
        return self.base.action_dim

    @property
    def state_components(self):
        return self.base.state_components

    def set_domain_rand_training_epoch(self, epoch: int) -> None:
        self.base.set_domain_rand_training_epoch(epoch)

    def set_domain_rand_stage_multiplier(self, multiplier: float) -> None:
        self.base.set_domain_rand_stage_multiplier(multiplier)

    def _action_transform(self, action: torch.Tensor) -> torch.Tensor:
        a = torch.as_tensor(action, dtype=torch.float32).flatten()
        if a.shape != (self.action_dim,):
            raise ValueError(f"action must be shape ({self.action_dim},)")

        coupling = 0.06 if self.fidelity_level == "mild" else 0.12
        drift_amp = 0.03 if self.fidelity_level == "mild" else 0.06
        rolled = torch.roll(a, shifts=1, dims=0)
        phase = self._step_index * 0.09
        drift = torch.tensor(
            [math.sin(phase + i * 0.37) for i in range(self.action_dim)],
            dtype=torch.float32,
        )
        return (a + coupling * rolled + drift_amp * drift).clamp(-1.0, 1.0)

    def _state_warp(self, raw_state: torch.Tensor) -> torch.Tensor:
        s = torch.as_tensor(raw_state, dtype=torch.float32).flatten()
        d = self.dim
        warped = s.clone()
        pos_noise = 0.01 if self.fidelity_level == "mild" else 0.02
        vel_noise = 0.015 if self.fidelity_level == "mild" else 0.03

        pos_slice = slice(0, d)
        vel_slice = slice(d, 2 * d)
        ball_pos_slice = slice(2 * d, 3 * d)
        ball_vel_slice = slice(3 * d, 4 * d)
        target_slice = slice(4 * d, 5 * d)

        warped[pos_slice] += pos_noise * torch.tanh(s[pos_slice])
        warped[vel_slice] += vel_noise * torch.tanh(s[vel_slice])
        warped[ball_pos_slice] += pos_noise * torch.tanh(s[ball_pos_slice])
        warped[ball_vel_slice] += vel_noise * torch.tanh(s[ball_vel_slice])
        # Target uses smaller sensor warp to keep task semantics stable.
        warped[target_slice] += (0.5 * pos_noise) * torch.tanh(s[target_slice])
        return warped

    def reset(self, seed=None):
        self._step_index = 0
        raw = self.base.reset(seed=seed)
        self._last_raw_state = torch.as_tensor(raw, dtype=torch.float32)
        return self._state_warp(self._last_raw_state)

    def step(self, action):
        transformed_action = self._action_transform(action)
        raw_state, reward, done, info = self.base.step(transformed_action)
        self._step_index += 1
        self._last_raw_state = torch.as_tensor(raw_state, dtype=torch.float32)
        warped_state = self._state_warp(self._last_raw_state)

        penalty = 0.005 if self.fidelity_level == "mild" else 0.01
        reward = float(reward) - penalty * float(torch.dot(transformed_action, transformed_action).item())
        info = dict(info)
        info["fidelity_level"] = self.fidelity_level
        return warped_state, float(reward), bool(done), info

