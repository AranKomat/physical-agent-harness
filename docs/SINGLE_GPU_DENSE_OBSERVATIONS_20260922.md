# Acquisition Cadence and Coverage Diagnostics

## Retained Sparse Trace

Source: `single4090-grounding-extended-20260922-r1`, an ordinary seed-1 reset
with 768 frozen Behavior-Skill approach actions. No classical transit or GPT.
Native receipt SHA-256:
`2f140765ecba48ff9664b8fcd64d54a3c4ea71df07880bf7466a11ae56b03c49`.

Two CPU audits ran concurrently on the locally verified evidence:

- Adjacent independent head-depth ICP pairs: 15/24 passed the existing fit
  thresholds; nine were rejected. Zero pairs met the existing two-second wall
  freshness limit; eight passed both fit and camera step-size bounds.
- Four fitted pairs had accepted target detections at both endpoints. Partial
  surface-median residuals were 0.170, 0.128, 0.108 and 0.006 m. These are not
  independent pose errors: visible surfaces vary, and target depth is included
  in registration. Fit acceptance is not proof of correct motion.
- The fresh final-view coverage audit found all 1,361 exposed samples below
  0.4 m outside all three cameras for the hypothetical target-directed 10 cm
  move. A 5 cm forward control similarly left all 1,171 low samples outside.

Rejected pairs have no transform prediction, not an assumed zero displacement.
The coverage audit samples authored geometry; it does not certify a continuous
sweep or establish free volume. Both checks leave strict motion gates closed.

## Prospective Dense Diagnostic

`--dense-observation-diagnostic` adds legal all-camera RGB-D/proprio captures
every four actions during the fixed 384..512 action window of an isolated
768-action A acquisition. Existing 32-action boundary captures are reused;
28 additional captures are retained separately. There are no extra policy or
grounding calls, no new classical commands and no change to policy input cadence.
Extra evidence serialization changes wall timing; it is not a bitwise rollout
equivalence claim.

Dense and sparse independent pairs should be compared on the same retained
window with unchanged identity-initialized ICP and thresholds. This is an
offline localization diagnostic, not online fixed-reference tracker qualification
or authorization to integrate a map or execute motion. Early native termination
is preserved; incomplete dense schedules must not be scored as completed runs.

Verification: 1,076 public tests and 32 private audit/launcher tests passed.
Action-path regression tests cover exact action vectors, policy requests,
boundary observations, counts, and termination with dense capture on/off.

## Completed Live Run

`single4090-dense-acquisition-20260922-r1` completed 768 policy/native actions,
25 normal captures and 28 extra dense captures. Policy exposure took 261.875 s;
peak sampled GPU memory was 20,540 MiB. No GPT calls or classical actions were
added. Native task success remained false; this was an approach-only instruction.
All workers exited. The complete 266 MiB remote run was downloaded and a final
checksum-rsync comparison found no differences. Native receipt SHA-256:
`88d548ed9229ecff4602b2701521f4d08244ce9cecbd4bbf43e9a3d2734d03f3`.

Head images at 384, 512 and 768 were visually checked: the radio is initially
outside view, becomes visible on the table, and appears closer at the end.
This is qualitative approach evidence, not base displacement or power-on.
Accepted detector targets start at 416. Do not compare this rollout pointwise to
the earlier seed-1 run as though ordinary resets were bitwise reproducible.

### Same-Trace Cadence Comparison

Both CPU audits ran concurrently after the local backup passed checksum checks.
They use identical depth registration, identity initialization and thresholds,
without retries or simulator poses.

| Measure, action window 384..512 | Dense, 4 actions | Sparse, 32 actions |
| --- | ---: | ---: |
| Independent pairs | 32 | 4 |
| ICP fit passes | 32 | 0 |
| Fit plus camera-step bounds | 32 | 0 |
| Wall gap <= 2 seconds | 28 | 0 |

Dense estimated camera increments reached at most 0.02185 m and 2.0889 degrees.
Gaps ranged from 1.450 to 2.900 s, median 1.618 s. The four freshness failures
were 384->388, 416->420, 448->452 and 480->484, immediately after ordinary chunk
boundaries. Boundary processing includes serialization, synchronous grounding
(~0.75-0.77 s), and policy inference. Investigate capture scheduling rather than
increasing the freshness threshold.

Composing eight dense transforms across each 32-action window gives target
surface-median residuals of 0.02647 m (416..448), 0.02450 m (448..480), and
0.00552 m (480..512). The first window has no starting target detection. These
are non-independent consistency diagnostics, not pose ground truth; each
composed window still contains a freshness failure. No map/control authority
is granted. Full-trace sparse results were 15/24 fit passes and 0/24 fresh pairs.

## Next Gate

Qualify a separate sensor/localization cadence that does not inherit synchronous
model-boundary delays, then test the actual fixed-reference tracker and its loss
behavior. This adjacent-pair diagnostic is not that test. Do not promote composed
transforms directly into control or weaken the two-second gate. Low-body swept
clearance remains a separate unresolved sensing problem; these denser head views
do not establish a safe target-directed B condition.
