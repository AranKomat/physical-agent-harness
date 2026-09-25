# Phase 14 Model-Duty Comparison

Date: 2026-09-25

## Result

A frozen six-case M2 comparison supports selective GPT-6 Astra review while
retaining GPT-6 Sol as the default executive model.

The comparison combined the completed orange, blue, second-seed, composite
distractor, apple-category, and blue-for-orange negative boundaries. All packets,
images, prompts, schemas, model settings, providers, and existing decisions were
frozen. Four missing Astra responses were collected without robot motion, retry,
or provider fallback.

| Profile | Correct | Calls | Astra calls | Sequential latency | Cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| All Sol | 5/6 | 6 | 0 | 24.971 s | $0.02258675 |
| All Astra | 6/6 | 6 | 6 | 25.416 s | $0.10857125 |
| Selective review | 6/6 | 8 | 2 | 33.473 s | $0.05694175 |

The preregistered selective rule runs Sol first and asks Astra to review only an
M2 `hold` whose decision depends on supplied historical visual identity or
attribute evidence. It triggered on two cases:

- blue evidence with blue required: Sol held; Astra correctly lifted;
- blue evidence with orange required: both correctly held.

Sol and Astra both selected the expected lift on the other four cases. Relative
to all-Astra, selective review preserved the observed `6/6` score while reducing
Astra calls by 66.7% and cost by 47.6%. Relative to all-Sol, it corrected one
decision but used two extra calls, added 8.502 s of sequential latency, and cost
`$0.034355` more.

This makes the deployment direction more concrete: Sol remains the routine model,
and Astra is an escalation candidate for an ambiguous visual-memory hold. It does
not yet authorize Astra review to change robot motion automatically.

## Execution Notes

The original preregistration used a `$0.10` per-call reservation cap. A no-network
preflight established that Astra Flex's published cache-write ceiling raises the
conservative reservation to `$0.12768`; no request or output directory was
created. A revised preregistration set `$0.13` per call and `$0.52` aggregate.

The next preflight created its preflight file but the campaign ledger's explicit
call-ceiling allowlist still ended at 4,187. It stopped before request creation.
The exact 4,191 ceiling was added with a regression check that 4,192 remains
rejected, and the unsent first case used a fresh output ID. Both failed preflights
remain retained.

The four new Astra calls cost `$0.07421625` total. Campaign accounting afterward
is 4,191 cumulative calls, `$23.85374317140` confirmed,
`$34.979327322900` unresolved, `$58.833070494300` exposure, and
`$16.166929505700` available under the retained `$75` ceiling.

## Evidence

- revised preregistration:
  `8e2e20cc7598dde102a6405829fe1f9f82dff21fb8a752a7ba26047aa30e2bcd`;
- final score:
  `a718c54e35d99d5c17ab126ed131fa60687acd84947e67b5d596c0e2a851bb98`;
- new Astra reports, original orange / seed 71 / composite / apple:
  `52d5bbd2bb92f93bad2517f101bcf7aed5c79bf11864dc33d81729412a12a114`,
  `3216202922f026ea51c4c90f4aadc378eaf942269cd182deb44dca34bd42878c`,
  `639ddc599bc3a5dd44e6ac8a7aaeab53df0e65e9d87b56e265bcd1e1d65ec58e`,
  `324692e627ca305b21272a2642e2f2c6b92d050af672ac38bcb64d4d4ed43b1c`;
- retained original `$0.10` preregistration:
  `0740e93f81c30ddd24811d8ff236a2fbafe7bac1dca6c5f75c76f6c3faa20b02`.

## Limits And Next Gate

These are six accumulated controlled M2 boundaries, not independent benchmark
episodes. The rule was preregistered before the four completion calls but after
the two-case blue gate had exposed the only Sol failure. There is one negative
review case, no prospective online routing, and no new physical execution in this
comparison.

Run the rule prospectively in shadow mode on new M2 decisions and record every
trigger, including cases where Sol's hold is correct. Do not grant the reviewer
motion authority until a broader set measures both corrections and false
positives. Neural VLA duty, perception duty, and device energy remain unmeasured
by this executive-only comparison.
