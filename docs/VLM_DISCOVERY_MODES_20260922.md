# Discovery reasoning-mode smoke test

Follow-up to VLM_DISCOVERY_SMOKE_20260922.md, using the exact same three
720-square PNGs and label-blind inventory prompt. No simulator or GPU actions.
These are correlated development frames, not general recognition qualification.

## Endpoints and results

| Endpoint | Requested mode | Result | Seconds, frames 384/448/512 |
| --- | --- | --- | --- |
| z-ai/glm-5.3-flash, together | low | Three radio labels, but two seven-object packets and one coordinate-scale failure | 8.59 / 19.71 / 4.12 |
| qwen/qwen3-vl-30b-a3b-thinking, alibaba | low | First response violates output-token ceiling; lane stopped | 30.11 / not run / not run |
| qwen/qwen3-vl-30b-a3b-instruct, alibaba | Non-thinking checkpoint; no reasoning parameter | Two capped outputs and one malformed JSON output; 0/3 usable packets | 17.73 / 14.09 / 17.15 |
| xiaomi/mimo-v2.6-flash, xiaomi/fp8 | low | Three valid JSON/schema packets and useful target boxes; inconsistent semantic labels | 11.85 / 15.83 / 18.86 |
| xiaomi/mimo-v2.6-flash, xiaomi/fp8 | enabled=false | Three valid JSON/schema packets and useful target boxes; inconsistent semantic labels | 6.02 / 18.88 / 5.04 |

GLM's public catalog marks reasoning mandatory and lists low/high/max. No
instant/none trial was attempted. Qwen Thinking and Instruct are separate
checkpoints, not a clean within-checkpoint reasoning toggle. The provider
accepts reasoning parameters but its low behavior was not qualified: the
Thinking receipt reports 3818 completion tokens (3439 reasoning), exceeding
the requested 2048-token ceiling. Its saved raw response localizes an unknown
device, but is excluded from accepted transport results. No retry was made.
User subsequently requested stopping Qwen; all Qwen testing remains stopped.

MiMo low reports 113/585/576 reasoning tokens; disabled mode reports zero on
all three. Disabled calls had 576 cached input tokens each, whereas only one
low call had 128 cached tokens. Thus this tiny sequential comparison is not
a cache-controlled latency/cost measurement. Flash, not Pro, was selected for
the requested cheap discovery test and disclosed before dispatch.

## Important qualifications

GLM's third box is [373,380,431,425] in a requested 0..1000 convention. Applied
as returned it misses the radio entirely, although the numbers resemble native
720-pixel coordinates. No retrospective rescaling is accepted. The two earlier
target boxes overlap the model-derived SAM reference at 0.780/0.736 IoU, but
their seven-object packets violate the frozen six-object limit. This repeat
weakens the earlier impression that GLM localization was consistently reliable.

MiMo low target-box IoUs against SAM's model-derived mask bounding boxes are
0.823/0.804/0.736; disabled mode gives 0.917/0.934/0.932. These are internal
agreement figures, not ground-truth localization accuracy. Semantic defects
remain: low mode calls the first target possibly a bag/case; disabled mode
describes the second as possibly a toy/camera. Both sometimes copy the literal
placeholder `ordinary category or unknown` into label fields. Schema validity
does not mean a semantic claim is acceptable. Some foreground grippers are
also confidently described as VR controllers.

Recommendation: retain MiMo disabled as a candidate for sparse box proposals,
not accepted object identity. Use explicit coordinate/semantic validation and
SAM visual refinement. Neither cheap model is qualified for automatic memory
identity updates. Do not continue Qwen or add further model sweeps without
new direction. The three-frame test cannot establish general superiority.

## Records and budget

Private runs: `vlm-discovery-variants-20260922-r1` (GLM and stopped Thinking
lane) and `vlm-discovery-variants-20260922-r2` (unattempted Instruct and MiMo
lanes only). Exact requests, image hashes, endpoint metadata, receipts and
results retained. The second run audit verifies cross-model identical inputs,
response hashes, validation outcomes, and SAM reference artifact hashes; box
montage visually inspected. Five focused tests and Ruff pass.

13 new calls: 12 settled, one token-contract violation retains its full
$0.01789824 reservation. New confirmed spend $0.00505312680. Shared totals:
4096/4100 calls, $23.60634165640 confirmed, $34.944996222900 unresolved holds,
$58.551337879300 exposure under $75. All earlier holds unchanged. No active
inference requests remain.
