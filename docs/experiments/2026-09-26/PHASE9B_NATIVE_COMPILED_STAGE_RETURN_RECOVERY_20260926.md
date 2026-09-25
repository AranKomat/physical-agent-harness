# Phase 9B Native Compiled Stage/Return Recovery

## Result

The frozen fixture-domain Phase 9B stage/return completed through the public
Action Compiler and ActionExecutor path after a separately validated Warp
lifecycle correction.

The run executed all 36 bounded R1Pro actions, produced completed stage and
retract receipts, acknowledged stop at both boundaries, and passed independent
endpoint measurement. It used no policy, GPT, SAM, object contact, or paid call.

This closes the **fixture-domain compiler/native ownership path only**. The full
simulator collision world was privileged pre-motion fixture evidence. The run
does not qualify strict BEHAVIOR clearance, natural target selection, grasping,
contact, placement, semantic task progress, or benchmark success.

## Frozen Protocol

The original preregistration and all amendments preserved:

- `picking_up_trash`, public-test index 0 / native ID 301, simulator seed 23;
- retained R1Pro `START` and `LIFT` torso plus left-arm configurations;
- ten quintic commands and eight settling actions per direction;
- 36-action total cap;
- five collision samples per segment, 102 samples total;
- 3 mrad joint, 20 mrad/s stop, 3 mm position, and 30 mrad orientation limits;
- no contact, payload, learned policy, semantic completion claim, or retry after
  a physical/collision outcome.

The executed path was:

```text
compile_catalog
-> ActionExecutor
-> one JobManager actuator lease
-> typed native Driver
-> 18 stage actions
-> fresh legal RGB-D/proprio capture
-> new compiled retract action
-> 18 return actions
-> fresh legal RGB-D/proprio capture
-> independent endpoint measurement
```

Every action used the audited 23-dimensional native codec. Base and right-arm
channels were held; the left gripper remained open.

## Results

| Measure | Result | Frozen criterion |
| --- | ---: | ---: |
| Collision samples | 102/102 free | no accepted collision |
| Actions attempted/completed | 36/36 | 36/36 |
| Stage outcome / stop | completed / true | completed / true |
| Return outcome / stop | completed / true | completed / true |
| Stage displacement | 50.006 mm | at least 35 mm |
| Stage position error | 0.008 mm | at most 3 mm |
| Stage orientation error | 0.027 mrad | at most 30 mrad |
| Return position error | 0.009 mm | at most 3 mm |
| Legal captures | pre-stage, post-stage, post-return | all three |
| Paid/model calls | 0 | 0 |

The immutable SQLite journal contains eight ordered records: `reserved`,
`step_started`, `step_receipt`, and `terminal` for each of the two compiled
actions. Both terminal records are `completed`, `stop_acknowledged=true`, and
`fault_latched=false`.

## Infrastructure Recovery

The earlier report retained three zero-action failures. The fourth and fifth
amendments resolved the exact runtime boundary without changing motion:

1. A no-scene check passed with pip Warp 1.12.1 but was rejected as
   non-representative.
2. A scene-matched check showed Isaac had created a split import: pip Warp root
   and types with bundled Warp 1.8.2 context and torch.
3. Initializing only the pip root left the bundled runtime null.
4. Initializing bundled context while retaining pip types produced incompatible
   `Device` objects.
5. Reloading root, context, torch, and types from one bundled Warp 1.8.2 root
   allowed full `CuRoboMotionGenerator` construction.
6. The first compiler attempt with that correction accepted all 102 collision
   samples but left the temporary module replacement installed, breaking Isaac
   Replicator before the first legal capture.
7. The final amendment restored the exact preexisting Warp module objects after
   collision review and before RGB-D capture. The frozen motion then completed.

The runner now persists exceptions inside the `Evaluator` context before Isaac
shutdown can terminate the process.

## Reporting Defect

The final sidecar's inline `journal_records` snapshot is empty even though the
source SQLite database contains all eight committed records. A separate hashed
post-run analysis records the discrepancy and exact terminal values. Neither the
sidecar nor the database was modified, and no motion was repeated.

The runner was subsequently changed to close and reopen the journal before
embedding future snapshots. That reporting-only change is not part of the
executed-motion hash and does not alter this result.

## Interpretation

This result establishes that a reviewed free-space pose can traverse
`compile_catalog -> ActionExecutor -> native Driver`, execute counted commands,
stop, return, and satisfy independent endpoint checks in the disclosed fixture.
It removes the previous OmniGibson/cuRobo/Warp infrastructure blocker.

It does **not** resolve the project's dominant strict-safety blocker: the
default legal R1Pro cameras still do not observe enough external swept volume to
certify general motion. The next compiler experiment should therefore be a
separately labeled exploratory contact/grasp integration using current legal
target evidence, or a strict run only if a materially different legal clearance
authority becomes available. More fixture-only stage/return repetition is not
useful.

## Evidence

```text
original Phase 9B preregistration
1f153ae380999763ce683686b967d41e83dd923017a3a9bd240f6657fe116c64

r5 amendment
4f619addbe85949815c5aabf81629bf8286799dfd6cf236fc1356d2db2de0c7d

scene-matched Warp/cuRobo lifecycle pass
e4e454b826691a39f2351e3831bc4ce60c003a0de6703c2db720cee003ae6707

executed runner
ee33c2aa17e3a09bfd30bf8a82870628014483b3964a93c07a7bb740db2062b1

final receipt
cf5469dac5620e6219c355c094148f8c40bc32e0c9d5431b4b91bdc8741f1317

evaluator sidecar
0d3b442954881a97049aa6a4fc70574efa1b818c485987c66dd215c68c41a4ec

immutable SQLite journal
0ab48b25cba617ed3a4acca0161813b314c095ef63544bb4af60769eb1012977

post-run journal analysis
e14bea5a33c0badcfab81d5dd30531f36084d2432ccace40a6d56318f9bff3aa

native log
a3af06992a0f67110c9750e8677e285b3ff129c64a484d2e8e7226c68ea58e18
```

Private raw evidence is retained under:

```text
runs/phase9b-compiled-stage-return-20260926-r5/
```
