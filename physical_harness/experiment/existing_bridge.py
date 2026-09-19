"""Adapt an existing legal BEHAVIOR sensor/policy driver without guessing action codecs."""
from __future__ import annotations

from collections.abc import Callable

from ..adapters.behavior import LegalObservation
from .media import image_geometry
from .native import CameraCapture, NativeBindings, Observation
from .validation import fields, integer


def from_existing_driver(*, name: str, episode: str, capture_legal: Callable,
                         read_rgb: Callable, run_skill: Callable, stop: Callable,
                         qualification_id: str, estimates=None, boxes=None, place=None,
                         coverage=None) -> NativeBindings:
    """Use the private driver's actual callable implementations.

    capture_legal returns a validated LegalObservation or the same strict envelope.
    Optional estimate/detection callbacks receive only that legal envelope, never
    a simulator object or scorer. read_rgb resolves opaque native artifacts.
    """
    def observe():
        value = capture_legal()
        env = value.to_envelope() if hasattr(value, "to_envelope") else value
        fields(env, {"schema_version", "episode_id", "observation_id", "sim_time", "rgb_refs",
                     "depth_refs", "proprioception", "camera_intrinsics", "camera_frames"},
               {"estimated_pose"})
        env = LegalObservation.from_envelope(env).to_envelope()
        if env["episode_id"] != episode or integer(env["schema_version"]) != 1:
            raise ValueError("Unsupported legal observation envelope")
        captures = []
        for camera, ref in env["rgb_refs"].items():
            data = read_rgb(ref)
            width, height, _ = image_geometry(data)
            calibration = env["camera_intrinsics"][camera]
            if width != calibration["width"] or height != calibration["height"]:
                raise ValueError("Native camera calibration dimensions do not match pixels")
            captures.append(CameraCapture(camera, data))
        location = place(env) if place else (None, None)
        return Observation(episode, env["observation_id"], env["sim_time"], tuple(captures),
                           tuple(estimates(env)) if estimates else (),
                           tuple(boxes(env)) if boxes else (), location[0], location[1],
                           tuple(coverage(env)) if coverage else (), env)

    return NativeBindings(name, observe, run_skill, stop, simulated=True,
                          qualification_id=qualification_id)


def driver_factory(episode: str) -> NativeBindings:
    """CLI factory: adapt an operator's existing private driver object.

    PHYSICAL_DRIVER_FACTORY=your_project.driver:create_driver
    create_driver(episode) returns name, qualification_id and the four required
    methods below. Optional estimate/crop/place/coverage callbacks stay in that
    private driver rather than guessing the policy or simulator's representation.
    """
    import os

    from .native_rpc import load_factory

    spec = os.environ.get("PHYSICAL_DRIVER_FACTORY")
    if not spec:
        raise ValueError("Set PHYSICAL_DRIVER_FACTORY to a reviewed module:factory")
    driver = load_factory(spec)(episode)
    required = ("capture_legal", "read_rgb", "run_skill", "stop")
    if any(not callable(getattr(driver, name, None)) for name in required):
        raise TypeError("Private driver requires capture_legal/read_rgb/run_skill/stop")
    if getattr(driver, "simulated", None) is not True:
        raise ValueError("Only simulator drivers are accepted by this factory")
    return from_existing_driver(
        name=driver.name, episode=episode, qualification_id=driver.qualification_id,
        capture_legal=driver.capture_legal, read_rgb=driver.read_rgb,
        run_skill=driver.run_skill, stop=driver.stop,
        estimates=getattr(driver, "estimates", None), boxes=getattr(driver, "boxes", None),
        place=getattr(driver, "place", None), coverage=getattr(driver, "coverage", None))
