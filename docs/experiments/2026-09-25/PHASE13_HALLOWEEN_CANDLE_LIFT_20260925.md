# Phase 13 Halloween Candle Lift

## Result

One controlled exploratory subgoal transferred the fixed 5 cm grasp/lift fixture
to `putting_away_Halloween_decorations` and `candle.n.01_1`. The physical effect
passed robot-only FK and quarantined post-control evaluator scoring, but the full
preregistered protocol did not pass because its independent Astra visual response
was lost after a settled API call.

A later retained run reproduced the intermediate lift before attempting release.
The lift remained successful, but upward and lateral open-gripper retreats both
carried the candle with the gripper. A two-second open-hold diagnostic established
that the assisted-grasp constraint was inactive, no object was registered in hand,
and the finger joints were fully open. The candle was therefore physically
wedged or cupped by this fixture rather than retained by insufficient opening time
or a stale assisted-grasp constraint.

| Measurement | Result |
| --- | ---: |
| Native public-test ID | 301 |
| Candle horizontal extent | 101.420 mm |
| Fixture extent limit | 105 mm |
| Actions | 30/30 |
| Robot-only FK vertical lift | 50.004 mm |
| Robot-only FK horizontal drift | 0.245 mm |
| Evaluator target lift | 50.004 mm |
| Final target-to-grasp-center distance | 11.500 mm |
| Astra call cost | $0.008365 |
| Retained Astra verdict | unavailable |

The run used no learned motor policy and no model call during motion. Initial
robot and candle poses were scripted. External clearance remained unknown and
`motion_qualified=false`.

## Release Diagnostics

Three bounded follow-ups tested whether the lifted candle could be released. None
changed the original experiment into a complete task result.

| Diagnostic | Actions | Result |
| --- | ---: | --- |
| Open then retreat upward | 70/70 | Gripper retreated 49.999 mm; candle followed 49.999 mm; final separation 11.504 mm |
| Hold fully open for about 2 s, then retreat upward | 118/118 | Constraint inactive and fingers fully open; candle still followed 49.994 mm |
| Open then retreat laterally | 70/70 | Gripper retreated 49.975 mm; candle followed 47.333 mm; final separation 12.540 mm |

The lateral trajectory also passed a robot-only self-collision screen over 33
postures and 363,099 tested link pairs, with zero collisions and a minimum
non-collision distance of 23.167 mm. External clearance nevertheless remained
unknown. The stopping rule now closes release-direction and longer-open
exploration for this fixture.

A separate zero-action pumpkin preflight rejected both available pumpkins before
motion. Their approximately 152.2 by 150.2 by 125.9 mm extent exceeded the
declared 90 mm horizontal fixture bound. No smaller pumpkin or candle asset exists
in this held-out task instance.

## Preflight

A zero-action run first resolved the task's public-test index 0 to native ID 301,
confirmed usable current imagery, and measured the candle at 101.420 mm across its
largest horizontal axis. The 100 mm nominal gripper opening required a narrowly
relaxed fixture admission limit of 105 mm. No pumpkin or cauldron was substituted.

The legal views were uneven: the left wrist was almost entirely filled by the
candle surface, the head did not clearly frame the target, and the right wrist
provided the useful external candle/gripper view.

## SAM Compatibility

Official SAM 3.1 inference on the frozen right-wrist image returned zero
candidates for each bounded prompt:

- `a candle`;
- `candle`;
- `a white pillar candle`.

The protocol therefore did not pretend that SAM supplied candle identity or use a
prompt-tuned mask as motion authority. Further wording search on this frame was
stopped.

## Physical Effect

The fixed runtime completed eight close actions, four closed holds, ten lift
actions, and eight lifted holds. Quarantined evaluator state, unavailable to
control, measured a 50.004 mm target-center lift and only 0.026 mm change in the
target-to-gripper relationship. Robot-only FK from legal proprioception measured
50.004 mm vertical grasp-center motion and 0.245 mm horizontal motion.

These two checks establish the scripted physical effect. They do not establish a
complete Halloween workflow, autonomous target discovery, policy competence,
strict collision clearance, or benchmark success.

## Visual-Verifier Failure

The preregistered post-motion diagnostic selected one GPT-6 Astra Flex call over
the source-bound right-wrist before/after pair. Its no-network preflight reserved
at most `$0.108045`, below the `$0.15` local cap. The provider settled the call at
`$0.008365`.

The local wrapper had not created its `responses/` directory. It received and
settled the response, then failed while opening the output artifact, so the
response body and verdict were not retained. No retry was attempted. The wrapper
now creates the directory and has focused citation-validation tests, but that fix
cannot retroactively satisfy this frozen trial.

Accordingly, the physical subgoal is positive evidence while the overall
preregistered experiment is a failure. Manual image review cannot replace the
missing independent response.

A new verifier was prepared against the retained lateral-release run and limited
strictly to its `pre_close`, `post_close`, and `post_lift` captures. Its no-network
preflight passed, including a one-call Astra Flex reservation capped at
`$0.10809`, but it was not dispatched because the previously used explicit local
OpenRouter credential file was unavailable. No new reservation or model call was
made. The failed release remains excluded from the proposed lift verdict.

## Evidence

```text
zero-action preflight receipt
11dddff45866757fcc05850cb14461de2dc425b53051ce2c348a7c557971395c

motion preregistration
304053e2399fc0e0f8bdf1a8495ed6998f5636637b82ba25de5070f6229f68c1

SAM compatibility reports
6c887f4331893bfb4db3248d4a25b8086acf6ac68603f73fc898ca86fe795cc2
b72f38d91784fd1ca2129e5f658e2ac7316422c2c8b21421bc4d2a989a100db5

motion receipt
3cd7973fc82021bd69fa9387ae1d17da0ea8a37abdd19fdb7653115c694cd55e

quarantined evaluator sidecar
50a506fb89094ce40be003fe1c977f4ed045d79632ae1f4c3d2d565903cd29ab

visual-verifier storage-failure record
8cbcd15a6618bb553ebc2764e388da655c1075abeb7a31fad57f1f1241561286

retained lateral-release receipt
c3713413e84f9876b2745ef3a04e9d71f947f9696518b0f55cb1ab6b9c4c2b9f

retained lateral-release evaluator sidecar
d436657897ba52fd968ffb90eff9c136d913e003537f2dc2a073f213ddd0c1f0

retained-lift verifier preregistration
5b0c890efae81a376811e473624c111dcbbbe677307f5d0136002249c8af1f43
```

## Next Gate

Do not repeat the lift, lengthen the open hold, try another release direction, or
force the oversized pumpkin through this fixture. The next useful task-level work
needs a release-compatible grasp/fixture or a different manipulation object, plus
fresh legal evidence. If the explicit credential file is restored, the already
preregistered retained-lift verifier may be dispatched exactly once; otherwise it
remains a documented pending check rather than a reason to repeat physical motion.
