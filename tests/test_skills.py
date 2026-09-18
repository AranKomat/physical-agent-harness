from dataclasses import replace

from physical_harness.contracts import SkillRequest
from physical_harness.skills import (
    ChunkedMotorBackend,
    MotorObservation,
    PolicyChunk,
    SkillFeedback,
)


class Clock:
    t = 10.0

    def __call__(self):
        return self.t


class Controller:
    def __init__(self, clock):
        self.clock, self.steps, self.stopped = clock, 0, False
        self.ack = True

    def observe(self):
        return MotorObservation("ep", f"o{self.steps}", 0, self.steps / 30, self.clock())

    def validate_action(self, action):
        if len(action) != 1 or abs(action[0]) > 1:
            raise ValueError("Invalid fixture action")

    def step(self, action, deadline):
        self.steps += 1
        self.clock.t += 0.01
        return self.observe()

    def stop(self, resources):
        self.stopped = True
        return self.ack


class Policy:
    name = "fixture"

    def __init__(self):
        self.hook = None

    def infer(self, obs, instruction, deadline):
        reply = PolicyChunk(obs.episode_id, obs.observation_id, obs.execution_epoch, ((0.1,),) * 4)
        return self.hook(reply) if self.hook else reply


def setup(**kwargs):
    clock = Clock()
    controller, policy = Controller(clock), Policy()
    backend = ChunkedMotorBackend(
        "ep",
        policy,
        controller,
        lambda obs, request: SkillFeedback(
            complete=controller.steps >= 6, progress=controller.steps
        ),
        qualified=True,
        prefix_steps=2,
        clock=clock,
        **kwargs,
    )
    return backend, controller, policy, clock


def test_semantic_skill_spans_chunks():
    backend, controller, _, _ = setup()
    receipt = backend.run_skill(SkillRequest("s", "pick", "pick"))
    assert receipt.outcome == "completed"
    assert (receipt.policy_calls, receipt.chunks_generated, receipt.action_steps_executed) == (
        3,
        3,
        6,
    )
    assert controller.stopped and not backend.jobs.owners


def test_stale_reply_never_executes():
    backend, controller, policy, _ = setup()
    policy.hook = lambda reply: replace(reply, observation_id="old")
    receipt = backend.run_skill(SkillRequest("s", "pick", "pick"))
    assert receipt.outcome == "failed" and controller.steps == 0


def test_timeout_after_inference_never_executes():
    backend, controller, policy, clock = setup()

    def late(reply):
        clock.t += 50
        return reply

    policy.hook = late
    receipt = backend.run_skill(SkillRequest("s", "pick", "pick", max_wall_s=1))
    assert receipt.outcome == "timeout" and controller.steps == 0


def test_cancel_after_inference_never_executes():
    backend, controller, policy, _ = setup()

    def cancel(reply):
        backend.cancel()
        return reply

    policy.hook = cancel
    receipt = backend.run_skill(SkillRequest("s", "pick", "pick"))
    assert receipt.outcome == "cancelled" and controller.steps == 0


def test_unknown_stop_retains_ownership():
    backend, controller, _, _ = setup()
    controller.ack = False
    receipt = backend.run_skill(SkillRequest("s", "pick", "pick"))
    assert receipt.failure_reason == "stop_unacknowledged" and backend.jobs.owners
    second = backend.run_skill(SkillRequest("s2", "pick", "pick"))
    assert second.outcome == "failed" and controller.steps == 6


def test_unqualified_policy_is_disabled():
    backend, controller, _, _ = setup()
    backend.qualified = False
    assert (
        backend.run_skill(SkillRequest("s", "pick", "pick")).failure_reason
        == "unqualified_motor_backend"
    )
    assert controller.steps == 0


def test_action_validation_covers_whole_prefix_before_motion():
    backend, controller, policy, _ = setup()
    policy.hook = lambda reply: replace(reply, actions=((0.1,), (float("nan"),)))
    assert backend.run_skill(SkillRequest("s", "pick", "pick")).outcome == "failed"
    assert controller.steps == 0


def test_backend_can_be_swapped_without_request_change():
    request = SkillRequest("s", "pick", "pick")
    for _ in range(2):
        backend, _, _, _ = setup()
        assert backend.run_skill(request).outcome == "completed"
