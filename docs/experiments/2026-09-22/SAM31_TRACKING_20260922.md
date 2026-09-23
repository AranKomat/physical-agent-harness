# SAM 3.1 Tracking Probe

Historical offline probe. See the [incremental qualification report](SAM31_INCREMENTAL_SHADOW_20260922.md)
for the corrected live shadow results and the adapter frame-index bug found
during integration. Whole-clip timing/ID retention is not a live tracking result.

## Decision

Use official SAM 3.1 as the next experimental tracking backend. Do not continue
segmentation-model search. This is a retained-frame qualification, not a live
pipeline replacement or authorization for classical motion.

The official gated checkpoint was downloaded using the user's authorized HF
credential, without storing that credential on the GPU host. Revision:
`daa63191845a41281374e725f4c9e51c7a824460`; file `sam3.1_multiplex.pt`,
3,502,755,717 bytes. Its SHA-256 matches HF metadata:

```text
0567debeec80ba4ac6369540c6c248025283cb3ff2b92827509e57e2b3541cb6
```

Source remains official SAM commit `2345a4ad109ac29c569da749c91d84f10dc08c40`
in the isolated SAM environment. FlashAttention 3 and compilation were disabled.
Every learned parameter name in the assembled model is present in the merged
checkpoint. Upstream emits intermediate-load warnings and missing generated RoPE
buffer warnings; these are not missing learned parameters in the final model.

## Protocol and Results

Fourteen retained head-camera views at actions 352 through 768, every 32 actions,
from the previous policy-only approach. One text prompt, `a radio`, at the first
frame, forward propagation only. Native RGB was converted to quality-100 JPEGs
for the upstream loader; derived hashes and native evidence identities retained.
This is a sparse-view replay, not continuous camera-rate video or an occlusion
benchmark. No simulator actions or GPT calls occurred.

| Configuration | Track IDs | Peak allocated / reserved | Propagation |
| --- | --- | --- | --- |
| Default multiplex | ID 0 in 14/14 frames | 14,895.7 / 18,890 MiB | 1.812 s total, buffered |
| Small-batch candidate | ID 0 in 14/14 frames | 6,170.9 / 6,564 MiB | 1.758 s total; 142 ms median yield |

Numbers are PyTorch allocator measurements, not whole-system NVML peaks.
Propagation excludes model load, initial prompting, source capture and output
serialization. Default yields are batched and their near-zero median is not
per-frame inference latency. Neither result measures simulator/policy co-residency.

Selected mask panels show the radio retained through actions 384 and 416, where
single-image SAM 3 missed it, and through the final approach. Same-ID outputs
alone do not prove correct association; selected views were visually inspected.
This does not qualify identity through long occlusion, distractor swaps or depth
surface/contact geometry.

## Integration Details

The first run failed because the upstream session wrapper passes
`offload_state_to_cpu` to a multiplex initializer that does not accept it.
The private probe adapter omits only the disabled option and rejects an enabled
request. No upstream source modification or silent state-offload fallback.
Two regression tests cover this behavior; the failed receipt is retained.

Default SAM 3.1 uses 15-frame hotstart buffering, 16-frame batching and future
confirmation of earlier masklets. Forward direction alone is therefore not a
causality guarantee. The small-batch candidate explicitly sets:

```text
hotstart_delay = 0
postprocess_batch_size = 1
use_batched_grounding = False
batched_grounding_batch_size = 1
masklet_confirmation_enable = False
masklet_confirmation_consecutive_det_thresh = 1
```

These settings remove the identified buffering/confirmation paths but change
the filtering behavior. Live causal qualification remains false: the offline
loader has the full clip. Test incrementally available frames and log evidence
cutoff plus result-availability time before using outputs in online decisions.

## Next Experiment

First check co-residency with simulator and frozen policy, without motion. Do
not assume the isolated 6 GiB allocation fits alongside the earlier full stack.
Then move shadow perception off the synchronous capture path and measure timing
with bounded queues. Keep simulator access on its owning thread; do not call
rendering/step concurrently. Policy inference also pauses the current loop, so
asynchronous segmentation alone does not resolve every observation gap.

Maintain an object's established label when evidence supports the same track;
mark lost or ambiguous association explicitly rather than relabeling a different
object. Re-observation can confirm identity, but does not retroactively inform
past decisions. Return to the target-directed short handoff comparison after
timing/localization/motion admission, not after another model search.

Private receipts: `sam31-retained-20260922-r1` (failed),
`sam31-retained-20260922-r2` (default), and
`sam31-retained-lowlatency-20260922-r1` (small-batch). Source media stays private.
