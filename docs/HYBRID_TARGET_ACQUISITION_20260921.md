# Calibrated Target Acquisition Check

This follows the [tiny handoff diagnostic](HYBRID_TINY_HANDOFF_20260921.md).
It tests the prerequisite for sensor-based staging, not radio completion or GPT
reasoning. No GPT API calls, privileged scene poses or target-coordinate preload.

## First Calibrated Approach

`hybrid-calibrated-approach-20260921-r1`: ordinary radio reset, frozen
Behavior-Skill, unchanged approach instruction, 384 native/policy actions in
12 chunks. Protocol completed; native task success was false. Policy phase wall
time was 76.96 seconds, including first-call compilation.

All 13 captures retain three same-boundary camera calibrations. The 39 records
match their source observation stamps, timestamps and RGB/depth evidence IDs.
All 85 remote files match the local backup by SHA-256.

At the final capture the radio is outside the head and both wrist views. Thus
there is no supported final target pixel to deproject. No target distance or
staging candidate is asserted. Missing visibility is not evidence of a new
object location. The offline measurement helper remains unexercised on a target.

## Reset Variability

Compared with A in the prior tiny-handoff pair, the initial proprioception and
depth arrays are identical. Initial RGB mean absolute differences on the 0-255
scale are 2.124 (head), 1.610 (left wrist), and 1.845 (right wrist). The first
policy chunk differs by up to 0.01693 in native action coordinates (mixed units;
not a physical displacement metric). Source and checkpoint receipts match
apart from load duration. Reset-relative sampling-noise indices are unchanged.

This establishes that same seed/reset does not provide pixel-identical inputs.
It does not by itself identify every source of rollout variability. The earlier
one-pair handoff result must not be interpreted as a reliable treatment effect.

## Calibrated Repeat and Assisted Measurement

`hybrid-calibrated-approach-20260921-r2` completed the same 384 policy/native
actions and 12 chunks. Native task success was false; policy phase wall time was
73.94 seconds. All 85 source files match the local backup, and all 39 calibration
records pass the same-boundary checks. No GPU worker remained after completion.

The radio is partially visible in the final head view. An assistant visually
selected a pixel on its front surface, then a private offline diagnostic used
only that frame's measured depth/intrinsics and qualified robot-only FK:

| Measurement | Value |
| --- | --- |
| Pixel (u, v) | (44, 495) |
| Optical-axis depth | 1.2187 m |
| 5x5 depth neighborhood range | 1.2128-1.2274 m |
| Surface point in instantaneous base frame | (1.1766, 1.2585, 0.5181) m |
| Horizontal base-to-point distance | 1.7229 m |
| Left EEF-to-point distance | 1.1937 m |
| Right EEF-to-point distance | 1.6146 m |
| FK versus proprio EEF position residuals | Under 1.1 micrometres |

These are estimated surface-point measurements, not ground-truth object-center
errors, a button pose, an autonomous detector result, or a collision certificate.
The small FK residual checks robot-coordinate consistency, not target accuracy.
No action was selected or executed from this offline annotation, and its
coordinates must not be reused in a new episode.

Only one of these two fresh approaches exposed the target in the final head
view. That is descriptive of this tiny sample, not an estimated success rate.

## Next Gate

A nominal 0.65 m staging radius would require about 1.07 m of direct horizontal
travel from the measured endpoint before obstacle avoidance. This is a geometric
illustration, **not an admitted staging proposal**. It is far outside the roughly
1 cm exploratory pulse already tested. Coffee-table and whole-body clearance,
online target reacquisition and localization along that travel remain unresolved.

The next experiment must qualify bounded target-directed sensing/motion and
stopping before promoting to the equal-total-action A/B task comparison. Retain
the frozen checkpoint and do not spend GPT calls to mask this navigation gap.
The helper's successful offline deprojection is not completion of autonomous
stage 2, and the tiny-handoff result is not completion of target-directed stage 3.
