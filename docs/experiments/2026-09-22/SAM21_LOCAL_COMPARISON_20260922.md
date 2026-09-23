# Local SAM 2.1 Large Comparison

## Scope and Identity

User selected a larger checkpoint instead of Tiny. Tiny was downloaded but never
run. This test uses SAM 2.1 Large, 224,446,642 parameters, Apache-2.0, with source
revision `2b90b9f5ceec907a1c18123530e92e794ad901a4` and config
`configs/sam2.1/sam2.1_hiera_l.yaml`. Official checkpoint SHA-256:
`2647878d5dfa5098f2f8649825738a9345572bae2d4350a2468587ece47dd318`.

No simulator steps, GPT calls, policy calls, training or live-controller changes.
The simulator and policy were unloaded for these offline inferences on one RTX
4090. Small SAM dependencies were placed in an isolated import directory; existing
policy/simulator environments were not modified. The existing PyTorch 2.7.1
CUDA 12.6 runtime was reused. Driver: 580.178.04.

## Protocol

- Retained trace: `single4090-dense-acquisition-20260922-r1/A`.
- All 12 accepted radio detections, plus all six logged distractor boxes at
  preselected actions 0, 384 and 768. Distractor labels are detector outputs,
  not ground-truth object identities.
- Original 720x720 RGB and original detector box coordinates. No extra points,
  depth prompts, tracking, per-frame prompt tuning or selection of a favorable
  mask. Single-mask prediction with default model stability postprocessing.
- BF16 autocast, no compilation, no optional hole filling or speckle removal.
- Radio baselines are the original retained GrabCut masks. Distractor baselines
  were generated offline with the existing GrabCut algorithm and same boxes.
  GrabCut includes its existing one-pixel erosion; SAM does not. This compares
  the actual pipelines, not segmentation networks under identical morphology.
- RGB/depth identity hashes and mask checksums validated. Outputs remain at
  native resolution and carry source stamps and evidence IDs.

Runs `sam21-large-mask-comparison-20260922-r1` and `r2` completed. The repeat
uses a writable RGB copy to avoid a PyTorch warning about read-only NumPy input.
All 18 SAM mask hashes are identical across both runs. It is a technical repeat,
not an independent scene trial. r2 receipt SHA-256:
`a449f236a71aeeecee885321de1b5d344067252bef8873827b9c4c1a39008ad3`.
Both runs are locally backed up and checksum-rsync verified. No GPU workers remain.

## Performance

| Measurement, r2 | Result |
| --- | ---: |
| Model build/load after imports | 3.463 s |
| First image plus first box | 467 ms |
| Warm radio image-plus-box median, 12 views | 48.25 ms |
| Warm radio range | 46.81-52.94 ms |
| Peak PyTorch allocated | 1,711 MiB |
| Peak PyTorch reserved | 2,070 MiB |
| Total GPU memory at end, NVML | 2,547 MiB |

Timing includes image embedding, mask prediction and synchronized mask return;
it excludes source-file reading, detector inference, depth validation, artifact
writing and process startup. When multiple boxes share a frame, the embedding is
computed once; reported single-box totals include that embedding for each box
and must not be summed to estimate actual batch duration. NVML is an end sample,
not an observed total-memory peak. PyTorch records allocator peaks.

The live simulator/policy/grounding stack previously used about 20 GiB. This
standalone test does not qualify concurrent VRAM capacity, fragmentation,
latency or unchanged simulator throughput. Do not claim local inference is free
of interference merely because the model is small enough in isolation.

## Quality Findings

Numerical comparisons cover all 18 masks. Selected panels were visually checked
for radio actions 416/512/768, the actual initial TV, the fireplace false-positive
TV box, the final wall-picture false-positive TV box, and the final gripper.

- SAM recovers real radio regions omitted by GrabCut, notably the speaker,
  trim and handle outline. It similarly recovers gripper parts and avoids a hole
  caused by a TV-screen reflection. This is qualitative evidence, not labeled IoU.
- **SAM does not solve the handle-opening geometry error.** All 12 radio views
  include a larger fraction of pixels behind the original GrabCut median +15 cm.
  At action 512 this fraction rises from 5.65% to 9.57%; at 768 from 0% to 2.99%.
  This common-threshold statistic diagnoses a deep tail; it is not a measured
  background-pixel error rate, since legitimate parts can occupy other depths.
- Radio median image-plane depths shift by +3.3 to +20.0 mm. These are differences
  between estimates, not errors relative to independent truth.
- A box-prompted segmenter does not validate the detector's class. At 384 a
  fireplace region was labeled television; at 768 a wall picture was labeled
  television. SAM follows those boxes. These were distractor tests, not target
  detections promoted into control.

CPU panels and statistics are in private `sam21-large-mask-analysis-20260922-r1`;
they apply to r2 as well because masks are byte-identical. No renderer outputs
or licensed simulator images are redistributed in this public repository.

## Decision

Keep SAM 2.1 Large as the candidate semantic masker: standalone speed/memory
are practical and the inspected masks are more complete. **Do not automatically
replace the geometry/control masks.** The next small change should separate
semantic extent from measured surface patches and reject ambiguous contact
geometry, rather than assuming a newer segmenter removes all background holes.
Live deployment additionally needs a no-motion co-residency/timing check.

Nine focused private tests pass for prompt selection, box validity, mask shape,
hash/path binding, depth convention and invalid-depth handling. Ruff passes.

Sources: [official SAM 2 repository](https://github.com/facebookresearch/sam2),
[checkpoint](https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt).
