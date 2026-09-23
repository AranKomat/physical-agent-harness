import argparse
import json

from experiments.fixtures.basic import run_demo
from physical_harness.integrations.sensors.recorded import audit_archive


def main():
    parser = argparse.ArgumentParser(description="Physical harness offline integration checks")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Deterministic fixture; no robot or model calls")
    demo.add_argument("--output", required=True)
    replay = sub.add_parser(
        "audit-recording", help="Check saved native sensors without executing actions"
    )
    replay.add_argument("--archive", required=True)
    sub.add_parser("doctor", help="Report native integration gates without launching services")
    args = parser.parse_args()
    if args.command == "doctor":
        report = {
            "native_ready": False,
            "offline_demo_available": True,
            "paid_api_calls_enabled": False,
            "remaining_gates": [
                "Bind legal adapters to native BEHAVIOR process and recorded replay",
                "Qualify motor joint/gripper mapping and missing-part hold semantics",
                "Calibrate RTSM identity, relations and semantic verifier",
                "Qualify native odometry, calibrated camera extrinsics and N0 navigation",
                "Connect deadline-bounded IPC and API executive with explicit budget",
                "Qualify native IK/collision recovery before enabling it",
            ],
        }
    elif args.command == "audit-recording":
        report = audit_archive(args.archive)
    else:
        report = run_demo(args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
