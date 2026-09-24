from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from physical_harness.core.actions import Check, Pose, Primitive
from physical_harness.execution.actions import StepReview
from physical_harness.execution.planner_bridge import (
    attach_free_space_planner,
    enforce_embodied_checks,
    with_planner_requirements,
)
from physical_harness.execution.servo import (
    JointSample,
    ServoLimits,
    ServoObservation,
    TrajectoryStreamer,
    VisualServo,
)
from physical_harness.integrations.curobo import (
    CUROBO_REVISION,
    CuroboV2Planner,
    JointLimits,
    JointTrajectory,
    PlanRequest,
    SceneReceipt,
    quaternion_wxyz,
)
from tests.reasoning.embodied.conftest import make_basis
from tests.reasoning.embodied.test_executive_metrics import make_catalog


def request(b=None):
    b = b or make_basis()
    return PlanRequest('plan', b, (0.0, 0.0), Pose('local'), 'tcp', JointLimits(('j1', 'j2'), (-1.0, -1.0), (1.0, 1.0), (1.0, 1.0), (20.0, 20.0)), ('fixed',), (0.2,), 'scene', ('depth',), 0.1, 20, 'robot-config')

def trajectory(r=None, points=None):
    r = r or request()
    return JointTrajectory(r.fingerprint, r.basis, r.limits.names, points or ((0.0, 0.0), (0.01, 0.0), (0.02, 0.0)), 0.1, 'scene', 'fixture', 'v1', 'scene-receipt')

def scene_receipt(r):
    return SceneReceipt(r.fingerprint, r.scene_digest, r.robot_config_digest, r.fixed_joint_names, r.fixed_joint_positions, r.tool_frame, r.basis.frame, True, r.scene_evidence)

def test_named_trajectory_checks_position_velocity_acceleration_and_rest():
    r = request()
    assert trajectory(r).validate(r)
    for pts in [((0.0, 0.0), (2.0, 0.0)), ((0.0, 0.0), (0.2, 0.0)), ((0.0, 0.0), (0.01,))]:
        with pytest.raises(ValueError):
            trajectory(r, pts).validate(r)
    low = replace(r, limits=replace(r.limits, acceleration=(0.01, 0.01)))
    with pytest.raises(ValueError):
        replace(trajectory(low), request_fingerprint=low.fingerprint).validate(low)

@pytest.mark.parametrize('changes', [{'scene_digest': 'wrong'}, {'dt': 0.2}, {'joint_names': ('j2', 'j1')}, {'basis': make_basis(episode='other')}, {'positions': ((0.1, 0.0), (0.1, 0.0))}])
def test_stale_or_mismatched_trajectory(changes):
    with pytest.raises((ValueError, PermissionError)):
        replace(trajectory(), **changes).validate(request())

@pytest.mark.parametrize('changes', [{'fixed_joint_names': ('j1',)}, {'dt': 0}, {'max_samples': 1}, {'target': Pose('wrong')}, {'start': (float('nan'), 0.0)}])
def test_plan_request_rejects_ambiguous_interfaces(changes):
    with pytest.raises(ValueError):
        replace(request(), **changes)

@pytest.mark.parametrize('axis', [0, 1, 2])
def test_quaternion_conversion_handles_half_turn(axis):
    m = np.eye(4)
    m[:3, :3] = -np.eye(3)
    m[axis, axis] = 1
    q = quaternion_wxyz(Pose('local', tuple((float(x) for x in m.ravel()))))
    assert abs(q[axis + 1]) == pytest.approx(1.0) and abs(q[0]) < 1e-08

class TensorDouble:

    def __init__(self, value, dtype=None):
        self.array = np.array(value, dtype=dtype)
        self.dtype = self.array.dtype
        self.device = 'cpu'
        self.shape = self.array.shape

    def reshape(self, *shape):
        return TensorDouble(self.array.reshape(*shape))

    def __getitem__(self, index):
        return TensorDouble(self.array[index])

    def item(self):
        return self.array.item()

    def numel(self):
        return self.array.size

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.array

    def tolist(self):
        return self.array.tolist()

def fake_api():
    torch = SimpleNamespace(tensor=lambda x, device=None, dtype=None: TensorDouble(x, dtype=dtype), zeros=lambda n: TensorDouble(np.zeros(n)), float64=np.float64)

    class Goal:

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class Joint:

        @classmethod
        def from_position(cls, x, *, joint_names):
            return SimpleNamespace(position=x, joint_names=joint_names)
    return (torch, Goal, Joint)

def planner_stub(plan_shape=(1, 3, 2)):
    torch, _, _ = fake_api()
    calls = []
    p = SimpleNamespace(joint_names=['j1', 'j2'], tool_frames=['tcp'], default_joint_state=SimpleNamespace(position=torch.zeros(2)), trajopt_solver=SimpleNamespace(config=SimpleNamespace(interpolation_dt=0.1)))

    def plan(goal, state):
        calls.append((goal, state))
        points = np.broadcast_to(np.array([[0.0, 0.0], [0.01, 0.0], [0.02, 0.0]], dtype=np.float64), plan_shape)
        return SimpleNamespace(success=torch.tensor([True]), get_interpolated_plan=lambda: SimpleNamespace(position=TensorDouble(points)))
    p.plan_pose = plan
    return (p, calls)

def test_curobov2_uses_audited_new_api_shapes_and_wxyz():
    p, calls = planner_stub()
    adapter = CuroboV2Planner(planner=p, install_scene=lambda p, r, d: scene_receipt(r), source_revision=CUROBO_REVISION, enabled=True, api=fake_api(), clock=lambda: 100)
    r = request()
    result = adapter.plan(r, deadline=102)
    assert result.backend == 'curobo-v2-plan-pose'
    assert tuple(calls[0][0].position.shape) == (1, 1, 1, 1, 3)
    assert tuple(calls[0][0].quaternion.shape) == (1, 1, 1, 1, 4)
    assert calls[0][0].quaternion.reshape(-1).tolist() == [1.0, 0.0, 0.0, 0.0]
    assert calls[0][1].joint_names == ['j1', 'j2']

@pytest.mark.parametrize('shape', [(3, 2), (1, 3, 2), (1, 1, 3, 2)])
def test_curobov2_accepts_singleton_batch_and_goal_axes(shape):
    p, _ = planner_stub(shape)
    adapter = CuroboV2Planner(planner=p, install_scene=lambda p, r, d: scene_receipt(r), source_revision=CUROBO_REVISION, enabled=True, api=fake_api(), clock=lambda: 100)
    result = adapter.plan(request(), deadline=102)
    assert len(result.positions) == 3

@pytest.mark.parametrize('shape', [(2, 1, 3, 2), (1, 2, 3, 2), (1, 1, 1, 3, 2)])
def test_curobov2_rejects_multiple_batches(shape):
    p, _ = planner_stub(shape)
    adapter = CuroboV2Planner(planner=p, install_scene=lambda p, r, d: scene_receipt(r), source_revision=CUROBO_REVISION, enabled=True, api=fake_api(), clock=lambda: 100)
    with pytest.raises(ValueError, match='Unexpected planner trajectory dimensions'):
        adapter.plan(request(), deadline=102)

@pytest.mark.parametrize('case', ['disabled', 'old_api', 'scene', 'tool', 'rate', 'failure', 'late'])
def test_curobo_fail_closed(case):
    p, calls = planner_stub()
    now = [100.0]
    if case == 'tool':
        p.tool_frames = ['other']
    if case == 'rate':
        p.trajopt_solver.config.interpolation_dt = 0.05
    if case == 'failure':
        p.plan_pose = lambda *a: None
    if case == 'late':
        old = p.plan_pose

        def late(*a):
            now[0] = 104
            return old(*a)
        p.plan_pose = late

    def install(p, r, d):
        return replace(scene_receipt(r), fully_updated=case != 'scene')
    with pytest.raises((PermissionError, ValueError, TimeoutError)):
        adapter = CuroboV2Planner(planner=p, install_scene=install, source_revision='legacy' if case == 'old_api' else CUROBO_REVISION, enabled=case != 'disabled', api=fake_api(), clock=lambda: now[0])
        adapter.plan(request(), deadline=102)

def servo_obs(seq=0, *, distance=0.02, **changes):
    b = make_basis(seq, wall=100 + 0.1 * seq, sim=0.1 * seq)
    o = ServoObservation(b, Pose('local'), Pose('local').shifted((1.0, 0.0, 0.0), distance), 'radio', 'id-v1', 'mask', 'depth', True, True)
    return replace(o, **changes)

def test_servo_bounded_step_and_convergence():
    first = servo_obs()
    servo = VisualServo(first, ServoLimits(dt=0.1))
    p = servo.propose(first, now=100)
    assert p.xyz[0] == pytest.approx(0.002)
    for i in (1, 2):
        assert servo.propose(servo_obs(i, distance=0.001), now=100 + i * 0.1) is not None
    assert servo.propose(servo_obs(3, distance=0.001), now=100.3) is None
    with pytest.raises(PermissionError):
        servo.propose(servo_obs(4), now=100.4)

@pytest.mark.parametrize('case', ['lost', 'association', 'identity', 'jump', 'stale', 'repeat', 'frame'])
def test_servo_rejects_missing_or_changed_evidence(case):
    s = VisualServo(servo_obs())
    s.propose(servo_obs(), now=100)
    obs = servo_obs(1)
    if case == 'lost':
        obs = replace(obs, target_visible=False)
    if case == 'association':
        obs = replace(obs, association_established=False)
    if case == 'identity':
        obs = replace(obs, entity_id='other')
    if case == 'jump':
        obs = servo_obs(1, distance=0.3)
    if case == 'repeat':
        obs = servo_obs(0)
    if case == 'frame':
        obs = replace(obs, basis=replace(obs.basis, frame_epoch='reset'))
    with pytest.raises(PermissionError):
        s.propose(obs, now=104 if case == 'stale' else 100.1)

class JointPort:

    def __init__(self, r, now, case=None):
        self.r, self.now, self.case = (r, now, case)
        self.sample = JointSample(r.basis, r.limits.names, r.start, r.fixed_joint_names, r.fixed_joint_positions)
        self.ticks = 0

    def observe(self, d):
        return self.sample

    def check_segment(self, *args):
        if self.case == 'late_review':
            self.now[0] = 200
        return None if self.case == 'unknown_sweep' else True

    def tick(self, q):
        self.ticks += 1
        self.now[0] += 0.1
        b = make_basis(self.ticks, wall=self.now[0], sim=self.ticks * 0.1)
        fixed = (0.4,) if self.case == 'fixed_drift' else (0.2,)
        self.sample = JointSample(b, self.r.limits.names, q, self.r.fixed_joint_names, fixed)
        return self.sample

    def command(self, r, q, s, d):
        if self.case == 'bad_feedback':
            return None
        return self.tick((0.5, 0.0) if self.case == 'tracking' else q)

    def settle(self, r, s, remaining, d):
        if self.case == 'uncounted':
            self.tick(s.positions)
            return ()
        return (self.tick(s.positions),)

    def stopped(self, s):
        return self.case != 'stop'

    def endpoint_reached(self, r, s, d):
        return self.case != 'endpoint'

def test_trajectory_streamer_counts_movement_and_settle_under_existing_authority(gripper):
    r = request()
    now = [100.0]
    port = JointPort(r, now)
    program = make_catalog(r.basis, gripper).actions[0].program
    stream = TrajectoryStreamer(port=port, clock=lambda: now[0], tracking_tolerance=(0.01, 0.01), fixed_tolerance=(0.001,))
    receipt = stream.run(program, 0, r.basis, r, trajectory(r), 102, lambda: False)
    assert receipt.native_steps == 3 and receipt.stop_acknowledged
    assert receipt.policy_calls == receipt.policy_dofs == 0
    assert not hasattr(stream, 'jobs')

@pytest.mark.parametrize('case', ['late_review', 'unknown_sweep', 'bad_feedback', 'fixed_drift', 'tracking', 'stop', 'endpoint', 'uncounted'])
def test_native_streamer_failures_surface_instead_of_silent_fallback(gripper, case):
    r = request()
    now = [100.0]
    port = JointPort(r, now, case)
    program = make_catalog(r.basis, gripper).actions[0].program
    stream = TrajectoryStreamer(port=port, clock=lambda: now[0], tracking_tolerance=(0.01, 0.01), fixed_tolerance=(0.001,))
    with pytest.raises((ValueError, PermissionError, RuntimeError, InterruptedError)):
        receipt = stream.run(program, 0, r.basis, r, trajectory(r), 102, lambda: False)
        receipt.after.require_same(port.observe(102).basis)
    if case in {'late_review', 'unknown_sweep'}:
        assert port.ticks == 0

def test_planner_integration_adds_required_checks_not_second_owner(gripper):
    from physical_harness.execution.actions import Driver
    b = make_basis()
    program = make_catalog(b, gripper).actions[0].program

    def step_review(p, i, b, d):
        names = ('fresh_sensors', 'robot_settled', 'swept_collision', 'native_codec', 'payload_geometry', 'joint_limits')
        return StepReview(p.fingerprint, i, b.fingerprint, tuple((Check(n, True, b.evidence_ids) for n in names)))
    driver = Driver('fixture', 'q', 'robot', gripper.fingerprint, frozenset({Primitive.MOVE_EEF}), lambda d: b, lambda *a: None, step_review, lambda *a: 'original', lambda d: True)
    wrapped = attach_free_space_planner(driver, planner=None, request_factory=None, streamer=None)
    with pytest.raises(PermissionError):
        wrapped.execute(program, 0, b, 102, lambda: False)
    augmented = with_planner_requirements(program)
    guarded = enforce_embodied_checks(driver, {})
    with pytest.raises(PermissionError):
        guarded.review_step(augmented, 0, b, 102)
    checks = {n: lambda p, i, b, d, n=n: Check(n, True, b.evidence_ids) for n in augmented.required_checks if n.startswith('embodied_')}
    guarded = enforce_embodied_checks(driver, checks)
    assert guarded.review_step(augmented, 0, b, 102).checks
