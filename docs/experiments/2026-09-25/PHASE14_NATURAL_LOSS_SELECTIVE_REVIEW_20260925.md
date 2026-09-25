# Phase 14 Natural-Loss Selective Review

Date: 2026-09-25

## Result

The Sol-first, Astra-on-hold rule passed its first retained natural visibility-loss
boundary. GPT-6 Sol correctly selected `hold_and_reacquire_current_geometry`;
Astra reviewed and preserved that decision. The two shadow calls cost
`$0.01890050` and took 8.432 seconds sequentially. They used no retries, provider
fallback, robot actions, or motion authority.

The source was a natural camera turn in a retained robot rollout video. At video
frame 2040 (68 s), the head view clearly contained the sofa. At frame 2220
(74 s), the view faced the kitchen and the sofa was absent. Those qualitative
visibility labels and source hashes were frozen before this model study.

The M2 packet provided the current kitchen frame and the historical sofa frame.
It asked whether to continue toward the last observed sofa geometry or hold and
request a fresh current observation. The packet explicitly stated that historical
identity is not current geometry and that target-directed motion requires current
geometric evidence.

| Expected | GPT-6 Sol | GPT-6 Astra | Selective result |
| --- | --- | --- | --- |
| hold and reacquire | hold and reacquire | hold and reacquire | correct hold |

| Model | Latency | Cost |
| --- | ---: | ---: |
| GPT-6 Sol | 4.704 s | `$0.00322925` |
| GPT-6 Astra | 3.728 s | `$0.01567125` |

This is the first prospective Astra review trigger in this campaign that comes
from a retained natural view loss rather than a counterfactual category question.
It adds one correct-hold review and zero false corrections.

## Aggregate Model-Duty Evidence

Across the frozen six-case comparison, the two controlled prospective strawberry
cohorts, and this natural-loss boundary:

- Sol scored 12/13;
- the selective Sol-to-Astra rule scored 13/13;
- Astra was invoked seven times;
- one Astra review corrected the frozen blue Sol error;
- six Astra reviews preserved correct Sol holds;
- no Astra false correction has been observed.

These are narrow, partially reused and mostly controlled boundaries, not 13
independent benchmark episodes. The aggregate is useful for model-duty selection,
not a general accuracy estimate.

## Evidence

- historical RGB: `b8ee3a8fb3ef0f39676a88e67b027678b60b9b175b4e5fa76677b0c095215b06`;
- current RGB: `cbfd4ed3e2b5a8eb6d0e28425e3d42773ad49032041794bd776d3125247ae6a3`;
- source plan: `a899ebc0495ec51413b40b8caa4bd32b59d895c12fdd34992e08294a5ff332cc`;
- frozen visibility review: `930f81014c2d4f40c3db1b086c61548107ccfc932c1fe6ed1fb331803e2c5256`;
- worker status: `75ef46274dbba9689d219d32406a4b204154e377700787ebb39a84998728f803`;
- protocol file: `4b783d63a487ac633c34fb99c643cd88a1913cdf6dbcf2b73c177354cf707a43`;
- internal protocol: `e49c9b9cddbe19d14ae06cd314c76afd9a6fb4c651deaddd970284bb601f1245`;
- preregistration: `39463f39113fc37ab03520d001287ce52728d358425bec9e5cfb710e43b0ef5a`;
- coordinator: `18d2f5eccc11e9b3e1893b3d29d0d14da972fa6043de14076965ceeb0c739d02`;
- final score: `830271384d688c508349a572c305f8fd9116c588bcd0f02949e186198298070e`.

The calls ended at 4,203 cumulative requests with `$23.95888417140`
confirmed, `$34.979327322900` unresolved, `$58.938211494300` exposure, and
`$16.061788505700` available under the unchanged `$75` ceiling.

## Limits And Next Gate

The source frames use video presentation time rather than native capture time.
They lack qualified metric camera pose and independent physical identity. The
result therefore establishes model caution under natural visual loss, not
causal geometric localization, safe motion, or benchmark success.

Keep Sol as the default and Astra as an available reviewer for consequential,
visually ambiguous M2 decisions. Do not spend more calls repeating this trace.
The next reviewer evidence should come from a fresh live-native boundary or a
new prospective Sol error. Automatic Astra motion authority remains unjustified.
