# Phase 4A V3 Half

Date: 2026-09-24

This report scores the four completed V3 delta calls against the Phase 4A protocol frozen before output. The matched task-blind inventory cohort has not been authorized or run, so Phase 4A remains incomplete.

## Primary results

- Strict packets: 3/4
- Radio recall: 2/2 positive views
- Radio false positives: 0/2 negative views
- Supported updates at IoU at least 0.20: 4
- Unsupported updates at that threshold: 2
- Valid attention references: 4
- Primary reference categories covered: 4/24 across views

The clipped radio box reached IoU `0.4105`; the clear radio box reached IoU `0.3769`. The valid negative-view response did not claim a radio. Two broad negative-view landmark boxes, for the fireplace and television, missed the preregistered IoU threshold and are counted as unsupported rather than manually excused after output.

## Interpretation

V3 performed the task-directed role well on this very small held-out set: both radio positives were found and both negatives remained negative. It is intentionally sparse and therefore has low general room-inventory coverage. Its initial room packet also failed strict formatting by hitting the output cap.

This is not yet a prompt comparison. The four-call task-blind inventory cohort remains required under the separately frozen authorization and provider rules. No additional calls or robot actions were made for this scoring pass.
