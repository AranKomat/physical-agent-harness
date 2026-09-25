# Phase 13 Natural Trash Behavior-Skill Trial

## Result

The pinned Behavior-Skill `pi05-pt50-skill` checkpoint completed a long,
unmodified `picking_up_trash` public-test rollout from native instance index 0.
It navigated toward an orange soda can and brought the can into close head-camera
view, but it never closed either gripper, acquired the can, or advanced the task.

The amended run executed 1,536 policy-controlled actions over 51.2 simulated
seconds. It ended with native success `false`, Q-score `0`, and both grippers
fully open. This is a technically valid negative motor result. It is not a
benchmark score because motion remained exploratory and external clearance was
unknown.

## Frozen Protocol

The first pilot used four natural-language skills with 96 actions each:

```text
Move to the nearest soda can.
Pick up the nearest soda can from the floor.
Move to the ashcan in the kitchen.
Place the soda can in the ashcan.
```

That 384-action exposure was too short for a policy-quality conclusion: the
robot had only begun approaching the can when the prompt changed. A single
explicit amendment referenced the pilot preregistration hash, froze the exact
published skill labels below, doubled every label, and allocated 192 actions to
each block:

```text
move to
move to
pick up from
pick up from
move to
move to
place in
place in
```

The amendment prohibited further retries. Both runs used the same native task,
instance index, seed, legal head/left-wrist/right-wrist RGB, 61-D
proprioception, checkpoint, normalization, action codec, 16-action commit
prefix, and deterministic per-observation policy noise. No GPT, memory, SAM,
hidden simulator state, or paid API call influenced control.

## Quantitative Evidence

| Quantity | Pilot R1 | Amended R2 |
| --- | ---: | ---: |
| Policy actions | 384 | 1,536 |
| Policy calls | 24 | 96 |
| Simulated time | 12.8 s | 51.2 s |
| Control wall time | not used for verdict | 281.14 s |
| Native success | false | false |
| Final Q-score | 0 | 0 |
| Benchmark claim | false | false |

R2's two `pick up from` blocks had mean absolute base-channel command
magnitudes of `0.10063` and `0.09481`, the largest pair of any repeated skill
label. The policy was still using substantial base commands during pickup.

Across those same 384 pickup actions, the unnormalized left gripper command
stayed in `[0.99481, 1.00729]` and the right command stayed in
`[0.99323, 1.00586]`. At the two pickup boundaries, measured left/right summed
finger apertures were:

| Boundary | Left aperture | Right aperture |
| --- | ---: | ---: |
| After first pickup block | 99.853 mm | 99.670 mm |
| After second pickup block | 100.000 mm | 100.000 mm |

All eight skill boundaries remained approximately 100 mm open. The native
camera montage independently shows the robot moving from the kitchen start to
close visual proximity of the can while the grippers remain open. There is no
evidence of a grasp attempt or object acquisition.

## Interpretation

R1 removes the misleading implication that a very short probe was a full motor
evaluation. R2 then addresses both remaining confounds: it uses the checkpoint's
published atomic skill labels and gives each label a long, equal exposure.

The result supports a narrow conclusion: on this natural task start,
Behavior-Skill provides useful locomotion but its canonical pickup skill does
not transition to meaningful gripper closure. The result does not establish
universal language blindness, prove that every start fails, or compare policy
families fairly. Training overlap is disclosed, so it is also not evidence of
held-out motor generalization.

A recurrent GPT trial on this exact start is not justified without a credible
grasp-capable motor primitive. High-level supervision cannot recover task
success when the frozen backend never closes a gripper. Preserve Behavior-Skill
as a reproducible reference policy, not a sufficient general BEHAVIOR motor.

## Evidence

Private artifacts are retained under:

```text
runs/phase13-natural-trash-behavior-skill-20260926-r1/
runs/phase13-natural-trash-behavior-skill-20260926-r2/
```

R1 hashes:

```text
preregistration  1033358eb691a3a6e470a5d8d641d18c6225128e5cab941e8b0c6ea38be672d9
owner            7b0553c30bd8887281cd91149cb667baa50022c3f83f87c7d9babf9b64e6db55
report           0f0856d2e3a014fc1821b8bace4d27d3c4bab69e487c2f344fe5deeafa1ceedd
rollout          0e3e58b5b6d35cc1b1043f7903c61ee1be3f6adfc3b6c62a42246e4f86c12acb
source bundle    7fe018693eb016fb341fc34bc632165fc9c058d04c3a5691ec8dcf561fd35c44
```

R2 hashes:

```text
preregistration  57cde7c6f33ac1be3ab8369a7ef05ee1d7eafd1fa81edbc5dedcfabaf4ef907e
owner            0b23469df86f9217aafc7ed169cfdcec734631ff780dd088d8266cdcc76eb3fb
policy load      5bf6001caeb7dc4827020c40651c372180b2895ea9186770be7d0407fe32564c
report           cd9d5c8a2f4ecc7494f41d7c9d4796b7bbe60c9c76b3fc6430228d338dc31195
rollout          859421a04735e7b07e8baf2b0af235321a2cb8bf7f4409d9a1c924d35f16cdc9
source bundle    edd339de0f8a902238af2c36c95e9da8250c7693f6c873e39a8e525c3b5e5754
```

Checkpoint pins:

```text
source repository commit  7ca6eace02aaba2d8ce19af600b85dd04a60d720
checkpoint revision       98941096c94b0f978391d8a0accc699c32ec8b2a
checkpoint prefix         pi05-pt50-skill
verified files            727
verified bytes            12,438,645,457
```
