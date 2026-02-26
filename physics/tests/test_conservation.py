import torch

from physics.body import Body4D
from physics.engine import Physics4D


def _total_momentum(bodies):
    return sum((b.mass * b.velocity for b in bodies), torch.zeros_like(bodies[0].velocity))


def test_momentum_conservation_elastic_collision():
    physics = Physics4D(dim=4, gravity_strength=0.0, boundary=1_000.0, dt=0.01, restitution=1.0)
    body_a = Body4D(
        position=torch.tensor([-0.6, 0.0, 0.0, 0.0]),
        velocity=torch.tensor([1.0, 0.0, 0.0, 0.0]),
        mass=1.0,
        radius=0.2,
    )
    body_b = Body4D(
        position=torch.tensor([0.6, 0.0, 0.0, 0.0]),
        velocity=torch.tensor([-0.5, 0.0, 0.0, 0.0]),
        mass=2.0,
        radius=0.2,
    )
    bodies = [body_a, body_b]
    p_before = _total_momentum(bodies)

    for _ in range(500):
        physics.step(bodies)

    p_after = _total_momentum(bodies)
    error = torch.linalg.norm(p_before - p_after).item()
    assert error < 1e-4

