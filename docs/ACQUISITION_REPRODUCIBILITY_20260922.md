# Acquisition Reproducibility Audit

## Scope

CPU-only analysis of the retained `matched-target-handoff-20260922-r1` pair.
No GPU restart, simulator steps, inference, paid API calls or runtime changes.
The new `experiments.behavior.acquisition_audit` command validates content hashes,
observation bindings, complete acquisition prefixes, protocol equality and
matching policy-call receipts before comparing evidence.

## Findings

The earliest observed mismatch is **RGB at sequence 0**, before any policy action
or classical intervention. All three initial depth maps have identical values,
identical validity masks and 100% jointly valid pixels. Initial proprioception
and the adapter's projected policy state are also exactly equal.

| Initial camera | Mean absolute RGB difference, 0-255 | Pixels with any changed channel |
| --- | ---: | ---: |
| Head | 2.145 | 92.51% |
| Left wrist | 1.396 | 82.94% |
| Right wrist | 1.639 | 85.70% |

Changed-pixel fraction is not the fraction of materially changed scene content.
Most differences are small. The two initial head images look like the same scene
and viewpoint on manual inspection. Exact depth equality supports that reading,
but neither image inspection nor depth/proprioception proves equal hidden state.

A separate CPU check using the pinned upstream `resize_with_pad` implementation
at 224x224 still measured RGB mean absolute differences of 1.837 (head), 1.319
(left wrist), and 1.532 (right wrist). Resizing does not erase the discrepancy.
These are pixel differences, not model-embedding or decision-sensitivity scores.

| First observed difference | Native sequence |
| --- | ---: |
| RGB inputs | 0 |
| Action chunk | 0 |
| Proprioception | 32 |
| Projected policy state | 32 |

The first action chunk's maximum absolute difference is 0.005186; its RMS
difference is 0.001173. At the next boundary, proprioception differs by up to
0.01635 and projected state by up to 0.003360. These aggregates mix native units;
the machine-readable audit also reports action differences per dimension.

Every acquisition request has one matching server receipt with the expected
instruction, action shape and reset-relative noise index. Both conditions use
indices 0, 32, ..., 736. No missing, duplicate or differently indexed acquisition
call was found.

## Source Inspection

The local upstream checkout matches pinned Behavior-Skill commit
`7ca6eace02aaba2d8ce19af600b85dd04a60d720`.

- The adapter supplies explicit diffusion noise keyed by reset-relative sequence.
- Upstream `Policy.infer` advances an internal JAX random key on each request.
- In the inspected `Pi0.sample_actions`, that key supplies noise only when no
  explicit noise is provided. This adapter supplies noise.
- Inference preprocessing uses `train=False`, disabling its random augmentations.

Therefore advancing that internal key is not, by itself, evidence of the bug.
There is no justification yet for changing policy resets or preprocessing.
Logged indices and source inspection do not establish GPU numerical determinism.

## Interpretation

**The pair did not receive identical initial visual inputs.** Appearance/render
variation is a plausible contributor to the small initial action difference and
subsequent closed-loop divergence. The saved traces cannot establish that it is
the sole cause, or rule out numerical and simulator variation.

The classical intervention cannot explain the already-divergent acquisition.
The completed pair remains useful for operational handoff evidence, not as a
causal performance comparison. This does not show that Behavior-Skill is broken
or that deterministic rendering is necessary for all future evaluation.

## Smallest Next GPU Check

After the user restarts the instance:

1. Start only the pinned policy backend, not BEHAVIOR. Replay the saved initial
   input packets in order A, A, B, A, B: five inferences, no robot actions.
   Reset before each call so each uses relative noise index zero. Preserve exact
   RGB, state, instruction and preprocessing; retain outputs and source hashes.
2. Compare repeated identical-packet outputs separately from A-versus-B outputs.
   Report absolute/per-dimension differences rather than inventing a passing
   tolerance after inspecting the results. Separate cold compilation latency.
3. If identical packets reproduce while A/B packets differ, visual sensitivity
   is supported for those packets. It still does not explain every later action.
   If identical packets differ, investigate runtime reproducibility first.
4. Only then decide whether another native reset diagnostic is worth its cost.
   Rendering-only recaptures must verify unchanged sim time and proprioception;
   do not introduce uncounted physics warmup or oracle scene restoration.
5. For a practical intervention comparison, predeclare a small balanced-order
   repeated A/B design and report handoff-state distributions. Do not demand
   bitwise-identical natural rollouts indefinitely, select favorable starts,
   silently substitute A's actions into B, or claim one pair proves benefit.

Strict clearance and moving-localization gates remain unchanged. A longer drive
or equal-total-action experiment is not authorized by this offline report.

## Reproduction And Verification

```bash
python -m experiments.behavior.acquisition_audit /path/to/private/run \
  --output /path/to/new-audit.json
pytest -q tests/test_acquisition_audit.py
```

Output creation refuses overwrite. Input artifacts remain unchanged; no simulator
or policy service is imported or contacted by the audit. The command requires the
pair receipts, policy-call log and referenced RGB/depth evidence. Raw assets remain
private; hashes tie the report to the [matched pair](MATCHED_TARGET_HANDOFF_20260922.md).

The 16 regression tests cover identical pixels with distinct timestamps, first
divergence, state projection, per-dimension action reporting, bad protocol/counts,
invalid actions, missing cameras, bad stamps, ambiguous/noise-mismatched logs,
corrupt content and depth without jointly valid pixels.
