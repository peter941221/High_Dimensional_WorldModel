from __future__ import annotations

import math
from dataclasses import dataclass

import torch

from physics.body import Body4D
from physics.engine import Physics4D


@dataclass(frozen=True)
class DifficultyConfig:
    init_range: float
    target_range: float
    gravity: bool
    wind: bool = False
    gravity_strength: float = 0.0
    success_radius: float = 0.8
    wind_strength: float = 0.0


DIFFICULTY_CONFIGS = {
    "easy": DifficultyConfig(
        init_range=1.5,
        target_range=2.0,
        gravity=False,
        wind=False,
        gravity_strength=0.0,
        success_radius=0.8,
        wind_strength=0.0,
    ),
    "medium": DifficultyConfig(
        init_range=2.0906997605068978,
        target_range=3.4336149579273254,
        gravity=True,
        wind=False,
        gravity_strength=-2.0976494583021363,
        success_radius=1.1793923025791344,
        wind_strength=0.0,
    ),
    "hard": DifficultyConfig(
        init_range=3.180878144683795,
        target_range=3.910937991853727,
        gravity=True,
        wind=True,
        gravity_strength=-2.6581202889192523,
        success_radius=1.7274228419868347,
        wind_strength=0.03821015893462352,
    ),
}


class PushBallNDEnv:
    """Simple N-dimensional pushing task with deterministic dynamics."""
    STATE_COMPONENTS = (
        "agent_pos",
        "agent_vel",
        "ball_pos",
        "ball_vel",
        "target_pos",
    )

    def __init__(
        self,
        dim: int = 4,
        max_steps: int = 200,
        difficulty: str = "easy",
        dt: float = 0.02,
        domain_randomization: bool = False,
        domain_rand_scale: float = 0.15,
        domain_rand_profile: str = "full",
        domain_rand_warmup_episodes: int = 0,
        domain_rand_warmup_epochs: int = 0,
    ):
        if difficulty not in DIFFICULTY_CONFIGS:
            raise ValueError(f"unknown difficulty: {difficulty}")
        if dim < 2:
            raise ValueError("dim must be >= 2")
        if domain_rand_scale < 0:
            raise ValueError("domain_rand_scale must be >= 0")
        if domain_rand_profile not in {"full", "conservative"}:
            raise ValueError("domain_rand_profile must be one of: full, conservative")
        if domain_rand_warmup_episodes < 0:
            raise ValueError("domain_rand_warmup_episodes must be >= 0")
        if domain_rand_warmup_epochs < 0:
            raise ValueError("domain_rand_warmup_epochs must be >= 0")

        self.dim = int(dim)
        self.max_steps = int(max_steps)
        self.difficulty = difficulty
        self.config = DIFFICULTY_CONFIGS[difficulty]
        self.dt = float(dt)
        self.domain_randomization = bool(domain_randomization)
        self.domain_rand_scale = float(domain_rand_scale)
        self.domain_rand_profile = domain_rand_profile
        self.domain_rand_warmup_episodes = int(domain_rand_warmup_episodes)
        self.domain_rand_warmup_epochs = int(domain_rand_warmup_epochs)
        self.success_radius = float(self.config.success_radius)

        boundary = self.config.target_range * 2.0 + 2.0
        gravity_strength = float(self.config.gravity_strength) if self.config.gravity else 0.0
        self.physics = Physics4D(
            dim=self.dim,
            gravity_axis=1 if self.dim > 1 else 0,
            gravity_strength=gravity_strength,
            dt=self.dt,
            boundary=boundary,
            restitution=0.95,
        )

        self.agent: Body4D | None = None
        self.ball: Body4D | None = None
        self.target: torch.Tensor | None = None
        self.steps = 0
        self._generator = torch.Generator(device="cpu")
        self._episode_params: dict[str, float] = {}
        self._episode_index = 0
        self._training_epoch = 0
        self._stage_rand_multiplier = 1.0

    def _randvec(self, span: float) -> torch.Tensor:
        return (torch.rand(self.dim, generator=self._generator) * 2.0 - 1.0) * span

    def _ensure_ready(self) -> None:
        if self.agent is None or self.ball is None or self.target is None:
            raise RuntimeError("environment is not reset; call reset() first")

    def reset(self, seed=None):
        if seed is not None:
            self._generator = torch.Generator(device="cpu")
            self._generator.manual_seed(int(seed))
            self._episode_index = 0

        self._apply_episode_params()
        self._episode_index += 1
        self.steps = 0
        init_range = self.config.init_range
        agent_pos = self._randvec(init_range * 0.25)
        ball_pos = self._randvec(init_range)
        target_pos = self._randvec(self.config.target_range)

        # Keep target far enough to avoid accidental immediate success.
        while torch.linalg.norm(ball_pos - target_pos).item() < 1.0:
            target_pos = self._randvec(self.config.target_range)

        self.agent = Body4D(
            position=agent_pos,
            velocity=torch.zeros(self.dim, dtype=torch.float32),
            mass=float(self._episode_params["agent_mass"]),
            radius=0.2,
        )
        self.ball = Body4D(
            position=ball_pos,
            velocity=torch.zeros(self.dim, dtype=torch.float32),
            mass=float(self._episode_params["ball_mass"]),
            radius=0.3,
        )
        self.target = target_pos.to(dtype=torch.float32)
        return self._get_obs()

    def _get_obs(self) -> torch.Tensor:
        self._ensure_ready()
        assert self.agent is not None and self.ball is not None and self.target is not None
        obs = torch.cat(
            [
                self.agent.position,
                self.agent.velocity,
                self.ball.position,
                self.ball.velocity,
                self.target,
            ],
            dim=0,
        ).to(dtype=torch.float32)
        # Enforce semantic contract: state must decompose into fixed components.
        self.split_state(obs)
        return obs

    def _wind_force(self) -> torch.Tensor:
        wind_strength = float(self._episode_params.get("wind_strength", 0.0))
        if abs(wind_strength) <= 1e-12:
            return torch.zeros(self.dim, dtype=torch.float32)

        # Deterministic pseudo-random wind based on step index for reproducibility.
        phase = self.steps * 0.1
        components = [math.sin(phase + i * 0.7) for i in range(self.dim)]
        return wind_strength * torch.tensor(components, dtype=torch.float32)

    def step(self, action):
        self._ensure_ready()
        assert self.agent is not None and self.ball is not None and self.target is not None

        action = torch.as_tensor(action, dtype=torch.float32).flatten()
        if action.shape != (self.dim,):
            raise ValueError(f"action must be shape ({self.dim},)")

        action = action.clamp(-1.0, 1.0)
        agent_force = action * 8.0
        ball_force = self._wind_force()

        self.physics.step(
            [self.agent, self.ball],
            external_forces=[agent_force, ball_force],
        )

        # Contact-assist force to keep the task learnable in low-data regimes.
        agent_ball_dist = torch.linalg.norm(self.agent.position - self.ball.position).item()
        push_radius = float(self._episode_params["push_radius"])
        if agent_ball_dist < push_radius:
            gain = (push_radius - agent_ball_dist) / push_radius
            contact_gain = float(self._episode_params["contact_gain"])
            self.ball.velocity = self.ball.velocity + action * (contact_gain * gain)

        # Mild damping stabilizes long-horizon trajectories.
        damping = float(self._episode_params["damping"])
        self.agent.velocity = self.agent.velocity * damping
        self.ball.velocity = self.ball.velocity * damping

        self.steps += 1
        distance = torch.linalg.norm(self.ball.position - self.target).item()
        reward = -distance - 0.01 * float(torch.dot(action, action).item())
        success = distance < self.success_radius
        if success:
            reward += 100.0
        done = success or self.steps >= self.max_steps

        info = {
            "distance_to_target": distance,
            "success": success,
            "step": self.steps,
        }
        return self._get_obs(), float(reward), bool(done), info

    @property
    def state_dim(self):
        return 5 * self.dim

    @property
    def action_dim(self):
        return self.dim

    @property
    def state_components(self) -> tuple[str, ...]:
        return self.STATE_COMPONENTS

    def state_slices(self) -> dict[str, slice]:
        layout: dict[str, slice] = {}
        cursor = 0
        for name in self.state_components:
            layout[name] = slice(cursor, cursor + self.dim)
            cursor += self.dim
        return layout

    def split_state(self, state) -> dict[str, torch.Tensor]:
        s = torch.as_tensor(state, dtype=torch.float32).flatten()
        if s.shape != (self.state_dim,):
            raise ValueError(f"state must be shape ({self.state_dim},)")
        return {name: s[slc] for name, slc in self.state_slices().items()}

    @property
    def episode_params(self) -> dict[str, float]:
        return dict(self._episode_params)

    def set_domain_rand_training_epoch(self, epoch: int) -> None:
        self._training_epoch = max(0, int(epoch))

    def set_domain_rand_stage_multiplier(self, multiplier: float) -> None:
        self._stage_rand_multiplier = max(0.0, float(multiplier))

    def _sample_relative(self, base: float, rel_scale: float, min_value: float | None = None) -> float:
        base = float(base)
        rel_scale = max(float(rel_scale), 0.0)
        if rel_scale == 0.0:
            value = base
        elif abs(base) <= 1e-12:
            # For near-zero defaults, keep deterministic no-perturb behavior.
            value = 0.0
        else:
            lo = base * (1.0 - rel_scale)
            hi = base * (1.0 + rel_scale)
            low, high = (lo, hi) if lo <= hi else (hi, lo)
            alpha = float(torch.rand((), generator=self._generator).item())
            value = low + alpha * (high - low)
        if min_value is not None:
            value = max(float(min_value), float(value))
        return float(value)

    def _apply_episode_params(self) -> None:
        scale = self.domain_rand_scale if self.domain_randomization else 0.0
        if self.domain_randomization and self.domain_rand_warmup_episodes > 0:
            warmup_ratio = min(1.0, float(self._episode_index + 1) / float(self.domain_rand_warmup_episodes))
            scale = scale * warmup_ratio
        if self.domain_randomization and self.domain_rand_warmup_epochs > 0:
            epoch_ratio = min(1.0, float(self._training_epoch) / float(self.domain_rand_warmup_epochs))
            scale = scale * epoch_ratio

        scale = scale * self._stage_rand_multiplier

        profile = self.domain_rand_profile
        if profile == "conservative":
            success_radius_scale = 0.0
            mass_scale = 0.0
            push_radius_scale = 0.0
            contact_gain_scale = 0.5 * scale
            damping_scale = 0.2 * scale
            gravity_scale = 0.5 * scale
            wind_scale = 0.5 * scale
        else:
            success_radius_scale = 0.5 * scale
            mass_scale = scale
            push_radius_scale = 0.5 * scale
            contact_gain_scale = scale
            damping_scale = 0.2 * scale
            gravity_scale = scale
            wind_scale = scale

        gravity_strength = (
            self._sample_relative(self.config.gravity_strength, gravity_scale, min_value=None)
            if self.config.gravity
            else 0.0
        )
        wind_strength = (
            self._sample_relative(self.config.wind_strength, wind_scale, min_value=0.0)
            if self.config.wind
            else 0.0
        )

        params = {
            "gravity_strength": float(gravity_strength),
            "wind_strength": float(wind_strength),
            "success_radius": self._sample_relative(self.config.success_radius, success_radius_scale, min_value=0.2),
            "agent_mass": self._sample_relative(1.0, mass_scale, min_value=0.2),
            "ball_mass": self._sample_relative(1.5, mass_scale, min_value=0.2),
            "push_radius": self._sample_relative(1.2, push_radius_scale, min_value=0.5),
            "contact_gain": self._sample_relative(0.2, contact_gain_scale, min_value=0.01),
            "damping": self._sample_relative(0.995, damping_scale, min_value=0.9),
            "rand_scale_effective": float(scale),
        }
        self._episode_params = params
        self.success_radius = float(params["success_radius"])
        self.physics.gravity_strength = float(params["gravity_strength"])
