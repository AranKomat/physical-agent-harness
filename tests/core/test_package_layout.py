import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from physical_harness.core.actions import Basis
from physical_harness.core.events import BOUNDARY_WAKE_KINDS, BoundaryEvent
from physical_harness.perception.identity import Basis as IdentityBasis
from physical_harness.reasoning.executive import ExecutiveCadence


def test_shared_contracts_have_single_identity():
    assert Basis is IdentityBasis
    assert BoundaryEvent.__module__ == "physical_harness.core.events"
    assert ExecutiveCadence.WAKE is BOUNDARY_WAKE_KINDS


def test_canonical_modules_import_without_gpu_or_provider_side_effects():
    source = """
import importlib
import pkgutil
import sys
import physical_harness
for item in pkgutil.walk_packages(physical_harness.__path__, 'physical_harness.'):
    importlib.import_module(item.name)
assert not {'torch', 'curobo', 'sam3', 'transformers', 'omnigibson'} & sys.modules.keys()
"""
    result = subprocess.run([sys.executable, "-c", source], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_repository_ownership_and_links():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run([sys.executable, str(root / "tools/check_repository.py")],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


def test_configured_python_entry_points_exist():
    root = Path(__file__).resolve().parents[2]

    def values(value):
        if isinstance(value, dict):
            for child in value.values():
                yield from values(child)
        elif isinstance(value, list):
            for child in value:
                yield from values(child)
        elif isinstance(value, str):
            yield value

    for path in [*(root / "configs").rglob("*.json"),
                 *(root / "experiments/fixtures/configs").glob("*.json")]:
        for value in values(json.loads(path.read_text())):
            if value.startswith("physical_harness."):
                assert importlib.util.find_spec(value.split(":", 1)[0]) is not None, (path, value)
