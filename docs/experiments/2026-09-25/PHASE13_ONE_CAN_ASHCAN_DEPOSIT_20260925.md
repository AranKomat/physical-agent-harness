# Phase 13 One-Can Ashcan Deposit

## Result

One preregistered controlled fixture placed the task-native
`ashcan.n.01_1` beneath the staged soda can before the first legal observation.
The run then used only ordinary R1Pro actions to close, lift, return, release,
retreat upward, and hold. It completed all 82 actions and passed the frozen
one-can deposit criteria.

| Measurement | Result | Frozen criterion |
| --- | ---: | ---: |
| Actions | 82/82 | 82/82 |
| Evaluator lift | 50.015 mm | at least 35 mm |
| Closed return error | 0.822 mm | at most 15 mm |
| Constraint active after settling | no | no |
| Object registered in hand after settling | no | no |
| Upward gripper retreat | 50.001 mm | at least 35 mm |
| Final gripper separation | 592.677 mm | at least 35 mm |
| Post-retreat settling drift | 0.001 mm | at most 20 mm |
| `Inside` before close and after closed return | false, false | false, false |
| `Inside` after retreat and after settling | true, true | true, true |
| Exact task progress | 1/3 cans | report only |
| Native full-task success | false | false expected |

The native `Inside` predicate changed from false to true only after release and
remained true across the post-retreat and post-settle observations. The other two
task cans remained outside the ashcan. `passed=true`, but `benchmark_result=false`,
`motion_qualified=false`, and external clearance remained unknown. No paid model,
learned motor, SAM call, or GPT call participated.

## Interpretation

This is the first controlled manipulation result in the project that combines a
grasped lift, clean release, task-native destination, stable post-release state,
and exact task-predicate progress. It resolves the immediate question raised by
the failed pedestal diagnostic: the retained soda-can action sequence can produce
a semantically useful deposit when the destination supplies adequate containment
and the gripper retreats without disturbing the released object.

It does not establish autonomous placement or benchmark success. The robot, can,
and ashcan poses were scripted before the first legal observation. The run placed
one of the three required cans, and the public Action Compiler did not select or
authorize the trajectory. Evaluator poses and task predicates were quarantined
from control. A later frozen GPT-6 Sol verifier used only three retained legal
left-wrist images, cited all three, and independently returned a supported
`verified` verdict matching the native `Inside` and stability results. See
[One-Can Ashcan Visual Verification](../2026-09-26/PHASE13_ONE_CAN_ASHCAN_VISUAL_VERIFICATION_20260926.md).

## Causal Controls

- The task, public-test instance index 0, native ID 301, and seed 23 were frozen.
- The ashcan retained its loaded orientation. Its AABB center was aligned in x/y
  with the grasp center, with its top 30 mm below the initial can bottom.
- Neither of the other two cans was moved using hidden state.
- After the first legal RGB-D observation, all robot state changes used ordinary
  23-dimensional R1Pro actions.
- The run was executed once. No ashcan pose, threshold, opening, or retreat tuning
  followed the outcome.

## Evidence

```text
preregistration
249cfc312b7a45bf7112bccd8f4677203b1bce914ae2701235ad9c59a74e27e3

completed receipt
db7915db3addc1294a5b4f15b654d5991e35275edc154c6b11dcb9bedfed8cc6

quarantined evaluator sidecar
18838486c9b394aef8749a326b23132632b2d2d6796329b7350fc6cbb96816d0

source run log
0074e54d8721770bce6561a6118d70f0d99a85f73ea67306a717437afbc4827c

42-file content-addressed legal evidence manifest digest
c6bc3c6bb946faedc451b3c53e6cbc68dc836ef8389e338cde7cb429686be91d
```

The complete private evidence bundle was copied from the GPU host and its
44 source files matched the remote aggregate digest before a local contact sheet
was derived.

## Next Gate

Treat the concrete unlock criterion for later integrated phases as met only in
the controlled exploratory sense. The retained effect now also has a supported
model-based post-action verdict, so another verifier call or deposit fixture is
not the next gate. Complete-task and benchmark-valid claims remain open, as do
legally selected destinations and strict support-aware execution.
