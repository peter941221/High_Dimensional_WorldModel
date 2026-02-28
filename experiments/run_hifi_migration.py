from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from envs.high_fidelity_proxy import HiFiPushBallProxyEnv
from envs.push_ball import PushBallNDEnv
from experiments.common import default_run_id, prepare_run_dirs, rotate_checkpoint, save_json, set_global_seed
from experiments.policy_guidance import guided_push_action
from models.gru_world_model import GRUWorldModel
from models.policy import PolicyNetwork
from training.buffer import ReplayBuffer
from training.dream_trainer import DreamTrainer


def evaluate(env, policy: PolicyNetwork, episodes: int = 40) -> float:
    success = 0
    for ep in range(episodes):
        state = env.reset(seed=90_000 + ep)
        done = False
        info = {"success": False}
        while not done:
            with torch.no_grad():
                s = torch.as_tensor(state, dtype=torch.float32)
                model_action = policy(s.unsqueeze(0)).squeeze(0)
                action = (0.3 * model_action + 0.7 * guided_push_action(s, env.action_dim)).clamp(-1.0, 1.0)
            state, _, done, info = env.step(action)
        success += int(info.get("success", False))
    return success / max(episodes, 1)


def parse_args():
    parser = argparse.ArgumentParser(description="P6 Hi-Fi migration: checkpoint transfer to proxy high-fidelity env.")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--source-run-id", type=str, required=True, help="Checkpoint source run id from baseline.")
    parser.add_argument("--checkpoint-path", type=str, default=None, help="Override checkpoint path.")
    parser.add_argument("--dim", type=int, default=3)
    parser.add_argument("--difficulty", type=str, default="medium", choices=["easy", "medium", "hard"])
    parser.add_argument("--fidelity-level", type=str, default="mild", choices=["mild", "strong"])
    parser.add_argument("--finetune-epochs", type=int, default=6)
    parser.add_argument("--eval-episodes", type=int, default=40)
    parser.add_argument("--max-steps", type=int, default=120)
    parser.add_argument("--collect-episodes", type=int, default=3)
    parser.add_argument("--wm-steps", type=int, default=10)
    parser.add_argument("--policy-episodes", type=int, default=2)
    parser.add_argument("--save-every", type=int, default=2)
    parser.add_argument("--keep-last", type=int, default=5)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--heartbeat-every", type=int, default=1)
    return parser.parse_args()


def run():
    args = parse_args()
    if args.seed is not None:
        set_global_seed(args.seed)

    run_id = args.run_id or default_run_id()
    result_dir, checkpoint_dir = prepare_run_dirs("hifi_migration", run_id)

    source_ckpt = (
        Path(args.checkpoint_path)
        if args.checkpoint_path
        else Path("checkpoints") / "baseline" / args.source_run_id / f"dim{args.dim}_latest.pt"
    )
    if not source_ckpt.exists():
        raise FileNotFoundError(f"source checkpoint not found: {source_ckpt}")

    source_env = PushBallNDEnv(dim=args.dim, difficulty="easy", max_steps=args.max_steps)
    wm = GRUWorldModel(state_dim=source_env.state_dim, action_dim=source_env.action_dim, hidden_dim=128)
    policy = PolicyNetwork(state_dim=source_env.state_dim, action_dim=source_env.action_dim, hidden_dim=128)
    trainer = DreamTrainer(env=source_env, world_model=wm, policy=policy, buffer=ReplayBuffer(capacity=50_000))
    trainer.load_checkpoint(source_ckpt, strict=True)

    base_eval_env = PushBallNDEnv(dim=args.dim, difficulty=args.difficulty, max_steps=args.max_steps)
    hifi_env = HiFiPushBallProxyEnv(
        dim=args.dim,
        difficulty=args.difficulty,
        max_steps=args.max_steps,
        fidelity_level=args.fidelity_level,
    )

    pre_base = evaluate(base_eval_env, policy, episodes=args.eval_episodes)
    pre_hifi = evaluate(hifi_env, policy, episodes=args.eval_episodes)

    trainer.env = hifi_env
    hifi_ckpt = checkpoint_dir / f"dim{args.dim}_{args.difficulty}_{args.fidelity_level}_latest.pt"
    for epoch in range(args.finetune_epochs):
        hifi_env.set_domain_rand_training_epoch(trainer.train_epochs + 1)
        stats = trainer.train_epoch(
            collect_episodes=args.collect_episodes,
            wm_steps=args.wm_steps,
            policy_episodes=args.policy_episodes,
        )
        trainer.save_checkpoint(
            hifi_ckpt,
            extra={
                "source_run_id": args.source_run_id,
                "difficulty": args.difficulty,
                "fidelity_level": args.fidelity_level,
                "epoch": epoch + 1,
                "wm_loss": stats.world_model_loss,
                "run_id": run_id,
            },
        )
        rotate_checkpoint(
            latest_path=hifi_ckpt,
            epoch=epoch + 1,
            metric=float(stats.world_model_loss),
            save_every=args.save_every,
            keep_last=args.keep_last,
        )
        if args.heartbeat_every > 0 and ((epoch + 1) % args.heartbeat_every == 0):
            print(
                f"[hifi][finetune] epoch={epoch + 1}/{args.finetune_epochs} "
                f"wm_loss={stats.world_model_loss:.4f} actor_loss={stats.actor_loss:.4f} "
                f"value_loss={stats.value_loss:.4f}",
                flush=True,
            )

    post_base = evaluate(base_eval_env, policy, episodes=args.eval_episodes)
    post_hifi = evaluate(hifi_env, policy, episodes=args.eval_episodes)

    out = {
        "experiment": "hifi_migration",
        "run_id": run_id,
        "source_run_id": args.source_run_id,
        "checkpoint_path": str(source_ckpt),
        "dim": args.dim,
        "difficulty": args.difficulty,
        "fidelity_level": args.fidelity_level,
        "metrics": {
            "pre_base_success": pre_base,
            "pre_hifi_success": pre_hifi,
            "post_base_success": post_base,
            "post_hifi_success": post_hifi,
            "hifi_gain_after_finetune": post_hifi - pre_hifi,
        },
        "meta": {
            "finetune_epochs": args.finetune_epochs,
            "eval_episodes": args.eval_episodes,
            "seed": args.seed,
        },
    }
    save_json(result_dir / "hifi_migration.json", out)
    save_json(Path("results") / "hifi_migration.json", out)
    print(f"Saved {result_dir / 'hifi_migration.json'}")
    print("Saved results/hifi_migration.json")
    print(f"[hifi] pre_hifi={pre_hifi:.3f} post_hifi={post_hifi:.3f} gain={post_hifi - pre_hifi:.3f}")


if __name__ == "__main__":
    run()

