import torch

from models.physics_residual_world_model import PhysicsResidualWorldModel


def _zero_residual(model: PhysicsResidualWorldModel):
    for p in model.residual_net.parameters():
        p.data.zero_()
    model.state_residual_head.weight.data.zero_()
    model.state_residual_head.bias.data.zero_()
    model.reward_residual_head.weight.data.zero_()
    model.reward_residual_head.bias.data.zero_()


def test_physics_residual_matches_prior_when_residual_is_zero():
    dim = 4
    model = PhysicsResidualWorldModel(state_dim=5 * dim, action_dim=dim, hidden_dim=32)
    _zero_residual(model)

    state = torch.randn(3, 5 * dim)
    action = torch.randn(3, dim).clamp(-1, 1)

    with torch.no_grad():
        prior_state, prior_reward = model._physics_prior(state, action)
        pred_state, pred_reward = model(state, action)
    assert torch.allclose(pred_state, prior_state)
    assert torch.allclose(pred_reward, prior_reward)


def test_physics_residual_rejects_invalid_dim_relation():
    try:
        PhysicsResidualWorldModel(state_dim=19, action_dim=4, hidden_dim=32)
    except ValueError as e:
        assert "state_dim == 5 * action_dim" in str(e)
        return
    raise AssertionError("Expected ValueError for invalid state/action dimensions")

