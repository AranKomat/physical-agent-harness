# Phase 14 Scripted-Lift Power Baseline

## Result

One preregistered exploratory grasp-and-lift completed while retaining
time-aligned RTX 4090 device-power telemetry. The workload used the existing
scripted soda-can fixture, ordinary R1Pro actions, no learned policy, no learned
perception model, and no paid model call.

- Native actions: `30/30`
- Evaluator object lift: `50.015 mm`
- Legal RGB-D plus robot-only FK lift: `50.010 mm`
- Retained-surface mask IoU: `0.9964`
- Median depth change: `0.0173 mm`
- Legal verification: passed
- `motion_qualified=false`; external clearance remains unknown

This is a successful exploratory classical execution baseline, not a BEHAVIOR
benchmark result. Initial robot and object poses were scripted and disclosed.

## Power Measurement

The monitor sampled GPU 0 every `250 ms`, with 12 baseline samples before and
after the child process. There were 572 active samples and 143 periodic process
snapshots. No compute process existed before or after the run; every nonempty
active snapshot contained only the monitored child PID.

| Interval | Duration | Gross device energy | Mean power |
| --- | ---: | ---: | ---: |
| Full child sample span | 174.072 s | 2.1719 Wh | 44.92 W |
| Startup to pre-close capture | 162.441 s | 1.9119 Wh | 42.37 W |
| Close plus closed hold | 3.238 s | 0.0724 Wh | 80.54 W |
| Lift plus lifted hold | 2.481 s | 0.0685 Wh | 99.47 W |
| Whole manipulation window | 5.719 s | 0.1410 Wh | 88.75 W |
| Post-lift to process exit | 5.912 s | 0.1190 Wh | 72.48 W |

Cold startup consumed 93.3% of measured child time and 88.0% of gross measured
energy. The pre-close-to-post-lift manipulation consumed 3.3% of time and 6.5%
of energy. This supports keeping the simulator resident when running multiple
episodes or conditions; repeatedly launching a fresh process dominates this
small successful workload.

The pre/post idle estimate was `58.645 W`, which exceeded average draw during
some low-power startup intervals. Therefore baseline-subtracted energy is not
reported as a result. The defensible quantities are gross sampled device energy
and the capture-aligned interval breakdown. `nvidia-smi` samples power rather
than a cumulative hardware energy counter, so this remains an estimate with
sampling error.

## Interpretation

This closes the first measured-energy subquestion for a workload that produced a
verified physical effect. It does not measure Behavior-Skill, SAM, GPT, or cache
reuse. Representation-cache hits are not applicable because the workload made no
learned representation request. Cache-hit and neural-duty energy telemetry still
need a workload where those components participate and the physical task succeeds.

The next efficiency run should reuse a resident simulator and bracket only the
condition-specific workload. A matched cold-versus-resident study is useful only
when the resident runner can preserve an equivalent initial state and evidence
contract without hidden resets.

## Evidence

```text
preregistration
a6bb0970c886cd8e7cc991e646bc57d8cbcfb62036cd0002034bbbea77df4ba4

power telemetry
ff998647f2c50aeefc91f1dcc6763356d9cf6f36f4c8be7de8ff264913fcf71a

workload receipt
c6cee8989ee9f3214cbd77941a0f7e96c43eacf00de486bc69ab5a99c4c63494

evaluator sidecar
543ab7e84658df2c5a1005045c319456d1995790d2658babf74ad0dd72f13b5b

legal RGB-D/FK verification
b958f61c075ccb4e6bf920ce2f0f18742b7a1f62fdb1f0ed555b0ee2c5b389cc

analysis
fc3dba17f1927e79760d77e380eb98d73e40cd61392d9cbf4305180324db2d1d
```
