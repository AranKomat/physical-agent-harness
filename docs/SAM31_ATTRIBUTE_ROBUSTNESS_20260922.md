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
