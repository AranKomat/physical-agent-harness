# Phase 13 Image Quality And Occlusion Gate

## Result

The native-instance failure exposed two distinct conditions that must not share
one fallback: unusable current vision before motion, and target disappearance
during gripper closure. A conservative image-usability gate was added before the
first action, followed by one preregistered fresh native-instance run.

The retained regression classified all three known cases correctly:

| Native ID | Mean luminance | Near-black fraction | Gate |
| ---: | ---: | ---: | --- |
| 301 | 185.01/255 | 6.51% | Continue |
| 302 | 172.91/255 | 9.67% | Continue |
| 303 | 2.23/255 | 100% | Reject |

This `3/3` is a post-failure regression check, not an independent accuracy
estimate. The gate also rejects effectively white or flat frames.

## Fresh Native Instance

Public-test index 3 resolved to the predeclared native ID 304. Its pre-action
left-wrist image was usable:

- mean luminance: `174.36/255`;
- p95 luminance: `236.27/255`;
- near-black fraction: `3.40%`;
- p95-p05 range: `225.34/255`.

SAM found one current depth-supported strawberry mask before closure with 24,731
pixels. After the fixed 12 close/closed-hold actions, SAM correctly returned zero
candidates. The strawberry was fully occluded by the gripper in the current
left-wrist view and absent from the head and right-wrist views as well.

The preregistered post-SAM rejection branch executed: no lift and no additional
hold loop. The run stopped at exactly `12/12` actions. Its safety protocol passed,
while `task_success=false` and task progress remained zero.

## Interpretation

This is a natural full-occlusion result, not another wording failure. Propagating
a tracker ID through complete disappearance must not manufacture current geometry.
The runtime may retain historical semantic identity, but the fixed protocol has
no legal tactile/force evidence that the payload is actually retained. Therefore
the current system should abort rather than authorize lift.

The result also fixes the unsafe behavior exposed by native ID 303: a severely
dark frame is now rejected before the first action, and a later SAM rejection no
longer triggers 18 additional hold commands. These changes improve bounded safety
without claiming benchmark competence, current clearance, or a successful task.

## Fixed Protocol

The gate is model-independent and operates on current RGB luminance only:

- p95 luminance must be at least `16/255`;
- near-black fraction must not exceed `0.95`;
- near-white fraction must not exceed `0.98`;
- p95-p05 luminance range must be at least `8/255`.

Rejected pre-action images produce zero robot actions. Usable images continue to
the existing source-bound SAM gate. A post-close SAM rejection ends after the 12
already completed close/hold actions.

## Evidence

```text
retained quality regression
b23323ea225a24375a34a9e6e85caf6fbbfb373728977e74855affc4e97e1f4b

preregistration
9be5d425d186f08f9658a9e4699e0d63b4a8f8621ae2c6914c940f7dd51bb007

coordinator
e3e9499ee6eec97d6950b984d28096320eb157416d1e7af0ba363ffcb4225fc0

receipt
852e1356837e67f8c696cda7c3c376bd8e4a1e61669c04f9272bc08732213115

SAM gate
83defa7f9a57063dbdf6d7739239678bdfe1e3717572e6cac6dcc81087b43c9e
```

## Controlled Spectrum

Post-hoc synthesis of the separately preregistered runs gives a controlled
visibility spectrum. IDs 301 and 302 retained `0.6496` and `0.6607` of their
pre-close mask area after closure and completed verified lifts. ID 304 retained
`0.0` and executed the bounded abort. This supports current-evidence gating under
partial versus full loss; mask-area fraction is still only a visibility proxy.

## Remaining Boundary

Full occlusion is now handled conservatively, but recovery is unresolved. A
future route needs new legal evidence, such as tactile/force sensing, a visible
inspection pose, or another camera that actually observes the payload. It must
not reinterpret a historical mask or tracker-local ID as current geometry.
