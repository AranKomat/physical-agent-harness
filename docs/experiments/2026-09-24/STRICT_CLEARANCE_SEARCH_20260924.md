# Strict Clearance Candidate Search

## Question

After the native 10 cm outward-and-return mechanics trial succeeded, could a
different 10 cm right-EEF translation be qualified from the same fresh legal
reset capture without treating unobserved space as free?

This was an offline search only. It sent no robot actions and made no paid model
calls. Every candidate used the measured reset proprioception and the three
legally posed RGB-D cameras. Evaluator object or robot poses were not available
to the search.

## Fixed Screening Order

Each candidate had to pass, in order:

1. endpoint IK and the 0.25 rad active-joint departure bound;
2. authored-hull endpoint self-separation;
3. continuous straight-joint-path self-separation, including the declared
   tracking-error envelope;
4. rejection against sampled current depth points; and
5. camera coverage of exposed moving-geometry vertices at 21 path fractions.

The scene test is conservative in interpretation. Zero observed point
intrusions means only that the sampled depth did not show an intrusion. Any
exposed vertex outside every camera view remains unknown and prevents a strict
clearance claim.

## Results

| Requested 10 cm base-frame translation | Endpoint | Continuous self-separation | Endpoint exposed vertices outside all views | Decision |
| --- | --- | --- | ---: | --- |
| `+Y` | Pass | Fail near fraction 0.7995 | Not evaluated | Reject |
| `+Z` | Pass | Pass, 37 adaptive nodes | 6,708 / 6,710 | Reject: unknown volume |
| `-X` | Pass | Pass, 9 adaptive nodes | 6,629 / 6,651 | Reject: unknown volume |
| `-Y` | Pass | Pass, 7 adaptive nodes | 5,427 / 5,587 | Reject: unknown volume |
| `-Z` | Pass | Endpoint below path margin | Not evaluated | Reject |
| normalized `(+X,+Z)` | Pass | Pass, 19 adaptive nodes | 6,835 / 6,836 | Reject: unknown volume |
| normalized `(+X,-Y)` | Pass | Pass, 9 adaptive nodes | 6,224 / 6,321 | Reject: unknown volume |
| normalized `(-Y,+Z)` | Pass | Pass, 19 adaptive nodes | 6,982 / 6,983 | Reject: unknown volume |

For every scene-screened candidate, sampled depth points outside the reset-body
ambiguity band produced zero intrusions. This is not positive clearance evidence:
the overwhelming majority of exposed moving geometry was outside every retained
camera view. The best alternative, `-Y`, still left 97.1% of endpoint exposed
vertices out of view.

The first `+Z` scene invocation failed because required content-addressed depth
artifacts had not finished copying locally. That invocation produced no result.
After all three reset depth artifacts were copied and hash-checked, a new output
directory completed the analysis. The failed local-availability attempt remains
distinct from the completed result.

## Conclusion

No candidate authorizes another strict native motion trial. The search establishes
a current sensor-coverage limitation rather than a collision: fixed reset views
cannot observe enough of the moving right-arm/torso geometry to certify these
paths. Repeating nearby directions or the already successful `+X` mechanics path
would add little evidence.

Strict Phase 7 remains partial. The next useful clearance experiment needs a
deliberately qualified observer-camera posture or another source of current,
legal coverage. Historical unions and future camera motion must not be treated
as current free-space authority. Authored hulls also remain conservative proxies;
wheel coverage and cooked native-geometry equivalence are still open.
