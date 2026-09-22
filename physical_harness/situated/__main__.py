"""Offline synthetic demonstration. Never starts a policy, simulator, or paid model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["demo"])
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    from .fixture import run_fixture
    result=run_fixture(args.output)
    (args.output/"report.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("scope","native_robot_actions","model_calls","synthetic_graph_finished")},indent=2))


if __name__ == "__main__":
    main()
