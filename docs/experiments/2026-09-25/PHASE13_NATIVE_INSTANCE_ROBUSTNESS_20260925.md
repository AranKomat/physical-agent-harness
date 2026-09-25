# Phase 13 Native-Instance Robustness

## Result

A preregistered two-case robustness cohort changed only the BEHAVIOR
`freeze_fruit` public-test instance while retaining the same simulator seed,
strawberry binding, robot joint fixture, SAM 3.1 prompt and thresholds, 30-action
budget, and independent verification criteria. It produced one success and one
failure.

| Public index | Native ID | Current view | SAM reset gate | Executed result | Independent result |
| ---: | ---: | --- | --- | --- | --- |
| 1 | 302 | Mean luminance `172.91/255` | Passed; 22,498 mask/depth pixels | 30-action lift | Passed; 50.000 mm legal FK lift, 0.9612 mask IoU |
| 2 | 303 | Mean luminance `2.23/255`; 100% at or below 8 | Failed; 0 candidates before and after reset | Hold | Hold was not physically stable |

The cohort therefore failed its preregistered `2/2` robustness endpoint. It made
no paid calls and used no learned motor policy. Both cases remained exploratory:
`motion_qualified=false` and external clearance was unknown.

## Successful Case

Native instance 302 resolved to the predeclared ID, produced current
depth-supported masks before and after tracker reset, and authorized the fixed
lift. Evaluator-only scoring measured a `49.996 mm` payload lift. A separate
verifier used retained legal RGB-D plus robot-only FK and measured `50.000 mm`
grasp-center lift with `0.9612` retained-surface IoU.

This is a second independent native-instance success for the controlled
development fixture, not benchmark task success.

## Failed Case

Native instance 303 yielded an almost black legal left-wrist view. SAM returned
zero candidates in both generations, so the source-bound gate correctly denied
the lift and selected `hold`. The physical result was still not safe to call a
successful hold: evaluator-only diagnostics measured a `0.593 m` change in
object-to-grasp-center distance and approximately `0.65 m` grasp-center motion.

The public task metadata also changes the native robot base pose between IDs 301,
302, and 303. The cohort therefore tests coupled native viewpoint, illumination,
and physical scene compatibility rather than isolating background appearance.
The instance-303 failure must not be attributed only to SAM or repaired by
weakening the evidence gate.

## Infrastructure Correction

The live coordinator invoked the independent verifier from `.venv-native`, which
does not contain `yourdfpy`. That process exited before reading evidence and the
original coordinator report therefore marked even instance 302 failed. The
content-addressed instance-302 evidence was verified once afterward from the
already validated analysis venv. No motion or SAM inference was rerun, and no
threshold changed. The coordinator was corrected for future cohorts.

## Interpretation

This closes one initial natural native-instance robustness cohort with a mixed
negative result. The system works in native IDs 301 and 302 but is not robust to
ID 303. Before another such cohort, runtime preflight should reject near-black
current images explicitly, and a physically stable hold must be qualified for
the changed base/viewpoint regime. Exposure normalization alone cannot fix the
observed hold instability.

Do not retry ID 303 with changed prompts or thresholds and report it as the same
cohort. Any photometric recovery or normalized-base fixture is a separately
preregistered diagnostic condition.

## Evidence

```text
preregistration
a4fc7ca0edd1a0fda8f01081ac84066525ef1170ba55d33bb73989d4a22c4ea0

original coordinator
5cc959e36e34240a087bed354959c2c2f4dc6d4245ae613098aef9a114969368

final retained-evidence analysis
b2fe5060cd746a403c9fb05cf193d723f268bf3841e2e4b940c278cfb55d9f5a

instance-302 independent verification
006fb542582abff9a7f142d08c37d869073d4cfd9706037031613b3bb9f15008

instance-302 receipt / SAM gate
afe013444e2c811c844144c5f9b48633c305dcd41b89f6cbbb953325ea754bef
130b845d514def014c2b5b2fbdb7c08a63ae693e6184dde8ddec58c5394e735b

instance-303 receipt / SAM gate
b563c61526cb2ab98e1341224df063d1a57263c977e6e528ec171412553b261e
df65ad5c7dd3495270e5ed1993840b51619c4691c46ebf20af08592ef988b950
```
