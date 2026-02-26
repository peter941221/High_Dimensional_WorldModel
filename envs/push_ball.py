class PushBallNDEnv:
    """Gym-like N-dimensional push-ball environment placeholder."""

    def __init__(self, dim: int = 4, max_steps: int = 200, difficulty: str = "easy"):
        self.dim = dim
        self.max_steps = max_steps
        self.difficulty = difficulty

    def reset(self, seed=None):
        raise NotImplementedError("Implement reset")

    def step(self, action):
        raise NotImplementedError("Implement step")

    @property
    def state_dim(self):
        return 5 * self.dim

    @property
    def action_dim(self):
        return self.dim
