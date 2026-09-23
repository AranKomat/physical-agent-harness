"""Check source ownership and local Markdown links without contacting services."""
from __future__ import annotations

import ast
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = {"core", "perception", "world", "planning", "execution", "reasoning", "integrations"}
RETIRED = {"action_compiler", "hybrid_v0", "situated", "embodied_v3", "experiment",
           "memory", "adapters", "backends"}


def problems(root=ROOT):
    errors = []
    actual = {p.name for p in (root / "physical_harness").iterdir()
              if p.is_dir() and (p / "__init__.py").exists()}
    if actual != DOMAINS:
        errors.append(f"Unexpected runtime domains: {actual ^ DOMAINS}")
    for folder in ("physical_harness", "experiments", "tests", "examples", "tools"):
        for path in (root / folder).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                names = ([node.module or ""] if isinstance(node, ast.ImportFrom) else
                         [a.name for a in node.names] if isinstance(node, ast.Import) else [])
                for name in names:
                    if name.startswith("physical_harness.") and name.split(".")[1] in RETIRED:
                        errors.append(f"{path.relative_to(root)}:{node.lineno}: retired import {name}")
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
