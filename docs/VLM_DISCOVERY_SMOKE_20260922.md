# Label-blind discovery smoke comparison

Nine independent OpenRouter calls on three identical retained 720x720 full
frames (384, 448, 512), with no radio label, task, prior conversation, or
expected answer supplied. All models received exactly the same messages and
PNG bytes. Requested output: up to six objects, visible attributes, uncertainty,
and normalized bounding boxes. These are correlated views of one development
scene, not a distance benchmark or held-out accuracy evaluation.

## Results

| Model / pinned provider | Radio category | Location | Strict packet validity | Latency per call | Total three-call cost |
| --- | --- | --- | --- | --- | --- |
| Qwen3.8 27B / deepinfra/bf16 | 1 radio, 1 confident camera error, 1 unusable response | Good target boxes in first two | 2/3 | 23.53, 26.33, 57.60 s | $0.00475815 |
| GLM 5.3 Flash / together | Radio in all three raw responses | Good target boxes in all three | 2/3: third lists seven objects | 4.81, 3.53, 4.94 s | $0.00070855 |
| GPT-6 Astra / openai/flex | 2 radio, 1 unknown/uncertain | Good target boxes in all three | 3/3 | 6.35, 7.08, 7.49 s | $0.02748000 |

The Qwen third response is literally `{"": ""}` with finish reason `stop`;
it is rejected, not repaired. GLM's seven-object output is likewise rejected
under the frozen six-object limit. Its entries are inspected separately for
qualitative analysis, not silently treated as a valid runtime packet.
All calls requested low reasoning effort and a 2048-token output ceiling;
this does not imply equivalent internal reasoning across vendors. Qwen's
third receipt reports 1066 reasoning tokens and only seven other output tokens.
GLM's Together endpoint reports unspecified quantization. Latency includes
provider/network effects and is not an intrinsic model-speed comparison.

## SAM comparison and localization

Reuse audited SAM 3.1 image-mode results on exactly these PNGs, unchanged
thresholds. Admissions on frames 384, 448, 512 respectively:

- `a radio`: no, no, no.
- `radio`: no, yes, yes.
- `red radio`: yes, yes, yes.
- `a portable radio`: no, no, no.

This is prompted segmentation versus label-blind discovery, not equal tasks.
SAM was given the target description; VLMs were not. No broad SAM inventory
experiment was run. Prior roughly subsecond SAM timings concern local image
inference, not equivalent scene-description output.

For an internal localization cross-check, compare proposed boxes with bounding
boxes of retained `red radio` masks. IoUs: Qwen 0.928/0.814/no box;
GLM 0.825/0.794/0.820; GPT 0.890/0.895/0.869. These masks are model-derived,
NOT independent ground truth. Visual inspection supports approximate target
localization, not collision, depth, grasp, or absolute coordinate qualification.
Qwen's camera error is especially useful evidence: a good box does not establish
correct semantic identity. Some inventories group the two grippers into one
box, so distinct-instance handling is not qualified either.

## Decision

GLM is the leading cheap discovery candidate from this small test, not a
qualified replacement or a demonstrated stronger model than GPT. GPT's last
answer illustrates useful uncertain-candidate retention. Keep SAM for visual
refinement/tracking and depth for geometry; do not require semantic recognition
every frame. Next test: validated GLM boxes initializing SAM on retained causal
frames, preserving ambiguous identity and the original action gates. Strict
schema enforcement and multiple similar objects remain untested follow-ups.

## Reproducibility and limits

Private run `vlm-discovery-comparison-20260922-r1` retains preflight endpoint
metadata, exact requests, provider responses, parsed report, audit, and a
three-model/three-frame box montage. Audit checks request hashes, identical
messages and image hashes across models, parsed output consistency, and SAM
input/artifact hashes. Private runner, analyzer, and focused validation tests
are outside the public repo; no secrets or native images are published here.

Nine calls settled for $0.03294670. Shared ledger: 4083/4100 calls,
$23.60128852960 confirmed, $34.927097982900 unresolved holds unchanged,
$58.528386512500 exposure under the $75 ceiling. No retries, simulator actions,
GPU runs, policy changes, or production perception changes occurred.
