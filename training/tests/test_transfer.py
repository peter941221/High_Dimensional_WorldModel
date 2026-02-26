import torch
import torch.nn.functional as F

from models.mlp_world_model import MLPWorldModel
from training.transfer import DimensionTransfer


def test_transfer_forward_runs_after_hidden_only_copy():
    source = MLPWorldModel(state_dim=20, action_dim=4, hidden_dim=64)
    target = MLPWorldModel(state_dim=15, action_dim=3, hidden_dim=64)
    transfer = DimensionTransfer(source_dim=4, target_dim=3, transfer_strategy="hidden_only")
    target, stats = transfer.transfer(source, target)

    s = torch.randn(5, 15)
    a = torch.randn(5, 3)
    next_s, reward = target(s, a)
    assert next_s.shape == (5, 15)
    assert reward.shape == (5, 1)
    assert stats["transferred"] > 0


def test_truncate_strategy_transfers_with_shape_mismatch():
    source = MLPWorldModel(state_dim=20, action_dim=4, hidden_dim=64)
    target = MLPWorldModel(state_dim=15, action_dim=3, hidden_dim=64)
    transfer = DimensionTransfer(source_dim=4, target_dim=3, transfer_strategy="truncate")
    target, stats = transfer.transfer(source, target)
    assert stats["transferred"] >= stats["skipped"]


def test_transferred_model_is_trainable():
    source = MLPWorldModel(state_dim=20, action_dim=4, hidden_dim=64)
    target = MLPWorldModel(state_dim=15, action_dim=3, hidden_dim=64)
    target, _ = DimensionTransfer(4, 3, "hidden_only").transfer(source, target)

    optim = torch.optim.Adam(target.parameters(), lr=1e-3)
    states = torch.randn(32, 15)
    actions = torch.randn(32, 3)
    y_state = torch.randn(32, 15)
    y_reward = torch.randn(32, 1)

    for _ in range(10):
        pred_s, pred_r = target(states, actions)
        loss = F.mse_loss(pred_s, y_state) + F.mse_loss(pred_r, y_reward)
        optim.zero_grad()
        loss.backward()
        optim.step()

    final_loss = float(loss.item())
    assert final_loss > 0.0

