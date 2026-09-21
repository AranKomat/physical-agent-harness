# Experiment Progress: 2026-09-21

This report summarizes private BEHAVIOR/R1Pro development experiments. The public
repository contains reusable harness code, not all native drivers or raw results.
Weights, simulator assets, captured observations, videos, credentials and billing
journals remain outside this repository. Numerical and qualitative results below
are development findings, not an independently reproducible public leaderboard.

## Bottom Line

Bounded live semantic integration and controlled causal-memory experiments work.
Several released multitask policies have working native interfaces. **A reliable
general motor and a task-success improvement from GPT supervision or memory have
not been demonstrated.** No policy training was performed by us.

Stay with BEHAVIOR, use one frozen multitask motor where possible, and disclose
benchmark training overlap. Earlier claims that no released compatible multitask
checkpoint exists are superseded. Compatibility is not performance qualification.

## Stage Status

Latest hybrid prerequisite findings: [calibrated native hold, stationary odometry,
and robot-geometry coverage](HYBRID_CALIBRATED_GEOMETRY_20260921.md). This narrows the
current issue to unknown near-robot coverage and unqualified conservative collision
bounds; it is not a new policy failure or demonstrated task-success improvement.

| Stage | Status and scope |
| --- | --- |
| Live semantic cycle | Bounded native observation, GPT executive/verifier, ledger and termination checks passed |
| Prospective routing | Completed over controlled scripted traces, without affecting motion |
| Multi-trace memory | Corrected causal replay and executive-choice ablations completed; no executed task benefit |
| Motor bake-off | Several interfaces and screens completed; performance unresolved |
| Radio pilot | Short integration runs and longer supervision diagnostics completed without native success |
| Hard Halloween harness pilot | Not started; short atomic probes are not a full task episode |
| Full-system robustness | Not started |
| Final policy-only / supervised / memory comparison | Not started |

## Harness and Memory Evidence

- A stationary native scene supported a visible-fireplace diagnostic. The first
  three-call run reached semantic completion but supplied an invalid `finish`
  argument. The failure was preserved; a schema-contract fix and separate
  three-call rerun completed with zero motion. This was not radio-task success.
- Five short moving GPT/harness pilots executed 16, 96, 16, 16 and 16 actions.
  Verifiers stayed uncertain and the executive stopped unresolved. At 30 Hz,
  these are only 0.53-3.2 simulated seconds each, not success-rate trials.
- Legal posed RGB-D keyframes and events were captured in live shadow mode;
  earlier decision cutoffs excluded later verifier events. Memory did not change
  live executive inputs or motor behavior.
- Four scripted multi-object/multi-place traces provided 32 shadow boundaries,
  including displacement, failed pickup, recovery, occlusion and revisit. Full
  M0/M1/M2 answer ablations ran on three traces. Prospective routing used four
  model route declarations before selected-tier answers on each of three traces.
  The shared question template and manual review limit statistical inference.
- An early consequential-memory run leaked a future place-B identity limitation
  through metadata. Its comparisons were invalidated and preserved. Phase-gated
  metadata correction left RGB, event timestamps and labels unchanged; corrected
  traces passed cutoff and future-fact audits.
- Twelve corrected executive-choice calls across two traces showed event memory
  enabling a dated place-B search lead and historical pixels enabling opposite
  left/right scan choices after opposite displacements. M0 appropriately requested
  missing history. These are proposed decisions on frozen scripted traces, not
  executed robot outcomes or autonomous task improvement.

Perception remains unqualified: the short native RTSM/odometry sequence measured
0.895 frames/s with obvious false semantic labels. A stride-2 odometry-only path
measured about 4.27 Hz; that is not end-to-end perception throughput or measured
localization accuracy. Navigation, contact localization, collision checking and
native recovery also need qualification.

## Recent Motor Screen

All trials used ordinary public-test index 0, simulator seed 0, legal cameras and
proprioception, with no GPT, memory, oracle inputs, training or intermediate demo
resets. A common cap of 3,224 actions or 1,200 post-initialization wall seconds
produced unequal simulated horizons. Every row had native success false and Q=0.

| Candidate | Task | Actions | Simulated s | Wall s | Median RPC s |
| --- | --- | ---: | ---: | ---: | ---: |
| Kmy GR00T | Radio | 1720 | 57.33 | 1200.43 | 0.221 |
| Kmy GR00T | Trash | 1822 | 60.73 | 1200.18 | 0.223 |
| Corvid | Radio | 1908 | 63.60 | 1200.41 | 0.168 |
| Corvid | Trash | 1825 | 60.83 | 1200.18 | 0.171 |
| Behavior-Skill | Radio | 3224 | 107.47 | 397.77 | 0.166 |
| Behavior-Skill | Trash | 3224 | 107.47 | 404.02 | 0.176 |

Kmy and Corvid replan every action; Behavior-Skill executes 32-action prefixes.
RPC includes transport/encoding, not just network inference. One start per task
and unequal horizons cannot establish a general ranking.

Videos showed Corvid grasping/carrying a bin despite no completed trash predicate;
its radio run instead interacted with the refrigerator. Behavior-Skill approached
and contacted the radio but displaced/rotated it instead of activating it. Kmy
navigated without completion and had markedly tilted late trash views. These
are qualitative observations, not additional native scores or measured falls.

## Focused Follow-Ups

| Condition | Actions | Simulated s | Wall s | Success / Q |
| --- | ---: | ---: | ---: | --- |
| Behavior-Skill + GPT, radio | 3224 | 107.47 | 468.25 | false / 0 |
| Corvid trash, native301 | 6000 | 200.00 | 4056.67 | false / 0 |
| Corvid trash, native302 | 6000 | 200.00 | 4619.87 | false / 0 |

All reached action caps without runtime errors. Behavior-Skill's 9 executive
and 9 separate verifier calls chose approach twice, then press seven times;
all power verdicts were uncertain. It used a fixed skill menu and current views,
not the full memory harness. Repeated ineffective pressing does not isolate
contact precision from missing progress/recovery context.

Corvid's first longer trash run carried/repositioned the bin but did not collect
trash; the second interacted with the refrigerator and microwave. The intended
trash prompt was logged for all 12,000 actions and source forwarding was checked.
These runs had no GPT assistance and cannot test obedience to GPT advice.

A separate no-GPT Corvid instruction crossover ran two 40-s episodes: radio then
refrigerator, and reversed order, switching after 20 s. Both approached/stayed
near the radio table, including during the initial refrigerator instruction.
No convincing redirection was observed. Short navigation phrasing may be outside
the training distribution; this is not proof of universal language insensitivity.

## Matched GPT Comparison: Completed

One Corvid + GPT radio episode and one Behavior-Skill + GPT radio episode
completed sequentially under a frozen protocol. Both reached their action caps
without runtime errors or wall-time censoring; both native outcomes were false
with final Q=0.

| Candidate + GPT | Actions | Simulated s | Wall s | Policy calls | GPT calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Corvid | 3224 | 107.47 | 2372.55 | 3224 | 18 |
| Behavior-Skill | 3224 | 107.47 | 583.55 | 101 | 18 |

- Same ordinary native301 start, simulator seed0, 3,224-action / 107.47-s cap.
- Same 3,600-s post-initialization wall cap and 4,200-s native-process deadline.
- Same GPT-6 Astra medium Flex, executive/verifier prompts, schemas, skill menu,
  current-camera/proprio rules and 384-action decision interval.
- At most nine executive and nine fresh post-action verifier calls per episode;
  no historical memory, retries, provider fallback or mid-pair prompt changes.
- Preserve official motor recipes: Corvid every-action ensemble, Behavior-Skill
  32-action prefix. Model randomness is not paired.

Corvid's executive chose approach seven times and press twice. Behavior-Skill
chose approach twice, then press seven times. All nine verifications per episode
were power-uncertain. Sampled videos show Corvid repositioning around the table
and reaching toward the radio late, versus Behavior-Skill repeatedly contacting,
displacing/rotating it without activation. Neither is a task-success winner.

Median policy RPC was 0.17081/0.17234s respectively. GPT HTTP median latency was
16.85/8.72s despite the shared route, so wall-time differences include provider
latency as well as control recipe, rendering, logging and IPC. The 36 calls cost
$0.72168375 in total and all settled. This is not a general per-call price quote.

Shared protocol fields/prompt hashes and exact initial proprioception equality
passed checks. All 6,448 native actions were finite 23D vectors with contiguous traces;
instructions matched executive choices and verifier evidence was fresh.
Thirteen compact source artifacts matched remote hashes; 126 selected sensor
files, including all GPT current images, passed content hashes. Full every-action
RGB-D is not all retained locally. Both worker sets exited after completion.

Actual observations and adaptive choices differ as trajectories diverge. Equal
information rules do not mean replaying one robot's frames into another. One
episode each is exploratory. A supervision-benefit claim additionally needs
matched policy-only controls and replication, not the old wall-censored screen.

## Exact Recent Checkpoints

| Candidate | Checkpoint revision | Source revision |
| --- | --- | --- |
| [Behavior-Skill](https://huggingface.co/mafangniu/Behavior-Skill-VLA-Checkpoints), `pi05-pt50-skill` | `98941096c94b0f978391d8a0accc699c32ec8b2a` | `mafangniu/pi05-behavior-skill` at `7ca6eace02aaba2d8ce19af600b85dd04a60d720` |
| [Corvid](https://huggingface.co/0Corvid0/pi05-b1k-families), `backbone_foundation_100ep` only | `b627f22777d9babc6d4b06d7f088266dc484dd8c` | `charles-rl/BEHAVIOR-1K` at `cc60a469a376397f6fb579087150d9e987b7e34e` |
| [Kmy GR00T](https://huggingface.co/kmy17518/gr00t-n1.7-b1k-multitask), checkpoint238000 | `5831e9dc0ec1212e9aaa3d96c8e27d2548718a82` | `wensi-ai/Isaac-GR00T` multi-task branch at `58e546025c780ff4cac15671e24d92a6b4984f0f` |

BEHAVIOR source is pinned to `b1979916ec1549b10a4e65e630bc6504a9af1b00`.
Corvid/Kmy report all-100-task training; Behavior-Skill reports 50-task skill
training. No Corvid family experts were used. Benchmark overlap is disclosed;
these are not held-out motor-generalization results. Behavior-Skill accepts
language without its own planner; arbitrary-string acceptance does not establish
reliable arbitrary-skill execution.

Earlier auditions included official radio-only pi0.5/GR00T, RLinf PT50, Ryan
all100 step5000 and StarVLA all-task. None established a reliable general motor;
several RLinf/Ryan probes were far too short to represent full-task evaluation.
Comet PT50 weights were byte-identical to the tested RLinf artifact; a recipe
audit may still matter, but it is not an independent weight candidate. G0.5
recorded-input tests never qualified a complete native action interface. Ryan
step10000 was source/metadata-reviewed, not locally executed.

## Remaining Work

The immediate empirical queue is now the
[Hybrid experiment sequence](HYBRID_EXPERIMENT_SEQUENCE.md), not more long
supervised radio rollouts. Hybrid V0/V0.1 are integrated and offline-tested.
[Native codec equivalence and stationary settling](HYBRID_NATIVE_QUALIFICATION_20260921.md)
passed; nonzero base movement, sensor-derived full-body swept clearance,
online local pose and the classical-to-policy handoff remain unqualified.
Once those gates pass, compare Behavior-Skill A-short/B-short without GPT,
then equal-total-action A/B. Arm staging, GPT and memory follow only after
the relevant motor prerequisites. V0.1 integration itself ran no new GPU trial.

The subsequently authorized [native exploratory response tests](HYBRID_NATIVE_EXPLORATION_20260921.md)
record clearance as unknown without changing strict gates. A small forward pulse
and measured braking passed and reproduced on a fresh reset; a following backward
pulse failed tracking/cross-axis checks despite passing braking. General base
motion and policy handoff therefore remain unqualified. No GPT or VLA inference
was used for these diagnostics.

Use the completed matched pair to isolate instruction conditioning,
fine contact control, visual success observability and progress/recovery context.
The current-view-only supervisor lacks accumulated failed-attempt history and
the fixed menu lacks fine-adjustment/active-inspection actions. Those are plausible
limitations, not established causes or proof that memory would rescue the task.
Preserve exact upstream camera/state/action/normalization recipes. A failed
baseline can improve with supervision; it does not make comparison impossible.

Do not add another architecture layer before these results. Memory task benefit
needs a controllable, genuinely memory-sensitive online episode. Existing
symbolic simulator primitives directly changing hidden state are not a legal
sensor-driven motor fallback. Public test coverage establishes contracts, not
physical competence. Checkpoint/data/source licenses and current challenge rules
must be checked separately before redistribution or submission.
