from dataclasses import replace

import pytest

from physical_harness.action_compiler.fixture import Fixture
from physical_harness.action_compiler.metrics import (
    PowerSample,
    integrate_device_energy,
    record_model_usage,
    summarize,
)
from physical_harness.action_compiler.proposals import policy_candidate
from physical_harness.action_compiler.runtime import ActionExecutor
from physical_harness.action_compiler.types import Primitive
from physical_harness.jobs import JobManager


def select(catalog):
    return {'catalog_id': catalog.id, 'action_id': catalog.actions[0].id}


def run(f, e=None, c=None):
    catalog = c or f.catalog()
    return (e or f.executor()).execute(catalog, select(catalog), max_steps=1000, max_wall_s=10)


def test_whole_program_runs_without_model_calls_or_semantic_success():
    f = Fixture()
    e = f.executor()
    result = run(f, e)
    assert result.outcome == 'completed'
    assert result.semantic_status == 'requires_external_verification'
    assert not e.jobs.owners
    assert Primitive.CLOSE in f.executed and Primitive.HOLD_CHECK in f.executed
    metrics = summarize(f.journal)
    assert metrics['policy_action_time_fraction'] == 0
    assert metrics['policy_dof_time_fraction'] == 0
    assert metrics['energy_joules'] is None and metrics['complete_action_accounting']


@pytest.mark.parametrize('reason', ['disabled', 'domain', 'robot', 'gripper', 'primitive', 'budget', 'epoch'])
def test_pre_dispatch_rejections_never_move(reason):
    f = Fixture()
    e, c = f.executor(), f.catalog()
    max_steps = 1000
    if reason == 'disabled':
        e.allowed = False
    if reason == 'domain':
        e.driver = replace(e.driver, domain='behavior_sim')
    if reason == 'robot':
        e.driver = replace(e.driver, robot_fingerprint='other')
    if reason == 'gripper':
        e.driver = replace(e.driver, gripper_fingerprint='other')
    if reason == 'primitive':
        e.driver = replace(e.driver, supported=frozenset())
    if reason == 'budget':
        max_steps = 1
    if reason == 'epoch':
        e.jobs.invalidate_goal()
    with pytest.raises((PermissionError, ValueError, InterruptedError)):
        e.execute(c, select(c), max_steps=max_steps, max_wall_s=10)
    assert not f.executed


def test_shared_job_manager_blocks_other_actuator_owner():
    f = Fixture()
    jobs = JobManager([ActionExecutor.name, 'other'])
    jobs.start('other-id', 'other', ('base',), 'o', 100., 110.)
    e = f.executor(jobs)
    with pytest.raises(ValueError, match='Resource'):
        run(f, e)
    assert jobs.owners['base'] == 'other-id' and not f.executed


def test_unacknowledged_stop_retains_resource_lock_across_new_executor():
    f = Fixture()
    f.stop_ok = False
    e = f.executor()
    with pytest.raises(RuntimeError):
        run(f, e)
    assert e.jobs.owners and e.faulted
    f.stop_ok = True
    fresh = f.executor(e.jobs)
    assert fresh.faulted
    with pytest.raises(PermissionError):
        run(f, fresh)


def test_measured_grasp_failure_prevents_lift():
    f = Fixture()
    e = f.executor()
    original = e.driver.review_step
    def guard(program, index, before, deadline):
        result = original(program, index, before, deadline)
        if program.steps[index].kind == Primitive.HOLD_CHECK:
            result = replace(result, checks=tuple(replace(c, passed=None) if c.name == 'measured_grasp' else c
                                                 for c in result.checks))
        return result
    e.driver = replace(e.driver, review_step=guard)
    with pytest.raises(PermissionError):
        run(f, e)
    assert f.executed[-1] == Primitive.CLOSE
    assert Primitive.HOLD_CHECK not in f.executed


@pytest.mark.parametrize('case', ['steps', 'time', 'id', 'stop', 'policy_leak', 'foreign_frame', 'schema'])
def test_invalid_native_receipts_fail_closed(case):
    f = Fixture()
    e = f.executor()
    original = e.driver.execute
    def corrupt(program, index, before, deadline, cancelled):
        r = original(program, index, before, deadline, cancelled)
        if case == 'steps':
            return replace(r, native_steps=999)
        if case == 'time':
            return replace(r, after=replace(r.after, sim_time=r.after.sim_time+1))
        if case == 'id':
            return replace(r, step_index=99)
        if case == 'stop':
            return replace(r, stop_acknowledged=False)
        if case == 'policy_leak':
            return replace(r, policy_calls=1)
        if case == 'foreign_frame':
            return replace(r, after=replace(r.after, frame_epoch='other'))
        return {'completed': True}
    e.driver = replace(e.driver, execute=corrupt)
    with pytest.raises((ValueError, PermissionError, RuntimeError)):
        run(f, e)
    assert e.faulted
    report = summarize(f.journal)
    assert not report['complete_action_accounting']
    assert report['unresolved_steps'] == 1


def test_no_retry_after_partial_motion_and_transport_failure():
    f = Fixture()
    e = f.executor()
    def broken(*args):
        raise ConnectionError('uncertain')
    e.driver = replace(e.driver, execute=broken)
    with pytest.raises(ConnectionError):
        run(f, e)
    assert e.faulted
    assert f.executor(e.jobs).faulted  # restart cannot erase fault even if stop succeeded


def test_epoch_invalidation_in_flight_prevents_next_command():
    f = Fixture()
    e = f.executor()
    old = e.driver.execute
    def execute(*args):
        r = old(*args)
        e.jobs.invalidate_goal()
        return r
    e.driver = replace(e.driver, execute=execute)
    with pytest.raises(InterruptedError):
        run(f, e)
    assert len(f.executed) == 1


def test_fault_after_durable_reservation_is_visible():
    f = Fixture()
    e = f.executor()
    original = f.journal.put
    def fail(kind, identifier, payload):
        if kind == 'compiled_action' and payload['event'] == 'step_receipt':
            raise OSError('disk')
        return original(kind, identifier, payload)
    f.journal.put = fail
    with pytest.raises(OSError):
        run(f, e)
    assert e.faulted and len(f.executed) == 1
    assert summarize(f.journal)['unresolved_steps'] == 1


def test_reservation_write_failure_never_executes_primitive():
    f = Fixture()
    e = f.executor()
    original = f.journal.put
    def fail(kind, identifier, payload):
        if kind == 'compiled_action' and payload['event'] == 'reserved':
            raise OSError('disk')
        return original(kind, identifier, payload)
    f.journal.put = fail
    with pytest.raises(OSError):
        run(f, e)
    assert not f.executed


def test_failed_primitive_returns_failure_without_fallthrough():
    f = Fixture()
    e = f.executor()
    old = e.driver.execute
    e.driver = replace(e.driver, execute=lambda *args: replace(old(*args), outcome='stalled'))
    result = run(f, e)
    assert result.outcome == 'stalled' and len(f.executed) == 1
    assert not e.jobs.owners


def test_native_stop_cannot_smuggle_uncounted_settle_ticks():
    f = Fixture()
    e = f.executor()
    calls = [0]
    def stop(deadline):
        calls[0] += 1
        if calls[0] > 1:
            f.current = replace(f.current, sim_time=f.current.sim_time+1/30)
        return True
    e.driver = replace(e.driver, stop=stop)
    with pytest.raises(RuntimeError, match='uncounted'):
        run(f, e)
    assert e.jobs.owners and e.faulted


def test_consumed_catalog_not_replayed_after_restart():
    f = Fixture()
    c, e = f.catalog(), f.executor()
    original = f.current
    run(f, e, c)
    # Malicious reset of the fixture capture doesn't reset the durable registry.
    f.current = original
    with pytest.raises(PermissionError, match='already consumed'):
        run(f, f.executor(), c)


def test_equal_full_policy_dofs_and_separate_auxiliary_compute():
    f = Fixture()
    p = policy_candidate(f.current, f.gripper, entity='object-1', instruction='pick object', policy_fingerprint='p')
    run(f, c=f.catalog((p,)))
    record_model_usage(f.journal, call_id='g1', role='grasp_generation', calls=1, wall_s=.5)
    result = summarize(f.journal)
    assert result['policy_action_time_fraction'] == 1
    assert result['policy_dof_time_fraction'] == 1
    assert result['policy_inference_s'] is None
    assert result['auxiliary_model_calls_by_role']['grasp_generation'] == 1
    assert result['policy_inference_calls'] == 1


def test_masked_frozen_policy_rejected():
    f = Fixture()
    p = policy_candidate(f.current, f.gripper, entity='object-1', instruction='pick object', policy_fingerprint='p')
    e = f.executor()
    old = e.driver.execute
    e.driver = replace(e.driver, execute=lambda *a: replace(old(*a), policy_dofs=7))
    with pytest.raises(PermissionError, match='full normal'):
        run(f, e, f.catalog((p,)))


def test_energy_is_device_window_not_neural_attribution():
    samples = (PowerSample('gpu0', 0., 10.), PowerSample('gpu0', 1., 20.), PowerSample('gpu0', 2., 10.))
    result = integrate_device_energy(samples)
    assert result['gpu0']['joules'] == 30
    assert 'whole-device' in result['gpu0']['attribution']
    with pytest.raises(ValueError):
        integrate_device_energy((samples[0], replace(samples[1], wall_time=2.)))
