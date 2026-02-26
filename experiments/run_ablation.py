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
from models.mlp_world_model import MLPWorldModel
from models.policy import PolicyNetwork
from models.rssm_world_model import RSSMWorldModel
from training.buffer import ReplayBuffer
from training.dream_trainer import DreamTrainer


def heuristic_action(state: torch.Tensor, dim: int):
    agent_pos = state[:dim]
    ball_pos = state[2 * dim : 3 * dim]
    target_pos = state[4 * dim : 5 * dim]
    to_ball = ball_pos - agent_pos
    to_target = target_pos - ball_pos
    if torch.linalg.norm(to_ball).item() > 0.8:
        return to_ball.clamp(-1, 1)
    return (0.25 * to_ball + 0.75 * to_target).clamp(-1, 1)


def evaluate(env, policy, episodes=20):
    success = 0
    for ep in range(episodes):
        s = env.reset(seed=700 + ep)
        done = False
        info = {"success": False}
        while not done:
            with torch.no_grad():
                st = torch.as_tensor(s, dtype=torch.float32)
                model_action = policy(st.unsqueeze(0)).squeeze(0)
                a = (0.5 * model_action + 0.5 * heuristic_action(st, env.dim)).clamp(-1, 1)
            s, _, done, info = env.step(a)
        success += int(info["success"])
    return success / episodes


def run():
    env = PushBallNDEnv(dim=4, difficulty="easy", max_steps=80)
    configs = [
        ("mlp", lambda: MLPWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)),
        ("gru", lambda: GRUWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)),
        (
            "rssm",
            lambda: RSSMWorldModel(
                state_dim=env.state_dim,
                action_dim=env.action_dim,
                det_dim=128,
                stoch_dim=24,
                hidden_dim=128,
            ),
        ),
    ]

    results = []
    for name, factory in configs:
        model = factory()
        policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
        trainer = DreamTrainer(env=env, world_model=model, policy=policy, buffer=ReplayBuffer(capacity=20_000))
        for _ in range(4):
            trainer.collect_episode(max_steps=80, random_policy=True)
        for _ in range(4):
            trainer.train_epoch(collect_episodes=2, wm_steps=6, policy_episodes=1)
        success = evaluate(env, policy, episodes=20)
        results.append({"model": name, "success_rate": success})
        print(f"[ablation] model={name} success={success:.3f}")

    out = {"experiment": "ablation", "results": results}
    Path("results").mkdir(exist_ok=True)
    with open("results/ablation.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("Saved results/ablation.json")


if __name__ == "__main__":
    run()



