from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn.functional as F

from models.gru_world_model import GRUWorldModel
from models.mlp_world_model import MLPWorldModel
from models.policy import PolicyNetwork
from models.rssm_world_model import RSSMWorldModel
from models.value import ValueNetwork
from training.buffer import ReplayBuffer


@dataclass
class TrainStats:
    world_model_loss: float
    actor_loss: float
    value_loss: float


class DreamTrainer:
    """World-model training plus imagination-based actor-critic optimization."""

    def __init__(
        self,
        env,
        world_model,
        policy: PolicyNetwork,
        buffer: ReplayBuffer,
        value_model: ValueNetwork | None = None,
        device: str = "cpu",
        gamma: float = 0.99,
        actor_bc_coef: float = 0.05,
    ):
        self.env = env
        self.world_model = world_model.to(device)
        self.policy = policy.to(device)
        self.buffer = buffer
        self.device = device
        self.gamma = float(gamma)
        self.actor_bc_coef = float(actor_bc_coef)

        self.value_model = value_model or ValueNetwork(state_dim=env.state_dim, hidden_dim=256)
        self.value_model = self.value_model.to(device)
        self.target_value_model = ValueNetwork(state_dim=env.state_dim, hidden_dim=256).to(device)
        self.target_value_model.load_state_dict(self.value_model.state_dict())
        self.target_value_model.eval()

        self.wm_optimizer = torch.optim.Adam(self.world_model.parameters(), lr=3e-4)
        self.actor_optimizer = torch.optim.Adam(self.policy.parameters(), lr=3e-4)
        self.value_optimizer = torch.optim.Adam(self.value_model.parameters(), lr=3e-4)

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
                with torch.no_grad():
                    action = self.policy(state_t.unsqueeze(0)).squeeze(0).cpu()
                action = (action + 0.15 * torch.randn_like(action)).clamp(-1, 1)

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

    def _predict_world_model(self, state: torch.Tensor, action: torch.Tensor, hidden):
        if isinstance(self.world_model, MLPWorldModel):
            next_state, reward = self.world_model(state, action)
            return next_state, reward, hidden, 0.0

        if isinstance(self.world_model, GRUWorldModel):
            if hidden is None:
                hidden = self.world_model.init_hidden(state.shape[0], device=state.device)
            next_state, reward, next_hidden = self.world_model(state, action, hidden)
            return next_state, reward, next_hidden, 0.0

        if isinstance(self.world_model, RSSMWorldModel):
            if hidden is None:
                hidden = self.world_model.init_hidden(state.shape[0], device=state.device)
            next_state, reward, next_hidden, kl = self.world_model(state, action, hidden)
            return next_state, reward, next_hidden, float(kl.mean().detach().item())

        raise TypeError(f"unsupported world model type: {type(self.world_model)}")

    def _world_model_loss_from_batch(self, batch):
        states = batch["states"].to(self.device)
        actions = batch["actions"].to(self.device)
        rewards = batch["rewards"].to(self.device)

        input_states = states[:, :-1, :]
        input_actions = actions[:, :-1, :]
        target_states = states[:, 1:, :]
        target_rewards = rewards[:, 1:, :]

        hidden = None
        pred_states = []
        pred_rewards = []
        kl_values = []
        for t in range(input_states.shape[1]):
            pred_s, pred_r, hidden, kl_val = self._predict_world_model(
                input_states[:, t],
                input_actions[:, t],
                hidden=hidden,
            )
            pred_states.append(pred_s)
            pred_rewards.append(pred_r)
            kl_values.append(kl_val)

        pred_state = torch.stack(pred_states, dim=1)
        pred_reward = torch.stack(pred_rewards, dim=1)
        state_loss = F.mse_loss(pred_state, target_states)
        reward_loss = F.mse_loss(pred_reward, target_rewards)
        kl_term = sum(kl_values) / max(len(kl_values), 1)
        return state_loss + reward_loss + 0.1 * kl_term

    def train_world_model(self, steps: int = 50, batch_size: int = 16, seq_len: int = 20):
        if len(self.buffer.episodes) == 0:
            return 0.0

        total = 0.0
        seq_len = max(seq_len, 2)
        for _ in range(steps):
            batch = self.buffer.sample_batch(batch_size=batch_size, seq_len=seq_len)
            loss = self._world_model_loss_from_batch(batch)
            self.wm_optimizer.zero_grad()
            loss.backward()
            self.wm_optimizer.step()
            total += float(loss.item())
        return total / max(steps, 1)

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

    def _soft_update_target_value(self, tau: float = 0.02):
        with torch.no_grad():
            for target_param, online_param in zip(self.target_value_model.parameters(), self.value_model.parameters()):
                target_param.data.mul_(1.0 - tau).add_(tau * online_param.data)

    def train_actor_critic(
        self,
        steps: int = 20,
        batch_size: int = 64,
        imagine_horizon: int = 5,
    ):
        if len(self.buffer.episodes) == 0:
            return 0.0, 0.0

        actor_total = 0.0
        value_total = 0.0
        seq_len = max(imagine_horizon + 1, 2)

        for _ in range(steps):
            batch = self.buffer.sample_batch(batch_size=batch_size, seq_len=seq_len)
            start_states = batch["states"][:, 0, :].to(self.device)

            # 1) Critic update with imagined one-step TD targets.
            self.value_optimizer.zero_grad()
            states_for_value = start_states.detach()
            hidden_val = None
            value_losses = []
            for _ in range(imagine_horizon):
                with torch.no_grad():
                    actions = self.policy(states_for_value)
                next_states, rewards, hidden_val, _ = self._predict_world_model(
                    states_for_value,
                    actions,
                    hidden=hidden_val,
                )
                values = self.value_model(states_for_value)
                with torch.no_grad():
                    td_target = rewards + self.gamma * self.target_value_model(next_states)
                value_losses.append(F.mse_loss(values, td_target))
                states_for_value = next_states.detach()

            value_loss = torch.stack(value_losses).mean()
            value_loss.backward()
            self.value_optimizer.step()
            self._soft_update_target_value()

            # 2) Actor update through differentiable imagination.
            self.actor_optimizer.zero_grad()
            states_for_actor = start_states
            hidden_actor = None
            objectives = []
            bc_losses = []
            for _ in range(imagine_horizon):
                actions = self.policy(states_for_actor)
                next_states, rewards, hidden_actor, _ = self._predict_world_model(
                    states_for_actor,
                    actions,
                    hidden=hidden_actor,
                )
                objectives.append((rewards + self.gamma * self.value_model(next_states)).mean())
                bc_losses.append(F.mse_loss(actions, self._heuristic_targets(states_for_actor)))
                states_for_actor = next_states

            actor_objective = torch.stack(objectives).mean()
            bc_loss = torch.stack(bc_losses).mean()
            actor_loss = -actor_objective + self.actor_bc_coef * bc_loss
            actor_loss.backward()
            self.actor_optimizer.step()

            actor_total += float(actor_loss.item())
            value_total += float(value_loss.item())

        return actor_total / max(steps, 1), value_total / max(steps, 1)

    def train_policy(self, episodes: int = 5, gamma: float = 0.99):
        # Backward compatible wrapper: use actor-critic steps instead of imitation-only updates.
        self.gamma = float(gamma)
        actor_loss, _ = self.train_actor_critic(steps=max(episodes, 1), batch_size=64, imagine_horizon=4)
        return actor_loss

    def train_epoch(self, collect_episodes: int = 3, wm_steps: int = 20, policy_episodes: int = 2):
        for _ in range(collect_episodes):
            self.collect_episode(random_policy=False)
        wm_loss = self.train_world_model(steps=wm_steps)
        actor_loss, value_loss = self.train_actor_critic(
            steps=max(policy_episodes, 1),
            batch_size=64,
            imagine_horizon=5,
        )
        return TrainStats(
            world_model_loss=wm_loss,
            actor_loss=actor_loss,
            value_loss=value_loss,
        )
