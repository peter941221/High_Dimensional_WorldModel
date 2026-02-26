from dataclasses import dataclass

import torch


@dataclass
class Body4D:
    """N-dimensional rigid body state."""

    position: torch.Tensor
    velocity: torch.Tensor
    mass: float = 1.0
    radius: float = 0.1

    def clone(self) -> "Body4D":
        """Create a detached copy used by deterministic tests."""
        return Body4D(
            position=self.position.clone(),
            velocity=self.velocity.clone(),
            mass=float(self.mass),
            radius=float(self.radius),
        )
