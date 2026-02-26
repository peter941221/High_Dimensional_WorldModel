from __future__ import annotations

from typing import Iterable

import torch

from physics.body import Body4D


class Physics4D:
    """Deterministic N-dimensional rigid-body simulator with elastic collisions."""

    def __init__(
        self,
        dim: int,
        gravity_axis: int = 1,
        gravity_strength: float = -9.8,
        dt: float = 0.01,
        boundary: float = 10.0,
        restitution: float = 1.0,
        device: str | None = None,
    ):
        self.dim = int(dim)
        self.gravity_axis = int(gravity_axis)
        self.gravity_strength = float(gravity_strength)
        self.dt = float(dt)
        self.boundary = float(boundary)
        self.restitution = float(restitution)
        self.device = device or "cpu"

        if self.dim < 2:
            raise ValueError("dim must be >= 2")
        if not (0 <= self.gravity_axis < self.dim):
            raise ValueError("gravity_axis must be in [0, dim)")
        if self.dt <= 0:
            raise ValueError("dt must be > 0")
        if self.boundary <= 0:
            raise ValueError("boundary must be > 0")

    def _validate_body(self, body: Body4D) -> None:
        if body.position.shape != (self.dim,):
            raise ValueError(f"position must be shape ({self.dim},)")
        if body.velocity.shape != (self.dim,):
            raise ValueError(f"velocity must be shape ({self.dim},)")
        if body.mass <= 0:
            raise ValueError("mass must be > 0")
        if body.radius <= 0:
            raise ValueError("radius must be > 0")

    def _gravity(self) -> torch.Tensor:
        g = torch.zeros(self.dim, dtype=torch.float32, device=self.device)
        g[self.gravity_axis] = self.gravity_strength
        return g

    def step(
        self,
        bodies: Iterable[Body4D],
        external_forces: Iterable[torch.Tensor] | None = None,
    ) -> None:
        bodies = list(bodies)
        if not bodies:
            return

        for body in bodies:
            self._validate_body(body)
            body.position = body.position.to(dtype=torch.float32, device=self.device)
            body.velocity = body.velocity.to(dtype=torch.float32, device=self.device)

        if external_forces is None:
            external_forces = [
                torch.zeros(self.dim, dtype=torch.float32, device=self.device)
                for _ in bodies
            ]
        else:
            external_forces = [
                force.to(dtype=torch.float32, device=self.device) for force in external_forces
            ]
            if len(external_forces) != len(bodies):
                raise ValueError("external_forces length must match bodies length")

        gravity = self._gravity()
        dt = self.dt
        for body, ext in zip(bodies, external_forces):
            acceleration = gravity + ext / body.mass
            body.velocity = body.velocity + acceleration * dt
            body.position = body.position + body.velocity * dt

        self._resolve_collisions(bodies)
        self._resolve_boundaries(bodies)

    def _resolve_boundaries(self, bodies: list[Body4D]) -> None:
        for body in bodies:
            for axis in range(self.dim):
                lower = -self.boundary + body.radius
                upper = self.boundary - body.radius
                if body.position[axis] < lower:
                    body.position[axis] = lower
                    if body.velocity[axis] < 0:
                        body.velocity[axis] = -body.velocity[axis] * self.restitution
                elif body.position[axis] > upper:
                    body.position[axis] = upper
                    if body.velocity[axis] > 0:
                        body.velocity[axis] = -body.velocity[axis] * self.restitution

    def _resolve_collisions(self, bodies: list[Body4D]) -> None:
        eps = 1e-8
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                a = bodies[i]
                b = bodies[j]
                delta = b.position - a.position
                dist = torch.linalg.norm(delta).item()
                min_dist = a.radius + b.radius

                if dist >= min_dist:
                    continue

                if dist <= eps:
                    normal = torch.zeros(self.dim, dtype=torch.float32, device=self.device)
                    normal[0] = 1.0
                    dist = eps
                else:
                    normal = delta / dist

                overlap = min_dist - dist
                correction = normal * (overlap / 2.0)
                a.position = a.position - correction
                b.position = b.position + correction

                relative_velocity = b.velocity - a.velocity
                vn = torch.dot(relative_velocity, normal).item()
                if vn >= 0:
                    continue

                inv_mass_sum = (1.0 / a.mass) + (1.0 / b.mass)
                impulse = -(1.0 + self.restitution) * vn / inv_mass_sum
                impulse_vec = impulse * normal
                a.velocity = a.velocity - impulse_vec / a.mass
                b.velocity = b.velocity + impulse_vec / b.mass

    def get_state(self, bodies: Iterable[Body4D]) -> torch.Tensor:
        bodies = list(bodies)
        if not bodies:
            return torch.zeros(0, dtype=torch.float32, device=self.device)

        state_parts = []
        for body in bodies:
            self._validate_body(body)
            state_parts.append(body.position)
            state_parts.append(body.velocity)
        return torch.cat(state_parts, dim=0).to(dtype=torch.float32, device=self.device)

    def get_energy(self, bodies: Iterable[Body4D]) -> dict:
        bodies = list(bodies)
        if not bodies:
            return {"kinetic": 0.0, "potential": 0.0, "total": 0.0}

        kinetic = 0.0
        potential = 0.0
        g_mag = -self.gravity_strength

        for body in bodies:
            self._validate_body(body)
            kinetic += 0.5 * body.mass * float(torch.dot(body.velocity, body.velocity).item())
            potential += body.mass * g_mag * float(body.position[self.gravity_axis].item())

        total = kinetic + potential
        return {"kinetic": kinetic, "potential": potential, "total": total}
