# Phase 13 Apple Category And Task Replication

Date: 2026-09-25

## Result

The first broader object-category and official-task-label replication passed in
the controlled exploratory fixture.

The source fixture changed from a soda can under `picking_up_trash` to
`apple.n.01_1` under the official `freeze_fruit` task at simulator seed 23. It
retained the same R1Pro start and 5 cm grasp/lift trajectory. All 30 actions
completed, the evaluator measured a 50.01694 mm apple lift, and the final
apple-to-grasp-center distance was 10.494 mm. Independent legal RGB-D and
proprioceptive verification measured a 50.01599 mm forward-kinematic lift,
0.98386 red-mask IoU, 1.883 px centroid shift, and 0.0755 mm median depth
change.

A frozen category-memory protocol then asked the executive to lift the staged
object only if historical evidence established that it was an apple. The current
left-wrist RGB was removed at the post-close decision boundary by the same
predeclared transport dropout used in the earlier memory study.

- M0 received current evidence only.
- M1 added a causal event that explicitly stated the category was not recorded.
- M2 additionally received the historical wrist image with its original stamp
  and content hash.

GPT-6 Sol returned the expected `hold`, `hold`, and
`lift_current_candidate`. Each packet-bound decision was executed from a fresh
deterministic start for 30 actions and independently verified from legal RGB-D
plus robot-only forward kinematics.

| Condition | Decision | Physical execution valid | Verified progress |
| --- | --- | --- | ---: |
| M0 | hold | yes | 0/1 |
| M1 | hold | yes | 0/1 |
| M2 | lift | yes | 1/1 |

The two holds each moved the grasp center by about 0.012 mm. M2 raised it
50.016 mm. Every verifier retained all 230,400 paired depth pixels; median
absolute depth change was 0.0019 mm for each hold and 0.0075 mm for the lift.
The three model calls used 5,927 prompt tokens, 267 completion tokens, and
`$0.0087415` total. Physical execution made no additional paid calls.

One operator launch supplied the retained fixture run where the runner expected
the pinned BEHAVIOR source checkout. It stopped at host preflight before creating
an output directory, starting motion, or making a paid call. The failed attempt
is retained in the private cohort rather than discarded.

## Evidence

- source apple lift receipt / legal verification:
  `554bdde49e6c98be74344265448829bbd208cc2f6925d099277c8115db2a1413` /
  `ca502d70775ae5bfcfca1d4e110dacf924f8ba3453b046164ae6308b02094b34`;
- protocol / decision report:
  `296fb4a5271ad273e1c46cd229499117dd24c9d41a8f2179752c74645d3bb898` /
  `ca9923477a787a0611349f56f39e279fd8cd3c6bc47b3a0ad7a7735591474f74`;
- M0 receipt / verification:
  `5fad741c3594c640ea73d1013cd4d54e1bc769221c1c6de98a3957017194960b` /
  `fe67fe57d6f833e4383adec2ceec714b419e6a4e42b70210810e28474e823262`;
- M1 receipt / verification:
  `6c4b5ad5cd9f42e607fba9beb90382e96d2dc861843b542c11463773dd95a791` /
  `fd8aa7e8eebe9130c74a286fb07ba6f384f6a368c2dab52ee39cb37374445cbe`;
- M2 receipt / verification:
  `0fbd3f739abc341d426f6a63b59783bdf92b13b185a5a874ebee9470ea8a302d` /
  `b9a4414518ed852e53918705dace9dc65737a5137543160e61f62c8af517477a`;
- aggregate score:
  `b6f3f7d285546ab042c7076024effd60dc4a32298e048eacffa8ae953faac3e5`;
- retained failed preflight:
  `db163d9e78241b2ea25d4f5586502aee2e7f269b8d69223635eb1e29dee51faf`.

## Interpretation

This extends the controlled memory-in-execution result across a new object
category and official task label. It also shows that the parameterized fixture,
packet binding, image rebinding, physical execution, and legal verifier are not
hard-coded to soda-can color.

It does not establish general manipulation or `freeze_fruit` benchmark success.
Initialization remained scripted, the robot trajectory was unchanged, the
current-camera dropout was injected, external clearance remained unknown, and
`motion_qualified=false`. The next useful Phase 14 work should measure selective
model escalation and neural duty on broader frozen cases, not add nearby fixture
replications or claim that this fixed trajectory generalized as a motor policy.
