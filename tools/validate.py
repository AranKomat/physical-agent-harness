"""One offline validation entry point; no models, simulator or paid calls."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    commands = [[sys.executable, "-m", "pytest", "-q"],
                [sys.executable, "-m", "ruff", "check", "."]]
    for name, module in [("basic", "physical_harness"),
                         ("handoff", "physical_harness.execution.handoff"),
                         ("actions", "physical_harness.planning.actions"),
                         ("graph", "physical_harness.planning.tasks"),
                         ("embodied", "physical_harness.reasoning")]:
        commands.append([sys.executable, "-m", module, "demo", "--output", str(output / name)])
    rows = []
    for index, command in enumerate(commands):
        try:
            result = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                    timeout=600, check=False)
            log, code = result.stdout + result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            log, code = "Software validation subprocess timed out.\n", 124
        (output / f"check-{index}.log").write_text(log)
        rows.append({"command": command, "returncode": code})
        if code:
            break
    passed = len(rows) == len(commands) and all(r["returncode"] == 0 for r in rows)
    report = {"passed": passed, "scope": "software-only", "native_motion": False,
              "model_inference": False, "checks": rows}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
