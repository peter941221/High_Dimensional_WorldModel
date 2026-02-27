from __future__ import annotations

import torch


# Tuned controller coefficients (searched on easy 3D, validated across 2-6D easy).
FAR_THRESHOLD = 1.12
FAR_TO_BALL_GAIN = 1.65
FAR_TO_TARGET_GAIN = -0.08
FAR_AGENT_VEL_DAMP = 0.66

NEAR_TO_BALL_GAIN = 0.05
NEAR_TO_TARGET_GAIN = 2.39
NEAR_AGENT_VEL_DAMP = 0.66
NEAR_BALL_VEL_DAMP = 0.67


def guided_push_action(state: torch.Tensor, dim: int) -> torch.Tensor:
    """Single-state guidance policy used for evaluation and trajectory collection."""
    s = torch.as_tensor(state, dtype=torch.float32)
    agent_pos = s[0:dim]
    agent_vel = s[dim : 2 * dim]
    ball_pos = s[2 * dim : 3 * dim]
    ball_vel = s[3 * dim : 4 * dim]
    target_pos = s[4 * dim : 5 * dim]

    to_ball = ball_pos - agent_pos
    to_target = target_pos - ball_pos
    if torch.linalg.norm(to_ball).item() > FAR_THRESHOLD:
        action = (
            FAR_TO_BALL_GAIN * to_ball
            + FAR_TO_TARGET_GAIN * to_target
            - FAR_AGENT_VEL_DAMP * agent_vel
        )
    else:
        action = (
            NEAR_TO_BALL_GAIN * to_ball
            + NEAR_TO_TARGET_GAIN * to_target
            - NEAR_AGENT_VEL_DAMP * agent_vel
            - NEAR_BALL_VEL_DAMP * ball_vel
        )
    return action.clamp(-1.0, 1.0)


def guided_push_action_batch(states: torch.Tensor, dim: int) -> torch.Tensor:
    """Batch version of guided_push_action for training targets."""
    agent_pos = states[:, 0:dim]
    agent_vel = states[:, dim : 2 * dim]
    ball_pos = states[:, 2 * dim : 3 * dim]
    ball_vel = states[:, 3 * dim : 4 * dim]
    target_pos = states[:, 4 * dim : 5 * dim]

    to_ball = ball_pos - agent_pos
    to_target = target_pos - ball_pos
    far = (torch.linalg.norm(to_ball, dim=-1, keepdim=True) > FAR_THRESHOLD).float()

    far_action = (
        FAR_TO_BALL_GAIN * to_ball
        + FAR_TO_TARGET_GAIN * to_target
        - FAR_AGENT_VEL_DAMP * agent_vel
    )
    near_action = (
        NEAR_TO_BALL_GAIN * to_ball
        + NEAR_TO_TARGET_GAIN * to_target
        - NEAR_AGENT_VEL_DAMP * agent_vel
        - NEAR_BALL_VEL_DAMP * ball_vel
    )
    return (far * far_action + (1.0 - far) * near_action).clamp(-1.0, 1.0)

