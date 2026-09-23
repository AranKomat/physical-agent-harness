# Native Sensor Restoration

## Result

The new single RTX 4090 host passed its first bounded native sensor check.
`native-sensor-restore-20260923-r1` exited zero after approximately 7.6 minutes
of cold startup, initialization, observation and cleanup. No GPU client remained.
This restores basic simulator/sensor readiness, not task or motion qualification.

| Check | Result |
| --- | --- |
| Head RGB/depth | 720 x 720, nonblank RGB, finite positive depth fraction 1.0 |
| Left/right wrist RGB/depth | 480 x 480 each, nonblank RGB, valid depth fraction 1.0 |
| Proprioception | 61 values |
| Native action interface | 23 channels, 30 Hz |
| Intrinsics | Valid finite matrices for all three cameras |
| Commanded actions / paid calls | 0 / 0 |
| Task success / native Q | Not measured; null |

The head image was also inspected visually and shows a rendered room rather
than a blank output. This is not a metric-depth or semantic accuracy assessment.
Controller inspection computes but does not execute no-op commands; policy
mapping remains explicitly unqualified. Normal reset/settling physics occur.

## Declared Protocol And Restoration

The private `NATIVE_SENSOR_RESTORE_PROTOCOL_20260923.md` was written before the
sensor run: one attempt, 900-second limit plus 30-second termination grace,
reserved Halloween development index 0 (native ID 301), seed 0, no policy or API.
No collected map/task knowledge is reused as advance knowledge in later episodes.
Only legal RGB-D/proprioception and camera intrinsics were exported; no simulator
object poses, segmentation or hidden scorer information feed an agent.

- Public baseline: `6aa64f0`; existing private `physical_ai.native.sensor_smoke`.
- Clean BEHAVIOR source: `b1979916ec1549b10a4e65e630bc6504a9af1b00` (v3.9.2).
- Isaac Sim 5.1.0; NVIDIA driver 580.95.05; one RTX 4090.
- Dataset revision: `9f0d57d465726976ed98138d3f8b8ca3e2186775`.
  All three robot/scene/task archives match the previously recorded SHA-256s.
- Existing academic license approval used; key installed through upstream code.
  The old host stayed stopped, with no whole-disk copy or destructive operation.

Restoration failures are retained: the initial asset command lacked
`huggingface_hub` in the CPU venv; the successful download used the existing SAM
venv. Bootstrap installed the simulator but exited because the compatibility
file was absent remotely; copying and applying that existing file corrected it.
Neither was a failed sensor attempt, and neither changed the SAM environment.

`pip check` still reports the three known contradictory upstream requirements:
OmniGibson Pillow 11.0.x versus installed 11.3.0, Isaac websockets 12 versus
15.0.1, and Isaac packaging 23 versus 25. These are disclosed exceptions, not
suppressed checks. The package freeze is retained. This is not an exact old-env
reproduction: notably Open3D resolves to 0.20.0 rather than the geometry extra's
0.19.0. Restore geometry-specific pins before qualifying localization; no geometry
algorithm was qualified here. Startup warnings remain in the complete log.

## Preservation And Remaining Work

Private artifacts: `runs/native-restore-20260923-r1` (setup logs, protocol,
freeze and dataset receipt), `runs/native-sensor-restore-20260923-r1`
(sensor receipt, observation and six RGB-D files). Sensor evidence was copied
to the Mac; checksum-mode rsync dry run found no differences.

Sensor receipt SHA-256:
`41de619daf30baf35ffe78959a49cc6de5891033727cef6edcc4fd81e659c9de`.
Freeze SHA-256:
`c4c2f51c25c409543bcb527674fb1f78fc92af4b9da8152de1f66cdf547bf5f0`.

SAM and basic native sensing are now restored. Frozen-policy runtime, legal
estimated extrinsics/live timing, full loss/reappearance/crossings, positive
physical association, stopping and clearance remain separate unfinished gates.
This check does not authorize motion or prove Phase 2/5 completion. No test-suite
counts changed; public code was not edited for this restoration.
