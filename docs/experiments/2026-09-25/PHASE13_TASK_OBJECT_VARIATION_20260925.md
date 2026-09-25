# Phase 13 Task And Object Variation

## Result

One preregistered controlled task/object transfer passed. The fixed pipeline moved
from `freeze_fruit` with a strawberry to `picking_up_trash` with a soda can while
retaining the same pre-action image gate, source-bound SAM reset gate, 30-action
grasp/lift motor, and independent legal RGB-D plus robot-only FK verification.

| Measurement | Result |
| --- | ---: |
| Native public-test ID | 301 |
| Pre-action mean luminance | 165.26/255 |
| Pre-action near-black fraction | 0.12% |
| Pre-reset SAM mask/depth pixels | 140,846 / 140,846 |
| Post-reset SAM mask/depth pixels | 132,828 / 132,828 |
| Actions | 30/30 |
| Evaluator lift | 50.015 mm |
| Legal FK lift | 50.010 mm |
| Legal retained-surface IoU | 0.9966 |
| Legal median depth change | 0.015 mm |

The current image was usable, both SAM generations admitted the orange soda-can
region, and the fixed lift completed. No paid calls or learned-policy calls were
made. External clearance remained unknown and `motion_qualified=false`.

## Interpretation

This is positive controlled task/object variation. It shows that the integrated
quality gate, learned-perception gate, motor, and verifier are not specific to the
strawberry fixture. It does not establish broad task generalization: the initial
robot and can poses were scripted, the motor had previously been qualified on this
object, and only a grasp-and-lift subgoal was executed rather than the complete
`picking_up_trash` task.

The corresponding occlusion synthesis also closes the controlled fixture's first
visibility spectrum: native IDs 301 and 302 retained 65.0% and 66.1% of their
pre-close masks and completed verified strawberry lifts, while ID 304 retained 0%
and performed the bounded 12-action abort. This is post-hoc synthesis, not an
independent occlusion benchmark.

## Evidence

```text
preregistration
bd94aebd4c0f33a479ecfcc2f873ddb396cb4d76365a57b439f7ca716405b540

coordinator
73a0ef0cedcba7c55488e6b46fb331c4a426573003b687bc995c17b2767ede82

receipt
e788d20c5f96dfd35bb90128e088fc0e25b9b40120f45655c11101be5a535312

SAM gate
d5fe8c0dbd0f6edd33d915c134a98c40245811da7a5c3b372882fc2687fb5607

independent legal verification
cfca82b76491e13f4a9a43c405d37be3cd8b0aea954366507545f2167ccb604e

occlusion-spectrum synthesis
61eee01d304ebeca7339e90b8707d13fb22e0a88c42a29f884b2d9e958ff8c60
```

## Next Gate

Broader task variation needs another object family and, eventually, a complete
task workflow rather than another scripted lift. Do not count nearby colors or a
second soda-can instance as a new task axis.
