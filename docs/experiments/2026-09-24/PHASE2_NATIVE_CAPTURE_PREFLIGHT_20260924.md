# Phase 2 Native Capture Preflight

Date: 2026-09-24  
Run: `native-perception-sequence-20260924-r2`  
Scope: bounded sensor-only development diagnostic; no learned policy, paid
calls, task scoring, or motion authority.

## Result

The pinned BEHAVIOR checkout and challenge data root were restored explicitly.
The capture completed 16 native RGB-D frames over 60 upstream base-yaw
diagnostic actions. All frames retained source-bound RGB/depth and native
camera calibration. The capture receipt passed and reports
`benchmark_result=false`.

The repository RGB-D odometry backend accepted all 16 frames. Its largest
shadow camera transform was only:

- translation: `0.000465 m`
- rotation: `0.0824 deg`

This is far too little motion to expect a natural target disappearance or
reappearance in this trace.

SAM 3.1 then processed the exact 16 arrived head frames with the fixed
`radio` prompt and official-file preprocessing. It returned zero objects on
all 16 frames. This is a clean negative capture result, not evidence that the
SAM checkpoint or the harness is generally unable to detect radios: the scene
and motion protocol did not produce a target-bearing hard case.

## Decision

This run does not advance Phase 2. It is retained as a preflight failure for
experimental usefulness, and no further SAM inference will be run on this
trace. The next native capture must deliberately establish a target-bearing
initial view, a measurable camera trajectory, and a capture schedule that can
produce full loss/re-entry or similar-object ambiguity while retaining legal
pose/provenance evidence.

The prior negative launch failed before simulator startup because
`OMNIGIBSON_DATA_PATH` was unset; the successful retry used
`/workspace/behavior-data` and did not modify the audited source checkout.

## Provenance

Source directory on the GPU host:

`/workspace/physical-ai-lab/runs/native-perception-sequence-20260924-r2/`

| Artifact | SHA-256 |
| --- | --- |
| `sequence.json` | `477959ccb312c0fd765a8c9e88dd77baab32b8ce03aea9f0861a261db4a4cd9e` |
| `observations.jsonl` | `cdc1f007551516dd35393738807d3242fe9069c8ddde67d24464757cb8a61cd6` |
| `sam-native-summary.json` | `7dcfcf176868eb8fcc19bce52df9a4455eacf772a758f946492870b3b7234fdd` |
| `odometry-summary.json` | `a83e16eb3c558abd62bd1a9ece56eaacfa4a3209cf47dfaadc1de7eb7d9f5dce` |
