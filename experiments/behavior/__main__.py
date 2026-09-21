"""Plan and validate offline; native execution always requires separate opt-ins."""

import argparse
import json
from pathlib import Path

from .config import check_runtime, load_config
from .launcher import commands, protocol, run_pair
from .manifest import create_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "doctor", "run"):
        p = sub.add_parser(name)
        p.add_argument("--config", type=Path, required=True)
        p.add_argument("--output", type=Path, default=Path("runs/matched-radio-new"))
        if name == "run":
            for flag in ("allow-network", "allow-paid", "allow-motion", "licenses-accepted"):
                p.add_argument("--" + flag, action="store_true", required=True)
    p = sub.add_parser("manifest")
    p.add_argument("--candidate", choices=("corvid", "behavior-skill"), required=True)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "manifest":
        record = create_manifest(args.candidate, args.checkpoint, args.output)
        print(json.dumps({"files": len(record["files"]), "provenance": record["provenance"]}))
        return
    config = load_config(args.config)
    output = args.output.resolve()
    if args.command == "run":
        run_pair(config, args.config.resolve(), output, allow_network=args.allow_network,
                 allow_paid=args.allow_paid, allow_motion=args.allow_motion,
                 licenses_accepted=args.licenses_accepted)
    else:
        if args.command == "doctor":
            check_runtime(config)
        print(json.dumps({"mode": args.command, "network_calls": 0, "motion_actions": 0,
                          "runtime_paths_checked": args.command == "doctor",
                          "episodes": [{"protocol": protocol(c), "commands": commands(
                              config, args.config.resolve(), output, c)}
                              for c in ("corvid", "behavior-skill")]}, indent=2))


if __name__ == "__main__":
    main()
