import pytest
import torch

from envs.push_ball import PushBallNDEnv


def test_domain_randomization_disabled_matches_base_params():
    env = PushBallNDEnv(dim=4, difficulty="hard", domain_randomization=False, domain_rand_scale=0.3)
    _ = env.reset(seed=123)
    p = env.episode_params

    assert p["gravity_strength"] == env.config.gravity_strength
    assert p["wind_strength"] == env.config.wind_strength
    assert p["success_radius"] == env.config.success_radius
    assert p["agent_mass"] == 1.0
    assert p["ball_mass"] == 1.5
    assert p["push_radius"] == 1.2
    assert p["contact_gain"] == 0.2
    assert p["damping"] == 0.995


def test_domain_randomization_reproducible_with_same_seed():
    env_a = PushBallNDEnv(dim=4, difficulty="hard", domain_randomization=True, domain_rand_scale=0.2)
    env_b = PushBallNDEnv(dim=4, difficulty="hard", domain_randomization=True, domain_rand_scale=0.2)

    _ = env_a.reset(seed=7)
    _ = env_b.reset(seed=7)
    assert env_a.episode_params == env_b.episode_params


def test_domain_randomization_changes_across_different_seeds():
    env = PushBallNDEnv(dim=4, difficulty="hard", domain_randomization=True, domain_rand_scale=0.2)
    _ = env.reset(seed=7)
    p1 = env.episode_params
    _ = env.reset(seed=8)
    p2 = env.episode_params

    diffs = [abs(float(p1[k]) - float(p2[k])) for k in p1.keys()]
    assert any(d > 1e-8 for d in diffs)


def test_domain_randomized_env_step_keeps_shape_contract():
    env = PushBallNDEnv(dim=5, difficulty="medium", domain_randomization=True, domain_rand_scale=0.2)
    s = env.reset(seed=11)
    assert s.shape == (env.state_dim,)

    for _ in range(10):
        a = torch.randn(env.action_dim).clamp(-1, 1)
        s, _, done, _ = env.step(a)
        assert s.shape == (env.state_dim,)
        if done:
            s = env.reset()
            assert s.shape == (env.state_dim,)


def test_conservative_profile_keeps_mass_and_success_radius_fixed():
    env = PushBallNDEnv(
        dim=4,
        difficulty="hard",
        domain_randomization=True,
        domain_rand_scale=0.2,
        domain_rand_profile="conservative",
    )
    _ = env.reset(seed=9)
    p = env.episode_params
    assert p["agent_mass"] == 1.0
    assert p["ball_mass"] == 1.5
    assert p["success_radius"] == env.config.success_radius


def test_domain_rand_warmup_increases_effective_scale():
    env = PushBallNDEnv(
        dim=4,
        difficulty="hard",
        domain_randomization=True,
        domain_rand_scale=0.2,
        domain_rand_profile="full",
        domain_rand_warmup_episodes=10,
    )
    _ = env.reset(seed=5)
    s1 = env.episode_params["rand_scale_effective"]
    _ = env.reset()
    s2 = env.episode_params["rand_scale_effective"]
    assert 0.0 < s1 < s2 <= 0.2


def test_domain_rand_epoch_warmup_requires_epoch_progress():
    env = PushBallNDEnv(
        dim=4,
        difficulty="hard",
        domain_randomization=True,
        domain_rand_scale=0.2,
        domain_rand_profile="full",
        domain_rand_warmup_epochs=5,
    )
    _ = env.reset(seed=3)
    assert env.episode_params["rand_scale_effective"] == 0.0

    env.set_domain_rand_training_epoch(2)
    _ = env.reset()
    s2 = env.episode_params["rand_scale_effective"]
    assert 0.0 < s2 < 0.2

    env.set_domain_rand_training_epoch(5)
    _ = env.reset()
    assert env.episode_params["rand_scale_effective"] == pytest.approx(0.2)


def test_domain_rand_stage_multiplier_scales_effective_range():
    env = PushBallNDEnv(
        dim=4,
        difficulty="hard",
        domain_randomization=True,
        domain_rand_scale=0.2,
        domain_rand_profile="full",
    )
    env.set_domain_rand_stage_multiplier(0.5)
    _ = env.reset(seed=4)
    assert env.episode_params["rand_scale_effective"] == pytest.approx(0.1)
