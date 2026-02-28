from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from envs.push_ball import PushBallNDEnv
from experiments.common import default_run_id, load_json, prepare_run_dirs, rotate_checkpoint, save_json, set_global_seed
from experiments.policy_guidance import guided_push_action
from models.gru_world_model import GRUWorldModel
from models.policy import PolicyNetwork
from training.buffer import ReplayBuffer
from training.dream_trainer import DreamTrainer


def evaluate(env: PushBallNDEnv, policy: PolicyNetwork, episodes: int) -> float:
    success = 0
    for ep in range(episodes):
        state = env.reset(seed=20_000 + ep)
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
    parser = argparse.ArgumentParser(description="Curriculum training: easy -> medium -> hard with thresholds.")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--dim", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=120)
    parser.add_argument("--epochs-per-round", type=int, default=2)
    parser.add_argument("--collect-episodes", type=int, default=3)
    parser.add_argument("--wm-steps", type=int, default=10)
    parser.add_argument("--policy-episodes", type=int, default=2)
    parser.add_argument("--eval-episodes", type=int, default=40)
    parser.add_argument("--max-rounds-per-stage", type=int, default=20)
    parser.add_argument("--target-easy", type=float, default=0.70)
    parser.add_argument("--target-medium", type=float, default=0.35)
    parser.add_argument("--target-hard", type=float, default=0.25)
    parser.add_argument("--save-every", type=int, default=2)
    parser.add_argument("--keep-last", type=int, default=5)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--heartbeat-every", type=int, default=1)

    parser.add_argument("--domain-rand", action="store_true")
    parser.add_argument("--domain-rand-scale", type=float, default=0.10)
    parser.add_argument("--domain-rand-profile", type=str, default="conservative", choices=["full", "conservative"])
    parser.add_argument("--domain-rand-warmup-episodes", type=int, default=200)
    parser.add_argument("--domain-rand-warmup-epochs", type=int, default=8)
    return parser.parse_args()


def make_env(args, difficulty: str):
    return PushBallNDEnv(
        dim=args.dim,
        difficulty=difficulty,
        max_steps=args.max_steps,
        domain_randomization=args.domain_rand,
        domain_rand_scale=args.domain_rand_scale,
        domain_rand_profile=args.domain_rand_profile,
        domain_rand_warmup_episodes=args.domain_rand_warmup_episodes,
        domain_rand_warmup_epochs=args.domain_rand_warmup_epochs,
    )


def run():
    args = parse_args()
    if args.seed is not None:
        set_global_seed(args.seed)

    run_id = args.run_id or default_run_id()
    result_dir, checkpoint_dir = prepare_run_dirs("curriculum", run_id)
    progress_path = result_dir / "progress.json"
    ckpt_path = checkpoint_dir / f"dim{args.dim}_curriculum_latest.pt"

    targets = {
        "easy": float(args.target_easy),
        "medium": float(args.target_medium),
        "hard": float(args.target_hard),
    }
    stages = ["easy", "medium", "hard"]

    base_env = make_env(args, difficulty="easy")
    wm = GRUWorldModel(state_dim=base_env.state_dim, action_dim=base_env.action_dim, hidden_dim=128)
    policy = PolicyNetwork(state_dim=base_env.state_dim, action_dim=base_env.action_dim, hidden_dim=128)
    trainer = DreamTrainer(env=base_env, world_model=wm, policy=policy, buffer=ReplayBuffer(capacity=50_000))

    progress = load_json(
        progress_path,
        default={
            "experiment": "curriculum",
            "run_id": run_id,
            "dim": args.dim,
            "stages": [],
            "current_stage": "easy",
            "completed": False,
        },
    )
    rows = list(progress.get("stages", []))

    if args.resume and ckpt_path.exists():
        extra = trainer.load_checkpoint(ckpt_path)
        print(f"[curriculum] resumed trainer at epoch={trainer.train_epochs} extra={extra}")
    else:
        for _ in range(6):
            trainer.collect_episode(max_steps=args.max_steps, random_policy=True)

    start_stage_idx = stages.index(progress.get("current_stage", "easy"))
    global_round = int(progress.get("global_round", 0))
    completed = bool(progress.get("completed", False))

    for stage_idx in range(start_stage_idx, len(stages)):
        difficulty = stages[stage_idx]
        target = targets[difficulty]
        env = make_env(args, difficulty=difficulty)
        trainer.env = env

        stage_round = 0
        reached = False
        while stage_round < args.max_rounds_per_stage:
            stage_round += 1
            global_round += 1

            for _ in range(args.epochs_per_round):
                env.set_domain_rand_training_epoch(trainer.train_epochs + 1)
                trainer.train_epoch(
                    collect_episodes=args.collect_episodes,
                    wm_steps=args.wm_steps,
                    policy_episodes=args.policy_episodes,
                )

            env.set_domain_rand_training_epoch(max(trainer.train_epochs, 1))
            success = evaluate(env, policy, episodes=args.eval_episodes)

            row = {
                "stage": difficulty,
                "target_success": target,
                "stage_round": stage_round,
                "global_round": global_round,
                "train_epochs": trainer.train_epochs,
                "gradient_steps": trainer.gradient_steps,
                "success_rate": success,
            }
            rows.append(row)

            trainer.save_checkpoint(
                ckpt_path,
                extra={
                    "run_id": run_id,
                    "stage": difficulty,
                    "stage_round": stage_round,
                    "global_round": global_round,
                    "success_rate": success,
                    "target_success": target,
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

            next_stage = stages[stage_idx + 1] if stage_idx + 1 < len(stages) else "done"
            save_json(
                progress_path,
                {
                    "experiment": "curriculum",
                    "run_id": run_id,
                    "dim": args.dim,
                    "stages": rows,
                    "current_stage": next_stage if success >= target else difficulty,
                    "global_round": global_round,
                    "completed": False,
                },
            )

            if args.heartbeat_every > 0 and (global_round % args.heartbeat_every == 0):
                print(
                    f"[curriculum] stage={difficulty} round={stage_round}/{args.max_rounds_per_stage} "
                    f"epochs={trainer.train_epochs} success={success:.3f} target={target:.3f}",
                    flush=True,
                )

            if success >= target:
                reached = True
                break

        if not reached:
            break

    completed = rows and all(
        any(r["stage"] == s and r["success_rate"] >= targets[s] for r in rows) for s in stages
    )

    out = {
        "experiment": "curriculum",
        "run_id": run_id,
        "dim": args.dim,
        "targets": targets,
        "completed": bool(completed),
        "stages": rows,
        "meta": {
            "max_rounds_per_stage": args.max_rounds_per_stage,
            "epochs_per_round": args.epochs_per_round,
            "eval_episodes": args.eval_episodes,
            "seed": args.seed,
            "domain_rand": args.domain_rand,
            "domain_rand_scale": args.domain_rand_scale,
            "domain_rand_profile": args.domain_rand_profile,
            "domain_rand_warmup_episodes": args.domain_rand_warmup_episodes,
            "domain_rand_warmup_epochs": args.domain_rand_warmup_epochs,
        },
    }
    save_json(result_dir / "curriculum.json", out)
    save_json(Path("results") / "curriculum.json", out)
    save_json(
        progress_path,
        {
            "experiment": "curriculum",
            "run_id": run_id,
            "dim": args.dim,
            "stages": rows,
            "current_stage": "done" if completed else progress.get("current_stage", "easy"),
            "global_round": global_round,
            "completed": bool(completed),
        },
    )
    print(f"Saved {result_dir / 'curriculum.json'}")
    print("Saved results/curriculum.json")
    print(f"[curriculum] completed={bool(completed)} rounds={len(rows)}")


if __name__ == "__main__":
    run()

