# Phase 9B Native Compiled Stage/Return

## Result

The fixture-domain Phase 9B attempt did not execute robot motion. Three retained
attempts ended before the first action, and the final attempt exposed an
OmniGibson/cuRobo/Warp runtime incompatibility while constructing the frozen
full-scene collision checker.

| Attempt | Actions | Result |
| --- | ---: | --- |
| `r1` | 0/36 | OmniGibson's optional `curobo` dependency was absent |
| `r2` | 0/36 | The launch command supplied the OmniGibson child instead of the BEHAVIOR-1K source root |
| `r3` | 0/36 | Pinned cuRobo loaded, but Isaac Sim's bundled Warp 1.8.2 had no initialized CUDA runtime |

No compiler program was dispatched, no collision result was accepted, and no
stage or return motion occurred. This is a negative infrastructure result, not a
collision rejection, motion qualification, or benchmark result.

## Frozen Scope

The intended run would have exercised one fixture-only native path through:

```text
compile_catalog
-> ActionExecutor
-> one JobManager lease
-> typed native Driver
-> ordinary R1Pro actions
-> independent endpoint verification
```

The frozen path used ten stage commands, eight settling actions, ten return
commands, and eight final settling actions. Five collision samples per segment
produced 102 planned collision samples. All motion, thresholds, stop checks, and
the 36-action cap remained unchanged across amendments. The complete simulator
collision world was explicitly privileged fixture truth and could never qualify
strict BEHAVIOR clearance.

## Setup Corrections

The audited OmniGibson 3.9.2 checkout declares:

```text
warp-lang>=0.9.0,<1.13
nvidia-curobo @ StanfordVL/curobo@78612f45cef52c3fa0298de243a54cd7ca614414
```

The current host therefore received the CUDA 12.8 compiler subset, Warp 1.12.1,
and the exact cuRobo commit. The built geometry extension imported successfully
against PyTorch 2.7.0+cu128. Installer-only dependency drift was normalized back
to the environment's prior versions before the native run.

`r2` also added a focused completion assertion after the evaluator context.
That assertion catches an ordinary suppressed context exception in unit tests,
but did not protect `r3`: OmniGibson's `Evaluator.__exit__()` calls
`og.shutdown()`, which terminated the process before outer error persistence
ran. Consequently, the traceback is retained in the source log while the `r3`
receipt remains an incomplete zero-action receipt without its `error` field.
Future native runners must persist inner exceptions before entering evaluator
shutdown and must not infer success from process exit status alone.

## Evidence

```text
original r1 preregistration
1f153ae380999763ce683686b967d41e83dd923017a3a9bd240f6657fe116c64

r2 dependency/reporting amendment
67ee726f2b8e17e91ae3647bebe608e74cef02f44a4335b2f0b7984e92f60da5

r3 source-root amendment
9bf1ee5aa5e7abf728b341a2af00528bd3adef998d170226b10b3ea27b0ad980

amended runner
40477696c230cac946688be0bdfea2a1e82e0dcbaea76a34b2ab176c1c848bc5

focused regression test
c3b052c9d84e0a091c52521841d89f61d309c82e0d242eab0a360bb0ff5fdc1c

r1 receipt / sidecar
cc672ebf8773120a9d5e70e96703498512a6391853044d37ad45e31012512895
c7608769ab417b2123c26cab81ffcbbe6efba9eafb72ef34533538dfb8e5c3f1

r2 receipt / sidecar / log
f5a31fdbad5dcf8d51fe5b28567a320b18705b1c5f271a6125cbfdd131255363
c7608769ab417b2123c26cab81ffcbbe6efba9eafb72ef34533538dfb8e5c3f1
eef78ce62ecbaa1943d60188d4540810eef9e6257e356795f04ddbac09f9a4fc

r3 receipt / sidecar / log
cc672ebf8773120a9d5e70e96703498512a6391853044d37ad45e31012512895
c7608769ab417b2123c26cab81ffcbbe6efba9eafb72ef34533538dfb8e5c3f1
e97490f57224084451339b4055e590666f9f72eee85a664930549ddd872731fc
```

All receipts, amendments, sidecars, and logs are retained locally. The final
run used zero paid calls and zero robot actions.

## Interpretation

Phase 9A remains complete for proposal-only research. Phase 9B native compiled
execution remains unqualified. Separately, Phase 13 already demonstrated a
scripted exploratory grasp, lift, release, and one-can task-native deposit; that
physical success must not be misreported as Action Compiler execution.

Do not rerun this fixture or bypass the collision checker. A future compiler
experiment requires a separately validated OmniGibson/Warp lifecycle that can
construct the official full-scene cuRobo checker and record errors before
simulator shutdown. Strict BEHAVIOR execution remains blocked independently by
the legal current-clearance problem.
