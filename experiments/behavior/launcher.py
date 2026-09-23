"""Sequential worker ownership, opt-in execution and a persistent campaign lock."""

import fcntl
import hashlib
import json
import os
import platform
import shutil
import signal
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

from experiments.behavior.config import check_runtime
from experiments.behavior.model import endpoint_preflight, open_campaign, require_headroom
from experiments.behavior.radio import supervised_prefix
from experiments.behavior.supervisor import MATCHED_EXECUTIVE, SKILLS, VERIFIER

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def protocol(candidate):
    return {"protocol": "public-matched-radio-v1", "candidate": candidate,
            "task": "turning_on_radio", "native_instance": 301, "simulator_seed": 0,
            "steps": 3224, "prefix": supervised_prefix(candidate), "skill_block_steps": 384,
            "max_model_calls": 18, "model_cap_microusd": 3_000_000,
            "wall_budget_s": 3600, "process_limit_s": 4200,
            "current_context_only": True, "native_success_hidden": True,
            "automatic_retries": False, "held_out_motor_generalization": False,
            "skills": SKILLS, "executive_prompt": MATCHED_EXECUTIVE,
            "verifier_prompt": VERIFIER,
            "executive_sha256": hashlib.sha256(MATCHED_EXECUTIVE.encode()).hexdigest(),
            "verifier_sha256": hashlib.sha256(VERIFIER.encode()).hexdigest()}


def commands(config, config_path, output, candidate):
    runtime = config.corvid if candidate == "corvid" else config.behavior_skill
    directory = output / candidate
    module = "corvid_server" if candidate == "corvid" else "behavior_skill_server"
    args = ["--weights" if candidate == "corvid" else "--checkpoint", str(runtime.checkpoint)]
    policy = [str(runtime.python), "-u", "-m", "experiments.behavior." + module,
              "--source", str(runtime.source), *args, "--manifest", str(runtime.manifest),
              "--receipt", str(directory / "policy.json"), "--port", str(config.port)]
    native = [str(config.native.python), "-u", "-m", "experiments.behavior.radio",
              "--config", str(config_path), "--candidate", candidate,
              "--output", str(directory / "native"),
              "--endpoint", str(output / "endpoint.json"), "--allow-motion", "--allow-paid",
              "--allow-network", "--licenses-accepted"]
    return policy, native


def environments(config, candidate):
    # Policy workers don't need GPT credentials; don't inherit private PYTHONPATH.
    common = {**os.environ, "OMP_NUM_THREADS": "4", "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
              "WANDB_MODE": "disabled", "BEHAVIOR_RPC_SOURCE": str(config.rpc_source),
              "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
              "HF_HOME": str(config.hf_cache), "OPENPI_DATA_HOME": str(config.openpi_cache)}
    runtime = config.corvid if candidate == "corvid" else config.behavior_skill
    policy_root = (runtime.source / "b1k-baselines/baselines/openpi"
                   if candidate == "corvid" else runtime.source)
    base = [PACKAGE_ROOT, config.rpc_source]
    policy = {**common, "CUDA_VISIBLE_DEVICES": str(config.policy_gpu),
              "JAX_PLATFORMS": "cuda", "XLA_PYTHON_CLIENT_PREALLOCATE": "false",
              "PYTHONPATH": os.pathsep.join(map(str, base + [policy_root / "src",
                  policy_root / "packages/openpi-client/src", *runtime.pythonpath]))}
    for key in (config.model.api_key_env, "OPENAI_API_KEY", "CODEX_API_KEY", "HF_TOKEN"):
        policy.pop(key, None)
    native = {**common, "CUDA_VISIBLE_DEVICES": str(config.simulator_gpu),
              "JAX_PLATFORMS": "cpu", "OMNIGIBSON_GPU_ID": "0",
              "OMNIGIBSON_HEADLESS": "1", "OMNI_KIT_ACCEPT_EULA": "YES",
              "NO_ALBUMENTATIONS_UPDATE": "1",
              "PYTHONPATH": os.pathsep.join(map(str, base + [*config.native.pythonpath]))}
    return policy, native


def reap(process):
    if process is None:
        return
    # Kill the owned group even if its leader exited before a grandchild.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=10)


@contextmanager
def campaign_lock(config):
    config.journal.parent.mkdir(parents=True, exist_ok=True)
    with config.journal.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def wait_ready(process, config, env):
    # Run the RPC readiness client in the same explicit policy environment.
    # The orchestrator need not install the GPU or RPent dependency stack.
    code = ("from experiments.behavior.policy_server import HttpPolicyTransport; "
            f"HttpPolicyTransport({config.port}).client.call('healthz', timeout_s=1)")
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Policy exited before readiness")
        try:
            result = subprocess.run([env["python"], "-c", code], env=env["environment"],
                                    capture_output=True, timeout=5, check=False)
            if result.returncode == 0:
                return
        except subprocess.TimeoutExpired:
            pass
        time.sleep(2)
    raise TimeoutError("Policy readiness timeout")


def run_episode(config, config_path, output, candidate):
    directory = output / candidate
    directory.mkdir()
    (directory / "protocol.json").write_text(json.dumps(protocol(candidate), indent=2) + "\n")
    report = {"passed": False}
    policy = native = None
    try:
        if shutil.disk_usage(output).free < 60 * 1024**3:
            raise RuntimeError("At least 60 GiB free required before each episode")
        # Refuse an occupied port instead of connecting to someone else's worker.
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", config.port))
        policy_command, native_command = commands(config, config_path, output, candidate)
        policy_env, native_env = environments(config, candidate)
        with (directory / "policy.log").open("x") as log:
            policy = subprocess.Popen(policy_command, cwd=PACKAGE_ROOT, env=policy_env,
                                      stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            wait_ready(policy, config, {"python": policy_command[0], "environment": policy_env})
            with (directory / "native.log").open("x") as native_log:
                native = subprocess.Popen(native_command, cwd=PACKAGE_ROOT, env=native_env,
                                          stdout=native_log, stderr=subprocess.STDOUT,
                                          start_new_session=True)
                report["exit_code"] = native.wait(timeout=4200)
                result_path = directory / "native/RADIO_pilot.json"
                result = json.loads(result_path.read_text()) if result_path.exists() else {}
                if report["exit_code"] != 0 or result.get("passed") is not True:
                    raise RuntimeError("Native receipt failed, irrespective of process exit code")
                report["passed"] = True
    except BaseException as error:
        report["error_type"] = type(error).__name__
        raise
    finally:
        try:
            try:
                reap(native)
            finally:
                reap(policy)
        except BaseException as error:
            report["passed"] = False
            report["cleanup_error_type"] = type(error).__name__
            raise
        finally:
            report["native_reaped"] = native is None or native.poll() is not None
            report["policy_reaped"] = policy is None or policy.poll() is not None
            (directory / "processes.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def run_pair(config, config_path, output, *, allow_network=False, allow_paid=False,
             allow_motion=False, licenses_accepted=False):
    if not all((allow_network, allow_paid, allow_motion, licenses_accepted)):
        raise PermissionError("Network, payment, simulation and license confirmation required")
    if platform.system() != "Linux":
        raise RuntimeError("Native experiments require provisioned NVIDIA Linux runtimes")
    if not os.environ.get(config.model.api_key_env):
        raise ValueError("Set the configured credential environment variable")
    check_runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    report = {"protocol": "public-matched-radio-v1", "completed": False,
              "benchmark_result": False, "order": ["corvid", "behavior-skill"], "episodes": []}
    (output / "pair.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "implementation-sha256.json").write_text(json.dumps({
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in Path(__file__).parent.glob("*.py")}, indent=2) + "\n")

    def interrupt(signum, frame):
        raise KeyboardInterrupt("Matched pair interrupted")

    previous = signal.signal(signal.SIGTERM, interrupt)
    try:
        with campaign_lock(config.campaign):
            journal = open_campaign(config.campaign)
            try:
                require_headroom(journal, 36, 6_000_000)
            finally:
                journal.close()
            endpoint = endpoint_preflight(config.model, allow_network=True)
            (output / "endpoint.json").write_text(json.dumps(endpoint, indent=2) + "\n")
            (output / "config.json").write_text(config.model_dump_json(indent=2) + "\n")
            for candidate in report["order"]:
                receipt = run_episode(config, output / "config.json", output, candidate)
                report["episodes"].append({"candidate": candidate, "process_receipt": receipt})
                (output / "pair.json").write_text(json.dumps(report, indent=2) + "\n")
            report["completed"] = True
    except BaseException as error:
        report["error_type"] = type(error).__name__
        raise
    finally:
        signal.signal(signal.SIGTERM, previous)
        (output / "pair.json").write_text(json.dumps(report, indent=2) + "\n")
