import torch

from envs.high_fidelity_proxy import HiFiPushBallProxyEnv


def test_hifi_proxy_shapes_match_base_contract():
    env = HiFiPushBallProxyEnv(dim=4, difficulty="medium", fidelity_level="mild")
    s = env.reset(seed=123)
    assert s.shape == (env.state_dim,)

    for _ in range(12):
        a = torch.randn(env.action_dim).clamp(-1, 1)
        s, _, done, _ = env.step(a)
        assert s.shape == (env.state_dim,)
        if done:
            s = env.reset()
            assert s.shape == (env.state_dim,)


def test_hifi_proxy_is_reproducible_with_same_seed():
    env_a = HiFiPushBallProxyEnv(dim=3, difficulty="medium", fidelity_level="strong")
    env_b = HiFiPushBallProxyEnv(dim=3, difficulty="medium", fidelity_level="strong")

    s_a = env_a.reset(seed=7)
    s_b = env_b.reset(seed=7)
    assert torch.allclose(s_a, s_b)

    actions = [torch.randn(3).clamp(-1, 1) for _ in range(20)]
    for a in actions:
        ns_a, r_a, d_a, info_a = env_a.step(a)
        ns_b, r_b, d_b, info_b = env_b.step(a)
        assert torch.allclose(ns_a, ns_b)
        assert abs(float(r_a) - float(r_b)) < 1e-8
        assert bool(d_a) == bool(d_b)
        assert bool(info_a["success"]) == bool(info_b["success"])

