# SAM 3.1 acquisition score audit

## Result

The earlier empty-mask result is not evidence that SAM cannot propose the radio.
Pre-NMS inspection finds a top-ranked radio-shaped mask on all five full frames
and five corresponding crops, for all three tested prompts. These masks were
visually reviewed; precise boundary accuracy was not measured.

Using upstream file preprocessing and standard image-only admission, without
changing any threshold:

| Prompt | Full frames admitted | Crops admitted | Negative controls admitted |
| --- | --- | --- | --- |
| `a radio` | 2/5 | 3/5 | 0/3 |
| `radio` | 4/5 | 5/5 | 0/3 |
| `a red portable radio` | 5/5 | 3/5 | 0/3 |

The crop inputs at sequences 384, 448 and 512 are byte-identical to the three
positive crops sent to the prior blind GPT test. All three now produce admitted
SAM masks with `radio`. GPT performs open-category recognition while SAM receives
a category prompt and returns masks; these are still different tasks, not a
head-to-head general model ranking.

## Confidence versus absence

Top pre-NMS scores for `a radio` on full frames 384, 416, 448, 480 and 512:
0.376, 0.540, 0.449, 0.629, 0.484. Thus two pass image admission at 0.5 and none
pass video new-object admission at 0.65. The 384 proposal is also below the 0.4
detector cutoff. These are model scores, not calibrated correctness probabilities.

For `radio`, the same full-frame scores are 0.484, 0.675, 0.590, 0.746, 0.610.
For cropped inputs they are 0.750, 0.789, 0.668, 0.726, 0.793. Crop improvement
depends on the prompt: the longer descriptive prompt does worse on crops than
on full frames. Do not assume more adjectives or more cropping always helps.

The three manually chosen negative controls are television, brickwork and robot
gripper crops. Their largest score across all prompts is 0.0854 (rounded up).
These are easy controls, not a sufficiently hard look-alike distractor set.

## Method and verification

The private `diagnose_sam_scores.py` wraps `detector.forward_grounding` only to
copy the top ten scores, boxes and masks before upstream mutates logits for NMS.
It returns the original object untouched. Five normal `a radio` full-frame
output masks match the prior uninstrumented upstream test exactly.

Artifacts: private run `sam31-scores-20260922-r2`, 39 output NPZs, report,
independent audit, and three review sheets. All input and output SHA-256 hashes
were checked. Report hash:
`3d9945c61e65584dae6143e5a7b9f4e6af2c46f7194ab3dd11289c38a350d67b`.
The first launch failed at import before model execution; its log is preserved.

The rendered sheets intentionally show raw top proposals, including rejected
ones. A green overlay on those sheets does not mean the normal predictor admitted
the mask. Admission counts above come from unchanged predictor outputs.

No simulator actions, paid GPT calls, threshold changes or production-default
changes were made. Focused tests: 25 passed; both score-audit scripts pass Ruff.

## Next action

Keep SAM 3.1. Test the simple category prompt `radio` with explicit upstream
preprocessing on different retained views before adopting a new acquisition
configuration. The descriptive prompt is a development ablation, not permission
to supply an unseen object's color to an online benchmark agent. Preserve sparse
acquisition followed by tracking; separately qualify loss/reacquisition and
same-class distractors. Do not lower global thresholds based on this small set.

This supersedes any interpretation of the earlier crop experiment as a general
SAM-versus-GPT capability gap. That experiment used the streaming/video path;
the acquisition mode, preprocessing and prompt must accompany its result.
