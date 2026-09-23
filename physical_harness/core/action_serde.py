"""Strict finite JSON boundary for a separate grasp-inference worker."""
from dataclasses import fields

from physical_harness.core.actions import Basis, Gripper, Intent, Parameters, Pose, Proposal, Verb
from physical_harness.perception.geometry import ObjectCloud


def _fields(value, cls):
    if type(value) is not dict or set(value) != {f.name for f in fields(cls)}:
        raise ValueError("Unexpected fields for "+cls.__name__)
    return dict(value)


def basis_from_dict(value):
    data = _fields(value, Basis)
    data["evidence_ids"] = tuple(data["evidence_ids"])
    return Basis(**data)


def pose_from_dict(value):
    data = _fields(value, Pose)
    data["matrix"] = tuple(data["matrix"])
    return Pose(**data)


def gripper_from_dict(value):
    data = _fields(value, Gripper)
    for key in ("joint_names", "open_positions", "closed_positions", "lower_limits", "upper_limits"):
        data[key] = tuple(data[key])
    data["grasp_to_tcp"] = pose_from_dict(data["grasp_to_tcp"])
    return Gripper(**data)


def cloud_from_dict(value):
    data = _fields(value, ObjectCloud)
    data["basis"] = basis_from_dict(data["basis"])
    data["points"] = tuple(tuple(p) for p in data["points"])
    data["evidence_ids"] = tuple(data["evidence_ids"])
    data["camera_origin"] = tuple(data["camera_origin"])
    return ObjectCloud(**data)


def proposal_from_dict(value):
    data = _fields(value, Proposal)
    data["basis"] = basis_from_dict(data["basis"])
    intent = _fields(data["intent"], Intent)
    intent["verb"] = Verb(intent["verb"])
    intent["constraints"] = tuple(intent["constraints"])
    data["intent"] = Intent(**intent)
    params = _fields(data["parameters"], Parameters)
    if params["pose"] is not None:
        params["pose"] = pose_from_dict(params["pose"])
    if params["direction"] is not None:
        params["direction"] = tuple(params["direction"])
    data["parameters"] = Parameters(**params)
    data["evidence_ids"] = tuple(data["evidence_ids"])
    return Proposal(**data)
