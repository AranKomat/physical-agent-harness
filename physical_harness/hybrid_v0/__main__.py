"""Offline smoke test only. Does not load native drivers or call model providers."""
import argparse
from pathlib import Path

from .contracts import encoded
from .fixture import run_fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "demo":
        args.output.mkdir(parents=True, exist_ok=False)
        result = run_fixture()
        (args.output/"report.json").write_bytes(encoded(result)+b"\n")
        print(encoded({k: v for k, v in result.items() if k != "events"}).decode())


if __name__ == "__main__":
    main()
