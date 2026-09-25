# Phase 13 Composite Distractor

Date: 2026-09-25

## Result

The transport-compatible orange visual-distractor cohort passed. GPT-6 Sol chose
`hold`, `hold`, and `lift_current_candidate`; all three packet-bound decisions
executed for 30 actions and passed independent legal RGB-D/proprio verification.

| Condition | Decision | Physical execution valid | Verified progress |
| --- | --- | --- | ---: |
| M0 | hold | yes | 0/1 |
| M1 | hold | yes | 0/1 |
| M2 | lift | yes | 1/1 |

M2 received the current head image plus one derived historical memory image. The
historical artifact placed the orange left-wrist target view beside the unrelated
same-boundary head view. Its provenance records both source hashes, panel order,
and the transformation: the 480x480 wrist frame was resized to 720x720 with
Lanczos and concatenated with the unmodified 720x720 head frame. No crop, text,
annotation, hidden simulator state, or future evidence was added.

Both holds moved the grasp center by about 0.075 mm. M2 lifted it 50.010 mm. Every
verifier retained 230,400 paired depth pixels. The three calls used 6,927 prompt
tokens, 280 completion tokens, and `$0.0100565` total. No fallback or retry was
used.

## Transport Finding

The first preregistered distractor representation sent current head, historical
wrist, and historical head as three separate images. M0 and M1 completed, but the
M2 preflight exceeded its 16k conservative bound. A separately bounded 24k M2
request then returned `finish_reason=length`, empty text, and zero billed tokens.
It was retained without retry and is not scored semantically.

That preflight also exposed an implementation error: the protocol helper labeled
all RGB cameras as 480x480, while retained R1Pro head PNGs are 720x720. Raw bytes
were always sent at full resolution, so earlier evidence, timestamps, and decisions
are unchanged, but their head-image dimension metadata is inaccurate. The helper
now reads dimensions from RGB files; a guarded legacy flag reproduces frozen older
protocols byte-for-byte. The completed composite cohort used corrected 720x720
head metadata and fresh model calls.

## Evidence

- superseded raw three-image protocol / partial decisions / empty M2 continuation:
  `768a96532913751b27f76f05605fe8c78df4230dc1f17d86d3b1ae945384c26a` /
  `9367358f6a37e905a4fb0d59677765c4a4923397a0c615edb66305d98a811bab` /
  `d53827390af7bbdc60d83448b61dddd63c9330a3638c02b2028362fb0b6b4b82`;
- corrected preregistration / protocol:
  `f9cb27d43d42c7822bc1a505301601ac106d13fe6cb4e48ad129c1d794e93edb` /
  `42d6d9b4f6075756d4a2aa19250947b96029e28f92db30106ad38419fa609bc8`;
- decision report / final score:
  `c252e0f3f3de798db9883e95134fdaf1797fd83dd46fbb3da62546eea2975bfa` /
  `c6c465740df82c3032e2e8163c727e68a745047366e0ae8141d5a9393345dd90`;
- M0 receipt / verification:
  `ad5c9111cf947e28410c0aa340b4cb9c342c077dbf5e1c0f259deeb17fbb82b8` /
  `3a2208df7ce3893beabcc73534490fade5d065aeb04914edc41e83104852d558`;
- M1 receipt / verification:
  `22b7553a30da8896d83b3f1a96d7acea5c31becfd7e81c1affad0a9454c2e715` /
  `46fcb22ef63fd622bd53f88752981343a17cb9c1ead9998a205a05e7255719b2`;
- M2 receipt / verification:
  `9aabb78d32a5b3e0456d3e6585d952d969c17eca9024696aa63298c313e14f63` /
  `c9b35ef5cb34da25d029e14e05635f9cfa6553f2f60a4ab428b1d91613d9129f`.

## Interpretation

Phase 13 now contains a failed blue-attribute axis, a passed second-seed orange
axis, and a passed derived visual-distractor axis. This is useful narrow robustness
evidence, not broad held-out task robustness. The blue failure remains the clearest
candidate for a frozen Sol-versus-Astra model comparison.

This remains a scripted development fixture, not BEHAVIOR benchmark success.
Initialization was scripted, current left-wrist RGB dropout was injected,
external clearance stayed unknown, and `motion_qualified=false`.
