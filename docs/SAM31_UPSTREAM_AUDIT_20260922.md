# SAM 3.1 upstream usage audit

## Scope

Retained-image diagnostics only: no simulator actions, paid GPT calls, threshold
changes, or new motion authority. Five native full-frame PNGs from the missed
384-512 window were reused with fresh states and unchanged prompts. These are
correlated development examples, not a recognition benchmark.

Earlier successful overlays came from other trace/view/history conditions;
some subsequent overlays used broader prompts. They are not paired evidence
that the same input previously worked.

## Upstream and installation

- Official source pin `2345a4ad109ac29c569da749c91d84f10dc08c40` equals upstream
  `main` at audit time. No source upgrade was needed.
- Official multiplex checkpoint SHA-256:
  `0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6`.
- Every loaded learned parameter was compared exactly against checkpoint values:
  no mismatches. Early builder missing-key warnings do not establish missing
  final learned weights; final absent keys are rotary-frequency buffers.
- Python 3.12.14, torch 2.7.1+cu126, torchvision 0.22.1+cu126, Pillow 12.3.0.
- The documented public `start_session` call fails on this revision because it
  forwards `offload_state_to_cpu` to a model method that does not accept it.
  The failed attempt is retained as `sam31-official-audit-20260922-r1`.
  Subsequent comparisons use unchanged upstream `model.init_state` and
  `model.add_prompt`, not a claim of successful public-wrapper execution.

## Important distinctions

The upstream file loader resizes with torchvision's PIL bilinear path and stores
normalized images as FP16. Our original online adapter uses PIL's default resize
and FP32 storage. The upstream PIL-list loader also differs from the file loader.

More importantly, upstream marks a PNG path or a one-image PIL list as
`is_image_only=True`, but an image directory as video. Image-only new-object
admission uses `image_only_det_thresh=0.5`; video uses `new_det_thresh=0.65`.
Our online adapter initializes from a directory, so it correctly takes the video
path. Comparing it with single-image results without this distinction is unfair.

## Measured results

Each row tests the same five full images with `a radio`:

| Path | Positive frames |
| --- | --- |
| Upstream PNG, default settings, image mode | 2/5 (416, 480) |
| Upstream PNG, online settings, image mode | 2/5 (416, 480) |
| Upstream PIL list, online settings, image mode | 1/5 (480) |
| Original online adapter, video mode | 0/5 |
| Adapter with exact file preprocessing, video mode | 0/5 |
| Upstream lossless PNG folder, online settings, video mode | 0/5 |

The two upstream PNG masks were visually inspected and cover the radio.
All paths produced at least one candidate on every frame with `a red object`,
but candidate counts differed. That does not establish semantic identity.

The first image-vs-adapter difference was initially suspected to be preprocessing.
The preprocessing-only test did not recover radio detections. Do not cite the
2/5 versus 0/5 comparison as proof of a preprocessing bug. It also changes image
versus video admission. The matched upstream video-folder control also misses
all five radios. Its masks and IDs match the file-preprocessing adapter exactly
on all 10 prompt/image pairs, including the positive red-object controls.
This checks fresh acquisition, not full sequence propagation equivalence.

An opt-in `preprocessing="official_file"` was added to the private adapter for
controlled comparisons. The legacy default and deployed worker remain unchanged.
Focused local tests: 21 passed; touched Python files pass Ruff.

## Artifacts and sources

Private retained runs: `sam31-official-audit-20260922-r2` (40 paired outputs),
`sam31-official-audit-20260922-r3` (10 preprocessing-only outputs), and
`sam31-official-audit-20260922-r4` (10 matched video-folder outputs).
The diagnostic is `scripts/audit_sam31_official.py` in the private lab.

- [Official 3.1 release notes](https://github.com/facebookresearch/sam3/blob/2345a4ad109ac29c569da749c91d84f10dc08c40/RELEASE_SAM3p1.md)
- [Official 3.1 notebook](https://github.com/facebookresearch/sam3/blob/2345a4ad109ac29c569da749c91d84f10dc08c40/examples/sam3.1_video_predictor_example.ipynb)
- [Upstream loaders](https://github.com/facebookresearch/sam3/blob/2345a4ad109ac29c569da749c91d84f10dc08c40/sam3/model/io_utils.py)
- [Image/video association thresholds](https://github.com/facebookresearch/sam3/blob/2345a4ad109ac29c569da749c91d84f10dc08c40/sam3/model/sam3_multiplex_base.py)
- [Related upstream checkpoint-loading discussion](https://github.com/facebookresearch/sam3/issues/526)

Meta describes 3.1 primarily as Object Multiplex tracking efficiency work, with
mixed text-prompt benchmark changes. It is not a promise of uniformly better
category recognition. The upstream issue is contextual evidence, not proof that
its reported failure occurs in our installed model.

## Recommendation

No evidence from these paired tests that the adapter uniquely causes the radio
acquisition misses. Do not silently lower video thresholds or mark image-mode
candidates as confirmed identities. Next test sparse acquisition/semantic
confirmation followed by persistent tracking, with identity-loss and distractor
checks. Use explicit file preprocessing in that diagnostic to remove a needless
input-path difference. Qualify on retained traces before deploying to live runs.
