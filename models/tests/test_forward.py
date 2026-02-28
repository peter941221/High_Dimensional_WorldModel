import torch

from models.gru_world_model import GRUWorldModel
from models.mlp_world_model import MLPWorldModel
from models.physics_residual_world_model import PhysicsResidualWorldModel
from models.rssm_world_model import RSSMWorldModel


def test_forward_shapes_for_all_models():
    for dim in [2, 4, 8]:
        state_dim = 5 * dim
        action_dim = dim
        batch = 16

        state = torch.randn(batch, state_dim)
        action = torch.randn(batch, action_dim)

        mlp = MLPWorldModel(state_dim, action_dim, hidden_dim=128)
        pred_s, pred_r = mlp(state, action)
        assert pred_s.shape == (batch, state_dim)
        assert pred_r.shape == (batch, 1)

        phys_res = PhysicsResidualWorldModel(state_dim, action_dim, hidden_dim=128)
        pred_s, pred_r = phys_res(state, action)
        assert pred_s.shape == (batch, state_dim)
        assert pred_r.shape == (batch, 1)

        gru = GRUWorldModel(state_dim, action_dim, hidden_dim=128)
        hidden = gru.init_hidden(batch_size=batch)
        pred_s, pred_r, hidden = gru(state, action, hidden)
        assert pred_s.shape == (batch, state_dim)
        assert pred_r.shape == (batch, 1)
        assert hidden.shape == (batch, 128)

        rssm = RSSMWorldModel(state_dim, action_dim, det_dim=96, stoch_dim=24, hidden_dim=96)
        hidden = rssm.init_hidden(batch_size=batch)
        pred_s, pred_r, hidden, kl = rssm(state, action, hidden)
        assert pred_s.shape == (batch, state_dim)
        assert pred_r.shape == (batch, 1)
        assert hidden[0].shape == (batch, 96)
        assert hidden[1].shape == (batch, 24)
        assert kl.shape == (batch, 1)


def test_gradients_flow_for_all_models():
    dim = 4
    state_dim = 5 * dim
    action_dim = dim
    batch = 8

    state = torch.randn(batch, state_dim)
    action = torch.randn(batch, action_dim)
    target_state = torch.randn(batch, state_dim)
    target_reward = torch.randn(batch, 1)

    models = [
        MLPWorldModel(state_dim, action_dim, hidden_dim=64),
        PhysicsResidualWorldModel(state_dim, action_dim, hidden_dim=64),
        GRUWorldModel(state_dim, action_dim, hidden_dim=64),
        RSSMWorldModel(state_dim, action_dim, det_dim=64, stoch_dim=16, hidden_dim=64),
    ]

    for model in models:
        model.zero_grad()
        if isinstance(model, (MLPWorldModel, PhysicsResidualWorldModel)):
            pred_s, pred_r = model(state, action)
            loss = ((pred_s - target_state) ** 2).mean() + ((pred_r - target_reward) ** 2).mean()
        elif isinstance(model, GRUWorldModel):
            pred_s, pred_r, _ = model(state, action, model.init_hidden(batch))
            loss = ((pred_s - target_state) ** 2).mean() + ((pred_r - target_reward) ** 2).mean()
        else:
            pred_s, pred_r, _, kl = model(state, action, model.init_hidden(batch))
            loss = ((pred_s - target_state) ** 2).mean() + ((pred_r - target_reward) ** 2).mean() + 0.1 * kl.mean()
        loss.backward()

        has_grad = [p.grad is not None for p in model.parameters() if p.requires_grad]
        assert all(has_grad)

