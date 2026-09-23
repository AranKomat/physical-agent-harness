# LocateAnything-3B: Inventory And Grounding Smoke Test

## Conclusion

LocateAnything is a fast phrase/category grounder, not a demonstrated replacement
for GLM's goal-blind semantic inventory. Its documented detection interface takes
category descriptions. Generic or inventory-style prompts returned coarse labels,
echoes, and fragments rather than a useful list of ordinary object identities.

Native radio localization was accurate on two of three full-object views, but
selected a table-sized region on the third. The four mismatched-category/attribute
queries returned no match. It merits consideration as a fast grounder after an
independent model supplies semantic descriptions, not as an authoritative detector
or an automatic motion input based on this smoke test.

## Setup

- Model: `nvidia/LocateAnything-3B`, pinned revision
  `c32291ca5e996f5a7a485845b4f57a233936bba0`.
- Official custom model/processor code and safetensors; source and weight hashes
  recorded. Loading reported no missing, unexpected, or mismatched keys.
- Separate dependency directory; existing VLX, SAM, policy, and simulator packages
  were not replaced. Transformers 4.57.1, PyTorch 2.10 runtime, BF16 weights.
- RTX 4090, otherwise idle. Explicit SDPA for text and vision attention.
- NVIDIA worker settings: hybrid decoding, sampling enabled, temperature 0.7,
  top-p 0.9, repetition penalty 1.1, maximum 8192 tokens, KV cache enabled.
  Fixed per-request seeds are recorded. Each request had a 90-second bound.
- Six retained native 720x720 views: 0, 288, 352, 384, 512, 768. One independent
  current image per request, no history or audit target boxes.
- Eighteen primary requests plus four distractor requests; all 22 terminated.
- No paid API calls, simulator motion, training, or model deployment changes.

The automatic default originally chose FlashAttention2 after MagiAttention was
unavailable. This custom generation path raised `NotImplementedError` for that
backend before producing an answer. The successful run explicitly selected SDPA,
without modifying model source or weights. An earlier import attempt lacked
`requests`; it was installed only into the separate dependency directory. Failed
startup/model-run evidence was retained. These are runtime issues, not visual failures.

## Prompts

Goal-blind inventory:

```text
Identify up to twelve major noticeable visible objects in this image, covering the left, center, right, foreground and background rather than only the most salient item. Include furniture, fixtures and smaller distinct objects where visible. Do not assume a task or expected object. Use ordinary categories, or unknown if unclear. Give each object category and its bounding box using your native structured box tokens. Mark unclear identities as uncertain. Do not claim completeness or invent hidden objects.
```

Generic native-template control, also without a target category:

```text
Locate all the instances that matches the following description: visible objects.
```

Native radio control:

```text
Locate all the instances that matches the following description: radio.
```

The native template preserves the grammar in NVIDIA's example. Output coordinates
are the model's native integer tokens normalized to 0..1000, converted to pixels
using the documented convention. No box repair or retrospective rescaling was used.
These native coordinate tokens differ from asking a generic VLM to invent a JSON
coordinate convention.

## Results

| Path | Views | Median latency | Range | Outcome |
| --- | ---: | ---: | ---: | --- |
| Blind inventory | 6 | 3.34 s | 1.83-4.16 s | No useful specific-category inventory |
| Native visible objects | 6 | 0.74 s | 0.53-1.20 s | Some useful boxes, all labeled visible objects |
| Native radio | 6 | 0.34 s | 0.34-0.52 s | Two accurate full-object boxes, one oversized box |

The radio median includes three no-match replies. The positive replies took
approximately 0.34-0.52 s. Timings include processor work, device input transfer,
generation, and CUDA synchronization, excluding file opening and model loading.
Model/tokenizer/processor loading took 3.95 s after hashing; peak allocated GPU
memory was approximately 8.42 GiB. This is not an optimized Flash sparse-kernel or
co-resident simulator benchmark.

Inventory output often used `furniture`, `fixtures`, `object`, or `smaller objects`.
One response included broken labels such as `upurniture` and prompt words such as
`Mark`, `right`, and `background`. It did not satisfy the requested specific-category
inventory or uncertainty semantics. Some boxes nevertheless align with furniture
and the radio. The native visible-objects query also found useful regions, but
echoed the query as every label.

The automated checklist scorer therefore counted no specific expected categories
for these two broad-query paths. That is an interface/task mismatch result, not
evidence that the model sees no objects or deserves a general 0% detection score.
Its documented dense-detection mode supplies categories explicitly; it was not
given the ground-truth checklist as an input here.

## Target And Distractors

| View/query | Result |
| --- | --- |
| 0, radio | No match; target absent |
| 288, radio | No match; no full target visible, not independently scored as an absence test |
| 352, radio | No match on the heavily edge-clipped target |
| 384, radio | Tight box, manual-reference bbox IoU 0.919 |
| 512, radio | Tight box, IoU 0.891 |
| 768, radio | Table-sized region, target IoU 0.039 |
| 384 and 512, blue radio | No match in both red-radio images |
| 384, camera | No match, unlike the earlier VLX radio-as-camera false match |
| 512, television | No match, unlike the earlier VLX wall-art-as-TV false match |

All parsed positive boxes had structurally valid native coordinates. Structural
validity did not prevent the oversized radio box. References are approximate manual
visible boxes, not segmentation ground truth. One sample per prompt/view, with
sampling enabled, cannot establish calibrated rejection or repeatability.

## Recommendation

Keep GLM as the current stronger blind-inventory candidate and SAM for tracking.
LocateAnything's approximately 0.3-0.5 s native grounding suggests a possible
GLM-description-to-box role, but that combined pipeline was not tested here. It
would add latency and must improve robustness enough to justify another component.
Before adoption, qualify repeatability, oversized-box rejection, and loss/distractor
behavior; do not equate its good speed with reliable motion-ready geometry.

## License

The actual NVIDIA LICENSE section 3.3 limits use to non-commercial research or
evaluation. The model card describes the restriction more narrowly as academic/
non-profit research; the user confirmed this experiment qualifies. No commercial
deployment permission is assumed. Third-party component licenses also apply.

Sources:

- https://huggingface.co/nvidia/LocateAnything-3B
- https://huggingface.co/nvidia/LocateAnything-3B/blob/c32291ca5e996f5a7a485845b4f57a233936bba0/LICENSE
- https://github.com/NVlabs/Eagle/tree/main/Embodied

## Artifacts And Verification

Private parent-workspace artifacts:

- `internal/physical-ai-lab/runs/locateanything-inventory-20260923-r1/`: failed default-backend run.
- `internal/physical-ai-lab/runs/locateanything-inventory-20260923-r2/`: successful SDPA
  run, raw outputs, prompts, hashes, loading checks, timings, audit, and comparison image.
- `internal/physical-ai-lab/scripts/run_locateanything_inventory.py`
- `internal/physical-ai-lab/scripts/analyze_locateanything.py`
- `internal/physical-ai-lab/tests/test_locateanything_parse.py`

Five parser tests passed; Ruff passed. Raw-output labels were retained, malformed
boxes are not repaired, image hashes were checked, and the annotated comparison was
visually inspected. GPU processes exited and reports were copied locally. The
instance remains running. No commit or push was made in this turn.
