"""Native matched-pair episode, narrowed from the private radio pilot.

No task switching, symbolic primitives, memory, demonstrations or oracle inputs.
The parent process owns the hard deadline and reaps this process group.
"""

import argparse
import json
import os
import signal
import time
import uuid
from contextlib import ExitStack
from pathlib import Path

import numpy as np

from experiments.behavior.config import load_config
from experiments.behavior.contracts import Stamp
from experiments.behavior.model import RadioModel, open_campaign, qualify_endpoint
from experiments.behavior.native import BEHAVIOR_COMMIT, check_source, native_config
from experiments.behavior.observations import BehaviorObservationFilter, EvidenceStore
from experiments.behavior.preprocessing import verify_native_preprocessing
from experiments.behavior.supervisor import BLOCK, MATCHED_EXECUTIVE, STEPS, SkillSupervisor
from physical_harness.integrations.experiment.journal import Journal


def supervised_prefix(candidate):
    if candidate not in ("corvid", "behavior-skill"):
        raise ValueError("Unknown candidate")
    return 1 if candidate == "corvid" else 32


def selected_prefix(reply, stamp, remaining, prefix):
    if reply["stamp"] != stamp:
        raise ValueError("Stale policy reply")
    actions = np.asarray(reply["actions"], dtype=np.float32)
    if (actions.ndim != 2 or actions.shape[1] != 23 or not 1 <= len(actions) <= 256
            or not np.isfinite(actions).all() or not 1 <= remaining <= BLOCK
            or prefix not in (1, 32)):
        raise ValueError("Invalid native action chunk or budget")
    return actions[:min(prefix, remaining)].copy()


def execute_loop(evaluator, hook, transport, supervisor, ingress, stamp, directory,
                 trial, save, prefix, *, preprocessing=verify_native_preprocessing):
    started = time.monotonic()
    skill_end = 0
    terminated = truncated = False
    with (directory / "trace.jsonl").open("x") as trace:
        while trial["actions_sent"] < STEPS and not (terminated or truncated):
            if time.monotonic() - started > 3600:
                trial["stop_reason"] = "wall_budget"
                break
            current = stamp.model_copy(update={"sequence": trial["actions_sent"]})
            observation = ingress.convert(evaluator.obs, current, time.monotonic())
            if trial["actions_sent"] == skill_end:
                instruction, block_steps = supervisor.choose(observation, ingress.store)
                if instruction is None:
                    trial["stop_reason"] = supervisor.stop_reason
                    break
                skill_end = trial["actions_sent"] + block_steps
            if time.monotonic() - started > 3600:
                trial["stop_reason"] = "wall_budget"
                break
            call_start = time.monotonic()
            reply = transport.infer({
                "stamp": current.model_dump(), "instruction": instruction,
                "proprio": observation.proprio,
                "rgb": {k: ingress.store.read(v) for k, v in observation.rgb.items()},
            })
            rpc_s = time.monotonic() - call_start
            actions = selected_prefix(reply, current.model_dump(),
                                      skill_end - trial["actions_sent"], prefix)
            if not trial["calls"]:
                trial["preprocessing_proof"] = preprocessing(evaluator.robot, actions)
            trace.write(json.dumps({"sequence": current.sequence, "instruction": instruction,
                                    "inference_s": rpc_s, "prefix_steps": len(actions),
                                    "observation": observation.model_dump(),
                                    "raw_actions": actions.tolist()}) + "\n")
            trace.flush()
            for action in actions:
                hook.action = action
                terminated, truncated = evaluator.step()
                trial["actions_sent"] += 1
                if terminated or truncated:
                    break
            trial["calls"].append({"sequence": current.sequence, "inference_s": rpc_s,
                                   "instruction": instruction, "prefix_steps": len(actions)})
            save()
        if supervisor.pending is not None and trial["actions_sent"] > supervisor.pending["start"]:
            current = stamp.model_copy(update={"sequence": trial["actions_sent"]})
            supervisor.verify(ingress.convert(evaluator.obs, current, time.monotonic()),
                              ingress.store)
    trial.update(native_terminated=bool(terminated), native_truncated=bool(truncated),
                 physical_s=trial["actions_sent"] / 30, wall_s=time.monotonic() - started)
    trial.setdefault("stop_reason", "native_end" if terminated or truncated else "step_budget")


def jsonable(value):
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    if hasattr(value, "detach"):
        return value.detach().cpu().tolist()
    if isinstance(value, (np.ndarray, np.generic)):
        return value.tolist()
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--candidate", choices=("corvid", "behavior-skill"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--endpoint", type=Path, required=True)
    for flag in ("allow-motion", "allow-paid", "allow-network", "licenses-accepted"):
        parser.add_argument("--" + flag, action="store_true", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    if os.environ.get("CUDA_VISIBLE_DEVICES") != str(config.simulator_gpu):
        raise ValueError("Simulator GPU fence missing")
    check_source(config.native.source, BEHAVIOR_COMMIT)
    endpoint = json.loads(args.endpoint.read_text())
    qualify_endpoint({"architecture": {"input_modalities": ["image"]},
                      "endpoints": [endpoint]}, config.model)
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"passed": False, "benchmark_result": False, "task": "turning_on_radio",
              "candidate": args.candidate, "trials": [], "source_revision": BEHAVIOR_COMMIT,
              "memory_shadow_enabled": False, "skill_supervisor_enabled": True}

    def save():
        (args.output / "RADIO_pilot.json").write_text(json.dumps(report, indent=2) + "\n")

    def interrupt(signum, frame):
        raise KeyboardInterrupt("Native worker interrupted")

    signal.signal(signal.SIGTERM, interrupt)
    save()
    try:
        import omnigibson as og
        import torch
        from omegaconf import OmegaConf
        from omnigibson.eval.evaluator import Evaluator, resolve_instance_ids
        from omnigibson.eval.utils.eval_utils import seed_everything
        from omnigibson.macros import gm

        from experiments.behavior.policy_server import HttpPolicyTransport

        if config.native.source not in Path(og.__file__).resolve().parents:
            raise ValueError("Imported simulator differs from pinned source")
        gm.HEADLESS = True
        seed_everything(0)
        cfg = native_config(config.native.source)
        cfg["robot"] = OmegaConf.load(cfg.pop("robot_config_path"))
        native_id = resolve_instance_ids("turning_on_radio", [0], mode="public_test")[0]
        if int(native_id) != 301:
            raise ValueError("Unexpected public radio instance")

        class OneAction:
            action = None

            def reset(self):
                self.action = None

            def forward(self, obs):
                if self.action is None:
                    raise RuntimeError("No action armed")
                action, self.action = self.action, None
                return torch.from_numpy(action)

        with Evaluator(OmegaConf.create(cfg)) as evaluator, ExitStack() as stack:
            hook = OneAction()
            evaluator.policy = hook
            evaluator.reset()
            evaluator.load_task_instance(native_id)
            evaluator.reset()
            if evaluator.robot.action_dim != 23 or not np.isclose(og.sim.get_sim_step_dt(), 1/30):
                raise ValueError("Unexpected native controller contract")
            directory = args.output / "trial-0"
            directory.mkdir()
            store = EvidenceStore(directory / "evidence")
            ingress = BehaviorObservationFilter(store)
            stamp = Stamp(session=str(uuid.uuid4()), epoch=0, sequence=0)
            local = Journal(directory / "supervisor.sqlite", stamp.session,
                            max_calls=18, max_microusd=3_000_000)
            stack.callback(local.close)
            campaign = open_campaign(config.campaign)
            stack.callback(campaign.close)
            model = RadioModel(config.model, endpoint, local, campaign,
                               allow_paid=args.allow_paid, allow_network=args.allow_network)
            supervisor = SkillSupervisor(model, directory / "supervisor.jsonl", MATCHED_EXECUTIVE)
            transport = HttpPolicyTransport(config.port)
            if transport.reset(stamp.model_dump())["stamp"] != stamp.model_dump():
                raise ValueError("Wrong reset acknowledgement")
            trial = {"index": 0, "native_id": int(native_id), "actions_sent": 0,
                     "calls": [], "native_success": None, "completed": False}
            report["trials"].append(trial)
            save()
            evaluator.start_recording(str(directory / "rollout.mp4"))
            execute_loop(evaluator, hook, transport, supervisor, ingress, stamp, directory,
                         trial, save, supervised_prefix(args.candidate))
            evaluator.stop_recording()
            # Hidden native metrics are read only here, after all agent calls.
            metrics = {}
            for metric in evaluator.metrics:
                metrics.update(metric.aggregate(evaluator.env))
            trial.update(metrics=jsonable(metrics), native_success=bool(evaluator.env.task.success),
                         completed=True)
            report["passed"] = True
            save()
    except BaseException as error:
        report["error_type"] = type(error).__name__
        report["passed"] = False
        save()
        raise


if __name__ == "__main__":
    main()
