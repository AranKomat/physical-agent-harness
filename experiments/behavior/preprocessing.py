"""Source-faithful controller preprocessing audit; never changes sent actions."""

import numpy as np

from .observations import array


def verify_native_preprocessing(robot, actions):
    """Compare official preprocessing only; return original raw actions for execution."""
    import torch
    from omnigibson.controllers import controller_view
    from omnigibson.controllers.controller_view import ControllerView

    # The backend object is the same one used by ControllerView.update_goal.
    cb = controller_view.cb
    if actions.ndim != 2 or actions.shape[1] != 23 or not np.isfinite(actions).all():
        raise ValueError("Invalid raw native chunk")
    proof = {"raw_actions_sent_unmodified": True, "violations": [], "controllers": []}
    offset = 0
    for name, (group_key, _) in robot._controllers.items():
        controller = ControllerView._controller_groups[group_key]
        width = ControllerView.get_command_dim(group_key)
        limits = ControllerView.get_command_input_limits(group_key)
        low, high = (
            (np.full(width, -np.inf), np.full(width, np.inf))
            if limits is None
            else (array(limits[0]), array(limits[1]))
        )
        for step, local_channel in np.argwhere(
            (actions[:, offset : offset + width] < low)
            | (actions[:, offset : offset + width] > high)
        ):
            channel = offset + local_channel
            value = float(actions[step, channel])
            proof["violations"].append(
                {
                    "step": int(step),
                    "channel": int(channel),
                    "group": name,
                    "value": value,
                    "low": float(low[local_channel]),
                    "high": float(high[local_channel]),
                    "overshoot": float(
                        max(low[local_channel] - value, value - high[local_channel])
                    ),
                }
            )
        entry = {
            "name": name,
            "class": type(controller).__name__,
            "offset": offset,
            "width": width,
            "processed_commands": [],
            "declared_input_limits": None if limits is None else [low.tolist(), high.tolist()],
        }
        for action in actions:
            raw = action[offset : offset + width]
            # This bounded vector is only an equivalence witness, never sent to physics.
            witness = np.clip(raw, low, high)
            processed_raw = array(
                cb.to_torch(
                    controller._preprocess_command(cb.from_torch(torch.from_numpy(raw.copy())))
                )
            )
            processed_witness = array(
                cb.to_torch(
                    controller._preprocess_command(
                        cb.from_torch(torch.from_numpy(witness.astype(np.float32)))
                    )
                )
            )
            np.testing.assert_array_equal(processed_raw, processed_witness)
            entry["processed_commands"].append(processed_raw.tolist())
        proof["controllers"].append(entry)
        offset += width
    if offset != 23:
        raise ValueError("Unexpected native controller layout")
    proof["official_preprocess_equivalence_verified"] = True
    return proof
