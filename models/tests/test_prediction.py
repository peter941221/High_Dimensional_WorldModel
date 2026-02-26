import torch
import torch.nn.functional as F

from models.gru_world_model import GRUWorldModel
from models.mlp_world_model import MLPWorldModel


def _synthetic_transition(states: torch.Tensor, actions: torch.Tensor):
    action_pad = F.pad(actions, (0, states.shape[-1] - actions.shape[-1]))
    next_states = 0.85 * states + 0.15 * action_pad
    rewards = -next_states.pow(2).mean(dim=-1, keepdim=True)
    return next_states, rewards


def test_single_step_prediction_learns_simple_dynamics():
    torch.manual_seed(0)
    state_dim = 20
    action_dim = 4
    model = MLPWorldModel(state_dim, action_dim, hidden_dim=128)
    optim = torch.optim.Adam(model.parameters(), lr=3e-3)

    states = torch.randn(512, state_dim)
    actions = torch.randn(512, action_dim).clamp(-1, 1)
    targets_s, targets_r = _synthetic_transition(states, actions)

    for _ in range(300):
        pred_s, pred_r = model(states, actions)
        loss = F.mse_loss(pred_s, targets_s) + F.mse_loss(pred_r, targets_r)
        optim.zero_grad()
        loss.backward()
        optim.step()

    with torch.no_grad():
        pred_s, _ = model(states, actions)
        mse = F.mse_loss(pred_s, targets_s).item()
    assert mse < 0.03


def test_rollout_error_does_not_explode_too_fast():
    torch.manual_seed(1)
    state_dim = 20
    action_dim = 4
    model = GRUWorldModel(state_dim, action_dim, hidden_dim=96)
    optim = torch.optim.Adam(model.parameters(), lr=3e-3)

    batch = 128
    horizon = 8
    states = torch.randn(batch, horizon + 1, state_dim)
    actions = torch.randn(batch, horizon, action_dim).clamp(-1, 1)
    for t in range(horizon):
        nxt, _ = _synthetic_transition(states[:, t], actions[:, t])
        states[:, t + 1] = nxt

    for _ in range(400):
        hidden = model.init_hidden(batch_size=batch)
        preds = []
        for t in range(horizon):
            pred_s, _, hidden = model(states[:, t], actions[:, t], hidden)
            preds.append(pred_s)
        pred = torch.stack(preds, dim=1)
        loss = F.mse_loss(pred, states[:, 1:])
        optim.zero_grad()
        loss.backward()
        optim.step()

    with torch.no_grad():
        hidden = model.init_hidden(batch_size=batch)
        pred_states = [states[:, 0]]
        for t in range(horizon):
            pred_s, _, hidden = model(pred_states[-1], actions[:, t], hidden)
            pred_states.append(pred_s)
        errors = [
            torch.linalg.norm(states[:, t] - pred_states[t], dim=-1).mean().item()
            for t in range(horizon + 1)
        ]
    single_step = errors[1] + 1e-8
    final_error = errors[-1]
    assert final_error / single_step < 5.0

