# SAM attribute and paraphrase robustness

## Fixed-input experiment

Nine predeclared prompts on five full native images, their five fixed crops,
and three negative-control crops. All use upstream file preprocessing and
unchanged image-mode thresholds. No image editing, simulator action, GPT call,
or production deployment occurred. This tests one correlated red-radio asset,
not multiple objects or same-class target selection.

| Prompt | Full frames admitted | Crops admitted |
| --- | --- | --- |
| `a radio` | 2/5 | 3/5 |
| `radio` | 4/5 | 5/5 |
| `portable radio` | 2/5 | 3/5 |
| `a portable radio` | 0/5 | 0/5 |
| `red radio` | 5/5 | 5/5 |
| `a red radio` | 5/5 | 5/5 |
| `a red portable radio` | 5/5 | 3/5 |
| `blue radio` | 0/5 | 0/5 |
| `yellow radio` | 0/5 | 0/5 |

Every admitted positive overlaps the previously inspected radio proposal by
IoU > 0.5. That is a localization cross-check against a model-derived reference,
not independent ground-truth segmentation accuracy. All three control crops
(television, brickwork, gripper) are rejected by all nine prompts: 0/27 admissions.

Wrong-color descriptions reject the red radio in all 20 positive-image/prompt
combinations. Therefore this example does not support claiming that SAM ignores
color. However, equivalent-looking noun phrases have large confidence differences:
`a portable radio` misses all ten while `a red radio` finds all ten. The cause
inside the text/vision model remains unresolved; preprocessing is held fixed.

## Reproducibility

Private run `sam31-attributes-20260922-r1` contains 117 NPZ outputs and the report.
An independent audit checks all input/output hashes and unique case/prompt pairs.
All 39 repeated baseline outputs exactly match the prior uninstrumented-output
values stored by the raw-score diagnostic. `audit.json` records per-case scores,
reference overlaps and group counts. Full local copy retained.

Both diagnostic/audit scripts pass Ruff. The 25 focused existing configuration,
crop and streaming tests pass; the completed 117-case run supplies integration
evidence, not a general prompt-robustness guarantee.

## Interpretation and next action

Do not replace a target description with its bare category and call the task
solved. Preserve user/executive constraints such as color, subtype, relation,
and identity. Discovery may use broader prompts, but a broad proposal cannot
authorize selection without checking the complete target specification.

Do not special-case this radio as always red: red was a known development-image
attribute here, not automatically legal advance knowledge for every benchmark.
Likewise do not delete `portable` merely because it reduced scores. The proper
next integration is bounded candidate generation with explicit full-description
verification or abstention. Attribute-preserving paraphrases can be evaluated,
but this set is too small to bless a universal prompt-rewriting rule.

The prepared category-only live experiment remains unlaunched. These results
support SAM's usefulness for masks and tracking while showing why its prompted
mask output is not sufficient on its own to establish task-level identity.
GPT paraphrase robustness has not been measured in a matched experiment.

## Tokenizer and precision follow-up

The BPE asset SHA-256 equals the official pinned upstream file:
`924691ac288e54409236115652ad4aa250f48203de50a9e4722a6ecd48d6804a`.
Actual token IDs (including start/end tokens) are:

- `radio`: 49406, 2638, 49407.
- `portable radio`: 49406, 11949, 2638, 49407.
- `a portable radio`: 49406, 320, 11949, 2638, 49407.
- `red radio`: 49406, 736, 2638, 49407.

Decoded content retains every word. All fit well within the configured 32-token
context; no truncation or unexpected padding occurs. Earlier exact comparisons
already established that every loaded learned parameter matches the checkpoint.

Private run `sam31-text-precision-20260922-r1` compares default inference with
FP32 text encoding (text autocast and text TF32 disabled), holding visual
inference and thresholds unchanged. Four prompts on sequence-448 full/cropped
images and the television negative control yield 12 paired cases, 24 outputs.
FP32 text output dtype was checked during actual inference. The visual backbone
has explicit BF16 fused operations, so this is not full-model FP32 validation.

All 12 admission decisions are unchanged. Maximum top-score change is about
0.0081. `a portable radio` still fails on both positive views. All 12 default
output masks exactly match the preceding attribute audit. Every input and output
hash was verified; report SHA-256:
`172908cc79b96a3d33e50fb6131e44affbab20419717bfefe706a617230bbc23`.
The diagnostic script passes Ruff. No weights, production configuration or
thresholds were changed, and no model API calls or simulator actions were made.

This weakens tokenizer corruption and text-precision explanations for these
failures. It does not prove the whole upstream implementation correct or establish
the internal cause of the prompt sensitivity. Stop expanding this audit without
new evidence; preserve the full-description verification requirement and test a
bounded candidate-plus-semantic-check path next. Wider object-category testing
remains open rather than being inferred from this one asset.
