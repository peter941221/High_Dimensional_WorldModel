from __future__ import annotations

import random
from typing import Dict

import torch


class ReplayBuffer:
    """Episode-based replay buffer with sequence sampling support."""

    def __init__(self, capacity: int = 100_000):
        self.capacity = int(capacity)
        self.episodes: list[Dict[str, torch.Tensor]] = []
        self.total_steps = 0

    def add_episode(self, episode: Dict[str, torch.Tensor]):
        required = {"states", "actions", "rewards"}
        missing = required - set(episode.keys())
        if missing:
            raise ValueError(f"episode missing keys: {missing}")

        states = episode["states"].detach().clone()
        actions = episode["actions"].detach().clone()
        rewards = episode["rewards"].detach().clone()

        if states.ndim != 2 or actions.ndim != 2:
            raise ValueError("states/actions must be rank-2 tensors")
        if rewards.ndim == 1:
            rewards = rewards.unsqueeze(-1)
        if rewards.ndim != 2:
            raise ValueError("rewards must be rank-2 tensor")
        if not (len(states) == len(actions) == len(rewards)):
            raise ValueError("states/actions/rewards must have the same time length")

        item = {
            "states": states.float(),
            "actions": actions.float(),
            "rewards": rewards.float(),
        }
        self.episodes.append(item)
        self.total_steps += len(states)
        self._trim_capacity()

    def _trim_capacity(self):
        while self.episodes and self.total_steps > self.capacity:
            removed = self.episodes.pop(0)
            self.total_steps -= len(removed["states"])

    def sample_batch(self, batch_size: int, seq_len: int = 50) -> Dict[str, torch.Tensor]:
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        if seq_len <= 0:
            raise ValueError("seq_len must be > 0")

        candidates = [ep for ep in self.episodes if len(ep["states"]) >= seq_len]
        if not candidates:
            raise ValueError("no episode is long enough for requested seq_len")

        sampled_states = []
        sampled_actions = []
        sampled_rewards = []

        for _ in range(batch_size):
            ep = random.choice(candidates)
            max_start = len(ep["states"]) - seq_len
            start = random.randint(0, max_start)
            end = start + seq_len
            sampled_states.append(ep["states"][start:end])
            sampled_actions.append(ep["actions"][start:end])
            sampled_rewards.append(ep["rewards"][start:end])

        return {
            "states": torch.stack(sampled_states, dim=0),
            "actions": torch.stack(sampled_actions, dim=0),
            "rewards": torch.stack(sampled_rewards, dim=0),
        }

    def __len__(self) -> int:
        return self.total_steps

    def state_dict(self) -> dict:
        return {
            "capacity": self.capacity,
            "total_steps": self.total_steps,
            "episodes": [
                {
                    "states": ep["states"].detach().cpu().clone(),
                    "actions": ep["actions"].detach().cpu().clone(),
                    "rewards": ep["rewards"].detach().cpu().clone(),
                }
                for ep in self.episodes
            ],
        }

    def load_state_dict(self, state: dict) -> None:
        self.capacity = int(state["capacity"])
        self.total_steps = int(state["total_steps"])
        self.episodes = []
        for ep in state["episodes"]:
            self.episodes.append(
                {
                    "states": ep["states"].float(),
                    "actions": ep["actions"].float(),
                    "rewards": ep["rewards"].float(),
                }
            )
        self._trim_capacity()

