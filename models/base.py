class BaseWorldModel:
    """Base interface for world models."""

    def forward(self, *args, **kwargs):
        raise NotImplementedError
