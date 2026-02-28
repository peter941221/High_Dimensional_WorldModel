from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from envs.push_ball import PushBallNDEnv
from experiments.common import default_run_id, find_latest_run, prepare_run_dirs, save_json, set_global_seed
from experiments.policy_guidance import guided_push_action


def heuristic_policy(state: torch.Tensor, dim: int):
    return guided_push_action(state, dim)


def should_apply_domain_rand(enabled: bool, scope: str, difficulty: str) -> bool:
    if not enabled:
        return False
    if scope == "all":
        return True
    if scope == "medium_hard":
        return difficulty in {"medium", "hard"}
    if scope == "hard_only":
        return difficulty == "hard"
    raise ValueError(f"unknown domain-rand difficulty scope: {scope}")


def eval_under_condition(
    dim: int,
    difficulty: str,
    episodes: int = 40,
    heartbeat_every: int = 10,
    domain_rand: bool = False,
    domain_rand_scale: float = 0.15,
    domain_rand_profile: str = "full",
    domain_rand_warmup_episodes: int = 0,
    domain_rand_warmup_epochs: int = 0,
):
    env = PushBallNDEnv(
        dim=dim,
        difficulty=difficulty,
        max_steps=100,
        domain_randomization=domain_rand,
        domain_rand_scale=domain_rand_scale,
        domain_rand_profile=domain_rand_profile,
        domain_rand_warmup_episodes=domain_rand_warmup_episodes,
        domain_rand_warmup_epochs=domain_rand_warmup_epochs,
    )
    if domain_rand and domain_rand_warmup_epochs > 0:
        # Evaluation should reflect post-warmup randomization regime.
        env.set_domain_rand_training_epoch(domain_rand_warmup_epochs)
    success = 0
    for ep in range(episodes):
        state = env.reset(seed=ep + 42)
        done = False
        info = {"success": False}
        while not done:
            action = heuristic_policy(state, dim)
            state, _, done, info = env.step(action)
        success += int(info["success"])
        if heartbeat_every > 0 and ((ep + 1) % heartbeat_every == 0 or (ep + 1) == episodes):
            running_rate = success / (ep + 1)
            print(
                f"[robustness][eval] difficulty={difficulty} episode={ep + 1}/{episodes} "
                f"running_success_rate={running_rate:.3f}",
                flush=True,
            )
    return success / episodes


def resolve_run_id(exp_name: str, run_id: str | None, resume: bool) -> str:
    if run_id:
        return run_id
    if resume:
        latest = find_latest_run(exp_name)
        if latest is not None:
            return latest
    return default_run_id()


def parse_args():
    parser = argparse.ArgumentParser(description="Robustness evaluation with persistent run outputs.")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--dim", type=int, default=3)
    parser.add_argument("--seed", type=int, default=None, help="Global random seed for reproducibility.")
    parser.add_argument("--domain-rand", action="store_true", help="Enable domain randomization in environment.")
    parser.add_argument("--domain-rand-scale", type=float, default=0.15, help="Relative randomization scale.")
    parser.add_argument(
        "--domain-rand-profile",
        type=str,
        default="full",
        choices=["full", "conservative"],
        help="Domain randomization parameter profile.",
    )
    parser.add_argument(
        "--domain-rand-warmup-episodes",
        type=int,
        default=0,
        help="Linear warmup episodes for effective randomization scale.",
    )
    parser.add_argument(
        "--domain-rand-warmup-epochs",
        type=int,
        default=0,
        help="Linear warmup epochs for effective randomization scale.",
    )
    parser.add_argument(
        "--domain-rand-difficulties",
        type=str,
        default="all",
        choices=["all", "medium_hard", "hard_only"],
        help="Which difficulty levels apply domain randomization.",
    )
    parser.add_argument("--heartbeat-every", type=int, default=10, help="Print eval heartbeat every N episodes.")
    return parser.parse_args()


def run():
    args = parse_args()
    if args.seed is not None:
        set_global_seed(args.seed)
    exp_name = "robustness"
    run_id = resolve_run_id(exp_name, args.run_id, args.resume)
    result_dir, _ = prepare_run_dirs(exp_name, run_id)

    rows = []
    for difficulty in ["easy", "medium", "hard"]:
        apply_domain_rand = should_apply_domain_rand(
            enabled=args.domain_rand,
            scope=args.domain_rand_difficulties,
            difficulty=difficulty,
        )
        rows.append(
            {
                "difficulty": difficulty,
                "success_rate": eval_under_condition(
                    dim=args.dim,
                    difficulty=difficulty,
                    episodes=args.episodes,
                    heartbeat_every=args.heartbeat_every,
                    domain_rand=apply_domain_rand,
                    domain_rand_scale=args.domain_rand_scale,
                    domain_rand_profile=args.domain_rand_profile,
                    domain_rand_warmup_episodes=args.domain_rand_warmup_episodes,
                    domain_rand_warmup_epochs=args.domain_rand_warmup_epochs,
                ),
            }
        )

    out = {
        "experiment": exp_name,
        "run_id": run_id,
        "results": rows,
        "meta": {
            "episodes": args.episodes,
            "dim": args.dim,
            "seed": args.seed,
            "domain_rand": args.domain_rand,
            "domain_rand_scale": args.domain_rand_scale,
            "domain_rand_profile": args.domain_rand_profile,
            "domain_rand_warmup_episodes": args.domain_rand_warmup_episodes,
            "domain_rand_warmup_epochs": args.domain_rand_warmup_epochs,
            "domain_rand_difficulties": args.domain_rand_difficulties,
        },
    }
    save_json(result_dir / "robustness.json", out)
    save_json(Path("results") / "robustness.json", out)
    print(f"Saved {result_dir / 'robustness.json'}")
    print("Saved results/robustness.json")


if __name__ == "__main__":
    run()
