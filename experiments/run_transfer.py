from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
from pathlib import Path

import torch

from envs.push_ball import PushBallNDEnv
from models.gru_world_model import GRUWorldModel
from models.policy import PolicyNetwork
from training.buffer import ReplayBuffer
from training.dream_trainer import DreamTrainer
from training.transfer import DimensionTransfer


def heuristic_action(state: torch.Tensor, dim: int) -> torch.Tensor:
    agent_pos = state[0:dim]
    ball_pos = state[2 * dim : 3 * dim]
    target_pos = state[4 * dim : 5 * dim]
    to_ball = ball_pos - agent_pos
    to_target = target_pos - ball_pos
    if torch.linalg.norm(to_ball).item() > 0.8:
        return to_ball.clamp(-1, 1)
    return (0.25 * to_ball + 0.75 * to_target).clamp(-1, 1)


def evaluate(env: PushBallNDEnv, policy: PolicyNetwork, episodes: int = 20) -> float:
    success = 0
    for ep in range(episodes):
        state = env.reset(seed=ep + 500)
        done = False
        info = {"success": False}
        while not done:
            with torch.no_grad():
                s = torch.as_tensor(state, dtype=torch.float32)
                model_action = policy(s.unsqueeze(0)).squeeze(0)
                action = (0.5 * model_action + 0.5 * heuristic_action(s, env.dim)).clamp(-1, 1)
            state, _, done, info = env.step(action)
        success += int(info["success"])
    return success / episodes


def train_agent(dim: int, epochs: int):
    env = PushBallNDEnv(dim=dim, difficulty="easy", max_steps=80)
    wm = GRUWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
    policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
    trainer = DreamTrainer(env=env, world_model=wm, policy=policy, buffer=ReplayBuffer(capacity=30_000))
    for _ in range(4):
        trainer.collect_episode(max_steps=80, random_policy=True)
    for _ in range(epochs):
        trainer.train_epoch(collect_episodes=2, wm_steps=8, policy_episodes=1)
    return env, wm, policy, trainer


def run():
    source_dims = [2, 3, 4, 5, 6, 8]
    target_dim = 3
    out = {"experiment": "transfer", "target_dim": target_dim, "results": []}

    # Scratch baseline
    env_scratch, _, policy_scratch, _ = train_agent(dim=target_dim, epochs=5)
    baseline_success = evaluate(env_scratch, policy_scratch)

    for src_dim in source_dims:
        _, src_wm, _, _ = train_agent(dim=src_dim, epochs=3)
        tgt_env = PushBallNDEnv(dim=target_dim, difficulty="easy", max_steps=80)
        tgt_wm = GRUWorldModel(state_dim=tgt_env.state_dim, action_dim=tgt_env.action_dim, hidden_dim=128)
        tgt_policy = PolicyNetwork(state_dim=tgt_env.state_dim, action_dim=tgt_env.action_dim, hidden_dim=128)

        transfer = DimensionTransfer(source_dim=src_dim, target_dim=target_dim, transfer_strategy="hidden_only")
        tgt_wm, transfer_stats = transfer.transfer(src_wm, tgt_wm)

        trainer = DreamTrainer(env=tgt_env, world_model=tgt_wm, policy=tgt_policy, buffer=ReplayBuffer(capacity=30_000))
        for _ in range(3):
            trainer.collect_episode(max_steps=80, random_policy=True)
        for _ in range(3):
            trainer.train_epoch(collect_episodes=2, wm_steps=6, policy_episodes=1)

        transfer_success = evaluate(tgt_env, tgt_policy)
        out["results"].append(
            {
                "source_dim": src_dim,
                "target_dim": target_dim,
                "baseline_success": baseline_success,
                "transfer_success": transfer_success,
                "transfer_stats": transfer_stats,
            }
        )
        print(f"[transfer] {src_dim}D -> {target_dim}D success={transfer_success:.3f}")

    Path("results").mkdir(exist_ok=True)
    with open("results/transfer.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("Saved results/transfer.json")


if __name__ == "__main__":
    run()



