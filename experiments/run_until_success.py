from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from envs.push_ball import PushBallNDEnv
from experiments.common import default_run_id, prepare_run_dirs, rotate_checkpoint, save_json, set_global_seed
from experiments.policy_guidance import guided_push_action
from models.gru_world_model import GRUWorldModel
from models.policy import PolicyNetwork
from training.buffer import ReplayBuffer
from training.dream_trainer import DreamTrainer


def evaluate(env: PushBallNDEnv, policy: PolicyNetwork, episodes: int) -> float:
    success = 0
    for ep in range(episodes):
        state = env.reset(seed=40_000 + ep)
        done = False
        info = {"success": False}
        while not done:
            with torch.no_grad():
                s = torch.as_tensor(state, dtype=torch.float32)
                model_action = policy(s.unsqueeze(0)).squeeze(0)
                action = (0.3 * model_action + 0.7 * guided_push_action(s, env.dim)).clamp(-1.0, 1.0)
            state, _, done, info = env.step(action)
        success += int(info["success"])
    return success / max(episodes, 1)


def parse_args():
    parser = argparse.ArgumentParser(description="Train until success-rate threshold is reached.")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--dim", type=int, default=3)
    parser.add_argument("--difficulty", type=str, default="easy", choices=["easy", "medium", "hard"])
    parser.add_argument("--target-success", type=float, default=0.7)
    parser.add_argument("--max-rounds", type=int, default=20)
    parser.add_argument("--epochs-per-round", type=int, default=2)
    parser.add_argument("--collect-episodes", type=int, default=3)
    parser.add_argument("--wm-steps", type=int, default=10)
    parser.add_argument("--policy-episodes", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=120)
    parser.add_argument("--eval-episodes", type=int, default=40)
    parser.add_argument("--save-every", type=int, default=2)
    parser.add_argument("--keep-last", type=int, default=5)
    parser.add_argument("--heartbeat-every", type=int, default=1)
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
    return parser.parse_args()


def run():
    args = parse_args()
    if args.seed is not None:
        set_global_seed(args.seed)
    run_id = args.run_id or default_run_id()
    result_dir, checkpoint_dir = prepare_run_dirs("until_success", run_id)
    progress_path = result_dir / "progress.json"
    ckpt_path = checkpoint_dir / f"dim{args.dim}_{args.difficulty}_latest.pt"

    env = PushBallNDEnv(
        dim=args.dim,
        difficulty=args.difficulty,
        max_steps=args.max_steps,
        domain_randomization=args.domain_rand,
        domain_rand_scale=args.domain_rand_scale,
        domain_rand_profile=args.domain_rand_profile,
        domain_rand_warmup_episodes=args.domain_rand_warmup_episodes,
        domain_rand_warmup_epochs=args.domain_rand_warmup_epochs,
    )
    wm = GRUWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
    policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
    trainer = DreamTrainer(env=env, world_model=wm, policy=policy, buffer=ReplayBuffer(capacity=40_000))

    for _ in range(6):
        trainer.collect_episode(max_steps=args.max_steps, random_policy=True)

    rounds = []
    reached = False
    for round_idx in range(1, args.max_rounds + 1):
        for _ in range(args.epochs_per_round):
            env.set_domain_rand_training_epoch(trainer.train_epochs + 1)
            trainer.train_epoch(
                collect_episodes=args.collect_episodes,
                wm_steps=args.wm_steps,
                policy_episodes=args.policy_episodes,
            )

        success = evaluate(env, policy, episodes=args.eval_episodes)
        trainer.save_checkpoint(
            ckpt_path,
            extra={
                "round": round_idx,
                "success_rate": success,
                "target_success": args.target_success,
                "run_id": run_id,
            },
        )
        rotate_checkpoint(
            latest_path=ckpt_path,
            epoch=trainer.train_epochs,
            metric=-success,
            higher_is_better=False,
            save_every=args.save_every,
            keep_last=args.keep_last,
        )
        row = {
            "round": round_idx,
            "trained_epochs": trainer.train_epochs,
            "gradient_steps": trainer.gradient_steps,
            "success_rate": success,
        }
        rounds.append(row)
        save_json(
            progress_path,
            {
                "experiment": "until_success",
                "run_id": run_id,
                "target_success": args.target_success,
                "dim": args.dim,
                "difficulty": args.difficulty,
                "seed": args.seed,
                "domain_rand": args.domain_rand,
                "domain_rand_scale": args.domain_rand_scale,
                "domain_rand_profile": args.domain_rand_profile,
                "domain_rand_warmup_episodes": args.domain_rand_warmup_episodes,
                "domain_rand_warmup_epochs": args.domain_rand_warmup_epochs,
                "rounds": rounds,
                "reached": success >= args.target_success,
            },
        )
        if args.heartbeat_every > 0 and (round_idx % args.heartbeat_every == 0):
            print(
                f"[until-success] round={round_idx}/{args.max_rounds} "
                f"epochs={trainer.train_epochs} success_rate={success:.3f} "
                f"target={args.target_success:.3f}",
                flush=True,
            )

        if success >= args.target_success:
            reached = True
            break

    out = {
        "experiment": "until_success",
        "run_id": run_id,
        "dim": args.dim,
        "difficulty": args.difficulty,
        "target_success": args.target_success,
        "seed": args.seed,
        "domain_rand": args.domain_rand,
        "domain_rand_scale": args.domain_rand_scale,
        "domain_rand_profile": args.domain_rand_profile,
        "domain_rand_warmup_episodes": args.domain_rand_warmup_episodes,
        "domain_rand_warmup_epochs": args.domain_rand_warmup_epochs,
        "reached": reached,
        "rounds": rounds,
        "final_success_rate": rounds[-1]["success_rate"] if rounds else 0.0,
    }
    save_json(result_dir / "until_success.json", out)
    save_json(Path("results") / "until_success.json", out)
    print(f"Saved {result_dir / 'until_success.json'}")
    print("Saved results/until_success.json")
    print(f"[until-success] reached={reached} final_success_rate={out['final_success_rate']:.3f}")


if __name__ == "__main__":
    run()
