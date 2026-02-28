import pytest
import torch

from envs.push_ball import PushBallNDEnv
from models.mlp_world_model import MLPWorldModel
from models.policy import PolicyNetwork
from training.buffer import ReplayBuffer
from training.dream_trainer import DreamTrainer


def test_dream_trainer_epoch_runs_without_crashing():
    env = PushBallNDEnv(dim=3, max_steps=40, difficulty="easy")
    model = MLPWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=64)
    policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=64)
    buffer = ReplayBuffer(capacity=10_000)
    trainer = DreamTrainer(env=env, world_model=model, policy=policy, buffer=buffer)

    for _ in range(4):
        trainer.collect_episode(max_steps=40, random_policy=True)

    stats = trainer.train_epoch(collect_episodes=1, wm_steps=2, policy_episodes=1)
    assert stats.world_model_loss >= 0.0
    assert isinstance(stats.actor_loss, float)
    assert isinstance(stats.value_loss, float)


def test_actor_critic_step_updates_parameters():
    env = PushBallNDEnv(dim=3, max_steps=30, difficulty="easy")
    model = MLPWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=64)
    policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=64)
    buffer = ReplayBuffer(capacity=10_000)
    trainer = DreamTrainer(env=env, world_model=model, policy=policy, buffer=buffer)

    for _ in range(5):
        trainer.collect_episode(max_steps=30, random_policy=True)

    actor_before = [p.detach().clone() for p in trainer.policy.parameters()]
    value_before = [p.detach().clone() for p in trainer.value_model.parameters()]

    trainer.train_actor_critic(steps=2, batch_size=32, imagine_horizon=3)

    actor_changed = any(not torch.equal(p0, p1.detach()) for p0, p1 in zip(actor_before, trainer.policy.parameters()))
    value_changed = any(not torch.equal(p0, p1.detach()) for p0, p1 in zip(value_before, trainer.value_model.parameters()))
    assert actor_changed
    assert value_changed


def test_checkpoint_round_trip_restores_trainer_state(tmp_path):
    env = PushBallNDEnv(dim=3, max_steps=30, difficulty="easy")
    model = MLPWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=64)
    policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=64)
    trainer = DreamTrainer(env=env, world_model=model, policy=policy, buffer=ReplayBuffer(capacity=10_000))

    for _ in range(4):
        trainer.collect_episode(max_steps=30, random_policy=True)
    trainer.train_epoch(collect_episodes=1, wm_steps=2, policy_episodes=1)
    ckpt_path = tmp_path / "trainer.ckpt"
    trainer.save_checkpoint(ckpt_path, extra={"tag": "unit_test"})

    env2 = PushBallNDEnv(dim=3, max_steps=30, difficulty="easy")
    model2 = MLPWorldModel(state_dim=env2.state_dim, action_dim=env2.action_dim, hidden_dim=64)
    policy2 = PolicyNetwork(state_dim=env2.state_dim, action_dim=env2.action_dim, hidden_dim=64)
    trainer2 = DreamTrainer(env=env2, world_model=model2, policy=policy2, buffer=ReplayBuffer(capacity=10_000))

    extra = trainer2.load_checkpoint(ckpt_path)
    assert extra["tag"] == "unit_test"
    assert trainer2.train_epochs == trainer.train_epochs
    assert trainer2.gradient_steps == trainer.gradient_steps
    assert len(trainer2.buffer) == len(trainer.buffer)


def test_checkpoint_rejects_state_semantic_mismatch(tmp_path):
    class SwappedSemanticEnv(PushBallNDEnv):
        STATE_COMPONENTS = (
            "agent_pos",
            "ball_pos",
            "agent_vel",
            "ball_vel",
            "target_pos",
        )

    env = PushBallNDEnv(dim=3, max_steps=30, difficulty="easy")
    model = MLPWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=64)
    policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=64)
    trainer = DreamTrainer(env=env, world_model=model, policy=policy, buffer=ReplayBuffer(capacity=10_000))
    ckpt_path = tmp_path / "semantic.ckpt"
    trainer.save_checkpoint(ckpt_path)

    env2 = SwappedSemanticEnv(dim=3, max_steps=30, difficulty="easy")
    model2 = MLPWorldModel(state_dim=env2.state_dim, action_dim=env2.action_dim, hidden_dim=64)
    policy2 = PolicyNetwork(state_dim=env2.state_dim, action_dim=env2.action_dim, hidden_dim=64)
    trainer2 = DreamTrainer(env=env2, world_model=model2, policy=policy2, buffer=ReplayBuffer(capacity=10_000))

    with pytest.raises(ValueError, match="state_components"):
        trainer2.load_checkpoint(ckpt_path, strict=True, load_optimizers=False, load_buffer=False, load_rng=False)


def test_checkpoint_loads_legacy_without_state_components(tmp_path):
    env = PushBallNDEnv(dim=3, max_steps=30, difficulty="easy")
    model = MLPWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=64)
    policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=64)
    trainer = DreamTrainer(env=env, world_model=model, policy=policy, buffer=ReplayBuffer(capacity=10_000))

    ckpt_path = tmp_path / "new.ckpt"
    legacy_path = tmp_path / "legacy.ckpt"
    trainer.save_checkpoint(ckpt_path, extra={"tag": "legacy_case"})

    payload = torch.load(ckpt_path, map_location="cpu")
    payload["env"].pop("state_components", None)
    payload["env"].pop("state_layout_version", None)
    torch.save(payload, legacy_path)

    env2 = PushBallNDEnv(dim=3, max_steps=30, difficulty="easy")
    model2 = MLPWorldModel(state_dim=env2.state_dim, action_dim=env2.action_dim, hidden_dim=64)
    policy2 = PolicyNetwork(state_dim=env2.state_dim, action_dim=env2.action_dim, hidden_dim=64)
    trainer2 = DreamTrainer(env=env2, world_model=model2, policy=policy2, buffer=ReplayBuffer(capacity=10_000))

    extra = trainer2.load_checkpoint(legacy_path, strict=True, load_optimizers=False, load_buffer=False, load_rng=False)
    assert extra["tag"] == "legacy_case"
