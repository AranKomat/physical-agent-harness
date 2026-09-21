# Matched BEHAVIOR Radio Experiment

This package ports the useful parts of the private experiment lab into the
public repository: legal sensor ingress, two motor adapters, the matched GPT
supervisor, native action preprocessing, worker ownership, and durable model
accounting. It does not upload the lab or make it a dependency.

**Status:** offline-tested migration, not yet live-requalified. Original live
results in [the progress report](../../docs/EXPERIMENT_PROGRESS_20260921.md)
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
