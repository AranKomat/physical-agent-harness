# GLM Versus VLX: Matched-View Blind Inventory

## Conclusion

For general discovery on these six retained views, GLM was more useful and slightly
faster than the current local VLX pipeline. Prefer GLM as the next occasional
discovery candidate, with SAM tracking between discovery calls. Retain VLX as an
optional local target detector, not the preferred general inventory model based
solely on its earlier short-answer latency.

This is a small single-room development comparison, not a broad model ranking.

## Results

| Metric | GLM Flash, low requested effort | VLX-Seek-1.5-10B inventory |
| --- | ---: | ---: |
| Completed views | 6/6 | 6/6 |
| Major-category checklist coverage, ordinary synonyms joined | 37/39 (95%) | 25/39 (64%) |
| Coverage with earlier narrower alias table | 30/39 (77%) | 25/39 (64%) |
| Median practical latency | 4.53 s | 6.03 s including proposals |
| Latency range | 4.03-5.23 s | 5.40-8.58 s including proposals |
| Radio named in three fully visible views | 3/3 | 0/3; speaker instead in 3/3 |
| Valid strict JSON and at most twelve entries | 6/6 | Not strict JSON; native output sometimes exceeds twelve regions |

VLX inference alone was 4.75 s median. Its previously quoted approximately 0.7 s
inference / 2 s with proposals applied to seven-token target detection, not general
inventory. That was not a fair latency basis for choosing a general discovery model.
GLM's measured latency includes client/network/provider response time. VLX's combined
latency adds previously measured proposal-helper time to fresh inventory inference,
excluding one-time VLX loading. A persistent detector could improve VLX's number;
it was not tested here. Runs were not simultaneous or repeated for timing statistics.

## Matched Scope

Both inventories use views 0, 288, 352, 384, 512, 768, the same native 720x720 image
pixels, no history, no target category in the prompt, and a request for up to twelve
noticeable instances across the image. The pre-existing manual checklist covers
39 category/view pairs, excluding walls/floors, outdoor objects, robot parts, and
individual small picture frames/books. The model prompts do not forbid those items;
they consume inventory space but do not earn checklist coverage.

GLM user prompt:

```text
Identify up to twelve major noticeable visible objects in this image, covering the left, center, right, foreground and background rather than only the most salient item. Include furniture, fixtures and smaller distinct objects where visible. Do not assume a task or expected object. Use ordinary categories, or unknown if unclear. For each selected instance give its category, native pixel box, a short visible description and clear or uncertain identity. Do not claim completeness or invent hidden objects.
```

The system instruction explicitly requires native 720x720 pixel coordinates on both
axes, not normalized coordinates, positive box dimensions, and one instance per entry.
Strict JSON schema requires `label`, `attributes`, `certainty`, and `box` with four
named coordinates in 0..720. There is no extra rationale field. VLX used the same
semantic inventory request with its native supplied-region reference format rather
than JSON and free-coordinate generation. Therefore this is a comparison of usable
pipelines, not an identical-format decoder benchmark.

GLM endpoint: `z-ai/glm-5.3-flash`, Together only, no fallback, strict schema,
2048-token maximum, `reasoning.effort=low`. All six responses reported zero reasoning
tokens and no cached prompt tokens. This does not establish a provider-wide guarantee
about low mode. Total cost was **$0.002647**.

## Coverage Interpretation

The 95% is category-presence checklist coverage, not instance completeness or mAP.
It does not penalize all false positives or prove every box is accurate. Ordinary
subtype aliases added after inspection include TV stand/sideboard to cabinet,
pendant lamp to lamp, sliding door to door, and wall shelf/shelf unit to shelf.
They are applied equally to both models, with the earlier alias score preserved.
Even under that narrower table GLM leads 30/39 to 25/39.

| View | GLM categories | VLX categories |
| --- | ---: | ---: |
| 0 | 4/4 | 3/4 |
| 288 | 6/6 | 5/6 |
| 352 | 5/7 | 4/7 |
| 384 | 8/8 | 5/8 |
| 512 | 7/7 | 4/7 |
| 768 | 7/7 | 4/7 |

In view 352, GLM returned the clipped radio and cabinet as unknown, so neither earns
category credit, although it discovered their regions. Its clipped-target box IoU
was 0.396 against the approximate manual visible reference. Unknown is a legitimate
discovery outcome and should not be interpreted as absence.

## Localization And Errors

With the explicit pixel contract, GLM's three fully visible radio boxes scored
0.804, 0.742, and 0.853 bounding-box IoU against the frozen approximate manual
references. Boxes were used exactly as returned, without scale repair. Annotated
side-by-side images show useful furniture localization too, but no exhaustive
per-instance localization score was computed.

This is stronger evidence for usable pixel output than the earlier interrupted
two-view test. It is not a controlled causal proof that pixel wording alone fixed
the problem: inventory size, prompt wording, and output fields also changed.

GLM still made errors: one gripper was called a vacuum cleaner; other frames used
game/VR controller labels rather than robot parts. Some broad boxes include extra
background, and it spent slots on walls or outdoor details. VLX's radio-as-speaker
regions are still useful candidates, but its gripper-as-gun and other semantic errors
remain relevant. Neither inventory should be treated as authoritative world state.

## Next Step

Test GLM pixel discovery into the already-qualified box-to-SAM replay adapter,
retaining uncertain candidates and checking semantic identity before consequential
motion. Use discovery on scene changes or tracking loss, not every frame. The
earlier approximately 159 ms SAM propagation result is the reason this can be a
two-rate pipeline. No GLM-to-SAM or motion trial was run in this comparison.

## Budget And Artifacts

The user explicitly approved six fresh calls, cumulative ceiling 4127, local $0.25
cap, unchanged $75 campaign ceiling, and acknowledgment of the prior HTTP 429 to
allow new calls while retaining its full hold. The failed request was not retried.
All six new calls settled; every prior hold remains intact.

Afterward: 4127 calls, confirmed $23.61798139640, unresolved $34.955225022900,
exposure $58.573206419300. No GPU run or instance-state change was needed.

Private parent-workspace artifacts:

- `internal/physical-ai-lab/runs/glm-blind-inventory-20260923-r1/`
- `internal/physical-ai-lab/runs/glm-vlx-inventory-comparison-20260923-r1/`
- `internal/physical-ai-lab/scripts/run_glm_view_sweep.py --pixels --inventory`
- `internal/physical-ai-lab/scripts/analyze_glm_vlx_inventory.py`

Request/image hashes and parsed response receipts were checked; visual boxes were
inspected. Nine focused schema tests passed. Ruff passed after import formatting.
No production runtime changes, commit, or push were made in this turn.
