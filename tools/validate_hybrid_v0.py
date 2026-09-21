"""Local validation only. Never starts BEHAVIOR, policy services or paid APIs."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--full-suite", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=False)
    commands = [[sys.executable, "-m", "pytest", "-q"] + ([] if args.full_suite else ["tests/hybrid_v0"]),
                [sys.executable, "-m", "physical_harness.hybrid_v0", "demo", "--output",
                 str((args.output/"fixture").resolve())]]
    results = []
    for i, command in enumerate(commands):
        run = subprocess.run(command, cwd=root, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, timeout=600, check=False)
        (args.output/f"step-{i}.log").write_text(run.stdout)
        results.append({"command": command, "returncode": run.returncode})
        if run.returncode:
            break
    report = {"scope": "full-checkout-software" if args.full_suite else "hybrid-software-only",
              "native_motion_run": False, "model_calls": 0, "steps": results,
              "passed": len(results) == len(commands) and all(r["returncode"] == 0 for r in results)}
    (args.output/"validation.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
