import torch

from envs.push_ball import PushBallNDEnv


def test_env_dimensionality_and_reward_ranges():
    for dim in [2, 3, 4, 5, 6, 8]:
        env = PushBallNDEnv(dim=dim, difficulty="easy")
        state = env.reset(seed=123)
        assert state.shape == (5 * dim,)

        rewards = []
        done_count = 0
        for _ in range(200):
            action = torch.randn(dim).clamp(-1, 1)
            state, reward, done, _ = env.step(action)
            assert state.shape == (5 * dim,)
            rewards.append(reward)
            if done:
                done_count += 1
                env.reset()

        assert min(rewards) > -100
        assert max(rewards) < 200
        assert done_count >= 0

