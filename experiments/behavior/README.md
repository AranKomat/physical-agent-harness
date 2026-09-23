# Matched BEHAVIOR Radio Experiment

This package ports the useful parts of the private experiment lab into the
public repository: legal sensor ingress, two motor adapters, the matched GPT
supervisor, native action preprocessing, worker ownership, and durable model
accounting. It does not upload the lab or make it a dependency.

**Status:** offline-tested migration, not yet live-requalified. Original live
results in [the progress report](../../docs/experiments/2026-09-21/EXPERIMENT_PROGRESS_20260921.md)
were obtained with the private runner. Passing software tests does not establish
task success, checkpoint competence, or reproduction of those results.

## Frozen Protocol

The pair runs Corvid followed by Behavior-Skill, sequentially. Both use
`turning_on_radio`, native instance 301, seed 0, 3,224 actions at 30 Hz,
384-step supervisor blocks, and at most nine executive plus nine verifier calls.
The prompts are identical across candidates and hash-checked by tests.
Corvid replans every action; Behavior-Skill executes a 32-action prefix. These
are intentionally different published control recipes, not different task budgets.

The executive sees current legal camera images and proprioception. The verifier
receives fresh post-action evidence. Native success metrics are read only after
the final agent call. Memory, privileged object poses, pre-mapping, and future
frames are not supplied. Training overlap is permitted and disclosed: this is
not a held-out motor generalization claim or a full harness-memory comparison.

Each episode has a 3,600-second rollout budget and a 4,200-second native process
limit. Policy readiness has a 300-second deadline. A failed worker/receipt stops
the pair; there is no automatic provider fallback or model retry. A successful
process receipt means the protocol completed, not that the radio task succeeded.

## Offline Use

From the repository root:

```bash
python -m pip install -e '.[behavior,dev]'
python -m experiments.behavior plan --config configs/behavior/matched-radio.example.json
pytest -q
ruff check .
```

`plan` only renders the protocol and commands. It makes no network/model calls,
writes no files, and does not require the simulator or checkpoints. Relative
runtime paths resolve against the configuration file, not the working directory.
The output argument resolves against the working directory.

## Provisioning Is Explicit

Actual execution requires Linux, two NVIDIA GPUs, sufficient VRAM for the pinned
upstream stacks, and at least 60 GiB free output space before each episode.
Keep separate native, Corvid, and Behavior-Skill Python environments; their
CUDA/JAX/Isaac dependencies are not installed by this package. Follow the pinned
upstream installation instructions and install this package's `behavior` extra
into each worker environment. The orchestrator does not need Isaac or JAX.

Provision these clean source checkouts outside tracked source (the example uses
the ignored `runtime/` directory):

| Component | Upstream | Revision |
| --- | --- | --- |
| Native BEHAVIOR | [BEHAVIOR-1K](https://github.com/StanfordVL/BEHAVIOR-1K) | `b1979916ec1549b10a4e65e630bc6504a9af1b00` |
| RPC transport | [RPent](https://github.com/RLinf/RPent) | `886b3b274d3dd30bbc15615ea512d65ae90bc8b3` |
| Corvid runtime | [Corvid BEHAVIOR fork](https://github.com/charles-rl/BEHAVIOR-1K) | `cc60a469a376397f6fb579087150d9e987b7e34e` |
| Behavior-Skill runtime | [pi05-behavior-skill](https://github.com/mafangniu/pi05-behavior-skill) | `7ca6eace02aaba2d8ce19af600b85dd04a60d720` |

The Corvid OpenPI root is `b1k-baselines/baselines/openpi` inside its fork.
The launcher sets explicit import paths for these sources and checks pinned
revisions; extra dependency paths can be declared in each runtime's `pythonpath`.
Install the pinned RPC stack's dependencies in the workers as well. All simulator
assets, tokenizer/model caches, and native evaluation dependencies must already
be available. Workers run with Hugging Face/Transformers offline mode enabled.

Obtain checkpoints yourself, subject to their access gates and license terms:

| Candidate | Hugging Face repository | Revision / subtree |
| --- | --- | --- |
| Corvid | [0Corvid0/pi05-b1k-families](https://huggingface.co/0Corvid0/pi05-b1k-families) | `b627f22777d9babc6d4b06d7f088266dc484dd8c`, `backbone_foundation_100ep` only |
| Behavior-Skill | [mafangniu/Behavior-Skill-VLA-Checkpoints](https://huggingface.co/mafangniu/Behavior-Skill-VLA-Checkpoints) | `98941096c94b0f978391d8a0accc699c32ec8b2a`, `pi05-pt50-skill` |

Create integrity manifests after downloading the pinned files. Set the checkpoint
argument to the directory containing the selected checkpoint payload, not the
whole multi-checkpoint repository:

```bash
python -m experiments.behavior manifest --candidate corvid \
  --checkpoint runtime/corvid-weights --output runtime/manifests/corvid.json
python -m experiments.behavior manifest --candidate behavior-skill \
  --checkpoint runtime/behavior-skill-weights/pi05-pt50-skill \
  --output runtime/manifests/behavior-skill.json
```

Expected payload inventories are 40 and 727 files respectively. Keep manifests
outside checkpoint trees. Local hashing detects subsequent changes; it does
**not** prove that a download came from the claimed upstream revision. Preserve
your download provenance separately. Do not publish gated weights or assets.

Make a local configuration based on `configs/behavior/matched-radio.example.json`,
using the ignored `*.local.json` naming pattern. Point it at actual interpreters,
sources, caches, checkpoints and manifests. Then run:

```bash
python -m experiments.behavior doctor --config configs/behavior/matched-radio.local.json
```

`doctor` checks local paths and source revisions without starting workers. It
does not certify installed dependencies, license eligibility, CUDA compatibility,
model availability or control quality. Those still need live qualification.

## Budgets And Execution

The example preserves the historical `openai/gpt-6-astra`, `openai/flex` route,
medium reasoning, and recorded prices. It is not a current availability/pricing
claim. Execution validates endpoint metadata and refuses unsupported changes.
Credentials come only from the configured environment variable, never JSON.

The example budget is a **new standalone campaign**, 36 calls and $6 maximum
reserved exposure for the pair. It is not spending approval and does not import
the private campaign's historical accounting. Never create a fresh journal to
bypass existing caps or unresolved reservations. Continuing an existing campaign
requires reconciling its journal and authorization before execution.

Campaign and episode journals reserve before sending. Known costs are settled;
unknown outcomes retain their holds. Unresolved campaign holds block new runs.
Caps persist across restarts. Do not delete or reset journals to retry failures.

After provisioning, license review/acceptance, budget approval and credential
setup, explicitly opt into all four effects:

```bash
python -m experiments.behavior run \
  --config configs/behavior/matched-radio.local.json \
  --output runs/matched-radio-new \
  --allow-network --allow-paid --allow-motion --licenses-accepted
```

The license flag confirms the operator has accepted the applicable simulator,
dataset and checkpoint terms; it does not grant rights or submit access requests.
This is simulator-only, not a physical-robot deployment command. Output must be
a new directory. The launcher owns and reaps its worker process groups, captures
the resolved configuration, source-module hashes, protocol, logs and receipts,
and retains observations/actions/videos locally. Keep those artifacts private
unless separately reviewed for publication rights and privacy.

## Hybrid Base Qualification

`base_hold.py` constructs bounded body-frame base commands while preserving
measured absolute torso/arm positions and inverse-scaled smooth-gripper positions.
It rejects incompatible or asymmetric gripper feedback instead of clipping.
It is separate from learned-policy actions and does not authorize motion or
establish a safe hold for a carried object.

`base_hold_audit` opens the pinned radio scene, captures legal observations, and
compares the candidate hold against the native no-op action. Six command vectors
are checked through official preprocessing but never applied in default mode.
Default mode calls neither `evaluator.step` nor a policy/model service. Ordinary scene reset/loading still
advances setup physics; zero agent actions is not a claim of zero physics ticks.

Run only in a provisioned native environment with GPU 0 selected, applicable
licenses already accepted, and an external process timeout:

```bash
python -m experiments.behavior.base_hold_audit \
  --source /path/to/pinned/BEHAVIOR-1K --output /path/to/new/audit-directory \
  --allow-simulator --licenses-accepted
```

A passing audit qualifies command equivalence only. It does not qualify online
localization, full-body swept clearance, measured stopping, or a policy handoff.
No base-motion command is exposed by this audit.

For a separately authorized stationary-hold diagnostic, add
`--allow-motion --hold-steps 60`. This sends at most 60 controller ticks with zero
base velocity and fixed initial torso/arm/gripper targets. Every attempted and
completed action is recorded. Five consecutive low-velocity captures are required
for a measured settled result; a timeout is not a stop acknowledgement. Joint
drift or unexpected base velocity aborts the diagnostic. This tests settling from
an ordinary reset, not braking a moving base, collision clearance, navigation,
or task completion. There is no policy inference or GPT call in either mode.
Add `--full-hold-window` to continue through the requested tick budget after the
first five settled samples. Losing measured settling after it was established
aborts this sustained diagnostic; it cannot pass merely by settling again later.

Both modes now save native intrinsics bound to each captured observation's
stamp, timestamp and RGB/depth evidence IDs. No simulator camera/world pose is
read. A calibration-capture failure aborts while preserving completed action
accounting. Intrinsics alone do not qualify extrinsics or localization.

### Separate Empty-Scene Response Calibration

Only with explicit authorization, `experiments.behavior.empty_base_audit` creates
an empty floor-plane scene with the pinned R1Pro controller configuration. This
is **not** a benchmark trial or a way to override hybrid admission. It uses
proprioception only, without a VLA/GPT or global-pose observation. It requires
`--allow-empty-scene-motion --licenses-accepted`, plus the same `--source`, fresh
`--output`, GPU-0 environment and external watchdog as above.

After measured initial settling, it runs six 15-tick pulses: +/-0.03 m/s on each
translation axis and +/-0.05 rad/s yaw. Each is followed by at most 60 hold ticks
requiring five consecutive samples below 0.002 m/s and 0.005 rad/s, together with
the existing joint/gripper settling criteria. Arm, torso and gripper targets
stay fixed. Response mismatch, excess speed, joint/gripper drift or failed stop
aborts, with at most 60 additional emergency-hold ticks. All dispatched ticks
are counted; the maximum normal schedule is 510 ticks, plus 60 emergency ticks.
Environment construction/reset physics is disclosed separately.
The fixture also applies the pinned evaluator's 250 kg base-footprint mass and
its pre-trial 25-physics-tick `keep_still`/snapshot initialization. These setup
operations are never repeated during a pulse or braking measurement. Earlier
fixture attempts without all of these steps are retained as separate failures.

For an explicitly scoped response-characterization experiment only,
`--characterize-unsettled` permits the fixed pulses after an unsuccessful bounded
stop attempt. Failed stops remain recorded, acknowledgement times are null, and
`passed` is **always false**, even if responses look reasonable. Speed and
joint/gripper drift aborts remain enforced. This option is restricted to the
empty-scene runner and must not be used as a benchmark or hybrid gate override.
`--spawn-height` exposes only the declared 0, 0.01 and 0.05 m calibration conditions;
an elevated result is not floor-level navigation qualification.
`--posture-from-audit` can initialize only robot joint positions from a previously
passed, pinned native hold audit in this empty fixture. It excludes base/world
poses and all scene state, records source provenance, and is not an ordinary
benchmark reset or a policy-training operation.

Always inspect the saved receipt, not just the process exit code: simulator
shutdown can terminate the Python process with status zero even after a failed
diagnostic. Characterization completion likewise is never a qualification pass.

Braking-distance output is a sampled proprioceptive-velocity integral, not an
independent position measurement. A passing component test still does not
qualify radio-scene clearance, localization, navigation or policy handoff.

## Migration Boundaries

This port intentionally replaces machine-specific paths and private campaign
imports with standalone configuration and persistent journals. It adds explicit
execution opt-ins, counts the response schema in the input allowance, and reports
RPC latency separately from GPT boundary time. Exact timing/accounting fields
therefore need not equal the historical private runner's fields. Unrelated lab
experiments and operational utilities were not migrated.

No GPU trials, paid model calls, weight downloads or license acceptance were
performed to validate this migration. Offline tests cover the full action-loop
plumbing with fake workers, causal packets, prompts, budgets, adapters, cleanup
and manifest integrity. Next qualification is a deliberately authorized native
smoke test, followed by a matched pair only if that passes.

The private lab is unchanged. Credentials, private billing journals, host/SSH
details, checkpoints, simulator assets, captured media, backup archives, and
copied upstream repositories do not belong in Git. No software license has been
chosen for this repository; upstream licenses remain separate obligations.

## Simulator-Only Unknown-Clearance Diagnostic

`native_base_exploration` is an explicitly authorized research diagnostic, not
a benchmark controller or gate override. It uses the ordinary radio start and
legal RGB/depth/proprioception, records every fresh capture, and separately
journals completed native steps before capture failures. The pulse driver's
`actions_executed` counts successful step-and-capture callbacks; use the outer
`native_steps_completed` for native execution accounting if capture fails.

Run only with explicit simulator exploration authorization:

```bash
python -m experiments.behavior.native_base_exploration \
  --source /path/to/pinned/BEHAVIOR-1K --output /private/new-run \
  --allow-simulator --licenses-accepted \
  --allow-unknown-clearance-exploration --pulses forward
```

Use the same GPU-0 environment and external watchdog as other native diagnostics.
Clearance remains unknown even if response and braking pass. Inspect `audit.json`;
simulator shutdown status alone is not a diagnostic result.

For isolated sensor/controller debugging, `--record-quarantined-robot-truth`
optionally writes robot-base and camera world poses to a separate
`diagnostic_truth.jsonl`. This is privileged **evaluation-only** data: never use
it as controller input, policy context, target selection or a localization
fallback. It is disabled by default, its use is declared in the receipt, and
the logger returns no value to the pulse driver. Runs using it are diagnostic
runs, not evidence of oracle-free end-to-end qualification.

`--head-depth-shadow` adds opt-in fixed-reference head-depth estimates while
leaving pulse actions unchanged. Shadow failures are recorded, not silently
reset or treated as collision clearance. The simulator runner preloads Open3D
before the first capture timestamp; current capture gaps remain bounded.

## Tiny-Perturbation Handoff Diagnostic

`python -m experiments.behavior.hybrid_short` runs one A or B condition against
an owned, pinned Behavior-Skill server. It requires a verified policy load
receipt and explicit simulator/unknown-clearance authorization. A receives 384
policy actions; B first receives the tested short forward pulse and must pass
response, stop and live head-shadow stability checks before the same 384-action
ceiling. Native action provenance includes the classical exposure. Inference
noise is indexed from the acknowledged handoff reset so matching policy chunks
use matching noise. The original state/image/action normalization and 32-action
prefix remain unchanged.

This is neither target-directed staging nor the main equal-total-action radio
comparison. No GPT calls or simulator-truth reads occur in this runner. Inspect
`hybrid_short.json` for complete versus censored exposure and failure fields;
process exit alone is insufficient. Recordings and raw evidence remain private.

`--assisted-target-probe` adds a separate post-policy diagnostic, not another A/B
condition. It first settles the empty-handed robot, publishes a frozen legal
observation in `selection_request.json`, and pauses without stepping for at most
five minutes. An operator must inspect that episode's images and provide a
`selection_response.json` bound to the exact stamp and head RGB/depth evidence
IDs. `decision: not_visible` refuses motion. `decision: yaw` additionally requires
an interior integer `pixel_uv` and assisted `direction` of +1 or -1. The pixel
must have valid measured depth. Direction/identity are assisted inputs, not a
qualified detector or navigation planner.

At most one 15-tick 0.05 rad/s yaw is sent, followed by measured braking. Joint,
gripper and instantaneous speed aborts stay active. Stop checks allow at most
60 hold ticks, with a separate bounded emergency-hold attempt after failure.
Paused annotation time is recorded; this lane neither runs nor bypasses the
strict hybrid freshness gate, and cannot qualify autonomous live staging. No
annotation or coordinates may be recycled from an earlier episode. Inspect
`assisted_probe.passed` and `outcome` separately from overall protocol completion.
