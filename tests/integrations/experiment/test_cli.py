from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from physical_harness.integrations.experiment.__main__ import read_config

CONFIG = Path(__file__).parents[3] / 'experiments/fixtures/configs/doctor.fixture.json'


def test_doctor_does_not_start_native_or_network():
    result = subprocess.run([sys.executable, '-m', 'physical_harness.integrations.experiment', 'doctor',
                             '--config', str(CONFIG)], capture_output=True, text=True, check=True)
    report = json.loads(result.stdout)
    assert report['configuration_valid'] and not report['native_started'] and not report['network_attempted']


@pytest.mark.parametrize('mutate', ['permission', 'negative_budget', 'bad_model'])
def test_invalid_config_fails_before_native(tmp_path, mutate):
    cfg = json.loads(CONFIG.read_text())
    if mutate == 'permission':
        cfg['models']['executive']['settings']['allow_paid'] = True
    elif mutate == 'negative_budget':
        cfg['max_api_microusd'] = -1
    else:
        cfg['models']['executive']['settings']['model'] = 'REPLACE_WITH_REAL_ID'
    p = tmp_path / 'bad.json'
    p.write_text(json.dumps(cfg))
    with pytest.raises(ValueError):
        read_config(p)
