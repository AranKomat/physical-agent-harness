# VLX-Seek 1.5-10B retained-image smoke test

## Setup

Public source: https://github.com/om-ai-lab/VLX-Seek
at `01187078e02c7fba7d0eb87af930ee9aec3af12c`.
Main weights: `omlab/VLX-Seek-1.5-10B`, revision
`6d1925f932ee6f0a8790b15420f403ee8f8e8f6a`, Apache-2.0.
Proposal weights: `fushh7/WeDetect`, revision
`3b9d0670cbf300d0b48f900ae87a6c4785d88939`, GPL-3.0.
The authors' internal OPN is not public. This tests the released WeDetect-based
pipeline, not necessarily the system used for published benchmark numbers.

Standalone RTX 4090, simulator and other models unloaded. Isolated environment:
Python 3.12, torch 2.10.0+cu130, torchvision 0.25.0, transformers 5.13.0,
FlashAttention 2.8.3, timm 1.0.9, einops 0.6.1, accelerate 1.4.0.
Optional flash-linear-attention/causal-conv1d kernels were not installed;
upstream explicitly reports its slower PyTorch linear-attention fallback.
No source architecture edits, quantization, training, or API calls.

Same retained full PNGs at sequences 384/448/512 as the prior comparison,
hash checked. These are three correlated views of one development scene,
not a general discovery, distance, or held-out benchmark.

## Results

| Test | Frame 384 | Frame 448 | Frame 512 |
| --- | --- | --- | --- |
| Earlier blind JSON inventory instruction | Literal placeholder response; no inventory | Same failure | Same failure |
| Native combined query: radio; red radio; blue radio | Radio/red found, blue rejected | All rejected | Radio/red found, blue rejected |
| Native single query: radio | Correct candidate | Correct candidate | Correct candidate |
| Native single query: a portable radio | Correct candidate | Correct candidate | Correct candidate |
| Plain-language scene description | Mislabels target as camera | Red and white object | Red and white object |

The matched instruction text is preserved, but VLX uses its required native
user-only image/chat wrapper rather than the OpenRouter system/user wrapper.
It interpreted the example label `ordinary category or unknown` literally.
That is an interface-following failure, not proof that it cannot see objects.
The separate plain-language follow-up describes the scene, but does not
independently identify the radio correctly. It is not a matched-prompt win.

Native region grounding is more promising: single-query `radio` and
`a portable radio` each locate the target in 3/3 views. The miss under the
combined query remains evidence of query sensitivity. No claim of universal
prompt robustness or calibrated identity confidence is supported.

## Proposals, loading, and timing

WeDetect produced 100 proposals per image. Best candidate bounding-box IoUs
against the retained SAM radio-mask bounding box: 0.917/0.867/0.885.
This is agreement with a model-derived reference, NOT independent ground truth.
The selected single-query regions visually correspond to those target boxes.
Thus the combined-query middle-frame miss is not explained by absent proposals.

Proposal checkpoint loading reported zero missing keys and four unexpected
keys (`backbone.norm.weight/bias`, `backbone.head.weight/bias`) under the
upstream loader. These are recorded, not silently omitted from the audit.
The main checkpoint loaded without a missing-weight warning; a full per-tensor
checkpoint equality audit was not performed.

Timing (seconds, 384/448/512):

- Proposal generation including detector reconstruction/loading: 2.74/1.68/1.49.
- Combined native query, proposals already available: 1.55/1.50/1.50.
- Single `radio` query: 0.763/0.708/0.666.
- Single `a portable radio` query: 0.834/0.824/0.782.
- Plain-language VQA: 4.19/3.50/2.81.

VLX model loading took 13.8 seconds in the first run. Peak allocated tensor
memory was about 19536 MiB; peak allocator reservation 19990 MiB. This fits
standalone but does not establish coexistence with SAM, policy, and simulation.
Do not quote subsecond grounding as end-to-end discovery latency: proposal
generation and any separate category discovery are additional. Proposal timings
are not a persistent-worker benchmark. Native generation used greedy decoding,
512 tokens maximum; the initial inventory allowed 2048.

## Recommendation and records

Keep this as a candidate for region-based grounding: it avoids the generated
coordinate-scale errors seen in GLM and runs useful short queries locally.
It is not yet a replacement for general semantic discovery or video tracking.
Before integration, test nearby distractors, genuinely absent categories,
unseen objects, and acquisition-to-SAM tracking, not more tuning on this radio.
No action authorization or production behavior was changed.

Private artifacts: `internal/physical-ai-lab/runs/vlx-seek-20260922-r1/`,
including setup log, first result/log, and separate follow-up result/log.
Both runs completed (six initial and nine follow-up inferences). The isolated
runtime and weights remain on the GPU host for reuse. Inference processes exited;
instance remains running as requested. Qwen endpoint testing was not resumed.
