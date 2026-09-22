# Depth-Aware Surface Partition Replay

## Scope

CPU-only replay of all 18 masks from the SAM 2.1 Large comparison: 12 radio
views and six preselected detector distractor boxes. No model calls, simulator
steps, changed masks or live-controller integration. This is a small diagnostic
in the private lab, not another production perception subsystem.

The test asks whether measured depth can separate surfaces that a semantic mask
groups together. It does **not** ask the algorithm to decide which patches belong
to the object or delete the background. All patches remain semantically unknown.

## Fixed Rule

Use the existing explicit optical-z camera contract to deproject valid pixels.
Build a sparse graph over four-neighbor pixels inside each original SAM mask.
For each adjacent pair, connect them only if their Euclidean 3D separation is at
most `max(0.01 m, factor * max(endpoint_depth) / focal_length)`, with horizontal
or vertical focal length as appropriate. Run the same predeclared factors 2, 4
and 8 for every input. These are diagnostic tolerances, not qualified sensor
noise bounds or contact thresholds. No best setting is selected after seeing
the results.

Use SciPy's sparse connected-components implementation. Retain every component,
including singleton pixels and thin parts. Invalid depth stays label zero;
outside-mask pixels are never added. Original masks and depth are not modified.
This is geometric connectivity, not a planar-surface fit: connected patches can
still be curved, cross a crease, or contain two touching objects.

The 15 cm median-relative tail statistic is used only to describe the existing
depth issue. It is **not** used to split, select or reject patches.

## Results

Completed private run: `depth-surface-patches-20260922-r2`.
The first attempt stopped before processing any mask because the existing
intrinsics contract rejected NumPy scalar types. Explicit conversion to Python
floats corrected the adapter; no algorithm tolerance or input was changed.

All 54 partitions (18 masks x three settings) preserve exactly all valid masked
pixels. Median partition runtime on the local MacBook was 4.31 ms, maximum
17.13 ms, excluding image loading, plotting and per-component summaries.

At radio action 512:

- The SAM mask contains 2,225 valid pixels.
- With factor 4, the body-dominated patch has 1,790 pixels and median z 1.627 m.
- Separate patches of 141 and 43 pixels have medians 2.097 and 2.198 m. Visual
  inspection places these deeper regions around the handle opening.
- Factor 8 joins more of the radio surfaces into a 1,999-pixel patch, while the
  two deeper patches above remain separate. Factor 2 fragments the boundaries
  more aggressively, but also separates the deeper regions.

In 11/12 radio views the largest component contains no pixels more than 15 cm
behind the full SAM-mask median at any tested factor. At action 416, factor 4/8
leave three such pixels in the largest component out of 427 across the full
mask. These statistics indicate separation, **not a background-removal accuracy
score**. The largest component is inspected descriptively, never selected for
control; legitimate small handles and parts must not be discarded.

All settings produce small edge fragments: radio counts range from 27 to 161
components. Factor 2 splits one fireplace false-positive box into 837 patches;
factor 8 yields 14. A wall picture remains one connected surface across all
settings. This demonstrates both sensitivity and a key limitation: geometry
cannot correct the detector's television/gripper labels. The raw labels are
preserved rather than relabeled as true object identities.

Visual checks covered radio actions 416, 512 and 768, the initial fireplace
false-positive gripper box, and the final actual gripper. Machine-readable
statistics and complete component label arrays cover all 18 masks. Plots color
the largest 12 components for legibility and show other patches in gray; this
display convention does not merge or discard components in saved data.

## Verification and Decision

Twelve partition tests pass, covering background openings, retained thin parts,
smooth slopes, a connected surface spanning 40 cm depth, invalid/empty input,
four-neighbor connectivity, units, input immutability and tolerance validation.
Together with the prior mask/depth tests, 21 focused private tests pass; Ruff
passes. Source RGB/depth identities, SAM mask hashes, calibration bindings and
source receipt hash are checked before replay; generated label arrays have
checksums. No simulator poses or segmentation labels are used.

Keep SAM for semantic extent and retain observed depth patches separately.
The replay supports that representation change without a new model search.
Do not claim the mask is now clean, assign patches by size/depth alone, fit one
surface over the entire object, or use these results as contact authority.

Before contact use, a requested visible part must be associated with a patch,
its local geometry and support checked, and ambiguity must lead to abstention
or a new observation. Local normals, cross-view stability, moving localization
and low-space clearance remain separate unqualified requirements. Live SAM
co-residency also remains untested. None of these replay results advances the
strict hybrid-motion gate by itself.
