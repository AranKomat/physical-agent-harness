# Perception Options After Removing GrabCut

Checked current upstream documentation on 2026-09-22. This is a practical
shortlist, not an exhaustive leaderboard or measured comparison on our host.

## Immediate Change

GrabCut implementation and calls have been removed. The live grounding worker
now produces Grounding DINO boxes/scores only. SAM 2.1 Large remains the mask
producer in the private shadow worker, followed by measured depth partitions.
No replacement model has been installed in this change.

Robot FK/proprio convention validation remains. The old mask-median near-hand
filter no longer runs, because its GrabCut-derived point no longer exists.
Candidates explicitly have unverified identity and unqualified geometry.
Detector-only identity is distinct from the legacy segmented-geometry contract;
old exploratory-motion consumers reject it instead of silently bypassing their
requirements. A SAM part/patch association must be qualified before geometry
is used for control. Historical reports and saved masks are not rewritten.

The earlier 758 ms median grounding time with radio candidates included the
now-removed GrabCut work and associated target processing. The earlier no-radio
median was 161 ms. These suggest a useful reduction, but are not measurements
of the new implementation. No long simulator rollout was launched for removal.

## Shortlist

### YOLOE-26: First Speed-Oriented Candidate

[Current Ultralytics documentation](https://docs.ultralytics.com/models/yoloe/)
provides released text/visual-prompt detection and instance-segmentation models.
They could replace both Grounding DINO and the separate mask model. For this
project, test `yoloe-26l-seg.pt` rather than defaulting to a tiny model; M is an
alternative if necessary. The docs distinguish the detection-paper parameter
count from the released L segmentation checkpoint: 35.4M parameters, 142 GFLOPs.
Neither number is our end-to-end latency or memory consumption.

Text embeddings can be prepared once for a fixed prompt set. Exported models
bake in their classes; changing class sets requires re-export. Preserve the
original PyTorch path if dynamic vocabulary is important. The first text prompt
also downloads a roughly 254 MB encoder and a tokenizer dependency, so prepare
these before timing and pin them. Ultralytics uses AGPL-3.0; deployment licensing
needs review before incorporating it into a third-party product.

[Original YOLOE](https://github.com/THU-MIG/yoloe) reports high throughput using
TensorRT on T4, but those older models/hardware/backend figures must not be
presented as measurements for YOLOE-26 on our shared 4090. No verified local
latency or radio-identity result exists yet.

### SAM 3 / 3.1: Unified Semantic Segmentation and Tracking Candidate

[Official repository](https://github.com/facebookresearch/sam3) supports direct
text-prompted detection, segmentation and tracking. This is potentially a
replacement for Grounding DINO **and** SAM 2, not just a faster mask decoder.
The repository describes SAM 3 as 848M parameters, requires Python 3.12+,
PyTorch 2.7+ and CUDA 12.6+, and uses a custom SAM license with gated weights.
Use an isolated environment; do not modify the existing policy environment.

[SAM 3.1 release notes](https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md)
date its Object Multiplex release to March 27, 2026. Its advertised roughly 7x
speedup is at 128 tracked objects on an H100, relative to the original SAM 3
release. It is not a SAM 2.1 comparison and does not establish single-object
image latency or co-residency on our 4090. Video benchmarks have mixed changes.
Tracking must remain causal; do not use future frames from a saved video when
evaluating an online agent.

### Current Grounding DINO + SAM 2.1 Large

Already installed and exercised on native frames. Keep this as the immediate
GrabCut-free path while testing one replacement, not as a reason to preserve
duplicate segmentation. SAM plus depth partitioning measured 105 ms median
worker time in the previous moving run. It does not remove the need to fix
synchronous evidence I/O and capture scheduling.

## Decision

Update: the user selected SAM 3 for the first test instead. It is now installed
in an isolated environment and tested on retained frames. See
[the measured results](SAM3_RETAINED_TEST_20260922.md). The shortlist below
records the original recommendation, not the current installation status.

First candidate for a short retained-frame check: YOLOE-26 L, with direct
text-prompted masks. Compare the same images for radio recall, gripper/fireplace
confusion, thin parts/handle openings, warm latency and memory. Keep SAM 3/3.1
as the alternative if the fast candidate's semantic quality is inadequate.
Neither candidate is established as universally best or installed here.
