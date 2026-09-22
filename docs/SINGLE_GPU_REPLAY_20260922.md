# Single RTX 4090 Replay

## Scope And Host

Five retained-input Behavior-Skill inferences, A/A/B/A/B, with a reset before each
call. No simulator, robot actions, training or GPT/API calls. The old stopped
instance was not restarted or destroyed. Only the pinned policy runtime, weights
and two initial RGB/proprioception packets were restored to the new host.

The host exposes one RTX 4090, 24,564 MiB VRAM, a 450 W limit, PCIe 4.0 x16,
about 131 GiB system RAM, and initially 407 GiB free disk. Driver 580.95.05
matches the previous dual-4090 host. This is a policy-only qualification, not a
simulator migration or co-residency test.

## Timing And Memory

| Measurement | New single 4090 | Previous dual-4090 host |
| --- | ---: | ---: |
| Cold inference including compilation | 17.971 s | 14.086 s |
| Warm backend median | 0.08482 s, 4 calls | 0.08847 s, 71 calls |
| Warm backend range | 0.07977-0.08965 s | P10-P90: 0.08542-0.09297 s |
| GPU memory at end of loaded replay | 8,657 MiB | Not measured comparably |

New warm end-to-end adapter calls took 0.08860-0.09875 s, excluding RPC because
this diagnostic calls the adapter directly. Backend timings use the adapter's
same internal timer as the historical policy-server log. These are 32-action
chunks, not individual native control steps or achieved simulator throughput.

**No noticeable policy-only slowdown was observed.** Do not claim a speedup from
four warm samples against a different workload of 71 calls. Previously the
policy occupied one GPU and simulation the other; it did not use both GPUs for
one inference. No matched dual-3090 baseline was measured here.

JAX reported peak live allocation of 7,149,611,520 bytes and peak pool size of
8,625,586,176 bytes. The nvidia-smi figure includes more than JAX live tensors.
About 15.5 GiB of device capacity remains relative to the end-of-run figure,
but that does not establish that simulator, perception and inference fit or
perform acceptably together. Separate peak/co-residency testing is required.

## Reproducibility Finding

- Repeated A outputs are exactly equal within this process, including cold/warm.
- Repeated B outputs are exactly equal within this process.
- A versus B differs, with maximum native-action component difference 0.004097.
- Against each original host's recorded initial chunk, the new output differs
  by up to 0.004224 after matching float32 representation, for both A and B.

Identical initial proprioception and different RGB therefore yield reproducibly
different actions on this host. That supports sensitivity to the retained visual
differences, but cross-host numerical/runtime differences remain. The result
does not prove that rendering alone caused the original full-trace divergence.
Mixed-unit action maxima are descriptive, not calibrated motion errors.

## Preservation And Runtime

All 727 checkpoint files (12,438,645,457 bytes) were verified against immutable
Hub metadata. Source revision, checkpoint, quantile normalization, camera resize,
explicit reset-relative noise, JAX 0.5.3, Flax 0.10.2, Orbax 0.11.13 and the
relevant pinned inference dependencies were retained. This was a minimal rebuild,
not a byte-identical clone of all transitive packages in the old environment.

The initial attempt failed before inference on a missing `tqdm_loggable` import;
the dependency was installed and the successful retry retained separately. No
model or controller code was changed to make the probe pass.

Private receipt: `single4090-replay-20260922-r2/replay.json`.
SHA-256: `922b72246b782fcc48b71ec52ebc77cf8c97a289eee3f16471d8072a2bb0ae95`.
Raw outputs and source packets remain private. This fulfills the five-inference
check proposed in [the acquisition audit](ACQUISITION_REPRODUCIBILITY_20260922.md).

## Next Step

Keep this host for policy-only work. Before a live combined run, restore the
simulator assets/runtime and measure concurrent memory and step latency without
motion. Do not assume the existing two-GPU launcher works unchanged: it pins
policy and grounding to GPU1, which is absent here. No long policy rollout or
classical motion is authorized by this report.
