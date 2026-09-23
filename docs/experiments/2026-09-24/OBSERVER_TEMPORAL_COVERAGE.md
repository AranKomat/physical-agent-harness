# Temporal Observer Coverage

The corrected offline run `native-interpolated-sweep-20260924-r2-observer-setcover2`
retains sample-level visibility for all 13 candidates with nonzero proximal
visibility in the 513-candidate survey. It used no actions or paid calls.

The union of these 13 masks covers 6,969/10,725 total sampled return points.
A greedy total-coverage selection of six poses (137, 366, 346, 315, 21, 330)
covers 6,899 points. This is not a proximal-optimized sequence or a feasible
motion plan. Other candidates without proximal coverage could improve total
coverage, but cannot address the following decisive deficit.

Across all 513 ray-tested candidates, only candidate 119 sees any link-1
samples: 2/88. Thus even an optimistic union of every sampled viewpoint leaves
86/88 link-1 samples unseen. No sequence drawn from this sampled set can provide
complete sampled return visibility under this model. This does not prove that
all physically possible observer poses or alternative return paths fail.

Stop qualifying individual poses from this set for the full return. A different
camera/torso configuration or return trajectory is required before native
observer motion could address the missing evidence. Temporal visibility alone
would still not establish contemporaneous external clearance.

## Reproduction Caveats

The first launch never reached the host because its copy command omitted the
SSH port. The next run imported the original 129-candidate module because the
script directory took precedence over PYTHONPATH; it is retained as
`native-interpolated-sweep-20260924-r2-observer-setcover`, not used here.
The corrected launch imported the runner with `python -c` and the intended
temporary directory first on PYTHONPATH. All 513 rows have ray-test counts;
13 retain sample indices. The inherited scope string still says `top3` and is
incorrect; row inspection, not that string, establishes execution scope.

Corrected receipt SHA-256:
`06d9ff9c8add66d975ae7c747540a71e33201840917333e244b74f9654a851f8`.
Local retained copy: `internal/physical-ai-lab/backups/observer-temporal-20260924/`.
The scope remains optimistic authored-hull optics with the left arm fixed at
the anchor. No hypothetical scene depth, continuous clearance, native optical
calibration, or motion authority was established. No phase is marked complete.
