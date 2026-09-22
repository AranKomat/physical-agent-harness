# Radio Depth Audit

CPU-only inspection of all 12 accepted radio detections in
`single4090-dense-acquisition-20260922-r1/A`. No new model calls, simulator
steps, state reads, segmentation inference, or changes to control.

Source receipt SHA-256:
`88d548ed9229ecff4602b2701521f4d08244ce9cecbd4bbf43e9a3d2734d03f3`.
Private artifacts: `radio-depth-audit-20260922-r2/report.json` and per-frame
RGB/mask/depth panels. The r1 rendering preceded the diagnostic tail overlays;
r2 uses the same immutable source observations, not another experiment.

## Findings

1. **No obvious depth-convention mismatch.** The clean pinned BEHAVIOR source
   `b1979916ec1549b10a4e65e630bc6504a9af1b00` maps `depth_linear` to
   `distance_to_image_plane`, whereas `depth` maps to `distance_to_camera`.
   Our deprojection uses the former as optical-axis z, consistent with that
   contract. Intrinsics come from the contemporaneous camera projection. This
   source review is not an independent absolute calibration measurement.
2. **Masks have defects.** All retained mask pixels had finite positive depth,
   but that does not establish semantic purity. Visual review found omitted
   radio surfaces around the speaker/trim and inclusion around the handle gap
   and silhouette. Deeper pixels concentrate at those latter regions, consistent
   with background leakage. Do not use the whole mask as a precise object shape
   or button/contact surface.
3. **Surface medians are less sensitive than depth extents.** Additional 3-pixel
   erosion changes median image-plane depth by 3.8-15.2 mm across these 12 views.
   This is a sensitivity diagnostic, not a distance error bound. The 5th-to-95th
   percentile spread reaches 0.52 m in an early contaminated view. Later front
   views have about 0.05-0.09 m spreads. Shape/extents are more suspect than the
   coarse surface median; neither has independent truth validation.
4. **Image-plane depth is not camera range or base distance.** The radio moves
   toward the image center as the camera changes orientation. Its z can rise
   while its Euclidean range falls:

| Action | Masked median optical-axis z | Median camera-to-pixel range |
| --- | ---: | ---: |
| 416 | 1.246 m | 1.698 m |
| 448 | 1.483 m | 1.662 m |
| 512 | 1.626 m | 1.649 m |
| 768 | 0.983 m | 1.166 m |

Ranges are medians of individual deprojected point norms, not the norm of a
coordinate-wise median, and are not distances from the base or end effector.
Changing visible surfaces prevents interpreting differences as base displacement.

## Diagnostic Details

All 12 RGB/mask/depth panels were visually inspected. A second overlay highlights
masked pixels more than 15 cm behind that frame's median solely to locate the
long-depth tail; this is not a new rejection rule. Such pixels comprise 8.72%,
6.22%, and 5.65% at actions 416, 480, and 512 respectively; they are concentrated
around the handle opening and edges. No hand-selected replacement mask or
post-hoc filtered estimate was supplied to the policy or controller.

The existing audit reproduced mask hashes, RGB/depth evidence identities,
calibration bindings, deprojected medians and robot-only FK transforms. This
establishes provenance and algebraic consistency, not semantic accuracy or
world-frame localization. Two new private regression tests cover optical-axis
depth versus ray range and invalid-depth handling; Ruff passes.

## Decision

Do not replace the depth sensor or launch another long radio rollout on this
evidence. There is no demonstrated gross scale/convention failure. There is a
demonstrated mask-quality limitation and a misleading interpretation to avoid
when reporting distance. Keep current estimates shadow-only; contact geometry
remains unqualified. Any subsequent geometry-quality improvement must distinguish
object surfaces from background through holes rather than merely filling masks.

The next bounded integration question remains observation timing and live
localization. Low-space coverage is a separate blocker. Only after a usable
motion/handoff setup exists should a short hybrid-versus-policy comparison
decide whether this direction merits more effort. Arm/contact, memory and
efficiency extensions are deferred, not prerequisites to demonstrating benefit.
