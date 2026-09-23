# GLM Pixel Coordinates And VLX Goal Discovery

## Conclusion

VLX-Seek is promising for occasional target-conditioned detection: its native
proposal-selection path localized the radio in all five visible retained views,
including the heavily edge-clipped view, and returned no match in the absent view.
Measured proposal generation plus model inference was about 2 seconds median.

It did not provide the requested descriptions or uncertainty judgments. Both the
goal-directed and direct prompts produced the same radio-only selections. This is
not evidence that VLX replaces a general scene-discovery or reasoning model.

GLM's explicit pixel-coordinate test is incomplete after provider HTTP 429. Two
responses were usable, but only one contains the target. Do not conclude that the
pixel contract fixes its localization from this sample.

## Protocol

Same six 720x720 retained current images selected for the preceding GLM sweep:
0 (radio absent), 352 (left-edge clipped), 384, 448, 512, 768 (fully visible with
varying angle and apparent size). All are from one correlated development trace.
Only one current image per request; no history or audit target boxes were supplied.
Approximate manual reference boxes were fixed before the preceding sweep.

GLM used the same goal-directed prompt B, low effort, Together provider, and strict
JSON schema, with its localization instruction changed to:

```text
The box encloses the visible instance or region: native pixel coordinates in this 720 pixel wide by 720 pixel tall image. Do NOT normalize or rescale coordinates. The top-left image boundary is (0, 0); the bottom-right boundary is (720, 720). Both x and y use the same native pixel units. x increases rightward and y increases downward.
```

Each schema coordinate also states native pixels, with bounds 0..720. No example
object values, silent rescaling, fallback, or retry. Structural validation still
checks positive box dimensions separately.

VLX used the previously installed `VLX-Seek-1.5-10B` revision
`6d1925f932ee6f0a8790b15420f403ee8f8e8f6a`, source install record
`01187078e02c7fba7d0eb87af930ee9aec3af12c`. The actual installed worker SHA-256 is
retained in the result. Public WeDetect-Uni generated 100 class-agnostic proposals
per image. Two independent VLX paths selected among those proposals:

1. Goal-directed: the same B objective and candidate wording, followed by a native
   region-reference output instruction requesting categories, descriptions, and
   clear/uncertain judgments. Maximum 2048 generated tokens.
2. Control: upstream `worker.detect(..., 'radio')`. Maximum 512 generated tokens.

Goal output instruction:

```text
Use the supplied region references for localization, not invented coordinates. For each selected region use <ground>category</ground><objects><objN></objects>, where N is its supplied region index, followed by a short visible description and whether the identity is clear or uncertain. Return no candidates if none are worthwhile.
```

Native region references are decoded by the upstream worker into caller-proposal
pixel boxes. No task-specific manual box was supplied. Generation was greedy,
temperature zero; path order alternated between frames. No simulation actions.

## Results

| Path | Completed requests | Visible target localized | Absent-view result | Median latency |
| --- | ---: | ---: | --- | ---: |
| GLM pixel B | 2/6 | 1/1 tested | Search regions, no visible-radio claim | 13.74 s |
| VLX goal | 6/6 | 5/5 | No match | 2.00 s |
| VLX direct | 6/6 | 5/5 | No match | 1.97 s |

VLX timings sum measured per-image proposal generation and selection inference,
excluding one-time VLX model loading (32.43 s), network transfer of test files, and
image-file opening. Proposals were computed before loading VLX and reused between
the two independent query variants; each reported path is charged the full proposal
time. This is a staged component measurement, not live simulator throughput.

- Proposal helper: 0.99-2.69 s, including detector construction/loading per image.
- VLX goal selection: 0.67-0.71 s after the first call (first 1.25 s).
- Goal summed latency: 1.69-3.94 s, median 2.00 s.
- Direct summed latency: 1.67-3.41 s, median 1.97 s.
- Peak VLX allocated VRAM approximately 19.1 GiB; reserved approximately 19.9 GiB.
  This was an otherwise idle 24 GB RTX 4090, not a co-resident simulator/SAM test.

| Frame | VLX goal/control target box IoU | GLM pixel result |
| --- | ---: | --- |
| 0 | No target; no match | Search-region suggestions only |
| 352 | 0.797 | Uncertain radio/speaker hypothesis, box IoU 0.481 |
| 384 | 0.933 | HTTP 429; no model answer |
| 448 | 0.948 | Not dispatched |
| 512 | 0.913 | Not dispatched |
| 768 | 0.864 | Not dispatched |

These IoUs use approximate manually annotated visible boxes, not precise segmentation
ground truth. A 0.30 overlap threshold is descriptive only. The prior normalized B
already localized frame 352 (IoU 0.716), so the new pixel result on that frame is not
evidence of improvement. The previously failing full-object views remain untested
under the pixel contract.

VLX returned only `<ground>radio</ground><objects>...</objects>` on both paths.
It omitted descriptions and uncertainty even on the clipped view. Its empty response
on the absent view does not establish calibrated abstention or a general false-positive
rate. Similar distractors, attributes, unseen objects, and genuinely distant objects
still need testing. The native VLX path and GLM JSON path are system comparisons,
not identical-format or equal-output-length latency comparisons.

## API Interruption And Budget

The user approved six calls, $0.25 local cap, cumulative ceiling 4124, unchanged
$75 campaign ceiling and all existing holds. Two calls completed at $0.00066810
total; the third received HTTP 429 with no usage settlement. Its $0.01022880
reservation remains held.

After cooldown, a continuation attempted to dispatch only the three never-sent views.
The provider guard rejected this before transmission because the provider had an
unresolved reservation. No further calls were sent; no request was retried and no
hold was released. The guard was not bypassed.

Final recorded budget: 4121 calls, confirmed $23.61533439640, unresolved
$34.955225022900, exposure $58.570559419300. The GLM pixel sweep remains incomplete.

## Next Step

Use VLX as a candidate target-discovery component for a bounded handoff-to-SAM test,
not as a replacement for the whole perception stack. Test distractor rejection and
box-seeded tracking before enabling motion. It can run occasionally; it is not yet
a 200-300 ms frame-by-frame pipeline. Persistent proposal-model loading may reduce
latency, but this experiment did not measure that optimization.

Keep GLM available for richer semantics. Complete the pixel-coordinate qualification
only after resolving the provider reservation explicitly; never reinterpret a box
based on knowledge of where the target should have been.

## Artifacts And Verification

Private parent-workspace artifacts, not uploaded with this public report:

- `internal/physical-ai-lab/runs/glm-pixel-sweep-20260923-r1/`
- `internal/physical-ai-lab/runs/glm-pixel-sweep-20260923-r1-remaining/` (blocked before transmission)
- `internal/physical-ai-lab/runs/vlx-goal-sweep-20260923-r1/`
- `internal/physical-ai-lab/runs/pixel-vlx-comparison-20260923-r1/`
- Scripts: `run_glm_view_sweep.py`, `run_vlx_goal_sweep.py`, `analyze_pixel_vlx_sweep.py`
  in `internal/physical-ai-lab/scripts/`.

The initial VLX startup failed before inference because the installed source is an
archive without Git metadata. The runner was corrected to hash the installed worker;
both startup logs are retained. Proposal checkpoint missing-key checks passed.
Input/request hashes were checked, and rendered comparison boxes were visually audited.
Thirteen focused tests and Ruff passed. Full harness tests were not run; no production
runtime was changed. The GPU process exited and results were copied to the MacBook.
The Vast instance remains running, as requested.
