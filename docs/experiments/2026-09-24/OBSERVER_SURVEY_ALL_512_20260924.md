# All-Candidate Observer Survey

Date: 2026-09-24  
Scope: offline observer-pose visibility search over the retained interpolated
sweep anchor  
Receipt: `OBSERVER_SURVEY_ALL_512_20260924_RECEIPT.json`  
Receipt SHA-256: `f6c8e09ffe498f9eaa1a4255fcd8d8a4d1a858e693c81a057f48c5344f3f6af1`

## Result

The corrected run evaluated all 513 Sobol candidate configurations against
10,725 retained left-arm return samples. The earlier run had accidentally
retained a 129-posture `m=7` result; it is preserved as a failed/limited
attempt and is not used as the all-candidate result.

Candidate 384 remains the strongest total-visibility candidate with 6,545
unblocked samples. It has no sampled visibility on proximal left-arm links
1--4. Candidate 366 is a useful proximal follow-up with 1,462 unblocked
samples, including 1,239 of the 2,459 proximal samples on links 1--4. It is
not a complete return corridor: link 1 remains uncovered and substantial
proximal geometry is still unseen. Candidate 119 is the only surveyed
candidate with any link-1 samples, but it exposes only five samples total and
is not a practical observer candidate.

The survey confirms that the previous top-three search was too narrow and
changes the offline candidate ranking. It does not establish that any
candidate is safe to execute.

## Method And Limits

The search used the retained legal RGB-D/FK anchor and authored collision-hull
ray occlusion. Origin-containing hulls were skipped as specified by the
survey implementation. It did not have scene depth at hypothetical observer
poses, a continuous swept-volume clearance proof, pose uncertainty bounds,
dynamic-obstacle handling, or native stopping evidence. The receipt's
historical visibility union is therefore not current free-space authority.

Candidate 366 received a separate offline straight-path audit. It checked 65
interpolated postures and 715,195 hull-pair checks with zero sampled authored
hull intersections, valid joint limits, and a minimum FCL distance of
23.328 mm. Its maximum joint excursion was 2.861 rad and its joint-space L2
delta was 4.848 rad. These results are useful for selecting the next analysis
target but do not qualify continuous clearance or authorize motion.

## Decision

Do not execute candidate 384 or 366 on this evidence. The next meaningful
Phase 5/7 step requires a different authority source: either a camera/staging
strategy that covers the missing proximal corridor with contemporaneous scene
evidence, or a deliberately no-motion experiment that evaluates the executive
and memory layers without claiming physical control.

