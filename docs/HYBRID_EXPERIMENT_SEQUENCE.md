# Hybrid Experiment Sequence

Updated 2026-09-22 after Action Compiler V1 integration. This sequence supersedes doing
more GPT-supervised full-radio trials before the motor handoff is interpretable.
It does not authorize new spend, training, license acceptance or weakening gates.

## Immediate Three-Step Plan

The 15 stages below are a research roadmap, not a mandatory near-term checklist.
Focus on these three steps before expanding scope:

1. Check radio depth/geometry. The [retained-depth audit](RADIO_DEPTH_AUDIT_20260922.md)
   is complete: no obvious depth-convention mismatch; handle-gap/edge mask
   contamination and optical-axis-depth versus range confusion identified.
   Absolute metric accuracy and contact geometry remain unqualified.
   The subsequent [local SAM 2.1 Large comparison](SAM21_LOCAL_COMPARISON_20260922.md)
   completed on 18 boxes: warm radio inference ~48 ms and ~2.5 GiB total GPU memory
   at end. Masks recover omitted object parts but still include handle-gap
   background. SAM is a semantic-mask candidate, not a qualified geometry fix;
   [live stationary co-residency](SAM_LIVE_SHADOW_20260922.md) now passes:
   peak sampled 21.36 GiB and warm result age 1.18-1.22 s on one 4090.
   That start exercises distractor masks, not positive radio masks. The subsequent
   [policy-only moving shadow run](SAM_MOVING_SHADOW_20260922.md) completed 768
   actions, 25 shadow captures and 13 radio masks at peak sampled 21.44 GiB.
   All 52 partitions reproduce offline; warm return age stays below 2 s, but
   dense capture gaps still reach 3.27 s. Fix capture scheduling next; motion
   and contact geometry remain unqualified.
   The [depth-aware patch replay](DEPTH_SURFACE_PATCHES_20260922.md) then separated
   deeper handle-gap regions from the radio body across three fixed tolerances,
   preserving every valid pixel. This supports separate semantic masks and
   measured patches, not automatic background removal or contact admission.
2. Establish enough observation timing, localization and motion qualification
   for an interpretable short handoff comparison. This is the current work,
   spanning original stages 3/4. Low-space coverage remains unresolved.
3. Compare the short hybrid intervention against the frozen policy, then make
   a go/no-go decision on further investment. Earlier exploratory pairs do not
   establish causal benefit. Defer arm/contact, broad task expansion, memory
   comparisons and duty-cycle optimization until benefit is demonstrated.

## Current Position

The [native hold-codec and stationary-settling diagnostics](HYBRID_NATIVE_QUALIFICATION_20260921.md)
passed. Hold commands match the pinned native convention; a five-tick stationary
diagnostic achieved five measured settled captures. Subsequent labeled
[native exploratory pulses](HYBRID_NATIVE_EXPLORATION_20260921.md) passed forward
response and measured braking at one start, but reverse and yaw tracking failed.
Moving localization, collision clearance and classical-to-policy handoff remain
unqualified. Same-start reproducibility is not general motion qualification.
The V0.1 resolver and telemetry are offline-tested utilities, not implementations
of the missing perception/collision/native callbacks.

A [retained-view depth coverage diagnostic](HYBRID_DEPTH_COVERAGE_20260921.md)
identified substantial blind regions around proposed 5 cm translations. A
[fresh calibrated hold and authored-mesh audit](HYBRID_CALIBRATED_GEOMETRY_20260921.md)
reproduced that result with contemporaneous intrinsics. Short-trace stationary
odometry passed its bounds, but the 60-tick follow-up exceeded them for head
translation and right-wrist rotation; moving localization remains unqualified. Accumulating the
short stationary trace did not resolve blind regions, and upstream planning
spheres do not enclose all authored collision vertices. Separate empty-scene
base-response calibration is authorized, but cannot bypass benchmark clearance.
The [empty-scene response experiment](HYBRID_EMPTY_BASE_DIAGNOSTIC_20260921.md)
did not qualify tracking or stopping. Its failed baseline and cross-axis motion
must be resolved separately from the learned policy; do not promote it to B-short.
The sustained native radio hold passed 60 zero-base ticks. This does not repair
the empty-fixture discrepancy. The subsequent native pulses provide the bounded
moving-base stop evidence; they do not validate the empty fixture.

The [motion-measurement diagnosis](HYBRID_MOTION_MEASUREMENT_DIAGNOSIS_20260921.md)
subsequently isolated inaccurate per-tick odometry and misleading instantaneous
velocity interpretation. Fixed-reference head-depth registration passed forward
and yaw replay checks and a live forward shadow run. This supports a separate,
explicitly labeled tiny-perturbation handoff diagnostic; it does not complete
target localization or certify a navigation corridor.

The [tiny-perturbation A-short/B-short diagnostic](HYBRID_TINY_HANDOFF_20260921.md)
completed with 384 policy actions in each condition, no immediate obvious visual
handoff disruption, and no task success in either condition. This is a limited
positive handoff result, not completion of target-directed stage 3. The next
experiment records same-boundary camera calibration for legal target measurement.

Two [fresh calibrated approaches](HYBRID_TARGET_ACQUISITION_20260921.md) now
completed. One ended without the target in view; the other supports an assisted
offline RGB-D measurement about 1.72 m horizontally from the base. This exposes
the remaining target-acquisition/transit gap, not a completed staging proposal.

## Current Parallel Results

The [acquisition cadence and coverage audits](SINGLE_GPU_DENSE_OBSERVATIONS_20260922.md)
completed on the fresh extended single-GPU trace. Sparse 32-action views do not
pass the existing freshness requirement, and low-body coverage remains absent.
The bounded dense-observation run also completed: all 32 short-step pairs passed
fit and step-size checks versus 0/4 sparse fits in the same window. Four dense
intervals still exceeded the freshness gate at synchronous model boundaries.
Next qualify sensor scheduling and the actual tracker; do not promote independent
pair fits to control or authorize another unknown-clearance transit.

The [single-GPU restore and co-residency test](SINGLE_GPU_REPLAY_20260922.md)
passed with native radio simulation and frozen Behavior-Skill on one RTX 4090:
three no-motion captures/inferences, 18,902 MiB maximum sampled memory and
93.87 ms median warm inference. This qualifies static co-residency only, not
perception capacity, moving throughput or any motion gate. Both workers exited;
the complete private evidence is checksum-verified locally. Before full-stack
experiments, replace legacy GPU1 assignments and check perception co-residency.

The subsequent [grounding capacity probe](SINGLE_GPU_GROUNDING_20260922.md)
passed three fresh no-motion cycles with simulator, policy and detector resident
on GPU0 (20,416 MiB maximum sampled memory). An initial attempt was interrupted
by an unattended driver update and retained as failed. The passing retry uses
driver 580.178.04. The capacity probe shares a policy/detector worker and omits
robot-self-filtering; the normal RPC launcher and positive metric acquisition
still need qualification. It does not advance any motion gate.

The [normal single-GPU RPC integration](SINGLE_GPU_ONLINE_20260922.md) subsequently
passed with the robot self-filter enabled. One fresh 384-action acquisition run
and one separately declared 768-action run completed using policy-only motion;
no classical transit, GPT or memory intervention. The short run ended with a
clipped target and zero accepted detections; the longer run produced 12 accepted
target captures and one gap in its final 13 boundaries. Neither achieved task
success. Concurrent CPU checks reproduced the retained mask/depth/FK geometry,
without qualifying world localization or contact semantics. Migration setup is
no longer the next experiment; continue the stage 3/4 geometric gates.

The [compiler replay](ACTION_COMPILER_REPLAY_20260922.md) processed 78 legal
RGB-D views and produced zero qualified contact actions. The
[GraspGenX readiness audit](GRASPGENX_READINESS_20260922.md) identifies actual
R1Pro gripper/TCP and closure-geometry gaps; inference is not enabled.
The [online grounding report](ONLINE_TARGET_GROUNDING_20260922.md) records the
fresh shadow experiment, not navigation authority. The
[post-policy stop diagnosis](POST_POLICY_STOP_ANALYSIS_20260922.md) preserves
the failed stop gate. A fresh 60-hold diagnostic captured 240 physics substeps;
the velocity/position mismatch persists at that rate, and offline depth shows
little continuing drift after an early offset. No stop estimator was substituted
and no clearance or navigation qualification follows from those diagnostics.

The [joint position-window shadow](JOINT_STOP_SHADOW_20260922.md) now separates
the fresh moving-policy and zero-base hold phases without loosening thresholds.
Dense adjacent depth/FK hold checks also support experimental stop monitoring,
but neither check qualifies moving localization. The
[extended-view coverage audit](EXTENDED_VIEW_CLEARANCE_20260922.md) still finds
all sampled geometry below 40 cm outside the three cameras. The user separately
authorized [one labeled 10 cm exploratory transit](EXPLORATORY_TRANSIT_20260922.md)
with unknown clearance. It completed: 8 cm commanded, 6.67 cm estimated path,
experimental stopping before and after, and no abort. Estimated lateral deviation
was 1.11 cm. No policy handoff or task success was claimed, and this experiment
is not strict Stage 4 admission. Its one-probe authorization has been consumed.

The subsequent [matched target-directed handoff](MATCHED_TARGET_HANDOFF_20260922.md)
also completed in the separately labeled exploratory lane. Both conditions had
1,152 policy actions and 92 classical actions, including 384 fresh-reset policy
actions after control/transit. Both resumed approach without obvious immediate
base retreat. Acquisition states diverged before intervention, so this is not
evidence of causal improvement. Resolve that comparison limitation before a
longer A/B; strict clearance and moving-localization gates remain unchanged.

A [CPU-only acquisition audit](ACQUISITION_REPRODUCIBILITY_20260922.md) now locates
the first mismatch at initial RGB, before either intervention. Initial depth and
proprioception are identical and logged noise indices match. The next GPU check
was five retained-input inferences with no simulator or motion, not a longer drive.
That [single-GPU replay](SINGLE_GPU_REPLAY_20260922.md) has now completed: repeated
identical inputs reproduce within the process, policy-only latency is comparable
to the prior host, and small cross-host action differences remain. A single-GPU
simulator/policy co-residency check subsequently passed, as recorded above.

## Resume After Host Migration

Resume the same 15-stage sequence, not a new policy search. The old stopped VM
is not needed for these fresh experiments; some full historical sensor traces
remain there and must not be assumed durably backed up.

1. Complete: checked pinned grounding inference alongside resident simulator and policy on
   GPU0, with fresh calibrated observations and no applied actions. This is a
   capacity test, not semantic, robot-self-filter or moving-control qualification.
2. Complete: restored the normal grounding worker's verified robot-only self-filter,
   made GPU/path assignments explicit, and completed fresh online acquisition runs.
3. Continue stage 3 metric/multi-view acquisition and stage 4 localization/stop/
   clearance work. Do not reuse remembered target coordinates or silently extend
   the consumed one-probe unknown-clearance authorization.
4. Once admission is established, use repeated balanced-order short A/B pairs
   instead of requiring bitwise-identical independently rendered rollouts.
   Predeclare starts and budgets, report acquisition/handoff distributions and
   include rejected trials. Do not claim causal benefit from the existing pair.
5. Only then proceed to stage 6 and the later arm/contact/GPT sequence. Offline
   compiler analysis may continue independently, without bypassing motion gates.

## Ordered Gates

These are the updated 15 stages. Older experiment reports retain their original
stage numbers; use names rather than equating those historical numbers.

| Stage | Experiment | Status / Prerequisite |
| --- | --- | --- |
| 1 | Integrate Action Compiler V1, software only | Complete at `48695a0`; no native compiler motion |
| 2 | Retained legal RGB-D geometry/catalog replay | First replay complete; zero qualified contact candidates; actual-gripper inference blocked |
| 3 | Online target acquisition | Three fresh shadow resets complete; positive detection and failure cases retained; metric/multi-view qualification incomplete |
| 4 | Bounded target-directed base transit | One separately authorized unknown-clearance probe completed; strict qualification still blocked on moving localization and swept clearance; no metre-scale move |
| 5 | Target-directed A-short/B-short, no GPT | One unknown-clearance exploratory pair completed; handoff operational, causal benefit unproven; strict admission still gated by 3/4 |
| 6 | Equal-total-action A/B radio | After interpretable target-directed short handoff; 3,224 actions each |
| 7 | Arm/torso free-space staging and return | After B; qualified FK/IK, clearance and measured endpoint |
| 8 | C-short, then A/B/C radio | After staging; unchanged frozen policy and explicit handoff envelope |
| 9 | Compiler candidate quality and execution, no GPT | Offline contract checks started; native positive execution still gated |
| 10 | Bounded classical contact/press | After grounded part semantics, contact normal and qualified staging |
| 11 | Screen 2-3 other tasks | Same frozen policy/compiler; no checkpoint search or task-specific switching |
| 12 | GPT selects compiled action IDs | Only after useful deterministic motor competence; no invented joint targets |
| 13 | Event-driven GPT recovery | After 12; target loss, failed primitives, ambiguity and changed state |
| 14 | Current state versus causal memory | Only on a genuinely memory-sensitive online task |
| 15 | Neural duty-cycle optimization | After success; action/DOF time shares are not measured energy |

Async execution, monitoring and energy optimization follow demonstrated
competence; policy-action time share is not measured energy efficiency.

## Immediate Protocol

An explicitly authorized simulator-only exploratory lane now permits bounded
native-radio response pulses with clearance recorded as **unknown**, not free.
It is separate from the strict qualification sequence below. Passing response
and stopping checks in this lane does not establish swept clearance or authorize
a strict hybrid handoff. No GPT or VLA calls are needed for these diagnostics.

Stage 4 uses ordinary resets and bounded local commands after tiny response tests, tens
of ticks rather than hundreds. Pass only with legal finite full native actions,
bounded arm/torso/gripper drift, consistent legal local pose, fresh per-tick
observations, established swept clearance, measured stops and exact action/time
accounting. Include blocked/unknown corridors and failed-stop tests. Do not use
the fixture's always-true geometry callbacks on BEHAVIOR.

Stage 3 validates detector-selected pixels, actual measured depth and legally
estimated camera-to-local-map transforms across several views. RTSM labels are
not sufficient alone given the prior false positives. Visual confirmation may
complement a detector. Any simulator-ground-truth analysis is strictly
out-of-band and unavailable to control, target selection, prompts or retrieval.
Measure error distributions relative to workspace and contact tolerances rather
than inventing a favorable cutoff after seeing outcomes.

For stage 5, use one frozen Behavior-Skill checkpoint and its exact image/state
normalization, full action interface and 32-action prefix. A-short receives 384
policy actions from ordinary reset; B-short adds qualified classical transit,
measured stop, fresh capture and real queue/history/in-flight drain before the
same policy-action ceiling. Total horizons intentionally differ. No GPT, memory,
retreat, task-specific weight routing or training. Log censored exposure rather
than assuming every ceiling was reached.

Record handoff state, visibility/image scale, base/EEF-target distances where
measured, pose confidence, gripper/joint values, exact policy fingerprint, reset
generation, first 10-30 native action vectors/magnitudes, contact/progress trends,
reversal/backtracking, failures and every rejected handoff. The V0.1 telemetry
callback provides the structured boundary record; native traces must still
supply actual first-action/progress measurements. No template invents them.

For stage 6, rerun A through the same current wrapper as B rather than substituting
an old baseline. Hold starts, task, instructions and checkpoint fixed. Classical
and settling actions consume the shared 3,224-action ceiling. Track Q/success
out-of-band plus visible progress, displacement, contacts, policy/classical
action shares, inference calls, wall time and admission rejection. One pair is
exploratory, not a reliable effect estimate.

## Later Boundaries

Stage 7's direct joint interpolation must reject blocked or unknown swept space.
A qualified external planner may replace it behind the existing interface; do
not weaken the gate. Stage 8 should leave ordinary visual-servo/contact work to
the VLA rather than staging the EEF onto the button. Permitted demonstrations
may inform the envelope without retraining, but record their task/episode
provenance and call such a setup demonstration-informed, not zero-shot target-task
generalization. Never load those scene states as ordinary test starts.

Radio power is not reliably visually observable in the current setup. Do not
interpret an uncertain verifier as failure of reasoning or claim that reaching
the radio proves power-on. Prefer a visibly verifiable task for H0/H1/H2.
GPT should respond to failures, lost targets, unexpected changes, uncertain
verification or exhausted plans; successful internal phase transitions need no
additional call. Paused-world recapture remains diagnostic only until separately
qualified, with no automatic stale-decision bypass.
