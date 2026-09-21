"""Pinned R1Pro base commands with proprioceptive holds, not motion permission.

This codec is for empty-handed, settled classical base qualification only. It
does not modify any learned-policy actions and is not a payload hold controller.
Native configuration/parity must be checked separately before using its output.
"""

import math

import numpy as np

from physical_harness.hybrid_v0.classical import BodyTwist


def base_hold(proprio, twist: BodyTwist, *, gripper_ranges):
    p = np.asarray(proprio, dtype=float)
    if p.shape != (61,) or not np.isfinite(p).all():
        raise ValueError("Expected finite native 61D proprioception")
    if not isinstance(twist, BodyTwist):
        raise ValueError("Typed body-frame velocity required")
    if math.hypot(twist.vx, twist.vy) > .05 or abs(twist.wz) > .1:
        raise ValueError("Classical qualification velocity cap exceeded")
    limits = np.asarray(gripper_ranges, dtype=float)
    if (limits.shape != (2, 2) or not np.isfinite(limits).all()
            or np.any(limits[:, 1] <= limits[:, 0])):
        raise ValueError("Resolved smooth-gripper position ranges required")
    # Native base input [-1,1] maps to +/-0.75 m/s and +/-1 rad/s.
    action = np.empty(23, dtype=float)
    action[:3] = [twist.vx / .75, twist.vy / .75, twist.wz]
    action[3:7], action[7:14], action[15:22] = p[53:57], p[3:10], p[28:35]
    for index, feedback, (low, high) in zip((14, 22), (p[24:26], p[49:51]), limits):
        if abs(feedback[0] - feedback[1]) > .002:
            raise ValueError("Asymmetric fingers cannot be held with one scalar command")
        position = float(feedback.mean())
        if not low <= position <= high:
            raise ValueError("Gripper hold would require saturation")
        action[index] = 2 * (position - low) / (high - low) - 1
    return tuple(float(v) for v in action)


def settled(proprio):
    """Measured velocity check only; does not establish absence of a payload."""
    p = np.asarray(proprio, dtype=float)
    if p.shape != (61,) or not np.isfinite(p).all():
        raise ValueError("Expected finite native 61D proprioception")
    return bool(np.linalg.norm(p[:2]) <= .01 and abs(p[2]) <= .02
                and max(abs(p[10:17])) <= .03 and max(abs(p[35:42])) <= .03
                and max(abs(p[57:61])) <= .03
                and max(abs(p[26:28])) <= .005 and max(abs(p[51:53])) <= .005)
