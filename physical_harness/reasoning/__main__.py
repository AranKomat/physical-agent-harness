"""No implicit model, network, GPU, simulator or hardware launch."""
from __future__ import annotations

import argparse
import json


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Run a synthetic fixture; makes no paid or native calls")
    demo.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "demo":
        from experiments.fixtures.embodied import run_demo
        print(json.dumps(run_demo(args.output), indent=2))


if __name__ == "__main__":
    main()
