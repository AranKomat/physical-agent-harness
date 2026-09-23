# Observer 384 Sampled Path

CPU-only run `observer384-path-20260924-r2` checked 65 equally spaced postures
from the retained final sensing posture to observer candidate 384. The
[receipt](OBSERVER384_PATH_RECEIPT.json) records checked input and script hashes.

- 715,195 pair queries; no sampled authored-hull intersections.
- Joint limits valid at every sample.
- Minimum reported FCL distance: 23.33 mm, on the held left arm.
- Largest joint displacement: 2.9662 rad; joint-vector displacement: 4.0018 rad.
- Endpoint camera transform is finite and homogeneous. This is not optical
  calibration or an actual candidate-view depth measurement.
- No simulator, robot actions, or paid calls.

The script is `scripts/observer_candidate_path_audit.py`. It requires the
private lab geometry helpers on PYTHONPATH and FCL, USD, yourdfpy, NumPy,
SciPy and YAML dependencies. Run with `--lab`, `--survey`, `--sweep`, `--native`,
`--output` and `--candidate-index 384`. The first successful r1 lacked the
explicit geometry/source hash precheck; r2 adds it and reproduces the result.

## Decision

This rules out sampled self-collision as the immediate rejection reason for
this straight joint-space path, not collision between samples or with the
environment. It does not qualify continuous clearance, execution or stopping.
The required joint excursion is substantial, and candidate 384 still does not
observe proximal left-arm links 1--4 in the existing survey.

Do not execute this observer move merely because the sampled path passes.
Before further path qualification, the observer strategy must demonstrate
coverage of the missing proximal corridor; distal coverage alone does not
resolve Phase 7. Phase 7 remains partial.

Correction to earlier narrative: the prior 128-sample survey's best unblocked
count was 2,167 (candidate 10), not 193. Candidate 71 had the largest frustum
count but only 193 unblocked points. The expanded search ray-tested only its
top three by frustum count, so 6,545 is the best evaluated count, not a proven
maximum across all 513 postures.
