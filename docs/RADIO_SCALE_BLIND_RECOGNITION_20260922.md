# Radio Scale and Label-Blind Recognition

Date: 2026-09-22. Follow-up to the
[live acquisition miss](LIVE_SURFACE_FUSION_20260922.md). Development diagnostics
only; no new simulator or policy actions and no new motion authority.

## Question and Correction

The earlier red-object versus radio prompt comparison cannot establish that
semantic matching, rather than image detail, is the primary problem. Color
recognition requires less detail. The assistant also knew the target label while
inspecting images; that observation was not a blind model comparison.

The native images are 720x720. The five broad-candidate bounding boxes range from
50x44 to 84x68 pixels. Upsampling cannot add missing sensor information.

## Fixed Crop Test

On the exact missed frames 384, 416, 448, 480 and 512, compare fresh SAM states
using `a radio`, unchanged weights/settings, and three inputs:

- Full native image.
- Square crop with side twice the broad red-object candidate's largest dimension.
- Square crop with side four times that dimension.

Crop boxes shift at image boundaries to stay square; no aspect distortion.
All inputs are bilinearly resized to 720x720 for the unchanged adapter, which
then uses its normal 1008x1008 encoder preparation. Candidate selection uses
only the same image's previous broad-prompt output, not simulator labels/poses.
This changes apparent scale and context together, not native sensor resolution.

| Condition | Frames with radio output |
| --- | --- |
| Full | 0/5 |
| 2x candidate crop | 0/5 |
| 4x candidate crop | 0/5 |

All 15 inputs reproduce exactly from source pixels and the fixed crop rule.
Input/output hashes and current-frame reads pass; inverse mask mapping reproduces.
These results show that this magnification/context intervention did not repair
the misses. They do not isolate missing detail, unfamiliar asset appearance,
text matching, or model representation as the cause. No thresholds were tuned.

Private run: `sam31-scale-diagnostic-20260922-r1`. Source SHA-256:
`4d2155d4ef71523744a4b74117b57bb59c9e348990160a379054fa1f9f13f8d0`.

## Label-Blind GPT Check

Six independent GPT-6 Astra medium Flex API requests, each with one current crop
and the same generic instruction to name the centered object or say uncertain.
No task name, target category, candidate prompt, prior conversation, or expected
label was supplied. Image metadata used opaque content hashes. No category list
was provided. Expected labels and source lineage were stored separately.

Three positive inputs are the **exact PNG bytes** of SAM's 2x-crop cases at
384, 448 and 512. Three negative controls are manually chosen, square crops of
the television, brickwork, and gripper from retained native images. They are not
autonomous detector proposals or a held-out distractor benchmark.

| Case | Human-labeled content | GPT result | Stated certainty |
| --- | --- | --- | --- |
| a | Television | Wall-mounted television | Clear |
| b | Radio, frame 384 | Portable radio | Clear |
| c | Brickwork | Brick wall | Clear |
| d | Radio, frame 448 | Portable radio | Clear |
| e | Robot gripper | Handheld tool | Uncertain |
| f | Radio, frame 512 | Portable radio | Clear |

This is three correct radio identifications, two correctly described controls,
and one abstention/uncertain description. It is not six exact category matches.
No control was called a radio. The gripper answer does not identify the gripper.

All six submitted request-body hashes reproduce from the frozen inputs. An audit
checks two-message independent requests and absence of expected category names
or proposal wording in instructions and textual metadata. Each request completed
and settled. Total actual cost: **$0.044065**. Recorded transport times: 3.42-8.25 s.
This is not whole-pipeline latency. No automatic retries or provider fallback.

An initial local packaging attempt failed the content-addressed image URI check
before any reservation or provider request. Corrected the URI, retained the gate,
added a regression test, and ran the six-call experiment in a new output directory.

Private inputs: `blind-object-inputs-20260922-r1`.
Completed run: `blind-object-gpt-20260922-r2`, including `blindness-audit.json`.
Shared ledger after settlement: 4,068/4,100 calls, $23.52892682960 confirmed,
$34.927097982900 unresolved holds unchanged, $58.456024812500 total exposure
under the existing $75 ceiling.

## Interpretation and Next Gate

GPT identified the object from the same cropped pixels without conversational
label priming, while text-prompted SAM emitted no mask for those inputs. That is
useful evidence for complementary roles on these examples, not a general model
ranking: the tasks, model interfaces and output requirements differ. Training
familiarity with the asset is unknown. Three correlated views of one object do
not establish recognition robustness, calibration, or generalization.

Next test same-frame candidate plus semantic-label binding using the existing
identity/evidence contracts. Preserve unknown/abstain outcomes and separate
candidate discovery from confirmation. Before positive live qualification,
include look-alike distractors and measure acquisition latency; no broad red
candidate may automatically become the radio or a grasp target. The deployed
SAM prompt and all motion gates remain unchanged.

## Validation

Twenty focused tests pass across crop/remapping, arrived-frame access, default
prompt preservation, label-blind context construction and content-addressed
image packaging. New scripts pass Ruff. Public runtime code is unchanged.
Scale outputs are backed up locally with content checks; GPT inputs, responses,
audits and durable budget records are local. No new robot rollout was run.
