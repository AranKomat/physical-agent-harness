# Single-GPU Grounding Capacity

## Protocol

Resume prerequisite for the existing hybrid sequence, not a new policy search.
Three fresh paused native radio captures, each followed by frozen Behavior-Skill
inference and pinned GroundingDINO inference. Simulator and models reside on
GPU0. Policy and detector share one worker in this capacity diagnostic; this
does not qualify the normal separate-RPC-worker launcher's memory or throughput.

The detector uses the existing frozen contrast-class prompt and snapshot hashes.
Measured head depth and contemporaneous intrinsics are evidence-bound. The
robot-self-filter is deliberately absent here: this is not the full qualified
online grounding configuration and must not authorize navigation. Its robot-only
files were restored and hash-verified separately for subsequent integration.

Simulation time and all 61 proprioception values must remain exactly unchanged.
No inferred action is applied, no GPT/API call is made, and no motion/clearance
gate is weakened. Outputs and masks remain private.

## Interrupted Attempt

`single4090-grounding-capacity-20260922-r1` failed after two captures when
`nvidia-smi` exited 18: an unattended system update replaced NVIDIA userspace
580.95.05 with 580.178.04 while the old kernel modules remained loaded.
Both workers were reaped. This is an infrastructure failure, not a passing
capacity test or evidence of OOM. Maximum sampled memory before interruption
was 19,628 MiB. The complete partial run is checksum-verified locally.

After the package build installed matching modules for the running kernel,
verified no GPU clients remained, reloaded the modules and passed an NVML/CUDA
tensor check. No reboot, instance destruction or general security-update
disablement was performed. The retry therefore uses driver 580.178.04; comparisons
with earlier 580.95.05 timing are not matched-runtime comparisons.

## Completed Retry

`single4090-grounding-capacity-20260922-r2` passed all three fresh captures with
zero applied actions, unchanged simulation time/proprioception, and no GPT calls.

| Measurement | Result |
| --- | ---: |
| Maximum sampled global GPU memory | 20,416 MiB (19.94 GiB) |
| Policy inference | 96.47, 86.27, 89.97 ms |
| Grounding inference | 632.29, 129.63, 119.39 ms |
| Render/read/evidence capture | 444.32, 451.57, 444.46 ms |
| Native initialization | 306.06 s |

Memory sampling is approximately every five seconds, not an instantaneous peak
measurement. Inference/rendering are sequential with all models resident, not
simultaneous kernels or moving-rollout throughput. Roughly 4 GiB headroom at the
largest sample does not guarantee arbitrary scene, segmentation or RPC capacity.

All three negative initial head views yielded zero radio candidates and retained
TV/gripper distractors. The first fresh head image was visually inspected and
shows the furnished scene/TV, not a visible radio. This is a tiny negative-only
sample, not an accuracy estimate or a positive target-acquisition result.

Both workers exited and the GPU process list was empty. Native receipt SHA-256:
`d5cf54c7c9f3fa97a2100f2fb078840088e0f89d53bdafb01ae4970d8cd051b7`.
The complete retry was downloaded and checksum-rsync verification found no
differences after transfer completion.

## Verification

The full public offline suite passes 1,065 tests. The private no-motion owner
checks pass seven tests; these do not replace the live capacity gate.

The ordered next steps remain in [the experiment sequence](HYBRID_EXPERIMENT_SEQUENCE.md#resume-after-host-migration).
