from dataclasses import dataclass


@dataclass
class Body4D:
    """N-dimensional rigid body state."""

    position: object
    velocity: object
    mass: float = 1.0
    radius: float = 0.1
