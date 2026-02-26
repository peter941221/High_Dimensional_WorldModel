from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
from pathlib import Path

import torch

from envs.push_ball import PushBallNDEnv
from models.policy import PolicyNetwork


def heuristic_policy(state: torch.Tensor, dim: int):
    agent_pos = state[:dim]
    ball_pos = state[2 * dim : 3 * dim]
    target_pos = state[4 * dim : 5 * dim]
    to_ball = ball_pos - agent_pos
    to_target = target_pos - ball_pos
    if torch.linalg.norm(to_ball).item() > 0.8:
        return to_ball.clamp(-1, 1)
    return (0.2 * to_ball + 0.8 * to_target).clamp(-1, 1)


def eval_under_condition(dim: int, difficulty: str, episodes: int = 40):
    env = PushBallNDEnv(dim=dim, difficulty=difficulty, max_steps=100)
    success = 0
    for ep in range(episodes):
        state = env.reset(seed=ep + 42)
        done = False
        info = {"success": False}
        while not done:
            action = heuristic_policy(state, dim)
            state, _, done, info = env.step(action)
        success += int(info["success"])
    return success / episodes


def run():
    rows = []
    for difficulty in ["easy", "medium", "hard"]:
        rows.append(
            {
                "difficulty": difficulty,
                "success_rate": eval_under_condition(dim=3, difficulty=difficulty, episodes=50),
            }
        )

    out = {"experiment": "robustness", "results": rows}
    Path("results").mkdir(exist_ok=True)
    with open("results/robustness.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("Saved results/robustness.json")


if __name__ == "__main__":
    run()



