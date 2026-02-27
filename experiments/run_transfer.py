from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from envs.push_ball import PushBallNDEnv
from experiments.common import (
    default_run_id,
    find_latest_run,
    load_json,
    prepare_run_dirs,
    rotate_checkpoint,
    save_json,
)
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


def resolve_run_id(exp_name: str, run_id: str | None, resume: bool) -> str:
    if run_id:
        return run_id
    if resume:
        latest = find_latest_run(exp_name)
        if latest is not None:
            return latest
    return default_run_id()


def parse_args():
    parser = argparse.ArgumentParser(description="Cross-dimensional transfer with checkpoint resume support.")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--pretrain-epochs", type=int, default=3)
    parser.add_argument("--finetune-epochs", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=80)
    parser.add_argument("--eval-episodes", type=int, default=20)
    parser.add_argument("--save-every", type=int, default=5, help="Archive checkpoint every N epochs (0 disables).")
    parser.add_argument("--keep-last", type=int, default=5, help="How many archive checkpoints to keep.")
    parser.add_argument("--heartbeat-every", type=int, default=1, help="Print training heartbeat every N epochs.")
    return parser.parse_args()


def make_trainer(dim: int, max_steps: int):
    env = PushBallNDEnv(dim=dim, difficulty="easy", max_steps=max_steps)
    wm = GRUWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
    policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
    trainer = DreamTrainer(env=env, world_model=wm, policy=policy, buffer=ReplayBuffer(capacity=30_000))
    return env, wm, policy, trainer


def bootstrap_if_empty(trainer: DreamTrainer, max_steps: int):
    if len(trainer.buffer.episodes) == 0:
        for _ in range(4):
            trainer.collect_episode(max_steps=max_steps, random_policy=True)


def run():
    args = parse_args()
    exp_name = "transfer"
    run_id = resolve_run_id(exp_name, args.run_id, args.resume)
    result_dir, checkpoint_dir = prepare_run_dirs(exp_name, run_id)
    progress_path = result_dir / "progress.json"

    progress = load_json(
        progress_path,
        default={"experiment": exp_name, "run_id": run_id, "results": [], "meta": {}},
    )
    results_by_src = {int(item["source_dim"]): item for item in progress.get("results", [])}

    source_dims = [2, 3, 4, 5, 6, 8]
    target_dim = 3

    scratch_env, _, scratch_policy, scratch_trainer = make_trainer(dim=target_dim, max_steps=args.max_steps)
    scratch_ckpt = checkpoint_dir / f"scratch_dim{target_dim}.pt"
    if args.resume and scratch_ckpt.exists():
        scratch_trainer.load_checkpoint(scratch_ckpt)
        print(f"[transfer] resumed scratch baseline at epoch={scratch_trainer.train_epochs}")
    else:
        bootstrap_if_empty(scratch_trainer, args.max_steps)

    for epoch in range(scratch_trainer.train_epochs, args.pretrain_epochs):
        stats = scratch_trainer.train_epoch(collect_episodes=2, wm_steps=8, policy_episodes=1)
        scratch_trainer.save_checkpoint(
            scratch_ckpt,
            extra={"stage": "scratch", "epoch": epoch + 1, "run_id": run_id, "wm_loss": stats.world_model_loss},
        )
        rotate_checkpoint(
            latest_path=scratch_ckpt,
            epoch=epoch + 1,
            metric=float(stats.world_model_loss),
            save_every=args.save_every,
            keep_last=args.keep_last,
        )
        if args.heartbeat_every > 0 and ((epoch + 1) % args.heartbeat_every == 0):
            print(
                f"[transfer][scratch] epoch={epoch + 1}/{args.pretrain_epochs} "
                f"wm_loss={stats.world_model_loss:.4f} actor_loss={stats.actor_loss:.4f} "
                f"value_loss={stats.value_loss:.4f} grad_steps={scratch_trainer.gradient_steps}",
                flush=True,
            )
    baseline_success = evaluate(scratch_env, scratch_policy, episodes=args.eval_episodes)

    for src_dim in source_dims:
        src_env, src_wm, _, src_trainer = make_trainer(dim=src_dim, max_steps=args.max_steps)
        src_ckpt = checkpoint_dir / f"source_dim{src_dim}.pt"
        if args.resume and src_ckpt.exists():
            src_trainer.load_checkpoint(src_ckpt)
            print(f"[transfer] source {src_dim}D resumed at epoch={src_trainer.train_epochs}")
        else:
            bootstrap_if_empty(src_trainer, args.max_steps)

        for epoch in range(src_trainer.train_epochs, args.pretrain_epochs):
            stats = src_trainer.train_epoch(collect_episodes=2, wm_steps=8, policy_episodes=1)
            src_trainer.save_checkpoint(
                src_ckpt,
                extra={"stage": f"source_{src_dim}", "epoch": epoch + 1, "run_id": run_id, "wm_loss": stats.world_model_loss},
            )
            rotate_checkpoint(
                latest_path=src_ckpt,
                epoch=epoch + 1,
                metric=float(stats.world_model_loss),
                save_every=args.save_every,
                keep_last=args.keep_last,
            )
            if args.heartbeat_every > 0 and ((epoch + 1) % args.heartbeat_every == 0):
                print(
                    f"[transfer][source] src_dim={src_dim} epoch={epoch + 1}/{args.pretrain_epochs} "
                    f"wm_loss={stats.world_model_loss:.4f} actor_loss={stats.actor_loss:.4f} "
                    f"value_loss={stats.value_loss:.4f} grad_steps={src_trainer.gradient_steps}",
                    flush=True,
                )

        tgt_env, tgt_wm, tgt_policy, tgt_trainer = make_trainer(dim=target_dim, max_steps=args.max_steps)
        tgt_ckpt = checkpoint_dir / f"transfer_{src_dim}_to_{target_dim}.pt"

        transfer_stats = {"transferred": 0, "skipped": 0}
        if args.resume and tgt_ckpt.exists():
            tgt_trainer.load_checkpoint(tgt_ckpt)
            print(f"[transfer] target {src_dim}->{target_dim} resumed at epoch={tgt_trainer.train_epochs}")
        else:
            transfer = DimensionTransfer(source_dim=src_dim, target_dim=target_dim, transfer_strategy="hidden_only")
            tgt_wm, transfer_stats = transfer.transfer(src_wm, tgt_wm)
            tgt_trainer.world_model.load_state_dict(tgt_wm.state_dict())
            bootstrap_if_empty(tgt_trainer, args.max_steps)

        for epoch in range(tgt_trainer.train_epochs, args.finetune_epochs):
            stats = tgt_trainer.train_epoch(collect_episodes=2, wm_steps=6, policy_episodes=1)
            tgt_trainer.save_checkpoint(
                tgt_ckpt,
                extra={
                    "stage": f"transfer_{src_dim}_to_{target_dim}",
                    "epoch": epoch + 1,
                    "run_id": run_id,
                    "transfer_stats": transfer_stats,
                    "wm_loss": stats.world_model_loss,
                },
            )
            rotate_checkpoint(
                latest_path=tgt_ckpt,
                epoch=epoch + 1,
                metric=float(stats.world_model_loss),
                save_every=args.save_every,
                keep_last=args.keep_last,
            )
            if args.heartbeat_every > 0 and ((epoch + 1) % args.heartbeat_every == 0):
                print(
                    f"[transfer][finetune] src_dim={src_dim}->tgt_dim={target_dim} "
                    f"epoch={epoch + 1}/{args.finetune_epochs} wm_loss={stats.world_model_loss:.4f} "
                    f"actor_loss={stats.actor_loss:.4f} value_loss={stats.value_loss:.4f} "
                    f"grad_steps={tgt_trainer.gradient_steps}",
                    flush=True,
                )

        transfer_success = evaluate(tgt_env, tgt_policy, episodes=args.eval_episodes)
        results_by_src[src_dim] = {
            "source_dim": src_dim,
            "target_dim": target_dim,
            "baseline_success": baseline_success,
            "transfer_success": transfer_success,
            "transfer_stats": transfer_stats,
            "trained_epochs": tgt_trainer.train_epochs,
            "gradient_steps": tgt_trainer.gradient_steps,
        }
        progress["results"] = [results_by_src[d] for d in sorted(results_by_src.keys())]
        progress["meta"] = {
            "pretrain_epochs": args.pretrain_epochs,
            "finetune_epochs": args.finetune_epochs,
            "max_steps": args.max_steps,
            "eval_episodes": args.eval_episodes,
            "target_dim": target_dim,
            "save_every": args.save_every,
            "keep_last": args.keep_last,
        }
        save_json(progress_path, progress)
        print(f"[transfer] {src_dim}D -> {target_dim}D success={transfer_success:.3f}")

    final_payload = {
        "experiment": exp_name,
        "run_id": run_id,
        "target_dim": target_dim,
        "results": [results_by_src[d] for d in sorted(results_by_src.keys())],
        "meta": progress["meta"],
    }
    save_json(result_dir / "transfer.json", final_payload)
    save_json(Path("results") / "transfer.json", final_payload)
    print(f"Saved {result_dir / 'transfer.json'}")
    print("Saved results/transfer.json")


if __name__ == "__main__":
    run()
