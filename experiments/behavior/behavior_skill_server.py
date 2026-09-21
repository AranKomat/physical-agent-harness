"""Serve the pinned Behavior-Skill policy for bounded local simulation only."""

import argparse
from pathlib import Path

from .behavior_skill import load_backend


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "checkpoint", "manifest", "receipt"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()
    from .policy_server import PolicyFacade

    PolicyFacade(load_backend(args.source, args.checkpoint, args.manifest, args.receipt)).serve(
        transport="http", host="127.0.0.1", port=args.port,
        parent_watch=False, session_sweep_s=None,
    )


if __name__ == "__main__":
    main()
