# Local Perception Latency and Cloud API

## Decision

Keep SAM 3.1 local for the next tracking experiment. The earlier 0.49-0.55 s
capacity measurement covered three independent text prompts, not one tracking
update. The corrected arrived-frame replay measured 167 ms; the corrected live
moving shadow measured 252 ms tracking and 483 ms observation-to-result median.
An earlier incremental adapter had a one-frame indexing bug and its mask-freshness
results are superseded. No measurement proves a 300 ms capture-to-geometry pipeline.

Meta's [SAM overview](https://dev.meta.ai/docs/sam/overview) and
[prompt API](https://dev.meta.ai/docs/sam/segmenting) document `sam-3.1` through
`https://api.meta.ai/v1/responses`. The API accepts one text concept per request
and an image or a video clip. It streams output results for the supplied media;
the reviewed documentation does not establish a persistent incremental camera
input session, a serving region, or a 300 ms round-trip guarantee. Visual
point/box prompts supported locally are not inputs to this API.

Cloud may help occasional detection or offline processing, but upload time,
network RTT, queueing and output decoding must be included. Changing Vast regions
adds uncertainty. Measure from the actual GPU host, using p50/p95 and time to a
complete usable mask, not first response byte. No cloud calls or sensor uploads
were made for this assessment.

## CPU Evidence Microbenchmark

On the current GPU host's CPU, four retained native three-camera RGB-D captures
(actions 0, 384, 512, 768), five repetitions per PNG setting, fresh temporary
stores. All decoded RGB and depth values were checked against source pixels.
GPU models and simulator were not running. These are retained-array ingress
timings, excluding native rendering, device transfer and live scheduling.

| PNG level | Ingress median | PNG delivery median | RGB bytes, median |
| --- | --- | --- | --- |
| 6, existing default | 394.9 ms | 29.9 ms | 1,065,868 |
| 1, faster lossless | 117.1 ms | 32.6 ms | 1,212,605 |
| 0, uncompressed PNG | 62.6 ms | 20.0 ms | 2,940,425 |

Level 1 reduces ingress time by about 70% with about 14% larger RGB files in
this sample. Level 0 saves more CPU but substantially increases storage/bandwidth.
Use level 1 as the first live experiment candidate, without reducing resolution
or changing pixels. Do not add these separate microbenchmark timings to the old
tracking measurements and claim a measured end-to-end rate.

## Implemented Change

`EvidenceStore.png()` previously decoded and re-encoded existing PNGs. It now
checks the content hash, validates/decodes the image, and returns existing RGB PNG
bytes directly. The legacy helper took 415.3 ms median for the three level-6
images versus 29.9 ms now. This improvement applies to users of that helper;
array-based policy RPC does not use it, so do not assign that saving to policy
inference.

`EvidenceStore` also accepts an explicit `png_compress_level` (integer 0-9).
Default remains 6: existing encoding behavior is preserved until an experiment
opts into level 1. Compression changes encoded hashes, not image pixels;
old evidence stays valid and is not rewritten. Path/hash checks, source stamps,
timestamps and depth serialization remain intact. Eleven new regression tests
cover losslessness, original-byte delivery, defaults and invalid inputs.

Private receipt: `evidence-encoding-profile-20260922-r1.json`.
Full public suite: 1,091 passing tests; Ruff passes.

## Live Encoding Follow-Up

The three-cycle live level-1 test passed: capture 178-212 ms, warm three-prompt
result age 792-831 ms, versus prior capture 404-448 ms and result age 1.001-1.050 s.
This is no-motion single-frame detection, not incremental tracking. GPU peak was
23,482 MiB, close to the 23,552 MiB abort threshold. See the
[incremental qualification report](SAM31_INCREMENTAL_SHADOW_20260922.md) for
the live split timings, causal replay failures and mask-quality caveats.

## Moving Shadow Follow-Up

The corrected latest-only worker processed 25 captures during 768 frozen-policy
actions without queue drops; all raw-image reads were on the emitted current
frame. Warm result age p50/p95 was 483/540 ms; positive-mask depth partitioning
took 7 ms median. Results never entered policy inputs or authorized motion.
Captures were at 32-action boundaries, not continuously sampled video.

Keep the local model and return to geometry/temporal-quality qualification.
Encoding/decoding and observation cadence remain optimization candidates if
the next control experiment needs a faster path. The fixed 32-frame adapter
requires further long-stream/reset qualification. Do not trade source alignment
or archival integrity for a favorable timing number.
