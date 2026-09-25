# Phase 13 Orange Seed-71 Replication

Date: 2026-09-25

## Result

The Phase 12 orange visual-memory result replicated at a second simulator seed.
The protocol was preregistered before the seed-71 source capture and model calls.
Relative to the original seed-23 cohort, the declared changed axis was simulator
seed only. Task, orange attribute, evidence contract, current left-wrist RGB
dropout, model, provider, reasoning effort, motor backend, action counts, and
verifier stayed fixed.

The seed-71 source lift first passed independent legal RGB-D/proprio verification:
50.010 mm vertical grasp-center motion, 0.9961 retained-surface mask IoU, 0.64 px
centroid shift, and 0.020 mm median depth change.

GPT-6 Sol then selected the preregistered decisions. Each immutable packet-bound
choice executed in a fresh seed-71 fixture start for 30 actions.

| Condition | Decision | Expected | Physical execution valid | Verified progress |
| --- | --- | --- | --- | ---: |
| M0 | hold | hold | yes | 0/1 |
| M1 | hold | hold | yes | 0/1 |
| M2 | lift | lift | yes | 1/1 |

The two holds moved the grasp center by about 0.075 mm. M2 lifted it 50.010 mm.
Every verifier retained 230,400 paired depth pixels. The three calls used 5,791
prompt tokens, 265 completion tokens, and `$0.0085615` total. No retry or provider
fallback occurred.

This is positive evidence that the orange result is not unique to one simulator
seed. It does not erase the failed blue-attribute replication and does not
establish robustness across attributes, distractors, layouts, or tasks.

## Evidence

- preregistration SHA-256:
  `0162688eb1e60ce6a3452da56ffd421c7ce79ee1b88e1f51f2f828523d942e8a`;
- source receipt / verification:
  `4daad40206efad31deeda0fc8caef94f739ac76fad3c08fa90bbe2e99162f1d9` /
  `47d59d44f5c666fe9197b2b781e1566eee3b2caf5ee62f1c0f7e90374dc4917f`;
- protocol file SHA-256:
  `456e7fc1eb882202d599eb55f2f656bb4709b103166ecdbbfc4fdbd410ee1905`;
- decision report SHA-256:
  `5174773c8743690b2c430475c75aa1533899f8eb99d74380d8c6b980864f9d38`;
- final score SHA-256:
  `070ff2acf58384a3fdd0396701cd3ff3d75704e5792bc5a99de1d03b22f5399a`;
- M0 receipt / verification:
  `4adad481ee241ad611f261e797340d47be493efec314a2b816f97421c12b7758` /
  `c5bae3ad7e401b97886df793108d191895e92f81903ed81460d30467cc10c958`;
- M1 receipt / verification:
  `bde01e8766eb91f711d40d87bb7a1ddc8d45ec865293d74c53587e2aa8bb65d9` /
  `fed4185ee899465330279a5e81a3586ce23694bae841d3f0e964cdc46fdc7b4c`;
- M2 receipt / verification:
  `3da03fe0f14df65594140885486d4c8d7171a4109554d6bde9f366dfa7f02fe3` /
  `89afa8fa3809187ec88aceb3d510e24b90ea3380a057e06936d770592505b6f2`.

## Next Gate

Phase 13 now has one failed attribute axis and one passed seed axis. The next
single-axis test should be one predeclared visual distractor while retaining the
orange attribute and seed-71 execution contract. Do not revisit the failed blue
prompt after observing its result. Phase 14 efficiency work remains premature.

This remains a scripted development fixture, not BEHAVIOR benchmark success.
Initialization was scripted, current left-wrist RGB dropout was injected,
external clearance stayed unknown, and `motion_qualified=false`.
