from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn.functional as F

from models.gru_world_model import GRUWorldModel
from models.mlp_world_model import MLPWorldModel
from models.policy import PolicyNetwork
from models.rssm_world_model import RSSMWorldModel
from training.buffer import ReplayBuffer


@dataclass
class TrainStats:
    world_model_loss: float
    policy_loss: float


class DreamTrainer:
    """Minimal end-to-end trainer for world model and policy optimization."""

    def __init__(
        self,
        env,
        world_model,
        policy: PolicyNetwork,
        buffer: ReplayBuffer,
        device: str = "cpu",
    ):
        self.env = env
        self.world_model = world_model.to(device)
        self.policy = policy.to(device)
        self.buffer = buffer
        self.device = device

        self.wm_optimizer = torch.optim.Adam(self.world_model.parameters(), lr=3e-4)
        self.policy_optimizer = torch.optim.Adam(self.policy.parameters(), lr=3e-4)

    def collect_episode(self, max_steps: int = 200, random_policy: bool = False):
        state = self.env.reset()
        states = []
        actions = []
        rewards = []

        for _ in range(max_steps):
            state_t = torch.as_tensor(state, dtype=torch.float32)
            if random_policy:
                action = torch.randn(self.env.action_dim).clamp(-1, 1)
            else:
                expert = self._heuristic_targets(state_t.unsqueeze(0)).squeeze(0).cpu()
                with torch.no_grad():
                    policy_action = self.policy(state_t.unsqueeze(0)).squeeze(0).cpu()
                action = (0.8 * expert + 0.2 * policy_action).clamp(-1, 1)
            next_state, reward, done, _ = self.env.step(action)

            states.append(state_t)
            actions.append(action.float())
            rewards.append(torch.tensor([reward], dtype=torch.float32))
            state = next_state
            if done:
                break

        episode = {
            "states": torch.stack(states, dim=0),
            "actions": torch.stack(actions, dim=0),
            "rewards": torch.stack(rewards, dim=0),
        }
        self.buffer.add_episode(episode)
        return episode

    def _world_model_loss_from_batch(self, batch):
        states = batch["states"].to(self.device)
        actions = batch["actions"].to(self.device)
        rewards = batch["rewards"].to(self.device)

        input_states = states[:, :-1, :]
        input_actions = actions[:, :-1, :]
        target_states = states[:, 1:, :]
        target_rewards = rewards[:, 1:, :]

        if isinstance(self.world_model, MLPWorldModel):
            pred_state, pred_reward = self.world_model(
                input_states.reshape(-1, input_states.shape[-1]),
                input_actions.reshape(-1, input_actions.shape[-1]),
            )
            pred_state = pred_state.view_as(target_states)
            pred_reward = pred_reward.view_as(target_rewards)
            kl_term = 0.0

        elif isinstance(self.world_model, GRUWorldModel):
            hidden = self.world_model.init_hidden(states.shape[0], device=self.device)
            pred_states = []
            pred_rewards = []
            for t in range(input_states.shape[1]):
                pred_s, pred_r, hidden = self.world_model(input_states[:, t], input_actions[:, t], hidden)
                pred_states.append(pred_s)
                pred_rewards.append(pred_r)
            pred_state = torch.stack(pred_states, dim=1)
            pred_reward = torch.stack(pred_rewards, dim=1)
            kl_term = 0.0

        elif isinstance(self.world_model, RSSMWorldModel):
            hidden = self.world_model.init_hidden(states.shape[0], device=self.device)
            pred_states = []
            pred_rewards = []
            kls = []
            for t in range(input_states.shape[1]):
                pred_s, pred_r, hidden, kl = self.world_model(input_states[:, t], input_actions[:, t], hidden)
                pred_states.append(pred_s)
                pred_rewards.append(pred_r)
                kls.append(kl)
            pred_state = torch.stack(pred_states, dim=1)
            pred_reward = torch.stack(pred_rewards, dim=1)
            kl_term = torch.stack(kls, dim=1).mean()
        else:
            raise TypeError(f"unsupported world model type: {type(self.world_model)}")

        state_loss = F.mse_loss(pred_state, target_states)
        reward_loss = F.mse_loss(pred_reward, target_rewards)
        return state_loss + reward_loss + 0.1 * kl_term

    def train_world_model(self, steps: int = 50, batch_size: int = 16, seq_len: int = 20):
        if len(self.buffer.episodes) == 0:
            return 0.0

        total = 0.0
        for _ in range(steps):
            batch = self.buffer.sample_batch(batch_size=batch_size, seq_len=seq_len)
            loss = self._world_model_loss_from_batch(batch)
            self.wm_optimizer.zero_grad()
            loss.backward()
            self.wm_optimizer.step()
            total += float(loss.item())
        return total / max(steps, 1)

    def train_policy(self, episodes: int = 5, gamma: float = 0.99):
        losses = []
        for _ in range(max(episodes, 1)):
            if len(self.buffer.episodes) == 0:
                self.collect_episode(random_policy=True)

            batch = self.buffer.sample_batch(batch_size=64, seq_len=2)
            states = batch["states"][:, 0, :].to(self.device)
            target_actions = self._heuristic_targets(states).to(self.device)

            pred_actions = self.policy(states)
            loss = F.mse_loss(pred_actions, target_actions)

            self.policy_optimizer.zero_grad()
            loss.backward()
            self.policy_optimizer.step()
            losses.append(float(loss.item()))

        return sum(losses) / max(len(losses), 1)

    def _heuristic_targets(self, states: torch.Tensor) -> torch.Tensor:
        dim = self.env.action_dim
        agent_pos = states[:, 0:dim]
        ball_pos = states[:, 2 * dim : 3 * dim]
        target_pos = states[:, 4 * dim : 5 * dim]

        to_ball = ball_pos - agent_pos
        to_target = target_pos - ball_pos
        far_mask = (torch.linalg.norm(to_ball, dim=-1, keepdim=True) > 0.8).float()
        mixed = 0.25 * to_ball + 0.75 * to_target
        actions = far_mask * to_ball + (1.0 - far_mask) * mixed
        return actions.clamp(-1.0, 1.0)

    def train_epoch(self, collect_episodes: int = 3, wm_steps: int = 20, policy_episodes: int = 2):
        for _ in range(collect_episodes):
            self.collect_episode(random_policy=False)
        wm_loss = self.train_world_model(steps=wm_steps)
        policy_loss = self.train_policy(episodes=policy_episodes)
        return TrainStats(world_model_loss=wm_loss, policy_loss=policy_loss)

