# SAM 3 Retained-Frame Test

## Result

SAM 3 image-only inference works on the single RTX 4090. It is a promising
direct text-to-mask candidate, not a qualified replacement for live perception.
No simulator actions, policy runs, or GPT calls were made for this test.

Eight retained native RGB-D frames (actions 0, 352, 384, 416, 512, 640, 736,
768) were tested twice with independent prompts `a radio`, `a television`, and
`a robot gripper`. Threshold was 0.5; processor resolution was 1008 square.
One image encoding was reused for the three prompts. There was no video
tracking, prompt tuning, compilation, or text-embedding cache.

## Measurements

| Quantity | Measurement |
| --- | --- |
| Evaluations | 48, complete |
| Image model parameters | 840,509,750 |
| Model load | 10.231 s |
| Warm image encoding, median | 55.31 ms |
| Warm encoding plus all three prompts, median | 230.27 ms |
| Warm three-prompt range | 228.38-232.50 ms |
| Peak PyTorch allocated / reserved | 5087.92 / 5328 MiB |
| NVML memory at end of inference | 5807 MiB, not a measured NVML peak |

FP32 weights with BF16 autocast worked. A separate blanket BF16-weight test
failed on the first inference: the upstream decoder disables autocast in its
FFN, producing a Float/BFloat16 matrix mismatch. That run is incomplete, not
a lower-memory success. No upstream source was patched.

These are isolated model timings, not capture-to-decision latency. The earlier
SAM 2.1 measurement of 105 ms used supplied detector boxes and depth processing;
it is not an equivalent text-to-mask comparison. GPU co-residency with the
simulator and policy has not been tested and may be tight on a 24 GiB card.

## Quality

- Radio predictions occurred at 352, 512, 640, 736, and 768. The radio was
  visible in seven selected frames, but missed at 384 and 416.
- The final-frame radio was recovered where the earlier pipeline missed it.
- The initial wall television was detected, but wall artwork was also labeled
  television in later views, including 512 and 768.
- No gripper predictions occurred, including views containing visible grippers.
  Absence of false gripper detections is therefore not proof of good recognition.
- Repeated mask hashes were identical. Saved depth partitions reproduced on CPU.

This small selected sample has no manually annotated mask-quality benchmark.
Neither identity nor handle-hole/depth geometry is qualified for motion by it.
Partitions retain all components; they do not silently select an object surface.

## Provenance and Restore

User accepted the [SAM License](https://github.com/facebookresearch/sam3/blob/main/LICENSE)
for the local research test. The original `sam3.pt` from
[1038lab/sam3](https://huggingface.co/1038lab/sam3), revision
`ea8e153c669a0284a496c0ec65a53b8e4f5ca7e7`, was downloaded and its SHA-256
verified against the official published checkpoint hash:

```text
9999e2341ceef5e136daa386eecb55cb414446a00ac2b55eb2dfd2f7c3cf8c9e
```

Official source revision: `2345a4ad109ac29c569da749c91d84f10dc08c40`.
The isolated environment uses Python 3.12.14, torch 2.7.1+cu126 and torchvision
0.22.1+cu126. Simulator and policy dependencies were not changed. Only image
detector weights were loaded; optional interactive-tracker weights were unused.

Private receipts, masks and analysis panels are retained under
`sam3-retained-20260922-r1`, `sam3-retained-bf16-20260922-r1`, and
`sam3-analysis-20260922-r1`. Native sensor media remains private.

## Next Gate

Keep SAM 3 experimental and the existing GrabCut-free pipeline unchanged.
Before live adoption, measure memory and latency with the simulator/policy
resident, then run shadow-only comparisons on fresh frames. Continue to require
identity and measured-depth association checks: better segmentation does not
make semantic predictions authoritative or solve capture scheduling.
