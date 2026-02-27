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
