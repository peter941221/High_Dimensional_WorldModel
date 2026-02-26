import torch

from envs.push_ball import PushBallNDEnv


def _heuristic_action(state: torch.Tensor, dim: int) -> torch.Tensor:
    agent_pos = state[0:dim]
    ball_pos = state[2 * dim : 3 * dim]
    target_pos = state[4 * dim : 5 * dim]

    to_ball = ball_pos - agent_pos
    to_target = target_pos - ball_pos
    if torch.linalg.norm(to_ball).item() > 0.8:
        action = to_ball
    else:
        action = 0.25 * to_ball + 0.75 * to_target
    return action.clamp(-1.0, 1.0)


def _success_rate(env: PushBallNDEnv, episodes: int, policy) -> float:
    successes = 0
    for ep in range(episodes):
        state = env.reset(seed=ep)
        done = False
        while not done:
            action = policy(state, env.dim)
            state, _, done, info = env.step(action)
        if info["success"]:
            successes += 1
    return successes / max(episodes, 1)


def test_reproducibility_with_same_seed_and_actions():
    env_a = PushBallNDEnv(dim=4, difficulty="easy")
    env_b = PushBallNDEnv(dim=4, difficulty="easy")
    state_a = env_a.reset(seed=7)
    state_b = env_b.reset(seed=7)
    assert torch.allclose(state_a, state_b)

    actions = [torch.randn(4).clamp(-1, 1) for _ in range(30)]
    for action in actions:
        state_a, reward_a, done_a, _ = env_a.step(action)
        state_b, reward_b, done_b, _ = env_b.step(action)
        assert torch.allclose(state_a, state_b, atol=1e-6)
        assert abs(reward_a - reward_b) < 1e-6
        assert done_a == done_b


def test_task_is_not_trivial_but_solvable_on_easy():
    env_random = PushBallNDEnv(dim=4, difficulty="easy")
    random_rate = _success_rate(
        env_random,
        episodes=60,
        policy=lambda _s, dim: torch.randn(dim).clamp(-1, 1),
    )

    env_heuristic = PushBallNDEnv(dim=4, difficulty="easy")
    heuristic_rate = _success_rate(env_heuristic, episodes=60, policy=_heuristic_action)

    assert random_rate < 0.2
    assert heuristic_rate > 0.1

