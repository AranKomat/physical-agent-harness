# Live Surface Fusion and Retained Multi-View Check

Date: 2026-09-22. Follow-up to the passing cached
[live pose timing experiment](LIVE_POSE_SHADOW_20260922.md).

## Protocol

Add a CPU-only shadow consumer to the existing frozen Behavior-Skill/SAM 3.1
experiment. It waits for both pose and archived mask results for the five common
boundaries at actions 384, 416, 448, 480 and 512. Match episode/frame stamps,
observation time, exact RGB/depth IDs and content-addressed mask artifacts.
Preserve every valid masked depth pixel in separate connected surface patches.
Record actual consumer start/completion, not only the upstream availability time.

Outputs do not enter policy inputs, executive context, world-state authority, or
the actuator path. Unknown/stale joins remain unknown. The existing two-second
freshness bound and pose/registration checks are unchanged. The owner includes
the new process in startup, timeout, failure, memory monitoring and cleanup.

No GPU model changes, GPT calls, new classical actions, extra policy actions,
or relaxed clearance gates are introduced. This is not a contact-success test.

## Retained Surface Evidence

The first analysis uses the five views from
`sam31-live-pose-cache-20260922-r1`, not the new live consumer run.
All same-frame joins reproduce. The largest connected depth patch contains
80.0-82.0% of valid masked pixels. Its 5th-95th percentile spans are approximately
0.16 x 0.18 x 0.21 m, versus roughly 0.40 x 0.20 x 0.50 m for the whole mask.
The other patches are retained, not discarded or asserted to be background.

Visual review shows the dominant patch over the radio body; smaller patches
include handle/edge regions and separated depth. A whole-mask center/extent
would collapse these distinct surfaces and is not used as a grasp target.

Using saved camera poses without any additional ICP/alignment, adjacent dominant
patches have the following bidirectional nearest-point distances:

| Boundaries | Median | p95 |
| --- | --- | --- |
| 384 -> 416 | 3.58 mm | 5.78 mm |
| 416 -> 448 | 3.12 mm | 6.03 mm |
| 448 -> 480 | 2.49 mm | 4.39 mm |
| 480 -> 512 | 1.25 mm | 5.01 mm |

This is internal consistency on correlated views, not millimeter accuracy.
Largest-per-frame patch selection is an analysis heuristic, not persistent part
identity. Shared drift, camera/depth bias, incomplete surfaces and viewpoint
changes are not independently measured. No semantic button, grasp, clearance,
base localization or stopping qualification follows.

Private artifacts: `surface-multiview-20260922-r1/report.json` and
`surface-review.png`. The fixed source receipt is
`2078fdc61b310fc749ba98b464abf24bad1e8aa2ab20cf68ed516c701e2189ae`.

## Live Result: Empty Target Evidence

`sam31-live-fusion-20260922-r1` completed 768 frozen-policy actions with zero GPT
calls and zero classical actions. The cached pose updater again delivered 33/33
fresh estimates (median/max age 1.129/1.512 s). All five consumer joins were
fresh and ready during the episode, with median/max age 1.175/1.296 s. Consumer
CPU work was 60 ms median, 81 ms maximum. All reconstructed outputs reproduce.

**However, all five live joins had empty target lists.** SAM acquired its first
radio track only at action 704, after the fixed 384-512 pose window. The camera
review shows a visible radio during that earlier window. This is an acquisition
miss/delay, not simply absence of a target from the camera view. It must not be
counted as positive live target-surface qualification, even though the pipeline's
lineage and timing checks pass. The auditor now counts target-bearing and empty
boundaries separately; a fresh empty join is covered by a regression test.

SAM processed 25/25 boundary observations with 50/50 current-frame reads.
Warm tracking median was 241 ms and mask/depth age median/p95 was 484/544 ms.
Only frames 704, 736 and 768 had tracks. Peak sampled GPU use was 23,064 MiB.
Policy runtime was 217.96 s. The owner reaped all workers.

Native source SHA-256:
`4d2155d4ef71523744a4b74117b57bb59c9e348990160a379054fa1f9f13f8d0`.
Fusion receipt SHA-256:
`cf72f295c25d4bfe9bc3acb95d81b526554e0740a702f003f3242dfc258a9fb1`.

Do not move the capture window merely to report a success. Diagnose fresh
detection versus streaming acquisition on these exact saved images before
another native trial. The successful retained multi-view result above belongs
to the earlier source and does not fill this live evidence gap.

## Acquisition Diagnosis

A subsequent SAM-only replay of all 25 exact source frames reproduced the live
positive set exactly: 704, 736, 768. Fresh-state detection on each of the five
missed dense-window frames with the default `a radio` also yielded zero tracks.
Thus resetting streaming history or removing simulator CPU/GPU contention did
not repair these misses. Thirty saved outputs passed artifact hashes and
current-frame raw-read checks. No simulator, policy actions or paid GPT calls.

A bounded, fresh-state prompt probe used three fixed prompts on the same five
images, without changing weights or thresholds:

| Prompt | Frames with candidates |
| --- | --- |
| `a radio` (preceding fresh baseline) | 0/5 |
| `radio` | 1/5 |
| `a red portable radio` | 2/5 |
| `a red object` | 5/5 |

The broad red-object output is **candidate evidence, not radio identification**.
Color recognition needs less detail than category recognition. This comparison
does not isolate a semantic-matching defect from small target size, unfamiliar
asset appearance, or their interaction. Candidate boxes span only 50x44 to
84x68 pixels in the native 720x720 images. The assistant's visual inspection was
primed by knowing the task/target; it is not a blind GPT-versus-SAM comparison.
Visual review places these candidates on the radio in the five retained images,
but mask coverage varies and no distractor/negative-control qualification follows.
This diagnostic was chosen after viewing the misses; it is development evidence,
not an unbiased semantic benchmark. The deployed default remains `a radio`.
An optional bounded prompt parameter is available for isolated probes, with
tests preserving the default and rejecting empty/oversized prompts.

Next evaluate a current-image candidate plus separate semantic confirmation,
including distractors and negative controls. Do not relabel every red candidate
as the radio, borrow target locations from another episode, or perform another
full robot rollout merely to hope the category prompt succeeds.

## Validation

Seventy-nine focused private tests pass, covering queue/receipt contracts, same-frame
joins, surface support conservation, consumer unknown results, timing validation,
and launcher isolation. This count includes existing tests and is not additional
robotics replication. New scripts pass Ruff. Public runtime remains unchanged.

The completed native run is backed up locally and passed checksum rsync before
regenerating the local fusion audit with explicit empty/positive counts. Both
SAM-only diagnostic outputs are local; all 45 saved output artifacts passed
hash/current-frame-access checks. GPU workers exited; the instance remains running.

The live run qualifies timely empty-evidence handling only. Positive live target
geometry, persistent part identity and independent accuracy remain unqualified.
