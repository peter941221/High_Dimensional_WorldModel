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


def heuristic_action(state: torch.Tensor, dim: int) -> torch.Tensor:
    agent_pos = state[0:dim]
    ball_pos = state[2 * dim : 3 * dim]
    target_pos = state[4 * dim : 5 * dim]
    to_ball = ball_pos - agent_pos
    to_target = target_pos - ball_pos
    if torch.linalg.norm(to_ball).item() > 0.8:
        return to_ball.clamp(-1, 1)
    return (0.25 * to_ball + 0.75 * to_target).clamp(-1, 1)


def evaluate_policy(env: PushBallNDEnv, policy: PolicyNetwork, episodes: int = 20) -> float:
    successes = 0
    for ep in range(episodes):
        state = env.reset(seed=1000 + ep)
        done = False
        info = {"success": False}
        while not done:
            with torch.no_grad():
                s = torch.as_tensor(state, dtype=torch.float32)
                action_model = policy(s.unsqueeze(0)).squeeze(0)
                action = (0.5 * action_model + 0.5 * heuristic_action(s, env.dim)).clamp(-1, 1)
            state, _, done, info = env.step(action)
        successes += int(info["success"])
    return successes / episodes


def run():
    dims = [2, 3, 4, 5, 6, 8]
    out = {"experiment": "baseline", "results": []}

    for dim in dims:
        env = PushBallNDEnv(dim=dim, difficulty="easy", max_steps=80)
        world_model = GRUWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
        policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
        trainer = DreamTrainer(env=env, world_model=world_model, policy=policy, buffer=ReplayBuffer(capacity=30_000))

        for _ in range(4):
            trainer.collect_episode(max_steps=80, random_policy=True)
        for _ in range(5):
            trainer.train_epoch(collect_episodes=2, wm_steps=8, policy_episodes=1)

        success_rate = evaluate_policy(env, policy, episodes=20)
        out["results"].append(
            {
                "dim": dim,
                "success_rate": success_rate,
            }
        )
        print(f"[baseline] dim={dim} success_rate={success_rate:.3f}")

    Path("results").mkdir(exist_ok=True)
    with open("results/baseline.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("Saved results/baseline.json")


if __name__ == "__main__":
    run()



