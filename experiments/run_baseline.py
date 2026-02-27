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


def resolve_run_id(exp_name: str, run_id: str | None, resume: bool) -> str:
    if run_id:
        return run_id
    if resume:
        latest = find_latest_run(exp_name)
        if latest is not None:
            return latest
    return default_run_id()


def parse_args():
    parser = argparse.ArgumentParser(description="Baseline experiment with checkpoint resume support.")
    parser.add_argument("--run-id", type=str, default=None, help="Run identifier for persistent outputs.")
    parser.add_argument("--resume", action="store_true", help="Resume from existing run directory/checkpoints.")
    parser.add_argument("--epochs", type=int, default=5, help="Training epochs per dimension.")
    parser.add_argument("--max-steps", type=int, default=80, help="Max steps per episode.")
    parser.add_argument("--eval-episodes", type=int, default=20, help="Evaluation episodes per dimension.")
    parser.add_argument("--save-every", type=int, default=5, help="Archive checkpoint every N epochs (0 disables).")
    parser.add_argument("--keep-last", type=int, default=5, help="How many archive checkpoints to keep per worker.")
    parser.add_argument("--heartbeat-every", type=int, default=1, help="Print training heartbeat every N epochs.")
    return parser.parse_args()


def run():
    args = parse_args()
    exp_name = "baseline"
    run_id = resolve_run_id(exp_name, args.run_id, args.resume)
    result_dir, checkpoint_dir = prepare_run_dirs(exp_name, run_id)
    progress_path = result_dir / "progress.json"

    progress = load_json(
        progress_path,
        default={"experiment": exp_name, "run_id": run_id, "results": [], "meta": {}},
    )
    results_by_dim = {int(item["dim"]): item for item in progress.get("results", [])}

    dims = [2, 3, 4, 5, 6, 8]
    for dim in dims:
        env = PushBallNDEnv(dim=dim, difficulty="easy", max_steps=args.max_steps)
        world_model = GRUWorldModel(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
        policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
        trainer = DreamTrainer(
            env=env,
            world_model=world_model,
            policy=policy,
            buffer=ReplayBuffer(capacity=30_000),
        )

        dim_ckpt = checkpoint_dir / f"dim{dim}_latest.pt"
        if args.resume and dim_ckpt.exists():
            extra = trainer.load_checkpoint(dim_ckpt)
            print(f"[baseline] dim={dim} resumed from epoch={trainer.train_epochs} extra={extra}")
        else:
            for _ in range(4):
                trainer.collect_episode(max_steps=args.max_steps, random_policy=True)

        start_epoch = trainer.train_epochs
        for epoch in range(start_epoch, args.epochs):
            stats = trainer.train_epoch(collect_episodes=2, wm_steps=8, policy_episodes=1)
            trainer.save_checkpoint(
                dim_ckpt,
                extra={
                    "dim": dim,
                    "epoch": epoch + 1,
                    "wm_loss": stats.world_model_loss,
                    "actor_loss": stats.actor_loss,
                    "value_loss": stats.value_loss,
                    "run_id": run_id,
                },
            )
            rotate_checkpoint(
                latest_path=dim_ckpt,
                epoch=epoch + 1,
                metric=float(stats.world_model_loss),
                higher_is_better=False,
                save_every=args.save_every,
                keep_last=args.keep_last,
            )
            if args.heartbeat_every > 0 and ((epoch + 1) % args.heartbeat_every == 0):
                print(
                    f"[baseline][train] dim={dim} epoch={epoch + 1}/{args.epochs} "
                    f"wm_loss={stats.world_model_loss:.4f} actor_loss={stats.actor_loss:.4f} "
                    f"value_loss={stats.value_loss:.4f} grad_steps={trainer.gradient_steps}",
                    flush=True,
                )

        success_rate = evaluate_policy(env, policy, episodes=args.eval_episodes)
        result = {
            "dim": dim,
            "success_rate": success_rate,
            "trained_epochs": trainer.train_epochs,
            "gradient_steps": trainer.gradient_steps,
        }
        results_by_dim[dim] = result
        progress["results"] = [results_by_dim[d] for d in sorted(results_by_dim.keys())]
        progress["meta"] = {
            "epochs": args.epochs,
            "max_steps": args.max_steps,
            "eval_episodes": args.eval_episodes,
            "save_every": args.save_every,
            "keep_last": args.keep_last,
        }
        save_json(progress_path, progress)
        print(f"[baseline] dim={dim} success_rate={success_rate:.3f}")

    final_payload = {
        "experiment": exp_name,
        "run_id": run_id,
        "results": [results_by_dim[d] for d in sorted(results_by_dim.keys())],
        "meta": progress["meta"],
    }
    save_json(result_dir / "baseline.json", final_payload)
    save_json(Path("results") / "baseline.json", final_payload)
    print(f"Saved {result_dir / 'baseline.json'}")
    print("Saved results/baseline.json")


if __name__ == "__main__":
    run()
