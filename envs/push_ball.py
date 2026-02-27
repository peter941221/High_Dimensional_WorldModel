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

    def __init__(self, dim: int = 4, max_steps: int = 200, difficulty: str = "easy", dt: float = 0.02):
        if difficulty not in DIFFICULTY_CONFIGS:
            raise ValueError(f"unknown difficulty: {difficulty}")
        if dim < 2:
            raise ValueError("dim must be >= 2")

        self.dim = int(dim)
        self.max_steps = int(max_steps)
        self.difficulty = difficulty
        self.config = DIFFICULTY_CONFIGS[difficulty]
        self.dt = float(dt)
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

    def _randvec(self, span: float) -> torch.Tensor:
        return (torch.rand(self.dim, generator=self._generator) * 2.0 - 1.0) * span

    def _ensure_ready(self) -> None:
        if self.agent is None or self.ball is None or self.target is None:
            raise RuntimeError("environment is not reset; call reset() first")

    def reset(self, seed=None):
        if seed is not None:
            self._generator = torch.Generator(device="cpu")
            self._generator.manual_seed(int(seed))

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
            mass=1.0,
            radius=0.2,
        )
        self.ball = Body4D(
            position=ball_pos,
            velocity=torch.zeros(self.dim, dtype=torch.float32),
            mass=1.5,
            radius=0.3,
        )
        self.target = target_pos.to(dtype=torch.float32)
        return self._get_obs()

    def _get_obs(self) -> torch.Tensor:
        self._ensure_ready()
        assert self.agent is not None and self.ball is not None and self.target is not None
        return torch.cat(
            [
                self.agent.position,
                self.agent.velocity,
                self.ball.position,
                self.ball.velocity,
                self.target,
            ],
            dim=0,
        ).to(dtype=torch.float32)

    def _wind_force(self) -> torch.Tensor:
        if not self.config.wind:
            return torch.zeros(self.dim, dtype=torch.float32)

        # Deterministic pseudo-random wind based on step index for reproducibility.
        phase = self.steps * 0.1
        components = [math.sin(phase + i * 0.7) for i in range(self.dim)]
        return float(self.config.wind_strength) * torch.tensor(components, dtype=torch.float32)

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
        push_radius = 1.2
        if agent_ball_dist < push_radius:
            gain = (push_radius - agent_ball_dist) / push_radius
            self.ball.velocity = self.ball.velocity + action * (0.2 * gain)

        # Mild damping stabilizes long-horizon trajectories.
        self.agent.velocity = self.agent.velocity * 0.995
        self.ball.velocity = self.ball.velocity * 0.995

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
