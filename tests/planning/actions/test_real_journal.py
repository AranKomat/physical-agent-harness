import pytest

from experiments.fixtures.actions import Fixture
from physical_harness.execution.metrics import record_model_usage, summarize
from physical_harness.integrations.experiment.journal import Journal


def open_journal(path):
    return Journal(path, "fixture", max_microusd=0, max_calls=1)


def test_real_journal_execution_metrics_and_restart(tmp_path):
    path = tmp_path / "compiler.sqlite"
    f = Fixture()
    f.journal = open_journal(path)
    try:
        catalog = f.catalog()
        selection = {"catalog_id": catalog.id, "action_id": catalog.actions[0].id}
        initial = f.current
        result = f.executor().execute(catalog, selection, max_steps=1000, max_wall_s=10)
        record_model_usage(f.journal, call_id="perception-1", role="perception", calls=1, wall_s=.2)
        summary = summarize(f.journal)
        assert summary["known_robot_steps"] == result.native_steps
        assert summary["complete_action_accounting"]
        assert summary["auxiliary_model_calls_by_role"] == {"perception": 1}
        f.journal.close()
        f.journal = open_journal(path)
        restored = f.executor()
        assert result.attempt_id in restored.consumed
        assert not restored.faulted
        f.current = initial
        executed = len(f.executed)
        with pytest.raises(PermissionError, match="consumed"):
            restored.execute(catalog, selection, max_steps=1000, max_wall_s=10)
        assert len(f.executed) == executed
    finally:
        f.journal.close()


def test_real_journal_retains_unresolved_stop_fault(tmp_path):
    path = tmp_path / "fault.sqlite"
    f = Fixture()
    f.journal = open_journal(path)
    try:
        catalog = f.catalog()
        f.stop_ok = False
        with pytest.raises(RuntimeError, match="stopped"):
            f.executor().execute(catalog, {"catalog_id": catalog.id, "action_id": catalog.actions[0].id},
                                 max_steps=1000, max_wall_s=10)
        assert not f.executed
        f.journal.close()
        f.journal = open_journal(path)
        assert f.executor().faulted
        assert summarize(f.journal)["unresolved_stop_attempts"] == 1
    finally:
        f.journal.close()
