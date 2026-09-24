# Continuous Authored-Hull Path Screen

Follow-up to `STAGED_NONCONTACT_SCREEN.md` and `STAGED_SCENE_SCREEN.md`.
Phase 7 remains incomplete; this does not authorize robot motion.

## Method

The two fixed torso-plus-arm candidates were checked against 161 authored
convex hulls and 11,003 non-excluded pairs. Native exclusion pairs come from the
pinned inspection receipt, not from newly added exemptions. Wheel shapes are
not covered.

For each hull, the sum of downstream joint-origin lengths and maximum local
vertex radius bounds its radius about an ancestor joint for every posture.
Held prismatic offsets are included. Unmeasured ancestor joints are rejected.
For each pair, common ancestor rotations cancel because they preserve mutual
distance. The remaining radius-times-angle bounds sum to an upper bound on
relative displacement over the joint-linear path.

At each interval midpoint, the FCL separation must exceed the maximum relative
displacement to either interval endpoint plus a 1 mm numerical margin.
Inconclusive intervals are bisected, up to depth 10; collisions and unresolved
intervals fail. This extends beyond checking a finite set of poses, conditional
on the authored model, joint interpolation and numerical distance calculation.

## Results

| Candidate | Pair checks | Deepest subdivision | Minimum residual bound slack | Outcome |
|---|---:|---:|---:|---|
| Left torso + arm | 11,007 | 1 | 0.606 mm | All intervals separated |
| Right torso + arm | 11,003 | 0 | 22.212 mm | All intervals separated |

Slack is separation remaining after subtracting the motion bound and numerical
margin. It is not measured minimum native clearance. The right candidate has
the stronger bound and is preferred for subsequent qualification.

## Remaining Gates

External visibility/clearance still fails to qualify either path, as recorded
in `STAGED_SCENE_SCREEN.md`. No additional wrist-view sweep should be assumed
to fix proximal blind spots: prior observer surveys already found that
limitation. Native cooked geometry, wheel coverage, tracking uncertainty,
dynamic balance, endpoint/stop measurements and execution of the return remain
unqualified. The reverse geometric path shares the separation bound, not a
proven executable return. FCL distances are numerical, not interval arithmetic.

No robot actions, paid calls, GPU jobs or remote workload changes occurred.

## Evidence

Private script: `scripts/staged_sweep_screen.py`

Private receipt: `runs/staged-sweep-20260924-r2/receipt.json`

- Receipt SHA-256: `aacfefb185f74e1f539e103790ec5907b41ed7f9ef6cb44e969db64b4904ded8`
- Script SHA-256: `82cc1fe0cf8efa77105b523c542cd0dbca1b942fe59270c9d57d1c934fac8f60`

The receipt pins source, candidates, assets, native exclusions and helper
scripts and verifies input hashes unchanged after the run.

## Native Callback Follow-Up

The same fixed paths were subsequently screened with the retained native
convex-callback vertices transformed into each owning link. The 161-link-shape
inventory and exclusion sets agree with the authored screen. The callback
receipt still says `cooked_shapes_verified=false`: callback availability must
not be promoted to complete native geometry qualification.

Since native contact-offset ordering has no per-mesh correspondence, the
follow-up subtracts twice the maximum recorded contact offset plus 1 mm:
11.0707 mm per pair. Both paths pass the continuous numerical bound:

| Candidate | Pair checks | Deepest subdivision | Residual bound slack |
|---|---:|---:|---:|
| Left torso + arm | 11,019 | 2 | 1.798 mm |
| Right torso + arm | 11,003 | 0 | 12.539 mm |

The right candidate remains preferred. This strengthens self-separation
evidence only; the external coverage deficit, wheel geometry, complete cooked
shape verification and native execution gates are unchanged. Further no-op
planner or self-collision variants should not precede a concrete solution to
external coverage or a separately labeled exploratory execution protocol.

Private receipt: `runs/staged-native-sweep-20260924-r2/receipt.json`

- Receipt SHA-256: `f3fb739cd91316b6836108082b67114e75aa9b95c47c813fd5d4adf24878f4db`
- Updated script SHA-256: `56d77926b119e3635b652a0f040068fb7afbfb566315eb0673b4b0e97bb02ca6`

Reproduce with `--native-callbacks` on `scripts/staged_sweep_screen.py`.
The original authored-run hashes above remain historical evidence.

## Tracking-Envelope Correction

The preceding screens bound nominal joint-linear paths only. They did **not**
include the native monitor's allowed joint-tracking error and must not be used
as execution admission evidence. This omission was found while comparing the
new path against the existing scan admission contract.

The corrected run includes 0.003 rad error for every rotational joint and
0.002 m for held fingers, including their contribution to ancestor radii.
Common-ancestor rigid motion still cancels for self-separation. Separation is
now lower-bounded by vertex support gaps along FCL nearest-point directions,
using the existing `check_view_paths.support_gap` helper; the scalar FCL
distance alone is no longer the bound.

Both paths pass the corrected callback-geometry screen, retaining the same
11.0707 mm pair margin. Left requires three subdivision levels and has only
0.197 mm residual slack. Right requires no subdivision and retains 11.991 mm.
Keep only the right candidate for native preparation. These are numerical
model bounds, not physical accuracy estimates or complete motion admission.

Private receipt: `runs/staged-tracking-sweep-20260924-r2/receipt.json`

- Receipt SHA-256: `08bfeea2311dc53e0b0f3a8c058290aa75de6f36a937fc0df75112135ce0233a`
- Script SHA-256: `c40a096d5b17be4468cfd521bc5d0911412f7b1fcf030e90df3e12f2864be2c4`

No native actions or paid calls occurred. External clearance, complete native
geometry, fresh-state replanning and endpoint/return/stop execution remain open.
