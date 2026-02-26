import torch

from physics.body import Body4D
from physics.engine import Physics4D


def _rollout(seed: int):
    torch.manual_seed(seed)
    dim = 3
    physics = Physics4D(dim=dim, gravity_strength=-9.8, dt=0.01, boundary=50.0, restitution=0.95)
    bodies = [
        Body4D(position=torch.randn(dim), velocity=torch.randn(dim), mass=1.0 + i * 0.5, radius=0.2)
        for i in range(3)
    ]
    for _ in range(200):
        forces = [torch.randn(dim) * 0.1 for _ in bodies]
        physics.step(bodies, forces)
    return [b.clone() for b in bodies]


def test_determinism_same_seed_same_trajectory():
    a = _rollout(42)
    b = _rollout(42)
    for ba, bb in zip(a, b):
        assert torch.allclose(ba.position, bb.position, atol=1e-6)
        assert torch.allclose(ba.velocity, bb.velocity, atol=1e-6)

