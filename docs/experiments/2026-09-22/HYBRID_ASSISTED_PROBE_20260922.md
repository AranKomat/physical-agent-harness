# Assisted Probe: Stopped Before Yaw

Experiment work was stopped at the user's request to integrate Action Compiler
V1. No new experiment is authorized by that integration.

Run `hybrid-assisted-yaw-20260921-r1` completed 384 frozen-policy actions, then
60 zero-base hold actions and 60 bounded emergency-hold actions. The required
five consecutive instantaneous-velocity stop checks never passed. No target
annotation was requested and no nonzero base/yaw command was sent by the probe.
Native action total: 504. The diagnostic failed; it is not motion qualification.

Joint-position drift was small while instantaneous velocity fields remained
nonzero. This discrepancy was not resolved or used to loosen admission. The
native worker and policy server exited; the instance was left running with no
GPU worker active. Raw evidence and logs remain private and locally backed up.

The opt-in assisted probe and offline tests are retained for reproducibility.
They do not alter the strict hybrid gate, provide autonomous target grounding,
or enable the new action compiler. Further native runs are paused.
