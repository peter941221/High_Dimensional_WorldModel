import random

import torch

from training.buffer import ReplayBuffer


def _episode(length: int, state_dim: int = 10, action_dim: int = 3):
    return {
        "states": torch.randn(length, state_dim),
        "actions": torch.randn(length, action_dim),
        "rewards": torch.randn(length, 1),
    }


def test_store_and_retrieve_shapes():
    buffer = ReplayBuffer(capacity=1_000)
    buffer.add_episode(_episode(120))
    batch = buffer.sample_batch(batch_size=8, seq_len=50)
    assert batch["states"].shape == (8, 50, 10)
    assert batch["actions"].shape == (8, 50, 3)
    assert batch["rewards"].shape == (8, 50, 1)


def test_capacity_limit_discards_oldest_data():
    buffer = ReplayBuffer(capacity=100)
    buffer.add_episode(_episode(60))
    buffer.add_episode(_episode(60))
    assert len(buffer) <= 100
    assert len(buffer.episodes) == 1


def test_sequence_integrity_within_single_episode():
    random.seed(0)
    torch.manual_seed(0)
    length = 80
    states = torch.arange(length * 4, dtype=torch.float32).reshape(length, 4)
    episode = {
        "states": states,
        "actions": torch.zeros(length, 2),
        "rewards": torch.zeros(length, 1),
    }

    buffer = ReplayBuffer(capacity=500)
    buffer.add_episode(episode)
    batch = buffer.sample_batch(batch_size=5, seq_len=10)
    for seq in batch["states"]:
        diffs = seq[1:] - seq[:-1]
        assert torch.all(diffs == diffs[0])

