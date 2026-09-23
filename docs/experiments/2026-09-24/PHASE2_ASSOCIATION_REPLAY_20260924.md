# Phase 2 Association Contract Replay

## Result

The current public/private runtime was rerun against the frozen Phase 2
association protocol on 2026-09-24. The replay passed 987 checks with zero
errors, visited 36 mask archives and 30 positive mask outputs, and granted no
physical identity bindings.

The replay exercised 10 of the 14 predeclared scenarios. The following four
remain protocol/data gaps rather than passing results:

- two similar objects with a genuine identity-crossing sequence;
- natural full disappearance/occlusion;
- natural reappearance after disappearance;
- continuous object motion relative to the background.

The output is retained privately as
`runs/phase2-association-contracts-20260924-r1/REPORT.md` and
`report.json`. No model calls, paid calls, simulator actions, or public runtime
edits occurred.

## Decision

Phase 2 remains partial. The replay confirms the safety boundary: local tracker
IDs, semantic labels, stale boxes, and matching masks do not create physical
identity authority. It does not qualify association or current geometry.
