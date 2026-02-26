import torch

from physics.body import Body4D
from physics.engine import Physics4D


def test_free_fall_matches_analytic_solution():
    g = -9.8
    dim = 4
    dt = 0.001
    total_time = 1.0
    steps = int(total_time / dt)

    physics = Physics4D(dim=dim, gravity_axis=1, gravity_strength=g, dt=dt, boundary=1_000.0, restitution=1.0)
    body = Body4D(
        position=torch.zeros(dim),
        velocity=torch.zeros(dim),
        mass=1.0,
        radius=0.1,
    )

    for _ in range(steps):
        physics.step([body], external_forces=[torch.zeros(dim)])

    expected_y = 0.5 * g * total_time**2
    actual_y = body.position[1].item()
    relative_error = abs(actual_y - expected_y) / max(abs(expected_y), 1e-8)
    assert relative_error < 0.01

