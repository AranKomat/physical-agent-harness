# Fresh SAM 3.1 Retained-Frame Diagnostic

Date: 2026-09-23. Public runtime at `509fd76`, with private experiment runner.
This follows the [CPU association-contract replay](ASSOCIATION_CONTRACT_REPLAY_20260923.md).
It adds actual model inference on retained legal frames, not live simulator
collection, physical association qualification or task success.

## Restoration And Model Integrity

After the user authenticated locally, the official SAM 3.1 checkpoint was
downloaded to the new single RTX 4090 host. The old instance remained stopped.
No token was put in command arguments or saved in the remote HF credential store.

- Model: `facebook/sam3.1`, revision `daa63191845a41281374e725f4c9e51c7a824460`.
- Checkpoint: `sam3.1_multiplex.pt`, 3,502,755,717 bytes.
- SHA-256: `0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6`.
- SAM source: clean `2345a4ad109ac29c569da749c91d84f10dc08c40`.
- All 59 versions in the retained dependency freeze match; Torch 2.7.1+cu126.
- **All 1,589 learned tensors exactly equal the checkpoint values after loading.**
  No missing/mismatching learned parameters were found. Intermediate upstream
  missing-key messages therefore do not demonstrate learned-weight corruption in
  this run. Non-learned buffers were not exhaustively compared.

A separate builder-only probe took 21.89 s and reported 3,744.16 MiB Torch
allocated memory. That is not peak inference memory or a co-residency measurement.

## Frozen Trial

Private run: `phase2-fresh-sam-20260923-r1`. The runner fixed four cases, 25
model steps, six tracker initializations and a 600-second ceiling before execution.
All steps completed, with zero retries or deadline failures. No paid calls or
robot actions occurred. Source/runtime hashes remained unchanged, and model pins
were checked again afterward.

Forty-four source files (58,838,807 bytes) supply exact native RGB/depth/calibration
and the recorded VLX box/source image. Old masks and evaluator outcomes do not
drive inference. The original VLX box is used only on its matching first frame.

All cases use `official_file` preprocessing. S01 uses a source-bound VLX box;
the other cases use the predeclared single text prompt `radio` with image-mode
candidate acquisition at initialization, followed by video propagation rules.
This recipe was fixed before inspecting results; there was no wording sweep.
These are fresh cold starts on frozen subsets, not reproductions of full prior
tracker state or evidence that omitted intermediate frames were processed.

| Case | Scheduled frames | Positive-mask frames | Observed result |
| --- | ---: | ---: | --- |
| S01 box-seeded tracking | 13 | 13 | One source-bound mask follows the visible radio from sequences 384 to 768 |
| S07 reset diagnostic | 5 | 5 | Candidate present after both resets; local ID 0 reappears in three distinct generations |
| S12 partial hand occlusion | 4 | 4 | Visible target portions retained at 892/924/956/988; not complete disappearance |
| S13 negative view | 3 | 0 | No candidate on the three initial fireplace/TV views |

Positive-mask counts are not accuracy, recall or identity scores. Qualitative
inspection of all generated review panels supports radio alignment in the
positive frames. At action 924, most of the black hand is excluded, but apparent
gripper-edge contamination remains near the handle. No pixel ground truth,
part/contact accuracy, depth-surface qualification or physical association proof
was established. Every output remains `physical_identity=UNKNOWN`, with no
association proof or motion authority. Generation-scoped IDs do not resolve
identity after resets.

The arrived-frame adapter checked every raw model read against the current frame;
no future/noncurrent input reads were reported. Preflight hashes all files offline,
but the inference adapter receives and decodes only the next scheduled RGB frame.
Original source timestamps are retained; per-step durations are measured anew.
This runner does not establish native live capture-to-publication timing or record
a full per-result publication clock for a live downstream consumer.

## Timing

| Case | Initializing steps | Warm step median | Warm step p95 |
| --- | --- | ---: | ---: |
| S01 | 995 ms | 139 ms | 145 ms |
| S07 | 166 / 169 / 168 ms | 136 ms | 136 ms |
| S12 | 169 ms | 136 ms | 137 ms |
| S13 | 157 ms | 121 ms | 122 ms |

These are SAM step plus GPU synchronization timings on one otherwise idle 4090.
The first S01 step is also the first inference in the process; initialization
times across cases are not a controlled comparison. Timings exclude simulator
capture, depth/pose fusion, artifact publication, policy inference and contention.
They do not establish a 140 ms complete perception pipeline or two-GPU speedup.

## Verification And Artifacts

- Local fresh-runner tests: 25 passed; Ruff passed.
- Local and remote preflight passed without importing model packages.
- Full private suite: 629 passed, one existing skip.
- Initial full-suite run exposed one order-dependent test: another test had
  already imported `sam31_streaming`. The no-model-import assertion now runs in
  an isolated subprocess. The experiment runner/result was not changed or rerun.
- Public runtime remains the previously verified 1,481-test snapshot; this
  follow-up changes public documentation only.

Private files: `scripts/run_phase2_fresh_sam.py`,
`tests/test_phase2_fresh_sam_private.py`, and
`scripts/analyze_phase2_fresh_sam.py`.

Private artifacts under `runs/`:

- `phase2-fresh-sam-preflight-20260923-r2`: final local plan, source transfer list.
- `phase2-fresh-sam-remote-preflight-20260923-r1`: relocated source verification.
- `phase2-fresh-sam-20260923-r1`: report, worker log, masks, timings and manifests.
- `phase2-fresh-sam-analysis-20260923-r1`: hash-checked summaries and four mask
  review sheets. Crops are centered on predictions, not ground-truth annotations.
- `sam31-runtime-restore-20260923-r2`: runtime/weight restoration receipt.

Final inference report SHA-256:
`e845b41f1b91c9c6cd924aa94307d2447fc8020f507cebd46f396f65ef077697`.
Completed inference outputs and restoration receipts have been copied to the Mac.

## Remaining Gates

Phase 2 remains incomplete. Natural full disappearance/reappearance, similar-object
crossings, broader scene variation and independently supported physical association
remain unqualified. The four scripted gaps from the CPU protocol have not become
native passes. A useful next diagnostic can use those scripted images for explicit
ambiguity handling, but natural sequence collection still requires restoration of
the simulator/sensor environment. That environment and the frozen motor are not
restored on the new host yet.

Do not re-run generic SAM wording or model searches based on this result. Preserve
the current model recipe; next work should target missing association scenarios
and live timestamped integration. Paid live GLM/context studies still require
separate call approval. No strict motion or capability gate has been relaxed.
