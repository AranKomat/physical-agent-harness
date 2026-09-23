"""Offline end-to-end fixture; never starts BEHAVIOR, models or cloud services."""
import argparse
from pathlib import Path

from experiments.fixtures.actions import run_fixture
from physical_harness.core.actions import encode


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["demo"])
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = run_fixture()
    for key in ("catalog", "scene", "tool_schema", "selection", "usage", "events"):
        (args.output/(key+".json")).write_bytes(encode(report[key])+b"\n")
    (args.output/"report.json").write_bytes(encode(report)+b"\n")
    print(encode({"kind": report["kind"], "outcome": report["execution"]["outcome"],
                  "model_calls": 0, "native_motion": False}).decode())


if __name__ == "__main__":
    main()
