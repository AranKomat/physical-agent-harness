# Live radio fixture bridge

This document records the earlier deterministic fixture and replay milestones.
For subsequent real GPT cycles, live spatial shadow, controlled memory ablations
and multitask motor tests, see [experiment progress](../experiments/2026-09-21/EXPERIMENT_PROGRESS_20260921.md).
Historical next-step statements below are not the current experiment status.

## Recorded native memory shadow replay, 2026-09-19

The retained one-boundary native radio trace was replayed through the v0.8
memory sidecar without executing another robot action or making a model/API
call. Six genuine source camera images (three before and three after) were
registered, and the initial `decision_required` plus terminal
`verifier_uncertain` events produced two historical cards. Both cards retained
the trusted `radio` entity and `radio-room` place bindings.

The two decision cutoffs finalized successfully while returning the executive's
base context unchanged. Replaying the first cutoff reproduced its packet exactly
and did not expose the later terminal card. This validates native artifact,
event, binding and causal-cutoff wiring; it does not show that memory improves
decisions. The source run executed 16 task-trained fixture actions, reported
native success false, and made no task-success claim.

The private live pilot now has an opt-in memory-shadow path for future runs. The
next evidence milestone is a held-out multi-object, multi-place trace and an
equal-budget M0/M1/M2 comparison, not activation of memory in live context.

## Bounded pilot closeout

Follow-up `radio-harness-bounded-003` completed **600 native actions across 38
boundaries**, with 152 receipt evidence references. This represents 20 seconds
of simulated execution, 104.31 seconds of rollout wall time (scene/model startup
excluded). It stopped at the step budget, with native task success false.
The final head image shows the radio nearer and centered on the table; that
does not establish manipulation success. No task-success-rate claim is made.

The independent artifact checker passed remotely and on the complete local
copy. All task statuses stayed needs_verification; both GPU processes exited.
This closes the bounded wiring pilot, not an autonomous task-solving experiment.
The executive remains deterministic and semantic verification was uncertain.

Current scope keeps BEHAVIOR and defers generalization. Do not replace the motor
with benchmark-trained RoboTwin weights or start adaptation. GPT-6 medium Flex
is selected for future sparse visual verification; its separate saved-image
diagnostic cost $0.0721525. See `VISUAL_VERIFIER_PILOT.md`. It was not a live
reasoning executive or verifier in this 600-action rollout.

This opt-in integration probe uses the task-trained official radio pi0.5 policy.
It is not a general-policy result or a semantic planning evaluation.

`experiments.fixtures.native.NativeFixtureBridge` runs each prepared native
action prefix through the existing executive tool dispatch and HarnessRuntime.
The callback executes simulator steps, captures fresh post-action RGB/proprio,
imports evidence and robot telemetry into SQLite, then returns a SkillReceipt.
The runtime invokes VerificationRouter and sends its event back to the executive.

The bounded prefix being completed is NOT the radio task being complete.
There is deliberately no radio-power detector yet: the verifier returns uncertain,
the task remains needs_verification, and the deterministic executive requests an
inspection. The inspection handler reports that a semantic detector is required;
it does not perform perception or call a model. The outer pilot controls the fixed
step budget and may schedule another prefix. This is not autonomous recovery.
Policy inference occurs before prefix dispatch, in the existing radio pilot.

No native reward, task-success bit or privileged object state enters the harness.
The native success bit stays in the separate evaluator report. World-state changes
refer only to actually captured robot telemetry; no radio-power belief is invented.
Physical timestamps use executed action count times the checked simulator timestep,
not the observation's wall-clock timestamp. RGB content hashes are checked on import.

## Run on the prepared host

Run `scripts/radio_run_control.py` from the physical-ai-lab project with its existing
checkpoint, normalization and permission arguments, plus:

```text
--closed-loop-pilot --pilot-steps 96 --pilot-trials 1
--harness-source /path/to/physical-agent-harness
```

The launcher itself needs `PYTHONPATH=src:radio_runtime/radio_rpent`.
The harness-source directory must contain the physical_harness package. The
launcher adds it only to the native subprocess import path. No new dependencies,
checkpoint conversion, training or paid API calls are needed.

Outputs per trial: `harness.json`, `world.sqlite`, `after-N.json`, hashed sensor
evidence, native trace and rollout video. Source observation sequence, receipt
action count and physical time must agree. Duplicate prefix IDs are reserved
before execution; an ambiguous failure aborts rather than implicitly retrying.

Next milestone: add and independently test legal-observation semantic detection
before using verified success or an actual reasoning executive to control a task.

## Measured run, 2026-09-18

The retained private run contains 96 native actions, six boundaries, 24 receipt
evidence references and 12 deterministic executive dispatches. All six verdicts
were uncertain, with the task still needs_verification and no radio-power belief.
Both native and policy processes were reaped. No paid executive calls were made.
Native success was false at this short 3.2-second simulated horizon; no task
success-rate conclusion is warranted.

The experiment-side artifact checker independently checks receipt/action
counts, physical timestamps, episode-scoped database evidence, sensor content
hashes, executive tool round trips and conservative task status. It passed on
the remote run and again on the complete local copy. Attempt 001 failed before actions because the launcher's RPent
import path was missing; attempt 002 used the corrected path.

The exact bridge revision is retained with the private run. A subsequent
finite-timestamp guard was added and CPU-tested. Current harness tests: 161
passed; experiment-side tests: 183 passed, one skipped. Ruff passes.
