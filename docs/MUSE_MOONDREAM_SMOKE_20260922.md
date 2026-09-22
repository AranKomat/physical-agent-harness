# Muse Glimmer and Moondream 3 preview smoke tests

Same three retained 720-square development frames (384/448/512) as the earlier
discovery comparisons. These are correlated views of one scene. No simulator
actions, policy changes, or production perception changes occurred.

## Muse Glimmer

Endpoint `meta/muse-glimmer-30b`, pinned provider `deepinfra/bf16`, requested low
reasoning effort, 2048 output-token ceiling, identical label-blind messages and
PNG bytes to the earlier OpenRouter comparison. Three independent requests.

- Latency: 11.23 / 9.91 / 11.39 seconds.
- All three packets pass the syntactic schema, but every label repeats the
  literal example placeholder `ordinary category or unknown`.
- Target descriptions are `red retro boombox`, `red and white retro radio`,
  and `red and white retro radio` respectively. Thus semantic evidence is
  present in attributes, despite unusable category fields.
- Target box IoU against the retained model-derived SAM mask bounding box:
  0.211 / 0.387 / 0.498. Localization is relatively loose/misaligned.
- Reasoning tokens: 211 / 142 / 215. Total cost $0.00212760.

Private run `muse-discovery-20260922-r1` retains exact requests, responses,
preflight, report, box montage and audit. Audit verifies matched messages,
image/response hashes, parsing and SAM reference hashes. No automatic retries.
Shared budget now 4099/4100 calls, $23.60846925640 confirmed,
$34.944996222900 unresolved holds unchanged, $58.553465479300 exposure under
$75. Only one call remains under the current count ceiling.

## Moondream 3 Preview

Checkpoint `moondream/moondream3-preview`, revision
`5112966d1a723413b1c9a1e8bea272b72e647b35`. Downloaded only the indexed
`modelv2-*.safetensors` BF16 shards (about 18.5 GB) and pinned custom code/config.
Research is permitted by its BSL 1.1 Additional Use Grant; some competing
paid hosted/embedded offerings require a separate agreement. No redistribution
or deployment license conclusion is made here.

Standalone RTX 4090, torch 2.10.0+cu130, transformers 5.13.0. The pinned custom
loader was inspected; no adapters/cloud inference used. Image hashes checked.
The tokenizer is loaded by upstream from `moondream/starmie-v1`; its serialized
SHA256 was recorded as
`af29cb8afc240a4abcfdf1d0aed6e2f13246fc6565de424807f93fa934dfeb5a`.
Loader reports zero missing, unexpected, mismatched keys or errors. A first
attempt stopped before inference because the diagnostic logger could not
serialize loader metadata sets; the logger was fixed and the original log kept.

Compiled the actual inner `model.compile()` routine after cache setup: the
pinned HF wrapper otherwise inherits generic module compilation. No model
source edits or quantization. Query reasoning disabled; native detection uses
its own deterministic coordinate decoder. Encoding is cached per image using
the documented API. Upstream clones the image-prefix caches and restores them
for each detection, rather than carrying a prior question as conversation.

### Outputs

| Test | Result |
| --- | --- |
| Original JSON discovery prompt | 0/3 valid packets: boxes omitted; third also returns seven objects |
| Discovery category text | First calls it a boombox; next two call it a camera |
| Plain-language VQA | First red/silver device; next two red camera |
| Native `detect("radio")` | Target localized in 3/3 |
| Native `detect("a portable radio")` | Target localized in 3/3 |
| Native `detect("blue radio")` | Incorrectly returns the red target in 3/3 |

Native radio boxes are finite, in the documented 0..1 range, and have positive
area. IoU with model-derived SAM reference boxes: 0.901 / 0.824 / 0.815. These
are agreement checks, NOT independent localization ground truth. Wrong-color
queries return nearly the same object; native detections cannot establish that
all target attributes match. No multi-instance/video association is qualified.

### Timing and memory

- Weight load 7.91 seconds; compile/warmup 135.98 seconds.
- First actual image encoding 30.19 seconds, then 0.488 / 0.478 seconds.
- First native detection 8.07 seconds; subsequent detections 0.234-0.289 seconds
  excluding image encoding. Cold first-use overhead remains despite warmup.
- Warm image encoding plus one detection is roughly 0.72-0.75 seconds here.
- Plain descriptions 0.68-0.88 seconds excluding encoding.
- JSON discovery 10.46 seconds initially, then 1.90 / 2.06 seconds, despite
  failing the requested schema.
- Peak allocated tensor memory about 18688 MiB; reserved about 18976 MiB.
  Standalone fit is not proof of simulator/SAM/policy co-residency.

Private run `moondream3-20260922-r1` retains all 15 completed outputs and setup/
run logs. Runners pass Ruff. Local validation checks all detection coordinates
and confirms the original instruction matches the prior comparison. No paid
model API calls were made for Moondream. Processes exited after the tests.

## Interpretation

Muse supplies useful semantic descriptions but weak boxes in this test.
Moondream supplies fast native box proposals after warmup but fails the color
constraint and makes category mistakes. Neither is ready to establish object
identity automatically. Keep discovery hypotheses, geometry proposals, and
identity evidence separate.

The original JSON prompt's example placeholders are a confound: several models
copy or literally interpret them. These results evaluate that specific prompt
and endpoint configuration, not intrinsic model capability rankings. Any next
fair comparison should predeclare a clearer common instruction without literal
placeholder values, enforce a schema where supported, and include new objects
and distractors. Do not silently repair or rescore these saved outputs.
