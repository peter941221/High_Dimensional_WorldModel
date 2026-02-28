import pytest
import torch

from envs.push_ball import PushBallNDEnv


def test_state_components_and_split_contract():
    env = PushBallNDEnv(dim=4, difficulty="easy")
    state = env.reset(seed=123)

    assert env.state_components == (
        "agent_pos",
        "agent_vel",
        "ball_pos",
        "ball_vel",
        "target_pos",
    )

    parts = env.split_state(state)
    assert tuple(parts.keys()) == env.state_components
    for name in env.state_components:
        assert parts[name].shape == (env.dim,)

    reconstructed = torch.cat([parts[name] for name in env.state_components], dim=0)
    assert torch.allclose(reconstructed, state)


def test_split_state_rejects_wrong_shape():
    env = PushBallNDEnv(dim=3, difficulty="easy")
    env.reset(seed=0)
    with pytest.raises(ValueError, match="state must be shape"):
        env.split_state(torch.zeros(env.state_dim + 1))

