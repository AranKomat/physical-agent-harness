"""Check source ownership and local Markdown links without contacting services."""
from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = {"core", "perception", "world", "planning", "execution", "reasoning", "integrations"}
RETIRED = {"action_compiler", "hybrid_v0", "situated", "embodied_v3", "experiment",
           "memory", "adapters", "backends"}

# The normal dependency graph is acyclic; same-domain imports are allowed.
ALLOWED = {
    "core": frozenset(),
    "perception": frozenset({"core"}),
    "world": frozenset({"core", "perception"}),
    "planning": frozenset({"core", "perception", "world"}),
    "execution": frozenset({"core", "perception", "world", "planning"}),
    "reasoning": frozenset({"core", "perception", "world", "planning", "execution"}),
    "integrations": frozenset(DOMAINS - {"integrations"}),
}

# Existing bridges are debt, not additional allowed domain directions. Lock both
# the source module and imported symbols; unused exceptions must be removed.
BRIDGES = {
    ("physical_harness.planning.ik", "physical_harness.execution.handoff.classical"):
        ({"JointLimits", "vector"}, "IK consumes existing handoff joint limits"),
    ("physical_harness.planning.ik", "physical_harness.execution.handoff.contracts"):
        ({"integer", "real"}, "Preserve existing handoff validation semantics"),
    ("physical_harness.planning.staging", "physical_harness.execution.handoff.classical"):
        ({"BasePose"}, "Staging uses the existing base controller pose contract"),
    ("physical_harness.planning.staging", "physical_harness.execution.handoff.contracts"):
        ({"Snapshot", "identifiers", "integer", "real", "text"}, "Staging consumes legal handoff snapshots"),
    ("physical_harness.execution.servo", "physical_harness.integrations.curobo"):
        ({"JointTrajectory", "PlanRequest"}, "Planner contracts are still colocated with the adapter"),
    ("physical_harness.execution.action_bridge", "physical_harness.integrations.experiment.runner"):
        ({"Action"}, "Existing experiment action descriptor bridge"),
    ("physical_harness.perception.scene", "physical_harness.planning.actions.compiler"):
        ({"Catalog"}, "Scene projection consumes a reviewed catalog"),
    ("physical_harness.perception.overlays", "physical_harness.planning.actions.compiler"):
        ({"Catalog"}, "Diagnostic overlay renders reviewed candidates"),
    ("physical_harness.perception.localization", "physical_harness.integrations.sensors.behavior"):
        ({"LegalObservation"}, "Existing legal RGB-D envelope"),
    ("physical_harness.execution.handoff.contracts", "physical_harness.integrations.sensors.behavior"):
        ({"LegalObservation"}, "Handoff validates the same sensor allowlist"),
    ("physical_harness.planning.actions.catalogs", "physical_harness.execution.actions"):
        ({"StepReview"}, "Catalog helper extends existing per-step reviews"),
    ("physical_harness.planning.actions.cartesian", "physical_harness.execution.actions"):
        ({"StepReceipt"}, "Counted Cartesian execution uses the existing receipt"),
}

CLI_FIXTURES = {
    "physical_harness.__main__": "experiments.fixtures.basic",
    "physical_harness.planning.actions.__main__": "experiments.fixtures.actions",
    "physical_harness.planning.tasks.__main__": "experiments.fixtures.graph",
    "physical_harness.execution.handoff.__main__": "experiments.fixtures.handoff",
    "physical_harness.reasoning.__main__": "experiments.fixtures.embodied",
}


def imported_modules(source, module, *, is_package=False):
    """Resolve absolute/relative imports, including local and TYPE_CHECKING blocks.

    Literal import_module/__import__ calls are checked too. Computed plugin names
    are not statically resolvable; this is an architecture check, not a sandbox.
    """
    tree = ast.parse(source)
    package = module if is_package else module.rpartition(".")[0]
    dynamic = {"importlib.import_module", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib":
                    dynamic.add((alias.asname or alias.name) + ".import_module")
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            dynamic.update(a.asname or a.name for a in node.names if a.name == "import_module")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, frozenset(), node.lineno
        elif isinstance(node, ast.ImportFrom):
            name = node.module or ""
            if node.level:
                name = importlib.util.resolve_name("." * node.level + name, package)
            if name == "physical_harness" or name in {"physical_harness." + d for d in DOMAINS}:
                for alias in node.names:
                    yield name + "." + alias.name, frozenset(), node.lineno
            else:
                yield name, frozenset(a.name for a in node.names), node.lineno
        elif isinstance(node, ast.Call) and ast.unparse(node.func) in dynamic:
            value = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "name"), None)
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                continue
            name = value.value
            if name.startswith("."):
                context = next((k.value for k in node.keywords if k.arg == "package"),
                               node.args[1] if len(node.args) > 1 else None)
                if isinstance(context, ast.Constant) and isinstance(context.value, str):
                    name = importlib.util.resolve_name(name, context.value)
                elif isinstance(context, ast.Name) and context.id == "__package__":
                    name = importlib.util.resolve_name(name, package)
                else:
                    yield "physical_harness.<unresolved-relative-import>", frozenset(), node.lineno
                    continue
            yield name, frozenset(), node.lineno


def boundary_errors(source, module, *, is_package=False, used_bridges=None):
    errors = []
    parts = module.split(".")
    owner = parts[1] if len(parts) >= 2 and parts[0] == "physical_harness" else None
    for target, names, line in imported_modules(source, module, is_package=is_package):
        if module.startswith("physical_harness.") and target.split(".")[0] in {"experiments", "tests", "tools"}:
            if CLI_FIXTURES.get(module) != target:
                errors.append(f"{module}:{line}: runtime imports research/tooling module {target}")
        if target == "physical_harness" and owner in DOMAINS:
            errors.append(f"{module}:{line}: import the owning module, not the root facade")
        if not target.startswith("physical_harness."):
            continue
        domain = target.split(".")[1]
        if domain in RETIRED:
            errors.append(f"{module}:{line}: retired import {target}")
            continue
        if owner not in DOMAINS or domain == owner or domain in ALLOWED[owner]:
            continue
        bridge = BRIDGES.get((module, target))
        if bridge and names and names <= bridge[0]:
            if used_bridges is not None:
                used_bridges.setdefault((module, target), set()).update(names)
            continue
        errors.append(f"{module}:{line}: illegally imports {target} ({owner} -> {domain})")
    return errors


def problems(root=ROOT):
    errors = []
    used_bridges = {}
    actual = {p.name for p in (root / "physical_harness").iterdir()
              if p.is_dir() and (p / "__init__.py").exists()}
    if actual != DOMAINS:
        errors.append(f"Unexpected runtime domains: {actual ^ DOMAINS}")
    for folder in ("physical_harness", "experiments", "tests", "examples", "tools"):
        for path in (root / folder).rglob("*.py"):
            module = ".".join(path.relative_to(root).with_suffix("").parts).removesuffix(".__init__")
            errors.extend(boundary_errors(path.read_text(), module,
                          is_package=path.name == "__init__.py", used_bridges=used_bridges))
    for edge, (names, _reason) in BRIDGES.items():
        if used_bridges.get(edge, set()) != names:
            errors.append(f"Remove stale architecture exception symbols: {edge}")
    for path in [root / "README.md", *(root / "docs").rglob("*.md"),
                 *(root / "experiments").rglob("*.md")]:
        for target in re.findall(r"\]\(([^\s()]+)\)", path.read_text()):
            if re.match(r"\w+:|#|/", target):
                continue
            dest = (path.parent / unquote(target.split("#", 1)[0])).resolve()
            if dest.is_relative_to(root) and not dest.exists():
                errors.append(f"{path.relative_to(root)}: missing link {target}")
    return errors


if __name__ == "__main__":
    failures = problems()
    print("\n".join(failures) if failures else "Repository ownership and local links passed")
    raise SystemExit(bool(failures))
