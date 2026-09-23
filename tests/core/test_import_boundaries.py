import pytest

from tools.check_repository import ALLOWED, BRIDGES, boundary_errors


@pytest.mark.parametrize("source", [
    "from physical_harness.reasoning.executive import ExecutiveCadence",
    "import physical_harness.perception.keyframes as frames",
    "from ..reasoning import executive",
    "from .. import reasoning",
    "from physical_harness import HarnessRuntime",
    "if TYPE_CHECKING:\n from physical_harness.reasoning.executive import ExecutiveCadence",
    "def run():\n from physical_harness.execution.actions import Driver",
    "import importlib\nimportlib.import_module('physical_harness.reasoning.executive')",
    "from importlib import import_module as load\nload('physical_harness.reasoning.executive')",
    "import importlib as loader\nloader.import_module('..reasoning.executive', __package__)",
    "__import__('physical_harness.reasoning.executive')",
    "import importlib\nimportlib.import_module(name='physical_harness.reasoning.executive')",
])
def test_core_rejects_higher_layers_in_all_static_import_forms(source):
    assert boundary_errors(source, "physical_harness.core.example")


def test_relative_imports_in_package_init_are_resolved():
    assert boundary_errors("from ..reasoning import executive", "physical_harness.core", is_package=True)
    assert not boundary_errors("from .actions import Basis", "physical_harness.core", is_package=True)


def test_retired_modules_have_no_shims():
    import importlib.util
    for name in ("action_compiler", "hybrid_v0", "situated", "embodied_v3",
                 "core.discovery", "core.coordinator"):
        assert importlib.util.find_spec("physical_harness." + name) is None


@pytest.mark.parametrize("retired", ["action_compiler", "hybrid_v0", "situated", "embodied_v3"])
@pytest.mark.parametrize("source", ["from physical_harness.{name} import Something",
                                    "from physical_harness import {name}",
                                    "import physical_harness.{name}"])
def test_retired_namespaces_are_rejected_even_in_experiments(retired, source):
    errors = boundary_errors(source.format(name=retired), "experiments.example")
    assert errors and "retired import" in errors[0]


def test_normal_policy_is_acyclic_and_core_has_no_exemptions():
    def visit(domain, ancestors):
        assert domain not in ancestors
        for target in ALLOWED[domain]:
            visit(target, ancestors | {domain})
    for domain in ALLOWED:
        visit(domain, set())
    assert not ALLOWED["core"]
    assert not any(src.startswith("physical_harness.core.") for src, _ in BRIDGES)


def test_existing_bridge_does_not_authorize_another_module_or_symbol():
    statement = "from physical_harness.integrations.curobo import PlanRequest"
    assert not boundary_errors(statement, "physical_harness.execution.servo")
    assert boundary_errors(statement, "physical_harness.execution.other")
    assert boundary_errors(statement.replace("PlanRequest", "Planner"), "physical_harness.execution.servo")
    assert boundary_errors("import physical_harness.integrations.curobo", "physical_harness.execution.servo")


def test_forward_imports_and_explicit_experiment_composition_are_allowed():
    assert not boundary_errors("from physical_harness.core.actions import Basis", "physical_harness.perception.contracts")
    assert not boundary_errors("from physical_harness.reasoning.executive import ExecutiveCadence", "experiments.example")


@pytest.mark.parametrize("target", ["experiments.fixtures.embodied", "tests.core", "tools.check_repository"])
def test_runtime_cannot_bypass_layers_through_research_code(target):
    assert boundary_errors("import " + target, "physical_harness.core.example")


def test_only_existing_cli_fixture_edges_are_allowed():
    source = "from experiments.fixtures.embodied import run_demo"
    assert not boundary_errors(source, "physical_harness.reasoning.__main__")
    assert boundary_errors(source, "physical_harness.reasoning.executive")
