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


def resolve_run_id(exp_name: str, run_id: str | None, resume: bool) -> str:
    if run_id:
        return run_id
    if resume:
        latest = find_latest_run(exp_name)
        if latest is not None:
            return latest
    return default_run_id()


def parse_args():
    parser = argparse.ArgumentParser(description="Model ablation with checkpoint resume support.")
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=80)
    parser.add_argument("--eval-episodes", type=int, default=20)
    parser.add_argument("--save-every", type=int, default=5, help="Archive checkpoint every N epochs (0 disables).")
    parser.add_argument("--keep-last", type=int, default=5, help="How many archive checkpoints to keep.")
    return parser.parse_args()


def run():
    args = parse_args()
    exp_name = "ablation"
    run_id = resolve_run_id(exp_name, args.run_id, args.resume)
    result_dir, checkpoint_dir = prepare_run_dirs(exp_name, run_id)
    progress_path = result_dir / "progress.json"

    progress = load_json(
        progress_path,
        default={"experiment": exp_name, "run_id": run_id, "results": [], "meta": {}},
    )
    results_by_model = {item["model"]: item for item in progress.get("results", [])}

    env = PushBallNDEnv(dim=4, difficulty="easy", max_steps=args.max_steps)
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

    for name, factory in configs:
        model = factory()
        policy = PolicyNetwork(state_dim=env.state_dim, action_dim=env.action_dim, hidden_dim=128)
        trainer = DreamTrainer(env=env, world_model=model, policy=policy, buffer=ReplayBuffer(capacity=20_000))
        ckpt_path = checkpoint_dir / f"{name}_latest.pt"

        if args.resume and ckpt_path.exists():
            trainer.load_checkpoint(ckpt_path)
            print(f"[ablation] model={name} resumed at epoch={trainer.train_epochs}")
        elif len(trainer.buffer.episodes) == 0:
            for _ in range(4):
                trainer.collect_episode(max_steps=args.max_steps, random_policy=True)

        for epoch in range(trainer.train_epochs, args.epochs):
            stats = trainer.train_epoch(collect_episodes=2, wm_steps=6, policy_episodes=1)
            trainer.save_checkpoint(
                ckpt_path,
                extra={
                    "model": name,
                    "epoch": epoch + 1,
                    "run_id": run_id,
                    "wm_loss": stats.world_model_loss,
                    "actor_loss": stats.actor_loss,
                    "value_loss": stats.value_loss,
                },
            )
            rotate_checkpoint(
                latest_path=ckpt_path,
                epoch=epoch + 1,
                metric=float(stats.world_model_loss),
                save_every=args.save_every,
                keep_last=args.keep_last,
            )

        success = evaluate(env, policy, episodes=args.eval_episodes)
        results_by_model[name] = {
            "model": name,
            "success_rate": success,
            "trained_epochs": trainer.train_epochs,
            "gradient_steps": trainer.gradient_steps,
        }
        progress["results"] = [results_by_model[key] for key in sorted(results_by_model.keys())]
        progress["meta"] = {
            "epochs": args.epochs,
            "max_steps": args.max_steps,
            "eval_episodes": args.eval_episodes,
            "dim": 4,
            "save_every": args.save_every,
            "keep_last": args.keep_last,
        }
        save_json(progress_path, progress)
        print(f"[ablation] model={name} success={success:.3f}")

    final_payload = {
        "experiment": exp_name,
        "run_id": run_id,
        "results": [results_by_model[key] for key in sorted(results_by_model.keys())],
        "meta": progress["meta"],
    }
    save_json(result_dir / "ablation.json", final_payload)
    save_json(Path("results") / "ablation.json", final_payload)
    print(f"Saved {result_dir / 'ablation.json'}")
    print("Saved results/ablation.json")


if __name__ == "__main__":
    run()
