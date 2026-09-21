"""Tiny numerical world for software tests only. NOT R1Pro, BEHAVIOR or a VLA.

All coordinates and gate judgments here are fixture scaffolding. No rendered
image, grasp physics, learned policy inference or semantic success is simulated.
"""
from __future__ import annotations

import math
from dataclasses import asdict

from ..contracts import SkillReceipt, SkillRequest
from .classical import BasePose, HolonomicNavigation, JointLimits, JointTransit, StepPort
from .contracts import (
    Check,
    GateReport,
    Phase,
    PolicyIdentity,
    Qualification,
    Regime,
    ResetReceipt,
    Route,
    Snapshot,
)
from .executor import Backend, HybridExecutor


class Clock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value


class FixtureWorld:
    def __init__(self):
        self.clock = Clock()
        self.steps = 0
        self.pose = BasePose(0.0, 0.0, 0.0)
        self.q = (0.0, 0.0)
        self.commands = []
        self.resets = []
        self.stop_count = 0
        self.stop_ok = True
        self.policy = PolicyIdentity("fixture-not-a-model", "fixture-v1", "fixture-digest",
                                     "fixture-observation", "fixture-native", "fixture-none",
                                     "fixture-one-tick", "fixture-instruction")
        self.command_mode = None

    def snapshot(self, deadline=None):
        t = self.steps/30
        envelope = {
            "schema_version": 1, "episode_id": "fixture", "observation_id": f"obs-{self.steps}",
            "sim_time": t, "rgb_refs": {"head": f"fixture-rgb-{self.steps}"},
            "depth_refs": {"head": f"fixture-depth-{self.steps}"},
            "proprioception": {"joint_positions": list(self.q)},
            "camera_frames": {"head": "head_optical"},
            "camera_intrinsics": {"head": {"width": 32, "height": 24, "fx": 30., "fy": 30.,
                                             "cx": 16., "cy": 12., "depth_scale_m": .001}},
            "estimated_pose": {"method": "proprio_odometry", "frame": "local_map", "camera": "head",
                               "transform": [[math.cos(self.pose.yaw), -math.sin(self.pose.yaw), 0, self.pose.x],
                                             [math.sin(self.pose.yaw), math.cos(self.pose.yaw), 0, self.pose.y],
                                             [0, 0, 1, 1], [0, 0, 0, 1]],
                               "evidence_ids": [f"obs-{self.steps}"], "confidence": 1.0},
        }
        return Snapshot.from_envelope(envelope, captured_wall=self.clock(),
                                      frame_epoch="fixture-origin", geometry_revision="fixture-empty")

    def encode_twist(self, command, snapshot):
        self.command_mode = "twist"
        return (command.vx, command.vy, command.wz) + (0.0,)*20

    def encode_joints(self, q, snapshot):
        self.command_mode = "joint"
        return q+(0.0,)*21

    def step(self, action, deadline):
        self.commands.append(action)
        if self.command_mode == "joint":
            self.q = action[:2]
        elif self.command_mode == "twist":
            c, s = math.cos(self.pose.yaw), math.sin(self.pose.yaw)
            vx, vy, wz = action[:3]
            self.pose = BasePose(self.pose.x+(c*vx-s*vy)/30,
                                 self.pose.y+(s*vx+c*vy)/30, self.pose.yaw+wz/30)
        self.steps += 1
        self.clock.value += .0001
        return self.snapshot()

    def stop(self, deadline):
        self.stop_count += 1
        return self.stop_ok

    def reset(self, req, deadline):
        self.resets.append(req)
        return ResetReceipt(req, True, True, True)

    def learned(self, req, start, deadline, cancelled):
        # Faithful-interface test double, not a learned model or contact success.
        self.command_mode = "policy"
        for _ in range(req.metadata["max_action_steps"]):
            if cancelled():
                raise InterruptedError()
            self.step((0.0,)*23, deadline)
        end = self.snapshot()
        return SkillReceipt(req.skill_id, "fixture-policy", "completed", start.sim_time, end.sim_time,
                            policy_calls=1, chunks_generated=1,
                            action_steps_executed=req.metadata["max_action_steps"],
                            metadata={"episode_id": "fixture", "execution_epoch": req.execution_epoch,
                                      "stop_acknowledged": True})

    def guard(self, phase, when, snapshot, deadline):
        return GateReport(phase.id, when, snapshot.fingerprint,
                          tuple(Check(n, True, (snapshot.observation_id,), "Fixture-only truth")
                                for n in phase.required_checks(when)))

    def executor(self):
        port = StepPort(self.step, self.stop, lambda a: len(a) == 23, clock=self.clock)
        nav = HolonomicNavigation(port, pose=lambda s: self.pose,
                                  resolve=lambda r, s: (BasePose(.02, 0, 0),),
                                  encode=self.encode_twist, safe=lambda *a: True,
                                  tolerance_m=.005, linear_speed=.1)
        limits = JointLimits(("fixture-j1", "fixture-j2"), (-2., -2.), (2., 2.), (.5, .5), (1., 1.))
        stage = JointTransit(port, limits, joints=lambda s: self.q, target=lambda r, s: (.1, -.1),
                             encode=self.encode_joints, safe=lambda *a: True,
                             tracking_tolerance=(.05, .05), endpoint_tolerance=(.001, .001))
        phases = (Phase("navigate", Regime.NAVIGATE, "fixture navigate", ("target",), 100, 10),
                  Phase("stage", Regime.STAGE, "fixture stage", ("target",), 100, 10),
                  Phase("policy", Regime.POLICY, "fixture policy", ("target",), 8, 10, 1))
        backends = {}
        for regime, execute in ((Regime.NAVIGATE, nav), (Regime.STAGE, stage), (Regime.POLICY, self.learned)):
            qual = Qualification("fixture-"+regime.value, regime, ("fixture",),
                                  self.policy.fingerprint if regime == Regime.POLICY else None)
            backends[regime] = Backend(qual, execute, self.guard,
                                       (lambda: self.policy) if regime == Regime.POLICY else None,
                                       self.reset if regime == Regime.POLICY else None)
        return HybridExecutor(episode="fixture", routes={"demo": Route("C", phases)}, backends=backends,
                              observe=self.snapshot, stop=self.stop, policy=self.policy,
                              emit=lambda kind, value: None, allow_simulated_motion=True,
                              clock=self.clock)


def run_fixture():
    world = FixtureWorld()
    hybrid = world.executor()
    request = SkillRequest("demo-1", "hybrid", "fixture composite", ("target",),
                           max_wall_s=60, max_policy_chunks=1,
                           source_observation_id="obs-0",
                           metadata={"action_id": "demo", "max_action_steps": 208})
    receipt = hybrid.run_skill(request)
    return {"kind": "software-fixture-only", "native_benchmark_run": False,
            "policy_inference_performed": False, "receipt": asdict(receipt),
            "metrics": hybrid.metrics(), "events": hybrid.trace,
            "final_pose": asdict(world.pose), "final_joint_positions": world.q,
            "native_action_widths": sorted({len(a) for a in world.commands})}
