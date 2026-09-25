# Phase 13 Supported Place Diagnostic

## Result

One preregistered controlled fixture added a fixed cylindrical support under the
existing soda-can release pose. The corrected run completed all 70 grasp, lift,
return, open, and lateral-retreat actions. The can finished exactly on the support
top and inside its horizontal radius, but the frozen protocol failed because the
retreat perturbed the can slightly too much and did not achieve the required final
gripper separation.

| Measurement | Result | Frozen criterion |
| --- | ---: | ---: |
| Actions | 70/70 | 70/70 |
| Evaluator lift | 41.532 mm | at least 35 mm |
| Closed return error | 1.042 mm | at most 15 mm |
| Constraint active after opening | no | no |
| Object registered in hand after opening | no | no |
| Lateral gripper retreat | 50.854 mm | at least 35 mm |
| Object motion during retreat | 22.963 mm | at most 20 mm |
| Final gripper separation | 31.998 mm | at least 35 mm |
| Final object/support vertical gap | approximately 0 mm | at most 15 mm |
| Final horizontal support-center offset | 20.469 mm | at most 30 mm |

The final support contact passed geometrically, but the combined frozen result did
not. `passed=false`, `motion_qualified=false`, and external clearance remained
unknown. No paid model, learned motor, SAM call, or GPT call participated.

## Interpretation

The unsupported predecessor established that this smaller can cleanly leaves the
open gripper but falls without a support region. This run establishes the next
narrow fact: a support at the release pose prevents that fall. The can bottom and
support top matched within floating-point tolerance after the retreat, and the can
center remained within the 30 mm support radius.

The place trajectory is still not qualified. Between the `post_release` and
`post_retreat` captures the can moved 22.963 mm and tilted, while final separation
reached only 31.998 mm. Those misses are small but predeclared thresholds cannot
be relaxed after observing the result. The lateral retreat likely contacted or
dragged the newly supported payload. The run therefore supplies a useful physical
diagnosis, not a successful place action.

This fixture exercises place mechanics only. The support and initial poses were
scripted before the first legal observation, and the public Action Compiler did
not authorize or execute the motion. Evaluator target/support poses were used only
after control for scoring.

## Retained Setup Failure

The first attempt is retained as a zero-action setup failure. The BEHAVIOR task
loader discarded an extra object supplied at configuration time. A separately
preregistered `r2` changed only support insertion to OmniGibson's documented
post-load, state-preserving scene path; support geometry, target pose, motion,
thresholds, and stopping rules remained frozen.

## Evidence

```text
parent preregistration
b73d74bc12104d7f0e06b992b6853f6d3a45e060c163cc38b776729cf97bad76

zero-action setup-failure receipt
b541fefaeaa993c73122ec8b5606cc75b38f23600b3401f7ab9d70deaf51d26c

object-insertion correction preregistration
55ce0a269289b1b3fc825d7432c0cb80519fc134c9ddcb1de4434bcd13df7d67

completed receipt
104af29ed0845658600373dd4156a3380a20da47a0cab5c2a2ae57cfa6673765

quarantined evaluator sidecar
91f4c9c5b1f15142a60c9008d41b046926bc741c5a9fb71ac0465a2102b530cb
```

## Next Gate

Do not tune this pedestal, retreat direction, opening duration, or thresholds.
The next positive placement attempt must come from a new, independently reviewed
support-aware trajectory that avoids the released payload and verifies stable
support from fresh legal evidence. Integrating that trajectory through the Action
Compiler execution boundary remains open.
