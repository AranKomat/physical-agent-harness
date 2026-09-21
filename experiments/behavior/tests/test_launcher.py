import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.behavior import launcher
from experiments.behavior.config import ExperimentConfig, load_config

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "configs/behavior/matched-radio.example.json"


def config(tmp_path):
    data = json.loads(EXAMPLE.read_text())
    data["campaign"]["journal"] = str(tmp_path / "budget.sqlite")
    path = tmp_path / "portable config.json"
    path.write_text(json.dumps(data))
    return load_config(path), path


def test_relative_paths_are_config_relative(tmp_path, monkeypatch):
    cfg, path = config(tmp_path)
    monkeypatch.chdir(tmp_path.parent)
    assert cfg.native.python == (path.parent / "../../runtime/native/bin/python").resolve()
    assert load_config(path) == cfg


@pytest.mark.parametrize("change", [{"simulator_gpu": 1}, {"port": True},
                                   {"api_key": "not allowed"}])
def test_invalid_config_rejected(change):
    data = json.loads(EXAMPLE.read_text())
    data.update(change)
    with pytest.raises(ValueError):
        ExperimentConfig.model_validate(data)


def test_plan_cli_needs_no_gpu_key_or_private_imports(tmp_path):
    output = tmp_path / "unused"
    env = dict(os.environ)
    env.pop("OPENROUTER_API_KEY", None)
    result = subprocess.run([sys.executable, "-m", "experiments.behavior", "plan",
                             "--config", str(EXAMPLE), "--output", str(output)],
                            env=env, capture_output=True, text=True, timeout=20, check=True)
    plan = json.loads(result.stdout)
    assert plan["network_calls"] == plan["motion_actions"] == 0
    assert not output.exists()
    assert [p["protocol"]["prefix"] for p in plan["episodes"]] == [1, 32]


def test_environment_fences_and_credentials(tmp_path, monkeypatch):
    cfg, _ = config(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fixture-secret")
    monkeypatch.setenv("PYTHONPATH", "/private-campaign")
    policy, native = launcher.environments(cfg, "corvid")
    assert "OPENROUTER_API_KEY" not in policy
    assert native["OPENROUTER_API_KEY"] == "fixture-secret"
    assert policy["CUDA_VISIBLE_DEVICES"] == "1" and native["CUDA_VISIBLE_DEVICES"] == "0"
    assert "/private-campaign" not in policy["PYTHONPATH"] + native["PYTHONPATH"]
    assert policy["HF_HUB_OFFLINE"] == "1"


def test_frozen_prompt_hashes():
    a, b = launcher.protocol("corvid"), launcher.protocol("behavior-skill")
    assert a["executive_sha256"] == b["executive_sha256"] == (
        "ab935f6a31c511bfdf275dc9c07d8119676c4dbd4e34bb881df61f1d59f27881")
    assert a["verifier_sha256"] == b["verifier_sha256"] == (
        "22f5e24dba5c80ed06061453dd4098bd70cf4f48e3e7b58841da7edb9536a875")


def test_run_without_all_optins_has_no_effect(tmp_path):
    cfg, path = config(tmp_path)
    out = tmp_path / "not-created"
    with pytest.raises(PermissionError):
        launcher.run_pair(cfg, path, out, allow_network=True, allow_paid=True)
    assert not out.exists() and not cfg.campaign.journal.exists()


def test_first_failure_stops_pair_and_preserves_receipt(tmp_path, monkeypatch):
    cfg, path = config(tmp_path)
    monkeypatch.setattr(launcher.platform, "system", lambda: "Linux")
    monkeypatch.setattr(launcher, "check_runtime", lambda c: None)
    monkeypatch.setenv(cfg.model.api_key_env, "fixture")
    monkeypatch.setattr(launcher, "endpoint_preflight", lambda *a, **k: {})
    calls = []

    def fail(c, config_path, output, candidate):
        calls.append(candidate)
        assert config_path == output / "config.json"
        raise RuntimeError("fixture failure")

    monkeypatch.setattr(launcher, "run_episode", fail)
    out = tmp_path / "run"
    with pytest.raises(RuntimeError):
        launcher.run_pair(cfg, path, out, allow_network=True, allow_paid=True,
                          allow_motion=True, licenses_accepted=True)
    assert calls == ["corvid"]
    assert json.loads((out / "pair.json").read_text())["completed"] is False


def test_process_group_reaped_after_leader_exit(monkeypatch):
    calls = []
    monkeypatch.setattr(launcher.os, "killpg", lambda pid, sig: calls.append((pid, sig)))

    class Process:
        pid = 999

        def wait(self, timeout):
            return 0

    launcher.reap(Process())
    assert [pid for pid, _ in calls] == [999, 999]
