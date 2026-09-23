# Scan Tracking Envelope

## Question And Scope

Does candidate 67's authored-hull self-separation survive the diagnostic joint
monitor's permitted tracking errors, rather than only the exact nominal path?
This CPU-only follow-up uses the fresh captured posture and pinned robot assets
from `fresh-view-endpoints-20260923-r1`. No GPU job, robot action or paid call.

The prior 11.07-mm contact/diagnostic margin is unchanged. Each nonexcluded mesh
pair receives an additional conservative joint-error displacement bound. A
revolute joint contributes downstream radius times angular error; a prismatic
joint contributes its linear error. Common rigid ancestors cancel from relative
separation. Downstream prismatic radius bounds include their permitted error.
The existing support-gap interval check then includes both path variation and
tracking displacement. Tests cover shared ancestors, branch errors, prismatic
units/padding and invalid bounds.

## Results

Private receipts:

- `scan-tracking-envelope-20260924-r1`: the existing 0.02-rad active-arm error
  limit does **not** certify the path. Near its initial endpoint, one base/finger
  pair has a 107.48-mm projected support gap versus 123.32 mm required, including
  112.23 mm of conservative joint-error allowance. This is failure to certify
  an uncertainty envelope, not evidence of an actual collision.
- `scan-tracking-envelope-20260924-r2`: tightening active-arm tracking error to
  0.003 rad certifies the full nominal path plus the stated error envelope in
  43 adaptive nodes. Held revolute-joint error remains 0.003 rad and finger
  displacement error remains 0.002 m.
- `scan-joint-monitor-replay-20260924-r1`: the tightened monitor accepts all 120
  retained stationary physics samples. A regression test rejects tracking lag
  above 0.003 rad even when measured velocity alone would pass.

The monitor now uses the stricter 0.003-rad limit. The earlier 0.02-rad proposal
is superseded, not silently treated as covered by the new geometry result.

## Limitations And Next Step

No native scan has run. The proof is conditional on remaining inside the error
envelope. Discrete monitoring cannot guarantee this between samples or after an
abort; braking response and excursion still need native qualification. It also
does not cover external obstacles, wheel spheres or native collision cooking.
The new error-aware self-separation does not turn the sampled scene-depth check
into external clearance.

The next native runner must bind these checks to its own fresh state, include
legal head RGB-D/FK base monitoring, preserve unknown external clearance, and
honor the separately approved one-attempt/action/hold limits. No motion authority
or strict stop gate is enabled by this offline result.
