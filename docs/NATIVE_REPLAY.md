# Native Recording Bridge

The read-only bridge now accepts the existing development sensor capture:

```bash
python -m physical_harness audit-recording --archive \
  /path/to/native-sequence-301-001
```

Validation on 2026-09-18: 16 frames, 96 unique artifact hashes verified,
20.728238 seconds of monotonic capture-wall span. No new GPU inference,
simulator actions or paid calls. Source JSONL SHA256:
`049b3f197742f44cb1cced16ef37c99e52a49c5b7d3ec76b01405e3dff30b0bb`.

The capture was previously made with 60 diagnostic base-yaw/hold commands;
it is not a learned-policy trajectory. Hash verification establishes byte
integrity, not semantic accuracy or image-format validity. Native sensor
quality was checked by the original capture, not rerun by this audit.

## Decoding Contract

Pinned BEHAVIOR source: `b1979916ec1549b10a4e65e630bc6504a9af1b00`.
`OmniGibson/omnigibson/eval/r1pro.yaml` specifies the proprioception order.
The recorded 61-vector contains base velocity, two arms' positions/velocities,
EEF poses, two finger pairs' positions/velocities, and trunk positions/velocities.
The bridge exports joint arrays in left-arm/right-arm/trunk order (7/7/4),
finger positions separately, and base velocity separately. It drops EEF poses.
This is a simulator observation decoder, **not** a real-R1Pro policy action
mapping. It does not establish motor compatibility or training provenance.

## Clock Boundary

The archived `observed_at` is `time.monotonic()`, not simulation time. Therefore
`RecordedFrame` retains `captured_wall` and has no implicit `sim_time`.
`at_sim_time()` requires an independently established simulation timestamp.
Do not substitute wall elapsed time, frame ordinal or guessed frame intervals.
Future native capture should record simulation timestamps explicitly alongside
the existing wall clock before this recording can drive timed runtime replay.

Full audit consumes the whole stream before returning success. A caller using
the streaming reader must exhaust it to detect a truncated frame count. Scorer,
camera/global pose and other non-allowlisted input fields are never exported.

## Remaining Live Gates

Live sensor IPC and explicit simulator clock; controller/joint/gripper
qualification; calibrated perception/verification; native navigation/recovery;
then a bounded development-only motor trial. None are bypassed by replay success.
