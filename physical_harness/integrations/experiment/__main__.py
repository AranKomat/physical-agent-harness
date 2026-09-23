"""CLI: demo, doctor, run, serve-native, and export-replay. Paid/motion opt-ins are explicit."""
from __future__ import annotations

import argparse
from pathlib import Path

from physical_harness.integrations.experiment.actors import parse_goal
from physical_harness.integrations.experiment.fixture import run_demo
from physical_harness.integrations.experiment.journal import Journal
from physical_harness.integrations.experiment.models import JsonModel, ModelSettings, Rates
from physical_harness.integrations.experiment.native_rpc import ProcessNative, serve
from physical_harness.integrations.experiment.replay import evaluate_qa, export_replay
from physical_harness.integrations.experiment.runner import Action, EpisodeRunner, RunLimits
from physical_harness.integrations.experiment.transport import HttpTransport
from physical_harness.integrations.experiment.validation import dumps, fields, integer, loads, text
from physical_harness.reasoning.context.rich import RichContextPolicy


def read_config(path):
    cfg = loads(Path(path).read_bytes())
    fields(cfg, {"episode", "goal_text", "goals", "actions", "models", "native_command",
                 "limits", "max_api_microusd", "max_model_calls"}, {"context_policy"})
    text(cfg["episode"], maximum=256)
    integer(cfg["max_api_microusd"])
    integer(cfg["max_model_calls"], minimum=1)
    if not isinstance(cfg["native_command"], list) or not cfg["native_command"] or any(
        not isinstance(arg, str) or not arg for arg in cfg["native_command"]):
        raise ValueError("Explicit native command argument vector required")
    fields(cfg["models"], {"executive", "verifier"}, {"narrator"})
    goals = [parse_goal(g) for g in cfg["goals"]]
    actions = [Action(**dict(a, targets=tuple(a["targets"]))) for a in cfg["actions"]]
    policy = RichContextPolicy(**cfg.get("context_policy", {}))
    RunLimits(**cfg["limits"])
    for value in cfg["models"].values():
        fields(value, {"settings", "transport", "rates"})
        if any(k in value["settings"] for k in ("allow_paid",)):
            raise ValueError("Paid opt-in belongs on the CLI, not in a stored config")
        if any(k in value["transport"] for k in ("allow_network",)):
            raise ValueError("Network opt-in belongs on the CLI, not in a stored config")
        ModelSettings(**value["settings"])
        HttpTransport(**value["transport"])
        for rate in value["rates"].values():
            Rates(**rate)
    if "allow_motion" in cfg["limits"]:
        raise ValueError("Motion opt-in belongs on the CLI")
    return cfg, goals, actions, policy


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo")
    demo.add_argument("--output", type=Path, required=True)
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--config", required=True)
    run = commands.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--allow-network", action="store_true")
    run.add_argument("--allow-paid", action="store_true")
    run.add_argument("--allow-motion", action="store_true")
    native = commands.add_parser("serve-native")
    native.add_argument("--factory", required=True)
    native.add_argument("--episode", required=True)
    replay = commands.add_parser("export-replay")
    replay.add_argument("--run", type=Path, required=True)
    replay.add_argument("--output", type=Path, required=True)
    qa = commands.add_parser("evaluate-replay")
    qa.add_argument("--export", type=Path, required=True)
    qa.add_argument("--labels", type=Path, required=True)
    qa.add_argument("--model-config", type=Path, required=True)
    qa.add_argument("--output", type=Path, required=True)
    qa.add_argument("--max-api-microusd", type=int, required=True)
    qa.add_argument("--max-calls", type=int, default=100)
    qa.add_argument("--allow-network", action="store_true")
    qa.add_argument("--allow-paid", action="store_true")
    args = parser.parse_args()
    if args.command == "demo":
        result = run_demo(args.output)
    elif args.command == "serve-native":
        serve(args.factory, args.episode)
        return
    elif args.command == "export-replay":
        result = export_replay(args.run, args.output)
    elif args.command == "evaluate-replay":
        cfg = loads(args.model_config.read_bytes())
        fields(cfg, {"settings", "transport", "rates"})
        if "allow_paid" in cfg["settings"] or "allow_network" in cfg["transport"]:
            raise ValueError("Permissions belong on the CLI")
        if not args.allow_network:
            raise PermissionError("QA model transport requires --allow-network")
        if cfg["settings"].get("paid", True) and not args.allow_paid:
            raise PermissionError("Paid QA requires --allow-paid")
        manifest = loads((args.export / "manifest.json").read_bytes())
        args.output.mkdir(parents=True, exist_ok=False)
        journal = Journal(args.output / "journal.sqlite", manifest["episode"],
                          max_microusd=args.max_api_microusd, max_calls=args.max_calls)
        try:
            model = JsonModel(ModelSettings(**dict(cfg["settings"], allow_paid=args.allow_paid)),
                              HttpTransport(**dict(cfg["transport"], allow_network=args.allow_network)),
                              journal, {tier: Rates(**rate) for tier, rate in cfg["rates"].items()})
            result = evaluate_qa(export_dir=args.export, labels_file=args.labels,
                                 model=model, journal=journal)
            (args.output / "report.json").write_bytes(dumps(result))
        finally:
            journal.close()
    elif args.command == "doctor":
        cfg, goals, actions, _ = read_config(args.config)
        result = {"configuration_valid": True, "goals": len(goals), "actions": len(actions),
                  "models": {r: v["settings"]["model"] for r, v in cfg["models"].items()},
                  "network_attempted": False, "native_started": False,
                  "notice": "Configuration validation does not qualify models, perception, or motion"}
    else:
        cfg, goals, actions, policy = read_config(args.config)
        if not args.allow_network:
            raise PermissionError("Live run requires explicit --allow-network")
        if any(m["settings"].get("paid", True) for m in cfg["models"].values()) and not args.allow_paid:
            raise PermissionError("Paid model configuration requires --allow-paid")
        args.output.mkdir(parents=True, exist_ok=False)
        journal = Journal(args.output / "journal.sqlite", cfg["episode"],
                          max_microusd=cfg["max_api_microusd"], max_calls=cfg["max_model_calls"])
        models = {}
        for role, value in cfg["models"].items():
            settings = ModelSettings(**dict(value["settings"], allow_paid=args.allow_paid))
            transport = HttpTransport(**dict(value["transport"], allow_network=args.allow_network))
            models[role] = JsonModel(settings, transport, journal,
                                     {tier: Rates(**rate) for tier, rate in value["rates"].items()})
        native = None
        runner = None
        try:
            native = ProcessNative([s.replace("{episode}", cfg["episode"])
                                    for s in cfg["native_command"]], episode=cfg["episode"],
                                   timeout_s=cfg["limits"].get("max_wall_s", 600))
            runner = EpisodeRunner(args.output, cfg["episode"], cfg["goal_text"], native.bindings(),
                                   goals, actions, models["executive"], models["verifier"], journal,
                                   limits=RunLimits(**dict(cfg["limits"], allow_motion=args.allow_motion)),
                                   context_policy=policy, narrator_model=models.get("narrator"))
            result = runner.run()
        finally:
            try:
                if runner:
                    runner.close()
            finally:
                try:
                    if native:
                        native.close()
                finally:
                    journal.close()
    print(dumps(result).decode())
    if args.command == "run" and (result.get("error") or not result.get("stop_acknowledged")):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
