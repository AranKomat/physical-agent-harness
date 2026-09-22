# Local Perception Latency and Cloud API

## Decision

Keep SAM 3.1 local for the next tracking experiment. The earlier 0.49-0.55 s
capacity measurement covered three independent text prompts, not one tracking
update. Isolated single-radio tracking yielded frames at a 142 ms median.
Neither measurement proves a 300 ms capture-to-geometry pipeline.

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

## Next Measurement

Run the live shadow experiment with explicit level-1 evidence encoding and
incrementally available tracking inputs. Measure native capture, evidence ingest,
tracking, depth association, queue age and output delivery separately. Keep
archival work off the control-critical path where it can be bounded safely.
Only consider replacing the model if the measured local tracking/depth stage
still prevents the target after eliminating unnecessary serialization/detection.
