# Codex exec experiment transport

The deployable model path remains the Responses/Chat `JsonModel`. For bounded,
offline experiments, `CodexExecJsonModel` can instead invoke a locally installed
Codex CLI authenticated with ChatGPT. This consumes the signed-in account's
Codex allowance, not an OpenAI API-key balance. It is not a general Responses
API replacement and does not make computation free.

Use it as the preferred development transport for trace analysis, replay QA,
judging, planning, and sparse simulator-paused executive/verifier calls. The
same adapter satisfies the harness model interface for either role. Keep the API
transport for third-party deployment, experiments specifically testing API or
Flex behavior, benchmark-grade dollar accounting, high concurrency, and
latency-critical control. Never place either remote model transport in a dense
motor loop.

The account owner must run:

```bash
codex login
codex login status
```

Do not copy or share `~/.codex/auth.json`. The adapter removes API-key and access-
token environment variables, requires `Logged in using ChatGPT`, runs every call
ephemerally in an isolated temporary directory with a read-only sandbox, passes
only explicit image files, validates the final JSON against the supplied schema,
and never retries automatically. Its default minimal profile also replaces the
project instruction file with a short model-I/O instruction and disables the
Codex tools and application features that the harness model interface does not
use. `--strict-config` makes a future CLI incompatibility fail visibly.

The journal records the model, role, request hash, image provenance, token usage,
wall time, and ambiguous failures. It records zero API microdollars because no
API tariff is available, with an explicit `chatgpt_subscription` billing route.
That zero must not be interpreted as zero subscription usage or zero compute.

Before adopting this path for a large workload, compare it with the API transport
on a small sequential pilot:

1. Two text-only structured calls.
2. Two calls with three current images.
3. Two calls with seven current/historical images.

Record total wall time, token usage, schema-valid completion rate, failures, and
throttling. Run sequentially first. Codex process and agent-runtime overhead make
this path unsuitable for high-frequency control.

On 2026-09-19, Codex CLI 0.155.1 completed GPT-6 Astra low-effort smoke tests
using ChatGPT authentication:

| Profile/input | Wall time | Input tokens | Output tokens | Result |
|---|---:|---:|---:|---|
| Default Codex, text schema | 5.74 s | 14,515 | 21 | Valid structured output |
| Default Codex, one 480x480 radio frame | 7.93 s | 14,923 | 39 | Valid visual output |
| Tools disabled, text schema | 4.90 s | 11,329 | 15 | Valid structured output |
| Minimal instructions/tools, text schema | 5.46 s | 7,449 | 15 | Valid structured output |
| Minimal instructions/tools, one 480x480 radio frame | 8.68 s | 7,897 | 53 | Valid visual output |

These are transport checks, not quality or load tests. Even the minimal profile
has roughly 7.4k tokens of Codex runtime context, making it inefficient for
trivial micro-calls. Subscription allowance, throttling, and model availability
remain external limits. Codex CLI 0.144.1 was rejected as too old for GPT-6 Astra
in the same environment.

The remaining hidden Codex context cannot be removed through the documented CLI,
SDK, or app-server interfaces. Therefore, do not compare an API result directly
with a Codex result as if only model weights differed. Controlled M0/M1/M2 or
executive/verifier experiments may use this route when every compared condition
uses the same frozen Codex version and minimal profile. Use the Responses API
when the scientific question requires API-equivalent context or service behavior.

The transport intentionally has no deployment-configuration switch yet.
Instantiate it in a private development experiment script so a stored deployment
configuration cannot silently change billing or execution semantics.
