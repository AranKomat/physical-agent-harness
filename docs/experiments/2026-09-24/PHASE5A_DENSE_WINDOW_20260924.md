# Phase 5A Dense-Window Preparation

## Protocol Change

The previous live-fusion diagnostic dense-captured only sequences `384..512`.
The retained radio masks become target-bearing at sequences `704..768`, so the
pose worker had no legal intermediate observations at the target window. The
diagnostic now accepts an explicit end of `512` (default, backward-compatible)
or `768` (new bounded target-window mode). The extended mode requires the
dense diagnostic and preserves `motion_authorized=false` and zero additional
model calls.

The pose queue, native dense-capture receipt, and owner validation now use the
same declared end and preserve the two-second observation-gap rule. This avoids
joining a target mask to a pose estimated across the roughly ten-second gaps in
the sparse retained trace.

Focused validation after the change:

- private dense/launcher tests: 49 passed;
- public hybrid/dense tests: 29 passed;
- Ruff: passed.

## Attempt

The first `dense-end=768`, live-pose/live-fusion attempt did not start the
simulator because the GPU host no longer contains
`/workspace/behavior-skill-venv/bin/python`. It produced zero actions and zero
observations; all owned workers were reaped. This is an environment-preparation
failure, not a Phase 5A result.

## Next Requirement

Restore or explicitly provision the pinned frozen-policy runtime and checkpoint
on the host, then rerun exactly one extended shadow trial. The trial should be
interpreted as a sensor/lineage experiment only: even a successful dense pose
and target join would not qualify clearance, navigation, or manipulation.
