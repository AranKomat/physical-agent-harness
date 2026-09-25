# Phase 10 Semantic Choice: Partial Physical Cohort

Date: 2026-09-25

## Scope

This is an exploratory, non-benchmark Phase 10 comparison. External clearance
remains unknown and `motion_qualified=false`. GPT receives only frozen current
images and packet-bound semantic options; hidden fixture truth is scoring-only.

## Semantic decisions

GPT-6 Sol Flex returned valid structured decisions for three of four frozen
cases:

| Order | Case | Decision | Status |
| --- | --- | --- | --- |
| 0 | orange rule, orange can | `lift_current_candidate` | valid |
| 1 | orange rule, blue can | `hold` | valid |
| 2 | blue rule, blue can | visible prefix selected `lift_current_candidate` | rejected: JSON and packet ID truncated at the 128-token cap |
| 3 | blue rule, orange can | `hold` | valid |

The truncated response is not repaired or treated as a decision. Completing the
cohort requires one separately approved replacement call for order 2 with a
256-token output bound. Fixed routing still scores `2/4` analytically.

## Physical execution

The three valid decisions were executed independently with the same scripted
fixture backend, exact reference-image rebinding, and 30-action budget.

| Case | Executed effect | Independent result |
| --- | --- | --- |
| orange rule, orange can | lift | passed; grasp center rose 50.01 mm with 0.28 mm lateral drift |
| orange rule, blue can | hold | passed; grasp-center displacement was 0.011 mm |
| blue rule, orange can | hold | passed; grasp-center displacement was 0.007 mm |

All three receipts report `complete=true`, `passed=true`, exact requested/executed
decision agreement, `image_rebind_passed=true`, and 30/30 completed actions. All
three offline legal-evidence verifiers passed. Each verifier used robot-only FK
from legal proprioception plus retained legal RGB-D; no simulator object pose was
fed into control.

The hold runs exhibited large wrist RGB/depth changes while the robot remained
stationary. The preregistered hold verifier scores kinematic stationarity only,
so this remains an explicit limitation rather than a post-hoc gate change.

## Evidence digests

| Case | Receipt SHA-256 | Verification SHA-256 |
| --- | --- | --- |
| orange rule, orange can | `44f0d1bcb13c4d9a26d61350815d2036c705c8f82934489e99beac7a39ab5373` | `2835d5cb87121078c19aa29a2161fbc630e89429301de9c6535351da069f710a` |
| orange rule, blue can | `cd741024137ba0c729e87cf3023f86ceb2d8d207a60f5249e0ba7048f227c6da` | `5a3ea7da2b86c14e83d045660bf4371f508e4d5fe8f8d8ce5ae42467b6021a8e` |
| blue rule, orange can | `b745cc30a6e57d529e8f56f8fff747c66598e1fd2d7ccb43176ebf3a392f1b52` | `7b7f5b4b6ad4fd8fa876ee07aaba96931e821528b0f0c187732c677a65554b35` |

## Current gate

Do not start Phase 11. First obtain a valid order-2 decision, execute and verify
that fourth case, then score GPT against fixed routing. Phase 10 establishes a
causal semantic benefit only if all four physical cases are valid and GPT exceeds
the fixed `2/4` result.
