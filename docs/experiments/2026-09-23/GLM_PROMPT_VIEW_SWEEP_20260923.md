# GLM Flash Strict-JSON Prompt/View Sweep

## Conclusion

GLM is a promising occasional semantic discovery model, but its returned coordinates
are not ready to drive navigation or seed segmentation without qualification.
All 18 responses passed strict local schema and positive-box validation. Several
otherwise convincing object descriptions had completely misplaced boxes. Some
boxes mix coordinate conventions across axes, so automatic rescaling is not a fix.

The next narrow test should compare an explicitly pixel-coordinate contract against
the current normalized contract, or ask GLM to choose among detector-provided region
IDs. Do not silently repair this run or promote its boxes into motion authority.
No follow-up paid calls were made.

## Protocol

- Model: `z-ai/glm-5.3-flash`, pinned OpenRouter provider `together`, low reasoning.
- Three prompts on six preselected 720x720 retained native RGB images: 18 independent calls.
- Only one image per call. No history, future frames, target boxes, or audit annotations supplied.
- API `response_format.type=json_schema`, `strict=true`; no fallback or retry.
- Output cap 2048 tokens. Provider parameter support required. Serial dispatch,
  rotating A/B/C order between views to reduce fixed-order confounding.
- Local cap $1; actual total **$0.00526660**. All calls settled.
- Cumulative count 4118; confirmed $23.61466629640; unresolved prior holds
  $34.944996222900; exposure $58.559662519300 under unchanged $75 ceiling.
- No simulator actions, deployment changes, GPU model changes, or Qwen calls.

This is a small correlated development trace, not a benchmark or model ranking.
The camera views vary in apparent size and angle, not independently established
metric distance. There is one edge-clipped view, not a controlled occlusion study.

## Prompts

Each request used this common system instruction, without pseudo-JSON examples:

```text
Inspect only the supplied image. Return the requested JSON object with at most five objects. For each object, label gives an ordinary category or unknown; attributes describes directly visible features; certainty is clear or uncertain about the category; rationale briefly explains the identification or why inspection is worthwhile, marking hypotheses explicitly. The box encloses the visible instance or region: integer coordinates normalized to 0..1000 on each axis, origin top left, x rightward and y downward. Use x_min < x_max and y_min < y_max. Do not claim completeness or persistent identity. Return only JSON conforming to the schema.
```

User prompt A, general discovery:

```text
Identify up to five distinct visible objects in this room. Include unidentified objects when their category is unclear.
```

User prompt B, goal-directed discovery:

```text
Our objective is to find a radio. Identify up to five visible objects or regions worth inspecting toward that objective. Include plausible but uncertain candidates; do not assume a radio is present. Distinguish directly observed features from hypotheses.
```

User prompt C, direct detection:

```text
Locate any visible radio. Return each plausible candidate and mark its identity as clear or uncertain. Return no candidates if none are supported by the image. Do not force a match.
```

The schema requires a root `objects` array of at most five entries. Every entry
requires nonempty `label`, `attributes`, and `rationale` strings, a `certainty`
enum (`clear` or `uncertain`), and a `box` object with integer `x_min`, `y_min`,
`x_max`, `y_max`, each bounded 0..1000. All object levels disallow extra properties.
Local validation additionally rejects nonpositive boxes. Full executable schema,
request bodies, and raw receipts are retained in the private artifacts below.

A is category-blind; B/C know the radio objective. These compare useful prompting
conditions, not equal-information recognition. Wording and schema both changed
from earlier runs, so improvements cannot be attributed to schema alone.

## Results

| Prompt | Valid packets | Median latency | Range | Total cost |
| --- | ---: | ---: | ---: | ---: |
| A: general discovery | 6/6 | 6.50 s | 5.45-10.34 s | $0.0019660 |
| B: goal-directed | 6/6 | 8.98 s | 6.95-25.96 s | $0.0022811 |
| C: direct radio | 6/6 | 3.07 s | 1.72-3.55 s | $0.0010195 |

These are client-observed full-request latencies, including network/provider time.
No prompt caching was reported. Low effort was requested for all calls; reported
reasoning-token usage varied, including zero. The two empty C responses contribute
to its overall median; the four positive C responses took 2.90-3.55 s.

| Frame | Visible radio | A semantic description | B semantic description | C semantic description |
| --- | --- | --- | --- | --- |
| 0 | Not visible | No radio claim | Search-location hypotheses; no visible-radio claim | Empty |
| 352 | Heavily clipped at left edge | Omitted | Uncertain radio or speaker | Empty |
| 384 | Larger oblique view | Unknown; radio/boombox hypothesis | Clear radio | Clear radio |
| 448 | Smaller central view | Uncertain radio | Clear radio | Clear radio |
| 512 | Smaller frontal view | Clear camera; radio mentioned as alternative | Clear radio | Clear radio |
| 768 | Larger later view | Clear radio | Clear radio | Clear radio |

B nominated the target in all five visible views, including a cautious hypothesis
for the clipped object. C described it as radio in all four full-object views and
abstained on the clipped and absent views. A sometimes described it well but did
not consistently resolve the category. None claimed a visible radio in frame 0.
One absent view is insufficient to estimate general false-positive rate.

B always returned five entries, including speculative shelves, cabinets, and sofas
even when it had already identified the target. These are search suggestions, not
evidence of a radio at those locations. Certainty sometimes conflicts with cautious
rationale wording; it must not be treated as calibrated probability.

## Localization Failure

Approximate manual visible target boxes were frozen before dispatch, separately from
the inputs. No SAM mask was used as ground truth. Returned normalized coordinates
were converted to pixels exactly as instructed, with no repairs.

| Prompt | Target views with a box IoU >= 0.30, of five visible views |
| --- | ---: |
| A | 0/5 |
| B | 3/5 |
| C | 2/5 |

The 0.30 threshold is a post-run descriptive diagnostic, not a preregistered pass
gate. A's camera box in frame 512 scores 0.297, so its failure at this threshold is
borderline geometrically and also a semantic error. Many other failures have zero
target overlap, which is not a threshold artifact.

Examples:

- A384's object box overlaps well if interpreted as pixels (IoU 0.663), but has zero
  overlap when used according to the requested normalized contract.
- B768 similarly scores 0.770 under a diagnostic pixel interpretation but zero as requested.
- C448 returned x=408..486 and y=384..421. The x values resemble normalized target
  coordinates while y resembles native pixels. Neither uniform interpretation works.
- A768 also mixes normalized-looking x with pixel-looking y.

Diagnostic alternative interpretations are saved separately and are not counted
as successful localization. These outputs cannot be made trustworthy merely by
validating JSON, clipping bounds, or applying one global scale factor.

## Recommendation

Keep SAM tracking/segmentation and measured depth responsible for precise geometry.
Use GLM only as an occasional semantic hypothesis source for now. Qualify an explicit
pixel box contract, or ground semantics onto independently detected region IDs,
before using it for discovery-to-tracking handoff. Preserve uncertain candidates
without turning their labels or search-location guesses into persistent facts.

## Reproduction And Artifacts

Private lab, relative to the parent workspace (not part of this public repository):

- `internal/physical-ai-lab/scripts/prepare_glm_view_sweep.py`
- `internal/physical-ai-lab/scripts/run_glm_view_sweep.py`
- `internal/physical-ai-lab/scripts/analyze_glm_view_sweep.py`
- `internal/physical-ai-lab/tests/test_glm_view_sweep.py`
- `internal/physical-ai-lab/runs/glm-view-inputs-20260923-r1/manifest.json`
- `internal/physical-ai-lab/runs/glm-view-sweep-20260923-r1/`: preflight, requests,
  responses, report, audit, and `comparison.png` (green manual reference, magenta as-returned boxes).

The analyzer checked request hashes and image hashes against transport receipts.
Twelve focused tests passed (seven new schema cases plus five existing discovery
cases); Ruff passed for the new runner, analyzer, and tests. Full harness tests were
not run because this change adds a private diagnostic and a report, not runtime code.
