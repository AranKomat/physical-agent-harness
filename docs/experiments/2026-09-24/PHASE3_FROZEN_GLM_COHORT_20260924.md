# Phase 3 Frozen GLM Cohort

Date: 2026-09-24

## Scope

This run evaluated the four prospectively selected boundaries from the retained 119-frame moving trace. It used the real asynchronous discovery adapter with `z-ai/glm-5.3-flash`, pinned to Together before dispatch.

- Frozen source indices: `0`, `8`, `10`, `15`
- Frozen visibility labels: absent, absent, clipped, clear
- Paid calls: 4
- Automatic retries: 0
- Provider fallback: disabled
- Robot actions: 0
- New current geometry writes: 0
- Approved cumulative call ceiling: 4,149
- Local reservation cap: $0.05

The cohort required three process invocations because two scorer/runtime failures stopped their invocation after one call. No request was resent. The remaining invocations continued only with untouched boundaries.

## Results

| Source index | Expected visibility | Strict JSON accepted | Semantic visibility match | Latency |
|---:|---|---:|---:|---:|
| 0 | absent | no | yes | 12.35 s |
| 8 | absent | yes | yes | 11.94 s |
| 10 | clipped | yes | yes | 4.53 s |
| 15 | clear | yes | yes | 4.42 s |

Aggregate:

- Semantic visibility match: 4/4
- Strict JSON-contract acceptance: 3/4
- Results within the two-second live-use window: 0/4
- Latency: 4.42 s minimum, 8.23 s median, 12.35 s maximum
- Tokens: 8,185 prompt and 3,938 completion
- Actual provider-reported cost: $0.00319675
- Historical inventory records admitted: 3

## Failures preserved

The first room-inventory response reached the 2,048-token output ceiling and ended mid-JSON. Its visible text correctly said that the radio was absent, but the result was rejected by the structured contract. It was not retried.

The second response was valid and entered historical inventory, but post-delivery compact-context scoring failed because the retained observation was older than the two-second freshness window by the time inference completed. The scorer was changed to record this stale-context outcome rather than abort subsequent independent boundaries.

Continuation did not carry the second boundary's inventory into the third boundary because the process had terminated. The fourth boundary did receive the third boundary's newly admitted historical sighting and referred to it as an unconfirmed association, not as proven physical identity.

## Conclusion

The semantic path is useful as asynchronous historical discovery: it correctly handled absent, clipped and clear target views without authorizing motion or current geometry. It does not pass Phase 3 as a synchronous control dependency under the current two-second freshness budget.

Use the result to update historical inventory and request fresh reacquisition. Do not wait for it in a motion-critical loop. The room-initial prompt also needs a bounded response shape before it can be considered reliable; increasing the token ceiling after seeing this failure would require a separately frozen protocol.
